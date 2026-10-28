"""Executed P12 author contracts with original P11 + synthetic P21. Not real Anki."""
import copy
from dataclasses import replace
import unittest
from mocks.anki_transport.support import Harness, submit, query, event, control, Q, UNIT, SCOPE
from runtime.anki.transport.ipc_server_client.protocol import canonical, digest
from runtime.anki.transport.ipc_server_client.bridge import P11Bridge

class AckReplayTests(unittest.TestCase):
    def test_apply_requires_durable_receipt(self):
        with Harness() as h:
            r=h.send(submit())['payload'];self.assertEqual(r['disposition'],'ACK_APPLIED')
            self.assertEqual(r['receipt']['origin'],'P21_SIMULATOR');self.assertEqual(h.balance,Q)
            self.assertEqual(r['evidence_scope'],'ISOLATED_P11_P21_SIMULATION')

    def test_exact_replay_and_new_delivery_id_do_not_reaward(self):
        with Harness() as h:
            m=submit();first=h.send(m);version=h.store.snapshot().wallet['version']
            for next_message in [m,submit(),submit()]:
                self.assertEqual(h.send(next_message)['payload']['receipt'],first['payload']['receipt'])
            self.assertEqual(h.balance,Q);self.assertEqual(h.store.snapshot().wallet['version'],version)

    def test_identity_conflict_preserves_original_award(self):
        with Harness() as h:
            h.send(submit());changed=event(rating='Easy');r=h.send(submit(changed))['payload']
            self.assertEqual(r['disposition'],'ACK_QUARANTINED');self.assertEqual(h.balance,Q)
            self.assertEqual(r['detail_code'],'SAME_IDENTITY_DIFFERENT_PAYLOAD')

    def test_default_closed_evidence_quarantines_without_award(self):
        with Harness(closed=True) as h:
            r=h.send(submit())['payload'];self.assertEqual(r['disposition'],'ACK_QUARANTINED')
            self.assertEqual(r['award_status'],'NOT_AWARDED');self.assertFalse(r['delivery_terminal'])
            self.assertEqual(h.balance,0)

    def test_policy_withheld_quarantines(self):
        with Harness() as h:
            h.policy.available=False;r=h.send(submit())['payload']
            self.assertEqual(r['disposition'],'ACK_QUARANTINED');self.assertEqual(h.balance,0)

    def test_quarantine_replay_does_not_release(self):
        with Harness() as h:
            h.evidence.blocked.add('review-1');m=submit();h.send(m);h.evidence.blocked.clear()
            for req in [m,query(),submit()]:self.assertEqual(h.send(req)['payload']['disposition'],'ACK_QUARANTINED')
            self.assertEqual(h.balance,0)

    def test_bound_p11_resolution_is_observed_read_only(self):
        with Harness() as h:
            h.evidence.blocked.add('review-1');r=h.send(submit())['payload'];h.evidence.blocked.clear()
            row=h.store.snapshot().ledger['inbox'][r['inbox_id']]
            h.evidence.grant(row,'fixture:new-evidence')
            h.ledger.resolve(r['inbox_id'],'fixture:new-evidence')
            self.assertEqual(h.send(query())['payload']['disposition'],'ACK_APPLIED');self.assertEqual(h.balance,Q)

    def test_received_only_query_requests_safe_resubmit(self):
        with Harness() as h:
            h.ledger.receive(canonical(event()));r=h.send(query())['payload']
            self.assertEqual(r['disposition'],'RETRY_LATER');self.assertEqual(r['next_action'],'SUBMIT')
            self.assertEqual(h.balance,0);self.assertEqual(h.send(submit())['payload']['disposition'],'ACK_APPLIED')

    def test_unknown_authority_never_acks(self):
        with Harness() as h:
            h.store.lookup_unavailable=True;r=h.send(submit())['payload']
            self.assertEqual(r['disposition'],'RETRY_LATER');self.assertIsNone(r['receipt']);self.assertEqual(h.balance,0)

    def test_commit_then_reply_loss_queries_existing_result(self):
        with Harness(fault='after_commit_before_reply') as h:
            r=h.send(submit())['payload'];self.assertEqual(r['disposition'],'RETRY_LATER');self.assertEqual(h.balance,Q)
            version=h.store.snapshot().wallet['version'];h.store.lookup_unavailable=False
            r=h.send(query())['payload'];self.assertEqual(r['disposition'],'ACK_APPLIED')
            h.send(submit());self.assertEqual(h.store.snapshot().wallet['version'],version)

    def test_failure_before_commit_safe_retry(self):
        with Harness(fault='after_ledger_before_wallet') as h:
            r=h.send(submit())['payload'];self.assertEqual(r['disposition'],'RETRY_LATER');self.assertEqual(h.balance,0)
            self.assertEqual(h.send(submit())['payload']['disposition'],'ACK_APPLIED');self.assertEqual(h.balance,Q)

    def test_tampered_receipt_never_success(self):
        with Harness() as h:
            h.send(submit());h.store.tamper_receipt=True
            self.assertEqual(h.send(query())['payload']['disposition'],'RETRY_LATER')

    def test_foreign_or_unapproved_receipt_origin_fails_closed(self):
        with Harness() as h:
            h.send(submit());lookup=h.store.lookup
            h.store.lookup=lambda tx: replace(lookup(tx),receipt=replace(lookup(tx).receipt,origin='P21_PRODUCTION'))
            self.assertEqual(h.send(query())['payload']['disposition'],'RETRY_LATER')

    def test_receipt_for_different_transaction_rejected(self):
        with Harness() as h:
            h.send(submit());lookup=h.store.lookup
            h.store.lookup=lambda tx: replace(lookup(tx),receipt=replace(lookup(tx).receipt,transaction_id='process:'+'a'*64))
            self.assertEqual(h.send(query())['payload']['disposition'],'RETRY_LATER')

    def test_undo_before_original_is_not_reward_ack(self):
        with Harness() as h:
            undo=control('UNDO','undo-1','review-1',1)
            r=h.send(submit(undo))['payload'];self.assertEqual((r['disposition'],r['ledger_state']),('STATUS','REVERTED'))
            r=h.send(submit())['payload'];self.assertEqual(r['award_status'],'REVERTED');self.assertEqual(h.balance,0)

    def test_undo_duplicate_and_original_replay_follow_current_state(self):
        with Harness() as h:
            h.send(submit());undo=control('UNDO','undo-1','review-1',1)
            h.send(submit(undo));v=h.store.snapshot().wallet['version']
            h.send(submit(undo));r=h.send(submit())['payload']
            self.assertEqual(r['ledger_state'],'REVERTED');self.assertEqual(h.balance,0)
            self.assertEqual(h.store.snapshot().wallet['version'],v)

    def test_restore_duplicate_never_double_awards(self):
        with Harness() as h:
            h.send(submit());h.send(submit(control('UNDO','undo-1','review-1',1)))
            restore=control('RESTORE','restore-1','undo-1',2)
            h.send(submit(restore));v=h.store.snapshot().wallet['version'];h.send(submit(restore))
            self.assertEqual(h.balance,Q);self.assertEqual(h.store.snapshot().wallet['version'],v)

    def test_out_of_order_restore_requires_p11_resolution(self):
        with Harness() as h:
            restore=control('RESTORE','restore-1','undo-1',2)
            r=h.send(submit(restore))['payload'];self.assertEqual(r['disposition'],'RETRY_LATER')
            h.send(submit());h.send(submit(control('UNDO','undo-1','review-1',1)))
            self.assertEqual(h.send(submit(restore))['payload']['disposition'],'RETRY_LATER')
            row=h.store.snapshot().ledger['inbox'][digest(restore)]
            h.evidence.grant(row,'fixture:causal-proof');h.ledger.resolve(digest(restore),'fixture:causal-proof')
            self.assertEqual(h.send(query(restore))['payload']['disposition'],'ACK_APPLIED');self.assertEqual(h.balance,Q)

    def test_pending_compensation_is_not_quarantine_no_award_claim(self):
        with Harness() as h:
            first=h.send(submit())['payload'];family=h.store.snapshot().ledger['inbox'][first['inbox_id']]['family_key']
            h.store.fixture_spend(family,UNIT,7)
            r=h.send(submit(control('UNDO','undo-1','review-1',1)))['payload']
            self.assertEqual(r['disposition'],'RETRY_LATER');self.assertEqual(r['award_status'],'UNDETERMINED')
            self.assertEqual(r['ledger_state'],'PENDING_RECONCILIATION');self.assertEqual(h.balance,0)

    def test_unverified_epoch_quarantines(self):
        with Harness() as h:
            h.evidence.unverified_epochs.add('fixture:epoch-new')
            r=h.send(submit(event(epoch='fixture:epoch-new')))['payload']
            self.assertEqual(r['disposition'],'ACK_QUARANTINED');self.assertEqual(h.balance,0)

    def test_queries_do_not_recompute_rewards_or_write(self):
        with Harness() as h:
            h.send(submit());before=h.store.snapshot();calls=h.policy.calls
            h.send(query());h.send(query())
            self.assertEqual(h.store.snapshot(),before);self.assertEqual(h.policy.calls,calls)

    def test_bound_rejected_case_has_durable_rejection(self):
        with Harness() as h:
            h.evidence.blocked.add('review-1');r=h.send(submit())['payload']
            row=h.store.snapshot().ledger['inbox'][r['inbox_id']]
            h.evidence.grant(row,'fixture:reject-proof',action='REJECT')
            h.ledger.resolve(r['inbox_id'],'fixture:reject-proof','REJECT')
            r=h.send(query())['payload'];self.assertEqual(r['disposition'],'REJECTED')
            self.assertIsNotNone(r['receipt']);self.assertEqual(h.balance,0)

    def test_scope_change_never_reaches_ledger(self):
        with Harness() as h:
            for mutate in ['producer','scope','event']:
                m=submit()
                if mutate=='producer':m['producer_id']='fixture:other'
                elif mutate=='scope':m['scope']['beneficiary_id']='fixture:other'
                else:m['payload']['event']['beneficiary_id']='fixture:other'
                self.assertEqual(h.send(m)['payload']['error_code'],'E_SCOPE')
            self.assertEqual(h.store.snapshot().ledger['inbox'],{})

    def test_query_cannot_expose_other_beneficiary(self):
        with Harness() as h:
            other=event(beneficiary='fixture:other');h.ledger.handle(canonical(other))
            r=h.send(query(other))['payload'];self.assertEqual(r['error_code'],'E_SCOPE');self.assertIsNone(r['receipt'])

    def test_restore_fence_blocks_even_existing_receipts(self):
        with Harness() as h:
            old=h.store.snapshot();h.send(submit());h.store.fixture_restore_old_backup(old)
            self.assertEqual(h.send(query())['payload']['disposition'],'RETRY_LATER')
            self.assertEqual(h.send(submit())['payload']['disposition'],'RETRY_LATER')

    def test_not_found_is_read_only_not_award(self):
        with Harness() as h:
            r=h.send(query())['payload'];self.assertEqual(r['ledger_state'],'NOT_FOUND')
            self.assertEqual(r['next_action'],'SUBMIT');self.assertEqual(h.store.snapshot().ledger['inbox'],{})

    def test_production_bootstrap_is_unavailable(self):
        with Harness() as h:
            with self.assertRaises(ValueError):P11Bridge(h.ledger,h.store,SCOPE,execution_mode='production')

    def test_backend_backpressure_keeps_request_unconfirmed(self):
        from runtime.anki.transport.ipc_server_client.ports import Backpressure
        with Harness() as h:
            def busy(_raw):raise Backpressure('test')
            h.ledger.handle=busy
            r=h.send(submit())['payload']
            self.assertEqual(r['error_code'],'E_BACKPRESSURE')
            self.assertEqual(r['disposition'],'RETRY_LATER');self.assertIsNone(r['receipt'])
            self.assertEqual(h.balance,0)

if __name__=='__main__':unittest.main(verbosity=2)
