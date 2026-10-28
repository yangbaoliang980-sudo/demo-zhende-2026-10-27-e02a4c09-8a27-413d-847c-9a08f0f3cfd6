"""TEST ONLY: durable serializable model of the proposed P21 atomic port.

This is not P21's physical save implementation. It creates only explicitly
marked *.p11-sim.sqlite databases in existing isolated test directories. It must
never be installed in runtime/ or pointed at a game/Anki profile.
"""
from __future__ import annotations

import json
import os
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import sqlite3

from ledger_runtime.types import (CommitReceipt, CommitUnknown, Lookup, PortViolation,
                                  Snapshot, canonical, digest, new_ledger)


class SimulatedCrash(RuntimeError):
    pass


class SQLiteAtomicModel:
    def __init__(self, path, *, fault=None, hard_exit=False):
        self.path = Path(path).resolve()
        if self.path.suffixes[-2:] != ['.p11-sim', '.sqlite']:
            raise ValueError('EXPLICIT_SIMULATION_DATABASE_SUFFIX_REQUIRED')
        if not (self.path.parent / '.P11_SIMULATION_ONLY').is_file():
            raise ValueError('SIMULATION_DIRECTORY_MARKER_REQUIRED')
        self.fault = fault
        self.hard_exit = hard_exit
        self.lookup_unavailable = False
        self.tamper_receipt = False
        self._initialize()

    def connect(self):
        c = sqlite3.connect(str(self.path), timeout=20, isolation_level=None)
        c.execute('PRAGMA journal_mode=WAL')
        c.execute('PRAGMA synchronous=FULL')
        return c

    def _initialize(self):
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            c.execute('CREATE TABLE IF NOT EXISTS state (name TEXT PRIMARY KEY, data TEXT NOT NULL)')
            c.execute('CREATE TABLE IF NOT EXISTS receipts (tx TEXT PRIMARY KEY, request_sha TEXT NOT NULL, receipt TEXT NOT NULL)')
            c.execute('CREATE TABLE IF NOT EXISTS recovery_archives (seq INTEGER PRIMARY KEY, branch TEXT NOT NULL)')
            initial = {'ledger': new_ledger(), 'wallet': {'version': 0, 'balances': {}, 'sources': {}},
                       'meta': {'instance': 'P21_SIMULATOR:' + digest(str(self.path)), 'watermark': 0,
                                'continuity_verified': True, 'continuity_ref': 'fixture:initial-store'}}
            for k, v in initial.items():
                c.execute('INSERT OR IGNORE INTO state VALUES (?, ?)', (k, canonical(v).decode()))
            c.commit()

    @staticmethod
    def _read(c, name):
        return json.loads(c.execute('SELECT data FROM state WHERE name=?', (name,)).fetchone()[0])

    @staticmethod
    def _write(c, name, value):
        c.execute('INSERT OR REPLACE INTO state VALUES (?, ?)', (name, canonical(value).decode()))

    def _snapshot(self, c):
        meta = self._read(c, 'meta')
        return Snapshot(self._read(c, 'ledger'), self._read(c, 'wallet'), meta['continuity_verified'],
                        meta['continuity_ref'], meta['instance'], meta['watermark'])

    def snapshot(self):
        with self.connect() as c:
            c.execute('BEGIN')
            result = self._snapshot(c)
            c.commit()
            return result

    def lookup(self, transaction_id):
        if self.lookup_unavailable:
            return Lookup('UNKNOWN')
        with self.connect() as c:
            row = c.execute('SELECT receipt FROM receipts WHERE tx=?', (transaction_id,)).fetchone()
            if row is None:
                return Lookup('ABSENT')
            data = json.loads(row[0])
            if self.tamper_receipt:
                data['durable'] = False
            return Lookup('COMMITTED', CommitReceipt(**data))

    def _fault(self, name, tx):
        if self.fault != name or not tx.startswith(('process:', 'resolve:')):
            return
        self.fault = None
        if self.hard_exit:
            os._exit(71)  # actual process exit, no user code/cleanup/ACK afterward
        if name == 'after_commit_before_reply':
            self.lookup_unavailable = True
            raise CommitUnknown('INJECTED_REPLY_LOSS_AFTER_COMMIT')
        raise SimulatedCrash('INJECTED_' + name)

    def execute_once(self, transaction_id, request_sha256, decide):
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row = c.execute('SELECT request_sha, receipt FROM receipts WHERE tx=?', (transaction_id,)).fetchone()
            if row:
                if row[0] != request_sha256:
                    raise PortViolation('TRANSACTION_ID_PAYLOAD_CONFLICT')
                c.rollback()
                return CommitReceipt(**json.loads(row[1]))
            snapshot = self._snapshot(c)
            if not snapshot.continuity_verified:
                raise CommitUnknown('P21_SIMULATOR_RESTORE_FENCE_BACKPRESSURE')
            mutation = decide(snapshot)
            wallet = deepcopy(snapshot.wallet)
            self._fault('before_ledger_write', transaction_id)
            self._write(c, 'ledger', mutation.ledger)
            self._fault('after_ledger_before_wallet', transaction_id)
            if mutation.wallet_delta is not None:
                delta = mutation.wallet_delta
                if delta.expected_wallet_version != wallet['version'] or delta.wallet_before_sha256 != digest(wallet):
                    raise PortViolation('P21_SIMULATOR_STALE_WALLET')
                for unit, amount in delta.changes.items():
                    wallet['balances'][unit] = wallet['balances'].get(unit, 0) + amount
                    if wallet['balances'][unit] < 0:
                        raise PortViolation('P21_SIMULATOR_NEGATIVE_WALLET')
                wallet['sources'][delta.family_key] = deepcopy(delta.source_after)
                wallet['version'] += 1
            self._write(c, 'wallet', wallet)
            self._fault('after_wallet_before_commit', transaction_id)
            meta = self._read(c, 'meta')
            meta['watermark'] += 1
            receipt = CommitReceipt(transaction_id, request_sha256, meta['instance'], meta['watermark'],
                                    digest(mutation.ledger), digest(wallet), 'P21_SIMULATOR', True)
            c.execute('INSERT INTO receipts VALUES (?, ?, ?)',
                      (transaction_id, request_sha256, canonical(asdict(receipt)).decode()))
            self._write(c, 'meta', meta)
            self._fault('before_commit', transaction_id)
            c.commit()
            self._fault('after_commit_before_reply', transaction_id)
            return receipt

    def fixture_spend(self, family_key, unit, amount):
        """Synthetic P17 action, not a P11 API; attributed to this exact source."""
        if type(amount) is not int or amount < 0:
            raise ValueError('invalid fixture spend')
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            meta = self._read(c, 'meta')
            if not meta['continuity_verified']:
                raise ValueError('restore fence')
            wallet = self._read(c, 'wallet')
            values = wallet['sources'][family_key]['units'][unit]
            if amount > values['A']:
                raise ValueError('fixture spend exceeds source balance')
            values['S'] += amount
            values['A'] -= amount
            wallet['balances'][unit] -= amount
            wallet['version'] += 1
            self._write(c, 'wallet', wallet)
            meta['watermark'] += 1
            self._write(c, 'meta', meta)
            c.commit()

    def fixture_other_source_credit(self, unit, amount):
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            wallet = self._read(c, 'wallet')
            wallet['balances'][unit] = wallet['balances'].get(unit, 0) + amount
            wallet['version'] += 1
            self._write(c, 'wallet', wallet)
            meta = self._read(c, 'meta'); meta['watermark'] += 1
            self._write(c, 'meta', meta)
            c.commit()

    def fixture_hide_attribution(self, family_key):
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            wallet = self._read(c, 'wallet')
            wallet['sources'][family_key]['attribution_known'] = False
            wallet['version'] += 1
            self._write(c, 'wallet', wallet)
            c.commit()

    def checkpoint(self):
        s = self.snapshot()
        return {'store_instance': s.store_instance, 'high_watermark': s.high_watermark,
                'ledger_sha256': digest(s.ledger), 'wallet_sha256': digest(s.wallet),
                'evidence_scope': 'P21_SIMULATOR_INDEPENDENT_TEST_CHECKPOINT'}

    def fixture_restore_old_backup(self, old_snapshot):
        """Simulate P21-observed restore. Keep an independent authoritative copy.

        When fenced, all new writes are backpressured with NO ACK. The sender must
        retain them. No claim is made about undetectable full-disk rollback.
        """
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            current = self._snapshot(c)
            if not current.continuity_verified:
                raise ValueError('nested restore blocked')
            self._write(c, 'fixture_recovery_authority', {'ledger': current.ledger, 'wallet': current.wallet})
            self._write(c, 'ledger', old_snapshot.ledger)
            self._write(c, 'wallet', old_snapshot.wallet)
            meta = self._read(c, 'meta')
            meta['continuity_verified'], meta['continuity_ref'] = False, None
            self._write(c, 'meta', meta)
            c.commit()

    def fixture_p21_restore_authoritative_copy(self):
        """Test stand-in for P21 repair; P11 cannot call it through AtomicStore."""
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            branch = {'ledger': self._read(c, 'ledger'), 'wallet': self._read(c, 'wallet')}
            c.execute('INSERT INTO recovery_archives(branch) VALUES (?)', (canonical(branch).decode(),))
            authority = self._read(c, 'fixture_recovery_authority')
            self._write(c, 'ledger', authority['ledger'])
            self._write(c, 'wallet', authority['wallet'])
            meta = self._read(c, 'meta')
            meta['continuity_verified'] = True
            meta['continuity_ref'] = 'fixture:P21-authoritative-copy:' + digest(authority)
            self._write(c, 'meta', meta)
            c.commit()

    def export_receipts(self):
        with self.connect() as c:
            return [json.loads(row[0]) for row in c.execute('SELECT receipt FROM receipts ORDER BY rowid')]
