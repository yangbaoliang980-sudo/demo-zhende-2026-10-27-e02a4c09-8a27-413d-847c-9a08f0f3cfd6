"""Transport outbox reference, exercised only by the standalone plugin Mock.

No Anki import, hook, collection access or reward writes. Settled/rejected and
quarantined records are retained; this version provides no deletion API.
"""
from __future__ import annotations
import json
from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3
import stat
import uuid
from .local import private_directory
from .protocol import (ProtocolError, byte_hash, canonical, decode_request,
                       decode_response, digest, request)

class QueueFull(OSError):
    pass


def check_reply(raw_request, reply, pairing):
    msg = decode_request(raw_request)
    reply = decode_response(canonical(reply))
    if (reply['message_id'] != msg['message_id'] or reply['request_sha256'] != byte_hash(raw_request)
            or reply['scope'] != pairing.scope or reply['producer_id'] != pairing.producer_id):
        raise ProtocolError('E_RESPONSE_BINDING')
    expected = (digest(msg['payload']['event']) if msg['message_type'] == 'SUBMIT_EVENT'
                else msg['payload'].get('inbox_id'))
    body = reply['payload']
    if msg['message_type'] != 'HELLO':
        is_transport_reject = body['disposition'] == 'REJECTED' and body['ledger_state'] is None
        if not is_transport_reject and body['inbox_id'] != expected:
            raise ProtocolError('E_RESPONSE_INBOX_BINDING')
    return reply


class Outbox:
    def __init__(self, path, pairing, *, max_rows=1000, max_bytes=16*1024*1024):
        self.path = Path(path).absolute()
        private_directory(self.path.parent)
        if self.path.suffixes[-2:] != ['.p12-outbox', '.sqlite']:
            raise ValueError('EXPLICIT_TRANSPORT_OUTBOX_SUFFIX_REQUIRED')
        if not 1 <= max_rows <= 100000 or not 1024 <= max_bytes <= 1024**3:
            raise ValueError('BOUNDED_QUEUE_LIMITS_REQUIRED')
        if self.path.exists() or self.path.is_symlink():
            s = self.path.lstat()
            if (not stat.S_ISREG(s.st_mode) or s.st_nlink != 1 or
                    s.st_uid != os.getuid() or stat.S_IMODE(s.st_mode) & 0o077):
                raise PermissionError('PRIVATE_REGULAR_OUTBOX_REQUIRED')
        else:
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
            os.close(fd)
        self.pairing, self.max_rows, self.max_bytes = pairing, max_rows, max_bytes
        with self.connect() as c:
            c.execute('CREATE TABLE IF NOT EXISTS binding (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL)')
            expected = digest([pairing.producer_id, pairing.scope])
            c.execute('INSERT OR IGNORE INTO binding VALUES(1, ?)', (expected,))
            if c.execute('SELECT value FROM binding WHERE id=1').fetchone()[0] != expected:
                raise ValueError('OUTBOX_SCOPE_REPAIR_REQUIRES_REVIEW')
            c.execute('''CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY, raw BLOB NOT NULL, raw_sha TEXT NOT NULL,
                inbox_id TEXT UNIQUE NOT NULL, state TEXT NOT NULL, action TEXT NOT NULL,
                attempts INTEGER NOT NULL, due_ms INTEGER NOT NULL, last_error TEXT,
                last_reply TEXT, receipt_store TEXT, receipt_seq INTEGER, receipt_sha TEXT)''')
            c.commit()

    @contextmanager
    def connect(self):
        c = sqlite3.connect(self.path, timeout=2)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA journal_mode=WAL'); c.execute('PRAGMA synchronous=FULL')
        try:
            with c:
                yield c
        finally:
            c.close()

    def enqueue(self, message):
        raw = canonical(message)
        msg = decode_request(raw)
        if (msg['message_type'] != 'SUBMIT_EVENT' or msg['scope'] != self.pairing.scope or
                msg['producer_id'] != self.pairing.producer_id or
                any(msg['payload']['event'][k] != v for k, v in self.pairing.scope.items())):
            raise ValueError('OUTBOX_REQUIRES_PAIRED_SUBMIT')
        inbox = digest(msg['payload']['event'])
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            old = c.execute('SELECT * FROM messages WHERE message_id=?', (msg['message_id'],)).fetchone()
            if old:
                if old['raw_sha'] != byte_hash(raw):
                    raise ValueError('MESSAGE_ID_PAYLOAD_CONFLICT')
                return old['message_id']
            old = c.execute('SELECT message_id FROM messages WHERE inbox_id=?', (inbox,)).fetchone()
            if old:
                return old['message_id']
            count, size = c.execute('SELECT COUNT(*), COALESCE(SUM(length(raw)),0) FROM messages').fetchone()
            if count >= self.max_rows or size + len(raw) > self.max_bytes:
                raise QueueFull('E_LOCAL_OUTBOX_CAPACITY_NO_EVICTION')
            c.execute('INSERT INTO messages VALUES(?,?,?,?,?,?,0,0,NULL,NULL,NULL,NULL,NULL)',
                      (msg['message_id'], raw, byte_hash(raw), inbox, 'QUEUED', 'SUBMIT'))
            c.commit()
        return msg['message_id']

    def get(self, message_id):
        with self.connect() as c:
            row = c.execute('SELECT * FROM messages WHERE message_id=?', (message_id,)).fetchone()
            if row is None:
                raise KeyError(message_id)
            return dict(row)

    def begin_attempt(self, message_id, now_ms):
        if type(now_ms) is not int or not 0 <= now_ms <= 2**53-100000:
            raise ValueError('BOUNDED_MILLISECOND_CLOCK_REQUIRED')
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row = dict(c.execute('SELECT * FROM messages WHERE message_id=?', (message_id,)).fetchone())
            if row['state'] in ('SETTLED', 'HELD_REJECTED') or now_ms < row['due_ms']:
                return None
            if byte_hash(row['raw']) != row['raw_sha']:
                raise ValueError('OUTBOX_BYTES_CORRUPTED_PRESERVE_FOR_REVIEW')
            decode_request(row['raw'])
            if row['attempts'] >= 2**53-1:
                raise ValueError('ATTEMPT_COUNTER_EXHAUSTED_PRESERVE')
            # Commit ambiguity before network I/O. Crash recovery queries, never
            # invents a different source fact, transaction or delivery identity.
            c.execute("UPDATE messages SET state='IN_FLIGHT', action='QUERY', attempts=attempts+1, due_ms=? WHERE message_id=?",
                      (now_ms+10000, message_id))
            c.commit()
            row['attempts'] += 1
            return row

    @staticmethod
    def delay(message_id, attempt, floor=250):
        # Stable bounded jitter; tests need no sleeps. Cap exponent before pow.
        base = min(30000, 250 * 2**min(max(attempt-1, 0), 7))
        jitter = int(digest([message_id, attempt])[:8], 16) % max(1, base//4)
        return min(60000, max(floor, base+jitter))

    def network_failed(self, row, now_ms, code='E_CONNECTION_UNCERTAIN'):
        wait = self.delay(row['message_id'], row['attempts'])
        with self.connect() as c:
            c.execute("UPDATE messages SET state='RETRY_WAIT', action='QUERY', due_ms=?, last_error=? WHERE message_id=? AND attempts=? AND state='IN_FLIGHT'",
                      (now_ms+wait, code, row['message_id'], row['attempts']))
            c.commit()

    def accept(self, row, raw_request, reply, now_ms):
        reply = check_reply(raw_request, reply, self.pairing)
        body, mid = reply['payload'], row['message_id']
        proof = body['receipt']
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            old = dict(c.execute('SELECT * FROM messages WHERE message_id=?', (mid,)).fetchone())
            if old['attempts'] != row['attempts'] or old['state'] != 'IN_FLIGHT':
                return 'STALE_ATTEMPT_IGNORED'
            store, seq, sha = old['receipt_store'], old['receipt_seq'], old['receipt_sha']
            if proof is not None:
                if (store is not None and (store != proof['store_id_sha256'] or seq > proof['sequence'] or
                    (seq == proof['sequence'] and sha != proof['receipt_sha256']))):
                    raise ValueError('STALE_OR_CHANGED_AUTHORITY_PRESERVE_OUTBOX')
                store, seq, sha = proof['store_id_sha256'], proof['sequence'], proof['receipt_sha256']
            disposition = body['disposition']
            if disposition == 'REJECTED':
                state, action, due = 'HELD_REJECTED', 'NONE', now_ms
            elif disposition == 'ACK_APPLIED' or (disposition == 'STATUS' and body['ledger_state']=='REVERTED'):
                state, action, due = 'SETTLED', 'NONE', now_ms
            else:
                state = 'WATCHING_QUARANTINE' if disposition=='ACK_QUARANTINED' else 'RETRY_WAIT'
                action = body['next_action']
                if action not in ('QUERY', 'SUBMIT'):
                    raise ValueError('UNEXPECTED_NONTERMINAL_RESPONSE')
                due = now_ms + self.delay(mid, row['attempts'], body['retry_after_ms'] or 250)
            c.execute('''UPDATE messages SET state=?,action=?,due_ms=?,last_error=?,last_reply=?,
                      receipt_store=?,receipt_seq=?,receipt_sha=? WHERE message_id=?''',
                      (state,action,due,body['error_code'],canonical(reply).decode(),store,seq,sha,mid))
            c.commit()
        return state


class ClientPump:
    """Bounded work invocation; caller schedules later invocations. No busy loop."""
    def __init__(self, outbox, client, *, request_budget=8):
        if type(request_budget) is not int or not 1 <= request_budget <= 64:
            raise ValueError('BOUNDED_REQUEST_BUDGET_REQUIRED')
        self.outbox, self.client, self.budget, self.used = outbox, client, request_budget, 0

    def step(self, message_id, now_ms):
        if self.used >= self.budget:
            return 'BUDGET_EXHAUSTED_DATA_RETAINED'
        row = self.outbox.begin_attempt(message_id, now_ms)
        if row is None:
            return 'NOT_DUE_OR_SETTLED'
        self.used += 1
        raw = row['raw']
        if row['action'] == 'QUERY':
            raw = canonical(request('QUERY_STATUS', {'inbox_id':row['inbox_id']},
                message_id=uuid.uuid4().hex, producer_id=self.outbox.pairing.producer_id,
                scope=self.outbox.pairing.scope))
        try:
            reply = self.client.exchange(raw)
            return self.outbox.accept(row, raw, reply, now_ms)
        except (OSError, ValueError):
            self.outbox.network_failed(row, now_ms)
            return 'RETRY_WAIT'
