import copy
import json
import tempfile
import threading
import unittest
from pathlib import Path
from runtime.framework.yltt_framework.codec import FrozenMessage, fingerprint
from runtime.framework.yltt_framework.contracts import validate
from runtime.framework.yltt_framework.demo import fixture, CannedPort
from runtime.framework.yltt_framework.host import Backpressure, CommandMailbox, WrongThread
from runtime.framework.yltt_framework.path_guard import isolated_output_path
from runtime.framework.yltt_framework.ports import PortRegistry, UnboundPort, require_isolated
from runtime.framework.yltt_framework.sequence import BattleStreamGuard
from runtime.framework.yltt_framework.testing import ScriptedEndpoint


class CompositionTests(unittest.TestCase):
    def test_study_reader_can_be_tested_without_ledger_or_anki(self):
        query=validate(fixture('StudyStatusQuery'));status=validate(fixture('StudyStatusView'))
        endpoint=ScriptedEndpoint([((query,),status)])
        self.assertEqual(endpoint.call(query).value['state'],'UNKNOWN')
        self.assertEqual(len(endpoint.calls),1)

    def test_unlisted_mock_input_does_not_invent_result(self):
        query=validate(fixture('StudyStatusQuery'));status=validate(fixture('StudyStatusView'))
        endpoint=ScriptedEndpoint([((query,),status)]);different=query.value;different['inbox_id']='b'*64
        with self.assertRaises(LookupError):endpoint.call(validate(different))
        self.assertEqual(endpoint.calls,())

    def test_wallet_mock_reply_does_not_mutate_wallet(self):
        snapshot=validate(fixture('WalletSnapshot'));delta=validate(fixture('WalletDeltaCandidate'))
        endpoint=ScriptedEndpoint([((snapshot,),delta)]);before=snapshot.raw
        self.assertEqual(endpoint.call(snapshot).value['changes'],[])
        self.assertEqual(snapshot.raw,before)

    def test_unique_domain_owners(self):
        reg=PortRegistry();reg.bind('battle','P14',CannedPort())
        for name,owner in [('battle','P14'),('battle','P15'),('wallet','P11'),('commit','P13')]:
            with self.subTest(name=name,owner=owner),self.assertRaises(ValueError):reg.bind(name,owner,object())

    def test_registry_freeze_and_unbound(self):
        reg=PortRegistry()
        with self.assertRaises(ValueError):reg.get('battle')
        reg.freeze()
        with self.assertRaises(UnboundPort):reg.get('wallet')
        with self.assertRaises(ValueError):reg.bind('battle','P14',CannedPort())

    def test_production_is_unimplemented(self):
        with self.assertRaises(UnboundPort):require_isolated('production')

    def test_paths_default_deny_and_protect_upstream(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for rel in ['../outside','/tmp/outside','runtime/battle/state.py','architecture/evidence/upstream/P12/a.py','contracts/anki_transport/wire.py','a\\b','runtime//framework/x','architecture/./x']:
                with self.subTest(rel=rel),self.assertRaises(ValueError):isolated_output_path(root,rel)
            self.assertEqual(isolated_output_path(root,'runtime/framework/new.py'),root/'runtime/framework/new.py')

    def test_path_symlink_is_not_write_authorization(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'architecture').mkdir();(root/'architecture/escape').symlink_to(Path(td).parent,target_is_directory=True)
            with self.assertRaises(ValueError):isolated_output_path(root,'architecture/escape/test')


class HostTests(unittest.TestCase):
    def setUp(self):
        self.command=validate(fixture('BattleCommand'));self.port=CannedPort()

    def test_queue_receipt_is_not_business_commit(self):
        host=CommandMailbox(self.port.submit)
        q=host.post(self.command.raw)
        self.assertEqual(q.status,'QUEUED_NOT_COMMITTED');self.assertEqual(self.port.seen,[])
        result=host.drain();self.assertEqual(result[0].status,'PORT_RETURNED_UNVERIFIED');self.assertEqual(len(self.port.seen),1)

    def test_backpressure_keeps_accepted_request(self):
        host=CommandMailbox(self.port.submit,capacity=1);host.post(self.command.raw)
        with self.assertRaises(Backpressure):host.post(self.command.raw)
        self.assertEqual(len(host.drain()),1)

    def test_ui_cannot_inject_system_command(self):
        c=self.command.value;c.update(kind='SYSTEM_ENEMY_ACTION',payload={})
        host=CommandMailbox(self.port.submit)
        with self.assertRaises(ValueError):host.post(validate(c).raw)
        self.assertEqual(self.port.seen,[])

    def test_workers_post_but_only_host_thread_drains(self):
        host=CommandMailbox(self.port.submit);errors=[]
        def work():
            host.post(self.command.raw)
            try:host.drain()
            except Exception as exc:errors.append(type(exc))
        t=threading.Thread(target=work);t.start();t.join(5)
        self.assertFalse(t.is_alive());self.assertEqual(errors,[WrongThread]);self.assertEqual(len(host.drain()),1)

    def test_concurrent_posts_have_unique_tickets(self):
        host=CommandMailbox(self.port.submit,capacity=32);tickets=[];lock=threading.Lock()
        def work():
            ticket=host.post(self.command.raw).ticket
            with lock:tickets.append(ticket)
        threads=[threading.Thread(target=work) for _ in range(16)]
        for t in threads:t.start()
        for t in threads:t.join(5)
        self.assertEqual(sorted(tickets),list(range(16)))
        self.assertEqual([r.ticket for r in host.drain(32)],list(range(16)))

    def test_close_retains_queued_work(self):
        host=CommandMailbox(self.port.submit);host.post(self.command.raw);host.close()
        with self.assertRaises(ValueError):host.post(self.command.raw)
        self.assertEqual(len(host.drain()),1)

    def test_domain_exception_is_unknown_not_rejected_or_applied(self):
        def uncertain(_):raise OSError('synthetic commit ambiguity')
        host=CommandMailbox(uncertain);host.post(self.command.raw);r=host.drain()[0]
        self.assertEqual(r.status,'PORT_EXCEPTION_OUTCOME_UNKNOWN');self.assertIsNone(r.response)

    def test_mismatched_reply_is_not_delivered_as_success(self):
        def wrong(_):
            r=fixture('BattleReply');r.update(battle_id='other',result='REJECTED',commit=None)
            return validate(r)
        host=CommandMailbox(wrong);host.post(self.command.raw)
        self.assertEqual(host.drain()[0].status,'PORT_EXCEPTION_OUTCOME_UNKNOWN')

    def test_drain_budget_and_empty(self):
        host=CommandMailbox(self.port.submit);host.post(self.command.raw);host.post(self.command.raw)
        self.assertEqual(host.drain(0),());self.assertEqual(len(host.drain(1)),1)
        self.assertEqual(len(host.drain(1)),1);self.assertEqual(host.drain(),())


class StreamTests(unittest.TestCase):
    def setUp(self):
        self.base=validate(fixture('BattleSnapshot'));self.batch=validate(fixture('BattleCommitBatch'))
        self.guard=BattleStreamGuard();self.guard.rebase(self.base)

    def test_duplicate_batch_emits_no_second_acceptance(self):
        self.assertEqual(self.guard.offer(self.batch).disposition,'ACCEPT')
        self.assertEqual(self.guard.offer(self.batch).disposition,'DUPLICATE')
        self.assertEqual(self.guard.snapshot['revision'],1)

    def test_gap_requires_rebase_no_partial_update(self):
        b=self.batch.value
        for e in b['events']:e['seq']+=5
        b['snapshot']['last_event_seq']+=5
        before=self.guard.snapshot
        self.assertEqual(self.guard.offer(validate(b)).disposition,'NEED_SNAPSHOT')
        self.assertEqual(self.guard.snapshot,before)

    def test_missing_initial_snapshot_blocks_stream(self):
        self.assertEqual(BattleStreamGuard().offer(self.batch).disposition,'NEED_SNAPSHOT')

    def test_same_revision_conflict_and_old_snapshot(self):
        self.guard.offer(self.batch)
        bad=self.guard.snapshot;bad['energy']=4
        with self.assertRaises(ValueError):self.guard.rebase(validate(bad))
        with self.assertRaises(ValueError):self.guard.rebase(self.base)

    def test_explicit_battle_switch_required(self):
        s=self.base.value;s['battle_id']='another'
        with self.assertRaises(ValueError):self.guard.rebase(validate(s))
        self.guard.rebase(validate(s),new_battle=True)
        self.assertEqual(self.guard.offer(self.batch).disposition,'NEED_SNAPSHOT')

    def test_rebase_then_old_batch_is_safe(self):
        self.guard.rebase(validate(self.batch.value['snapshot']))
        self.assertEqual(self.guard.offer(self.batch).disposition,'NEED_SNAPSHOT')
        self.assertEqual(self.guard.snapshot['revision'],1)

    def test_readside_never_mutates_authority_input(self):
        before=self.base.raw;self.guard.offer(self.batch)
        view=self.guard.snapshot;view['energy']=0
        self.assertEqual(self.base.raw,before);self.assertEqual(self.guard.snapshot['energy'],3)

    def test_animation_cancellation_is_not_a_logic_port(self):
        # Interface-level spy only, no renderer or P29 player is being tested.
        class ViewSpy:
            def __init__(self):self.operations=[]
            def reconcile(self,s):self.operations.append(('snapshot',s.sha256))
            def begin(self,b):self.operations.append(('batch',b.sha256));return 'fixture:lease'
            def display_bars(self,lease_id,unit_id,hp,shield):self.operations.append(('transient',lease_id,unit_id,hp,shield))
            def finish(self,lease_id):self.operations.append(('finish',lease_id))
            def cancel(self,lease_id):self.operations.append(('cancel',lease_id))
        spy=ViewSpy();before=(self.base.raw,self.batch.raw)
        lease=spy.begin(self.batch);spy.display_bars(lease,'hero1',10,0);spy.cancel(lease);spy.reconcile(validate(self.batch.value['snapshot']))
        self.assertEqual(before,(self.base.raw,self.batch.raw));self.assertFalse(hasattr(spy,'submit'))


if __name__=='__main__':unittest.main()
