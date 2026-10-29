"""Real Python thread contention against an explicitly non-durable P21 model."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from character_party_runtime import DomainError,command
from tests.support.base import MetaCase
from tests.support.authority import CHARS


class WalletConcurrencyTests(MetaCase):
    def race(self,candidates):
        barrier=Barrier(len(candidates))
        def submit(c):
            barrier.wait()
            try:return self.model.submit(c,synthetic_counterpart=True)['status']
            except DomainError as exc:return exc.code
        with ThreadPoolExecutor(max_workers=len(candidates)) as pool:return list(pool.map(submit,candidates))

    def test_twelve_same_request_retries_one_commit(self):
        self.seed();s=self.model.snapshot()
        c=self.planner.plan(command(s,'fixture:once','LEVEL_UP',{'character_id':CHARS[0],'from_rank':1,'to_rank':2}),s).candidate
        outcomes=self.race([c]*12)
        self.assertEqual(outcomes.count('COMMITTED_SIMULATION'),1);self.assertEqual(outcomes.count('DUPLICATE_NO_OP'),11)
        self.assertEqual(self.balance(),96)

    def test_two_upgrades_compete_for_last_four_tokens(self):
        self.seed(amount=4);s=self.model.snapshot()
        cs=[self.planner.plan(command(s,'fixture:up-'+str(i),'LEVEL_UP',{
            'character_id':CHARS[i],'from_rank':1,'to_rank':2}),s).candidate for i in range(2)]
        out=self.race(cs)
        self.assertEqual(sorted(out),['COMMITTED_SIMULATION','E_REVISION_CONFLICT'])
        self.assertEqual(self.balance(),0)
        self.assertEqual(sorted(c['level'] for c in self.model.snapshot().value['characters']),[1,1,2])

    def test_same_entitlement_two_request_ids_one_credit(self):
        self.authority.grant('fixture:one',kind='STAGE_FIRST_CLEAR',amount=5);s=self.model.snapshot()
        cs=[self.planner.plan(command(s,'fixture:claim-'+str(i),'APPLY_GRANT',{'grant_ref':'fixture:one'}),s).candidate for i in range(2)]
        out=self.race(cs);self.assertEqual(out.count('COMMITTED_SIMULATION'),1);self.assertEqual(self.balance(),5)
        retried=self.planner.plan(command(self.model.snapshot(),'fixture:fresh','APPLY_GRANT',{'grant_ref':'fixture:one'}),self.model.snapshot())
        self.assertEqual(retried.status,'DUPLICATE_NO_OP')

    def test_reservation_race_cannot_overdraw(self):
        self.grant(amount=8);s=self.model.snapshot();cs=[]
        for i in range(2):
            ref='fixture:cost-'+str(i);self.authority.quote(ref,6)
            cs.append(self.planner.plan(command(s,'fixture:req-'+str(i),'RESERVE',{
                'quote_ref':ref,'reservation_id':'fixture:r-'+str(i)}),s).candidate)
        out=self.race(cs);self.assertEqual(out.count('COMMITTED_SIMULATION'),1);self.assertEqual(self.balance(),2)
        self.assertEqual(self.planner.wallet_snapshot(self.model.snapshot()).value['balances'][0]['reserved'],6)

    def test_capture_release_race_one_terminal_transition(self):
        self.grant(amount=10);self.authority.quote('fixture:cost',7)
        self.apply('RESERVE',{'quote_ref':'fixture:cost','reservation_id':'fixture:r'});s=self.model.snapshot()
        requests=[command(s,'fixture:capture','CAPTURE',{'quote_ref':'fixture:cost','reservation_id':'fixture:r'}),
                  command(s,'fixture:release','RELEASE',{'reservation_id':'fixture:r'})]
        out=self.race([self.planner.plan(r,s).candidate for r in requests])
        self.assertEqual(out.count('COMMITTED_SIMULATION'),1)
        self.assertIn(self.balance(),(3,10));self.assertEqual(self.planner.wallet_snapshot(self.model.snapshot()).value['balances'][0]['reserved'],0)

    def test_undo_spend_race_preserves_nonnegative_source(self):
        self.grant('fixture:study',kind='STUDY',amount=10)
        self.authority.quote('fixture:cost',4);self.authority.reversal('fixture:undo','fixture:study');s=self.model.snapshot()
        requests=[command(s,'fixture:spend','SPEND',{'quote_ref':'fixture:cost'}),
                  command(s,'fixture:revoke','REVOKE_STUDY',{'reversal_ref':'fixture:undo'})]
        out=self.race([self.planner.plan(r,s).candidate for r in requests]);self.assertEqual(out.count('COMMITTED_SIMULATION'),1)
        self.assertIn(self.balance(),(0,6))
        l=self.model.snapshot().value['wallet']['lots'][0]
        self.assertEqual(l['quantity'],l['available']+l['reserved']+l['spent']+l['revoked'])

    def test_same_request_id_distinct_payload_race_collides(self):
        self.seed();s=self.model.snapshot()
        cs=[self.planner.plan(command(s,'fixture:same-id','LEVEL_UP',{
            'character_id':CHARS[i],'from_rank':1,'to_rank':2}),s).candidate for i in range(2)]
        out=self.race(cs);self.assertEqual(sorted(out),['COMMITTED_SIMULATION','E_COMMAND_ID_COLLISION'])
        self.assertEqual(self.balance(),96)

    def test_twenty_distinct_spends_with_conflict_replan(self):
        self.grant(amount=20)
        for i in range(20):self.authority.quote('fixture:q-'+str(i),1)
        def worker(i):
            for attempt in range(100):
                s=self.model.snapshot();r=command(s,'fixture:spend-'+str(i),'SPEND',{'quote_ref':'fixture:q-'+str(i)})
                p=self.planner.plan(r,s)
                if p.status=='DUPLICATE_NO_OP':return p.status
                self.assertEqual(p.status,'CANDIDATE',p.reason)
                try:return self.model.submit(p.candidate,synthetic_counterpart=True)['status']
                except DomainError as exc:
                    if exc.code!='E_REVISION_CONFLICT':raise
            raise AssertionError('replan budget exhausted')
        with ThreadPoolExecutor(max_workers=8) as pool:out=list(pool.map(worker,range(20)))
        self.assertEqual(out.count('COMMITTED_SIMULATION'),20);self.assertEqual(self.balance(),0)
        self.assertEqual(len(self.model.snapshot().value['wallet']['consumptions']),20)


if __name__=='__main__':
    import unittest
    unittest.main(verbosity=2)
