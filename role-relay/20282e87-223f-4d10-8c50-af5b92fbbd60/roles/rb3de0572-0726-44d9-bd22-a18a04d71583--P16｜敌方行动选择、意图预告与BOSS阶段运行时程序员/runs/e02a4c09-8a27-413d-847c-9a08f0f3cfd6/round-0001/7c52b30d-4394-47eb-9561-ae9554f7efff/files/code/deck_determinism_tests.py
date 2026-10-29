"""Run directly, or through unittest discovery. Pure RNG and process replay tests."""
from pathlib import Path
import json,os,subprocess,sys,unittest
from deck_runtime import RngState,DeckRejected,shuffle
from deck_runtime.rng import advance
from deck_runtime.wire import MAX_INTEGER
from upstream.P14.battle_core.rng import advance as p14_advance,verify_transition

ROOT=Path(__file__).resolve().parent


class DeterminismTests(unittest.TestCase):
    def test_seven_literal_fixed_seed_vectors(self):
        doc=json.loads((ROOT/'fixtures/fixed_seed_vectors.json').read_text())
        for row in doc['vectors']:
            before=RngState.seeded(row['seed'])
            order,after=shuffle(tuple(row['input']),before)
            self.assertEqual(list(order),row['output'])
            self.assertEqual(after.state,row['state'])
            self.assertEqual(after.draw_count,row['draw_count'])
            stream=[];r=before
            for _ in row['rng_outputs']:
                r=r.next();stream.append(r.state)
            self.assertEqual(stream,row['rng_outputs'])
            self.assertTrue(verify_transition(before.value(),after.value()))

    def test_cross_owner_rng_jump_agreement(self):
        for seed in (1,2,42,0xffffffff):
            for count in (0,1,2,8,1000,2**32-1,MAX_INTEGER):
                self.assertEqual(advance(seed,count),p14_advance(seed,count))

    def test_shuffle_continues_existing_stream(self):
        before=RngState(1,advance(1,11),11)
        _,after=shuffle(('A','B','C','D'),before)
        self.assertEqual(after.draw_count,14)
        self.assertEqual(after.state,advance(1,14))

    def test_different_seed_changes_fixture_order(self):
        values=tuple(range(9))
        a,_=shuffle(values,RngState.seeded(1));b,_=shuffle(values,RngState.seeded(2))
        self.assertNotEqual(a,b)

    def test_invalid_seed_and_history_rejected(self):
        for seed in (0,-1,True,2**32):
            with self.assertRaises(DeckRejected):RngState.seeded(seed)
        with self.assertRaisesRegex(DeckRejected,'RNG_HISTORY_INVALID'):
            RngState.from_value({'algorithm':'xorshift32-v1','initial_seed':1,'state':2,'draw_count':0})

    def test_rng_count_exhaustion_no_wrap(self):
        r=RngState(1,advance(1,MAX_INTEGER),MAX_INTEGER)
        with self.assertRaisesRegex(DeckRejected,'RNG_COUNT_EXHAUSTED'):
            shuffle(('A','B'),r)
        self.assertEqual(r.draw_count,MAX_INTEGER)

    def test_three_python_hash_seed_processes_reexecute_real_p15(self):
        outputs=[]
        program='from examples.demo import run_demo; from deck_runtime.wire import fingerprint; print(fingerprint(run_demo()))'
        for seed in ('0','1','777'):
            p=subprocess.run([sys.executable,'-B','-c',program],cwd=ROOT,
                env=dict(os.environ,PYTHONHASHSEED=seed,PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            outputs.append(p.stdout.strip())
        self.assertEqual(len(set(outputs)),1)
        self.assertEqual(len(outputs[0]),64)


if __name__=='__main__':
    unittest.main(verbosity=2)
