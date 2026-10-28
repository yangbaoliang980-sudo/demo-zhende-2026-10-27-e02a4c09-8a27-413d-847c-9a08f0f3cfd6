import unittest
from battle_core.replay import replay
from .p02_adapter import (CASES,BLOCKED_HISTORY,make_case,execute,projected_state,
                          projected_expected_state,expected_event_projection)


class P02ProjectionTests(unittest.TestCase):
    """These PASS results refer to the documented projection, not legacy bytes."""

    def test_animation_flag_is_not_a_logic_input(self):
        a,ca,_,_=make_case('F001'); b,cb,_,_=make_case('F019')
        execute(a,ca);execute(b,cb)
        self.assertEqual(a.state().raw,b.state().raw)
        self.assertEqual(tuple(x.raw for x in a.committed_batches()),tuple(x.raw for x in b.committed_batches()))
        self.assertEqual(a.export_replay().sha256,b.export_replay().sha256)


def test_case(case_id):
    def run(self):
        if case_id in BLOCKED_HISTORY:
            self.skipTest('BLOCKED: legacy receipt only has old SHA; full command/range absent. Native equivalents tested separately.')
        core,commands,_,_=make_case(case_id)
        replies=execute(core,commands); case=CASES[case_id]
        expected=case['expected']['command_results']
        self.assertEqual(len(replies),len(expected))
        for got,want in zip(replies,expected):
            r=got.value
            self.assertEqual(r['result'],'COMMITTED' if want['status']=='ACCEPTED' else want['status'])
            self.assertEqual(r['code'],'OK' if want['error_code'] is None else want['error_code'])
        self.assertEqual(projected_state(core),projected_expected_state(case))
        actual=[e for b in core.committed_batches() for e in b.value['events']]
        projection=expected_event_projection(case)
        self.assertEqual(len(actual),len(projection))
        for got,(kind,data) in zip(actual,projection):
            self.assertEqual(got['event_type'],kind)
            self.assertEqual({k:got['data'][k] for k in data},data)
        if actual:
            self.assertEqual([e['seq'] for e in actual],list(range(actual[0]['seq'],actual[-1]['seq']+1)))
        replayed=replay(core.export_replay())
        self.assertEqual(core.state().raw,replayed.state().raw)
        self.assertEqual(tuple(b.raw for b in core.committed_batches()),tuple(b.raw for b in replayed.committed_batches()))
        self.assertEqual(None if core.result() is None else core.result().raw,
                         None if replayed.result() is None else replayed.result().raw)
    return run


for case_id in CASES:
    setattr(P02ProjectionTests,'test_'+case_id,test_case(case_id))
