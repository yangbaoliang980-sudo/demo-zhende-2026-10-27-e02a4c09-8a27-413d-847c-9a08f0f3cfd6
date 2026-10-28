from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

from ledger_runtime import StudyLedger
from ledger_runtime.audit import check_accounting, verify_audit
from ledger_runtime.types import (Event, LedgerStatus as S, PortViolation, WalletHold,
                                  canonical, digest, MAX_INPUT_BYTES)
from tests.support.simulated_ports import (FixtureEvidence, FixturePolicy, FixtureWallet,
                                          UNIT, Q, event, control)
from tests.support.sqlite_atomic_model import SQLiteAtomicModel, SimulatedCrash

ROOT = Path(__file__).resolve().parents[1]


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='p11-ledger-')
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        (self.directory/'.P11_SIMULATION_ONLY').write_text('TEST ONLY\n')
        self.db = self.directory/'ledger.p11-sim.sqlite'
        self.store = SQLiteAtomicModel(self.db)
        self.evidence, self.policy, self.wallet = FixtureEvidence(), FixturePolicy(), FixtureWallet()
        self.service = StudyLedger(self.store, self.wallet, self.evidence, self.policy)
        self.review = event()
        self.undo = control('UNDO', 'undo-1', 'review-1', 1)
        self.restore = control('RESTORE', 'restore-1', 'undo-1', 2)

    def run_event(self, value):
        return self.service.handle(canonical(value))

    def balance(self):
        return self.store.snapshot().wallet['balances'].get(UNIT, 0)

    def family_key(self, value=None):
        return Event.parse(canonical(value or self.review)).family_key

    def counters(self):
        return self.store.snapshot().wallet['sources'][self.family_key()]['units'][UNIT]

    def grant(self, outcome, ref='fixture:new-proof', action='REPROCESS', target=None):
        row = self.store.snapshot().ledger['inbox'][outcome.inbox_id]
        self.evidence.grant(row, ref, action, target)
        return self.service.resolve(outcome.inbox_id, ref, action)

    def test_receive_is_durable_without_award(self):
        result = self.service.receive(canonical(self.review))
        self.assertEqual(result.ack, 'ACK_RECEIVED')
        self.assertEqual(self.balance(), 0)
        reopened = StudyLedger(SQLiteAtomicModel(self.db), self.wallet, self.evidence, self.policy)
        result = reopened.process(result.inbox_id)
        self.assertEqual(result.ack, 'ACK_APPLIED')
        self.assertEqual(result.receipt.origin, 'P21_SIMULATOR')
        self.assertEqual(self.balance(), Q)

    def test_one_thousand_duplicate_deliveries_authorize_once(self):
        first = self.run_event(self.review)
        for _ in range(999):
            result = self.run_event(self.review)
            self.assertEqual(result.receipt, first.receipt)
            self.assertEqual(result.ack, 'ACK_APPLIED')
        snap = self.store.snapshot()
        self.assertEqual(self.balance(), Q)
        self.assertEqual(len(snap.ledger['operations']), 1)
        self.assertEqual(len(snap.ledger['audit']), 2)
        self.assertEqual(self.wallet.calls, 1)
        self.assertEqual(self.policy.calls, 1)

    def test_serializable_concurrent_duplicates(self):
        raw = canonical(self.review)
        def work(_):
            store = SQLiteAtomicModel(self.db)
            return StudyLedger(store, FixtureWallet(), FixtureEvidence(), FixturePolicy()).handle(raw)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(work, range(64)))
        self.assertTrue(all(x.ack == 'ACK_APPLIED' for x in results))
        self.assertEqual(len({x.receipt.transaction_id for x in results}), 1)
        self.assertEqual(self.balance(), Q)
        self.assertEqual(len(self.store.snapshot().ledger['operations']), 1)

    def test_independent_event_on_same_card_is_not_deduplicated(self):
        self.run_event(self.review)
        self.run_event(event('review-2', family_id='family-2', card=self.review['card_reference']))
        self.assertEqual(self.balance(), 2*Q)

    def test_four_ratings_do_not_create_engine_owned_amounts(self):
        for i, rating in enumerate(('Again','Hard','Good','Easy')):
            result = self.run_event(event('review-'+str(i), family_id='family-'+str(i), rating=rating))
            self.assertEqual(result.state, S.APPLIED)
        self.assertEqual(self.balance(), 4*Q)
        # The injected policy supplies Q; core contains no per-rating reward table.

    def test_same_identity_different_payload_quarantines_only_conflict(self):
        original = self.run_event(self.review)
        conflict = self.run_event({**self.review, 'rating': 'Easy'})
        self.assertEqual(conflict.state, S.QUARANTINED)
        self.assertEqual(self.balance(), Q)
        self.assertEqual(self.service.query(original.inbox_id).state, S.APPLIED)
        row = self.store.snapshot().ledger['inbox'][conflict.inbox_id]
        self.assertEqual(row['conflict_with'], original.inbox_id)
        self.assertNotEqual(row['raw_sha256'], self.store.snapshot().ledger['inbox'][original.inbox_id]['raw_sha256'])

    def test_same_family_cannot_be_awarded_as_another_review(self):
        self.run_event(self.review)
        result = self.run_event(event('another-review', family_id='family-1'))
        self.assertEqual(result.state, S.QUARANTINED)
        self.assertEqual(self.balance(), Q)

    def test_policy_mapping_day_change_cannot_reaward_duplicate(self):
        first = self.run_event(self.review)
        self.policy.version = 'fixture:new-policy'
        self.policy.category = 'NOUN'
        self.policy.reward_day = 'fixture:tomorrow'
        self.policy.entitlement = {UNIT: 999}
        self.policy.available = False
        result = self.run_event(self.review)
        self.assertEqual(result.receipt, first.receipt)
        self.assertEqual(self.balance(), Q)
        self.assertEqual(self.policy.calls, 1)

    def test_default_closed_gate_quarantines_all_four_buttons(self):
        service = StudyLedger(self.store, self.wallet)
        for i, rating in enumerate(('Again','Hard','Good','Easy')):
            result = service.handle(canonical(event(str(i), family_id=str(i), rating=rating)))
            self.assertEqual(result.state, S.QUARANTINED)
            self.assertEqual(result.ack, 'ACK_QUARANTINED')
        self.assertEqual(self.balance(), 0)
        self.assertEqual(self.wallet.calls, 0)

    def test_real_source_cannot_use_fixture_evidence(self):
        result = self.run_event(event(source='anki:real-source'))
        self.assertEqual(result.state, S.QUARANTINED)
        self.assertEqual(self.balance(), 0)

    def test_missing_identity_is_quarantined(self):
        result = self.run_event(event(None, family_id=None))
        self.assertEqual(result.state, S.QUARANTINED)
        self.assertEqual(self.balance(), 0)

    def test_missing_mapping_is_not_unknown(self):
        self.policy.mapping_available = False
        result = self.run_event(self.review)
        self.assertEqual(result.state, S.QUARANTINED)
        self.assertEqual(self.balance(), 0)

    def test_approved_fixture_unknown_category_has_single_general_branch(self):
        self.policy.category = 'UNKNOWN'
        self.assertEqual(self.run_event(self.review).state, S.APPLIED)
        self.assertEqual(self.balance(), Q)

    def test_persistent_quarantine_requires_new_bound_evidence(self):
        self.policy.available = False
        first = self.run_event(self.review)
        self.assertEqual(first.state, S.QUARANTINED)
        self.policy.available = True
        self.service = StudyLedger(SQLiteAtomicModel(self.db), self.wallet, self.evidence, self.policy)
        self.assertEqual(self.run_event(self.review).state, S.QUARANTINED)
        denied = self.service.resolve(first.inbox_id, 'invented-admin-proof')
        self.assertIsNone(denied.ack)
        self.assertEqual(self.balance(), 0)
        promoted = self.grant(first)
        self.assertEqual(promoted.state, S.APPLIED)
        self.assertEqual(self.balance(), Q)
        repeated = self.service.resolve(first.inbox_id, 'fixture:new-proof')
        self.assertEqual(repeated.state, S.APPLIED)
        self.assertEqual(self.balance(), Q)
        history = self.store.snapshot().ledger['inbox'][first.inbox_id]['history']
        self.assertEqual([x['to'] for x in history], [S.QUARANTINED, S.APPLIED])
        self.assertTrue(any(x['action']=='RESOLUTION_EVIDENCE_ATTACHED' for x in self.store.snapshot().ledger['audit']))

    def test_resolution_cannot_apply_to_another_input(self):
        self.policy.available = False
        a = self.run_event(self.review)
        b = self.run_event(event('review-2', family_id='family-2'))
        row = self.store.snapshot().ledger['inbox'][a.inbox_id]
        self.evidence.grant(row, 'fixture:proof-for-A')
        self.policy.available = True
        result = self.service.resolve(b.inbox_id, 'fixture:proof-for-A')
        self.assertIsNone(result.ack)
        self.assertEqual(self.balance(), 0)

    def test_undo_unspent_and_replay_original_remain_reverted(self):
        original = self.run_event(self.review)
        undone = self.run_event(self.undo)
        self.assertEqual(undone.ack, 'ACK_REVERTED')
        self.assertEqual(self.balance(), 0)
        duplicate_original = self.run_event(self.review)
        self.assertEqual(duplicate_original.ack, 'ACK_REVERTED')
        self.assertEqual(duplicate_original.receipt, undone.receipt)
        self.assertEqual(self.balance(), 0)
        self.assertEqual(self.counters(), {'G':Q,'R':Q,'S':0,'A':0,'T':0,'U':0,'K':0,'M':0})

    def test_undo_before_original_creates_durable_tombstone(self):
        self.assertEqual(self.run_event(self.undo).state, S.REVERTED)
        self.service = StudyLedger(SQLiteAtomicModel(self.db), self.wallet, self.evidence, self.policy)
        result = self.run_event(self.review)
        self.assertEqual(result.state, S.REVERTED)
        self.assertEqual(self.wallet.calls, 0)
        self.assertEqual(self.policy.calls, 0)
        self.assertEqual(self.balance(), 0)

    def test_repeated_undo_cannot_double_debit(self):
        self.run_event(self.review)
        self.run_event(self.undo)
        for _ in range(20):
            self.run_event(self.undo)
        extra = control('UNDO','different-undo-id','review-1',1)
        self.assertEqual(self.run_event(extra).state, S.QUARANTINED)
        self.assertEqual(self.counters()['R'], Q)
        self.assertEqual(self.balance(), 0)

    def test_restore_uses_original_policy_and_only_missing_amount(self):
        self.run_event(self.review)
        self.run_event(self.undo)
        self.policy.version = 'fixture:changed-version'
        self.policy.entitlement = {UNIT: 999}
        restored = self.run_event(self.restore)
        self.assertEqual(restored.state, S.APPLIED)
        self.assertEqual(self.balance(), Q)
        for _ in range(10):
            self.run_event(self.restore)
        self.assertEqual(self.balance(), Q)
        self.assertEqual(self.counters()['G'], 2*Q)
        self.assertEqual(self.policy.calls, 1)

    def test_spent_seven_undo_three_restore_three_matches_p08_math(self):
        self.run_event(self.review)
        self.store.fixture_spend(self.family_key(), UNIT, 7)
        undone = self.run_event(self.undo)
        self.assertEqual(undone.state, S.PENDING_RECONCILIATION)
        self.assertEqual(self.counters(), {'G':10,'R':3,'S':7,'A':0,'T':0,'U':7,'K':0,'M':0})
        self.assertEqual(self.balance(), 0)
        self.assertEqual(self.run_event(self.restore).state, S.APPLIED)
        self.assertEqual(self.balance(), 3)
        self.assertEqual(self.counters(), {'G':13,'R':3,'S':7,'A':3,'T':10,'U':0,'K':0,'M':0})
        self.run_event(control('UNDO','undo-2','restore-1',3))
        self.assertEqual(self.counters(), {'G':13,'R':6,'S':7,'A':0,'T':0,'U':7,'K':0,'M':0})

    def test_no_reclaim_policy_records_exposure_without_debit(self):
        self.policy.reclaim = False
        self.run_event(self.review)
        self.store.fixture_spend(self.family_key(), UNIT, 7)
        result = self.run_event(self.undo)
        self.assertEqual(result.state, S.PENDING_RECONCILIATION)
        self.assertEqual(self.balance(), 3)
        self.assertEqual(self.counters(), {'G':10,'R':0,'S':7,'A':3,'T':0,'U':10,'K':0,'M':0})
        self.run_event(self.restore)
        self.assertEqual(self.balance(), 3)

    def test_other_source_funds_are_never_reclaimed(self):
        self.run_event(self.review)
        self.store.fixture_other_source_credit(UNIT, 100)
        self.store.fixture_spend(self.family_key(), UNIT, 7)
        self.run_event(self.undo)
        self.assertEqual(self.balance(), 100)
        self.assertEqual(self.counters()['U'], 7)

    def test_unknown_attribution_does_not_use_total_balance(self):
        self.run_event(self.review)
        self.store.fixture_hide_attribution(self.family_key())
        result = self.run_event(self.undo)
        self.assertEqual(result.state, S.PENDING_RECONCILIATION)
        self.assertEqual(result.reason, 'SOURCE_SPEND_ATTRIBUTION_UNKNOWN')
        self.assertEqual(self.balance(), Q)

    def test_control_is_processed_when_new_policy_unavailable(self):
        self.run_event(self.review)
        self.policy.available = False
        self.assertEqual(self.run_event(self.undo).state, S.REVERTED)
        self.assertEqual(self.balance(), 0)

    def test_missing_predecessor_is_persistent_and_recoverable(self):
        self.run_event(self.review)
        waiting = self.run_event(self.restore)
        self.assertEqual(waiting.state, S.PENDING_RECONCILIATION)
        self.assertEqual(self.balance(), Q)
        self.run_event(self.undo)
        self.assertEqual(self.balance(), 0)
        result = self.grant(waiting, 'fixture:predecessor-commit-proof')
        self.assertEqual(result.state, S.APPLIED)
        self.assertEqual(self.balance(), Q)

    def test_cross_epoch_replay_is_quarantined_then_linked_without_award(self):
        original = self.run_event(self.review)
        incoming = self.run_event(event('epoch2-review', epoch='fixture:epoch-2'))
        self.assertEqual(incoming.state, S.QUARANTINED)
        self.assertEqual(self.balance(), Q)
        result = self.grant(incoming, 'fixture:verified-alias', 'LINK_DUPLICATE', original.inbox_id)
        self.assertEqual(result.state, S.APPLIED)
        self.assertEqual(self.balance(), Q)
        self.assertEqual(len(self.store.snapshot().ledger['operations']), 1)

    def test_invalid_wallet_candidate_is_not_committed(self):
        actual = self.wallet.compute
        def corrupt(intent, snapshot):
            delta = actual(intent, snapshot)
            return replace(delta, changes={UNIT:1000})
        self.wallet.compute = corrupt
        result = self.run_event(self.review)
        self.assertEqual(result.state, S.PENDING_RECONCILIATION)
        self.assertEqual(self.balance(), 0)
        self.assertEqual(len(self.store.snapshot().ledger['operations']), 0)

    def test_stale_wallet_delta_binding_is_rejected(self):
        actual = self.wallet.compute
        self.wallet.compute = lambda intent, snapshot: replace(actual(intent,snapshot), expected_wallet_version=55)
        result = self.run_event(self.review)
        self.assertEqual(result.state, S.PENDING_RECONCILIATION)
        self.assertEqual(self.balance(), 0)

    def test_atomic_failure_rolls_back_both_wallet_and_ledger(self):
        self.store.fault = 'after_ledger_before_wallet'
        with self.assertRaises(SimulatedCrash):
            self.run_event(self.review)
        snap = self.store.snapshot()
        self.assertEqual(self.balance(), 0)
        self.assertEqual(snap.ledger['operations'], {})
        self.assertEqual(next(iter(snap.ledger['inbox'].values()))['state'], S.PENDING_RECONCILIATION)
        self.assertEqual(self.run_event(self.review).state, S.APPLIED)
        self.assertEqual(self.balance(), Q)

    def test_lost_commit_response_never_acknowledges_without_lookup(self):
        self.store.fault = 'after_commit_before_reply'
        result = self.run_event(self.review)
        self.assertIsNone(result.ack)
        self.assertEqual(self.balance(), Q)
        self.store.lookup_unavailable = False
        result = self.run_event(self.review)
        self.assertEqual(result.ack, 'ACK_APPLIED')
        self.assertEqual(self.balance(), Q)
        self.assertEqual(self.wallet.calls, 1)

    def test_bad_receipt_cannot_emit_ack_applied(self):
        self.run_event(self.review)
        self.store.tamper_receipt = True
        result = self.run_event(self.review)
        self.assertIsNone(result.ack)
        self.assertEqual(self.balance(), Q)

    def test_receipt_lookup_unavailable_before_receive_is_backpressure(self):
        self.store.lookup_unavailable = True
        result = self.run_event(self.review)
        self.assertIsNone(result.ack)
        self.assertEqual(self.store.snapshot().ledger['inbox'], {})
        self.assertEqual(self.balance(), 0)

    def test_old_backup_requires_p21_reconciliation_before_replay(self):
        old = self.store.snapshot()
        self.run_event(self.review)
        checkpoint = self.store.checkpoint()
        self.store.fixture_restore_old_backup(old)
        report = self.service.reconcile(checkpoint)
        self.assertEqual(report['state'], S.PENDING_RECONCILIATION)
        self.assertIn('CHECKPOINT_LEDGER_MISMATCH', report['issues'])
        replay = self.run_event(self.review)
        self.assertIsNone(replay.ack)
        new = self.run_event(event('new-during-restore', family_id='new-during-restore'))
        self.assertIsNone(new.ack)
        self.assertEqual(self.balance(), 0)
        self.store.fixture_p21_restore_authoritative_copy()
        self.assertEqual(self.balance(), Q)
        self.assertEqual(self.run_event(self.review).state, S.APPLIED)
        self.assertEqual(self.balance(), Q)
        self.assertEqual(self.service.reconcile(checkpoint)['state'], 'CONSISTENT_SNAPSHOT')

    def test_no_checkpoint_is_not_proof_of_fresh_store(self):
        report = self.service.reconcile(None)
        self.assertEqual(report['state'], S.PENDING_RECONCILIATION)
        self.assertEqual(report['wallet_mutations'], 0)

    def test_case_index_and_append_only_audit_survive_restart(self):
        self.policy.available = False
        a = self.run_event(self.review)
        self.run_event(event('second',family_id='second'))
        service = StudyLedger(SQLiteAtomicModel(self.db), self.wallet, self.evidence, self.policy)
        self.assertEqual(len(service.pending_cases()), 2)
        before = deepcopy(self.store.snapshot().ledger['audit'])
        self.policy.available = True
        self.grant(a)
        after = self.store.snapshot().ledger
        self.assertEqual(after['audit'][:len(before)], before)
        verify_audit(after)
        damaged = deepcopy(after)
        damaged['audit'][0]['details']['reason'] = 'tampered'
        with self.assertRaises(PortViolation):
            verify_audit(damaged)

    def test_invalid_json_duplicate_keys_and_boolean_revision_are_rejected(self):
        cases = [b'{"schema_version":"x","schema_version":"y"}', b'{bad json',
                 canonical({**self.review,'revision':True}), canonical({**self.review,'trusted':True}),
                 canonical({**self.review,'rating':1}), b'{"a":NaN}', b'\xff']
        for raw in cases:
            with self.subTest(raw_sha=digest(list(raw))):
                result = self.service.handle(raw)
                self.assertEqual(result.state, S.REJECTED)
                self.assertEqual(result.ack, 'ACK_REJECTED')
        self.assertEqual(self.balance(), 0)

    def test_oversize_input_gets_no_durable_ack(self):
        result = self.service.handle(b'x'*(MAX_INPUT_BYTES+1))
        self.assertIsNone(result.ack)
        self.assertIsNone(result.inbox_id)

    def test_json_formatting_does_not_reset_identity(self):
        first = self.run_event(self.review)
        second = self.service.handle(json.dumps(self.review,indent=4).encode())
        self.assertEqual(first.inbox_id, second.inbox_id)
        self.assertEqual(self.balance(), Q)

    def test_real_p10_marker_remains_zero_samples_and_is_not_event(self):
        raw = (ROOT/'sources/P10/QUARANTINED.json').read_bytes()
        marker = json.loads(raw)
        self.assertEqual(marker['real_review_sample_count'], 0)
        self.assertFalse(marker['production_award_authorized'])
        self.assertEqual(self.service.handle(raw).state, S.REJECTED)
        self.assertEqual(self.balance(), 0)

    def test_randomized_valid_histories_and_retransmissions_preserve_net(self):
        # Deterministic independent oracle: each family supports Q or 0; spent
        # units are never reclaimed and duplicates never change the oracle.
        for seed in range(8):
            rng = random.Random(seed)
            fam, head = 'random-family-'+str(seed), 'random-review-'+str(seed)
            value = event(head, family_id=fam)
            history = [value]
            self.run_event(value)
            active, revision, spent = True, 0, 0
            for step in range(60):
                if rng.random() < .65:
                    self.run_event(rng.choice(history))
                else:
                    revision += 1
                    kind = 'UNDO' if active else 'RESTORE'
                    new_head = 'random-control-'+str(seed)+'-'+str(revision)
                    value = control(kind,new_head,head,revision,fam)
                    self.run_event(value)
                    active, head = not active, new_head
                    history.append(value)
                units = self.store.snapshot().wallet['sources'][self.family_key(history[0])]['units'][UNIT]
                self.assertEqual(units['G']-units['R'], Q if active else spent)
                check_accounting(units)
        verify_audit(self.store.snapshot().ledger)

    def test_wallet_port_cannot_mutate_frozen_policy_through_nested_dict(self):
        actual = self.wallet.compute
        def corrupt(intent, snapshot):
            intent.policy_snapshot['entitlement'][UNIT] = 999
            return actual(intent, snapshot)
        self.wallet.compute = corrupt
        result = self.run_event(self.review)
        self.assertEqual(self.balance(), 0)
        self.assertEqual(result.state, S.PENDING_RECONCILIATION)

    def test_wallet_delta_cannot_hide_offsetting_credit_and_reclaim(self):
        actual = self.wallet.compute
        def corrupt(intent, snapshot):
            delta = actual(intent, snapshot)
            delta.source_after['units'][UNIT]['G'] += 5
            delta.source_after['units'][UNIT]['R'] += 5
            return delta
        self.wallet.compute = corrupt
        result = self.run_event(self.review)
        self.assertEqual(result.state, S.PENDING_RECONCILIATION)
        self.assertEqual(self.balance(), 0)

    def test_duplicate_link_cannot_cross_beneficiary_scope(self):
        target = self.run_event(event('other-review',family_id='other-family',beneficiary='fixture:other-player'))
        self.policy.available = False
        held = self.run_event(self.review)
        result = self.grant(held,'fixture:wrong-scope-proof','LINK_DUPLICATE',target.inbox_id)
        self.assertIsNone(result.ack)
        self.assertEqual(self.balance(), Q)

    def test_reject_case_is_observable_and_not_reopened_by_restore(self):
        self.policy.available = False
        held = self.run_event(self.review)
        rejected = self.grant(held,'fixture:ineligible-fact','REJECT')
        self.assertEqual(rejected.state,S.REJECTED)
        self.policy.available = True
        self.run_event(self.undo)
        self.run_event(self.restore)
        self.assertEqual(self.balance(),0)

    def test_missing_identity_reason_does_not_claim_sufficient_evidence(self):
        held = self.run_event(event(None,family_id=None))
        self.assertEqual(held.reason,'MISSING_PROVEN_IDENTITY_FIELDS')


class ProcessCrashTests(LedgerTests):
    # Only the generated crash methods below are loaded by the evidence runner.
    def run_crash_case(self, point):
        proc = subprocess.run([sys.executable,'-B','-m','tests.crash_worker',str(self.db),point],
                              cwd=ROOT, capture_output=True, text=True, timeout=20)
        self.assertEqual(proc.returncode,71,proc.stderr)
        self.assertEqual(proc.stdout,'')
        before = self.store.snapshot()
        committed_before_ack = point == 'after_commit_before_reply'
        self.assertEqual(before.wallet['balances'].get(UNIT,0), Q if committed_before_ack else 0)
        result = self.run_event(self.review)
        self.assertEqual(result.ack,'ACK_APPLIED')
        self.assertEqual(self.balance(),Q)
        self.assertEqual(len(self.store.snapshot().ledger['operations']),1)
        print(json.dumps({'observation':'ACTUAL_SUBPROCESS_EXIT_AND_REOPEN','fault':point,
                          'child_exit_code':proc.returncode,'child_stdout':proc.stdout,
                          'balance_before_replay':before.wallet['balances'].get(UNIT,0),
                          'balance_after_replay':self.balance(),'scope':'P21_SIMULATOR'},sort_keys=True))


for _point in ('after_receive_commit','before_ledger_write','after_ledger_before_wallet',
               'after_wallet_before_commit','before_commit','after_commit_before_reply'):
    def _test(self, point=_point):
        self.run_crash_case(point)
    setattr(ProcessCrashTests, 'test_crash_'+_point, _test)


def load_tests(loader, tests, pattern):
    suite = unittest.TestSuite(loader.loadTestsFromTestCase(LedgerTests))
    for name in sorted(x for x in dir(ProcessCrashTests) if x.startswith('test_crash_')):
        suite.addTest(ProcessCrashTests(name))
    return suite
