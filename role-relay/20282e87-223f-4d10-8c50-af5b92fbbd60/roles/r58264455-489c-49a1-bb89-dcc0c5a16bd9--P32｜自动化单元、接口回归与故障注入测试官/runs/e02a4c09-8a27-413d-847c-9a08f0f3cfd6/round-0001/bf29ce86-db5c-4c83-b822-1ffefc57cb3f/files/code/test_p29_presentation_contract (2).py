import sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "target_fixture"))
from runtime.animation.battle_animation_player import BattleAnimationPlayer, ConsumeStatus

def snapshot():
    return {"battle_id":"qa-battle","hp":{"enemy":100},"shield":{"enemy":0},"outcome":"ONGOING","revision":1}
def event(seq, event_id=None, epoch=1):
    return {"seq":seq,"event_id":event_id or f"e{seq}","event_type":"DAMAGE_APPLIED",
            "battle_id":"qa-battle","epoch":epoch,"payload":{"target_id":"enemy","hp_loss":1}}

class P32PresentationContractTests(unittest.TestCase):
    def setUp(self):
        self.p=BattleAnimationPlayer()
        self.p.recover_from_snapshot(snapshot(),1,1)

    def test_001_contiguous_sequence_accepted(self):
        self.assertEqual(self.p.consume(event(1)),ConsumeStatus.QUEUED)
        self.assertEqual(self.p.last_seq,1)

    def test_002_sequence_gap_does_not_advance_cursor(self):
        self.assertEqual(self.p.consume(event(2)),ConsumeStatus.SYNC_REQUIRED)
        self.assertEqual(self.p.last_seq,0)
        self.assertEqual(len(self.p.queue),0)

    def test_003_duplicate_event_id_with_new_sequence_is_rejected(self):
        self.assertEqual(self.p.consume(event(1,"same")),ConsumeStatus.QUEUED)
        self.assertEqual(self.p.consume(event(2,"same")),ConsumeStatus.DUPLICATE)
        self.assertEqual(self.p.last_seq,1)

    def test_004_other_battle_is_not_consumed(self):
        e=event(1); e["battle_id"]="other"
        self.assertEqual(self.p.consume(e),ConsumeStatus.SYNC_REQUIRED)
        self.assertEqual(self.p.last_seq,0)

    def test_005_skip_is_idempotent_one_logical_cancel(self):
        self.p.skip_epoch(); self.p.skip_epoch(); self.p.skip_epoch()
        cancels=[c for c in self.p.commands if c.kind=="CANCEL_DECORATION"]
        self.assertEqual(len(cancels),1,"repeated skip emitted more than one logical cancellation")

    def test_006_boolean_sequence_is_invalid_counterexample(self):
        e=event(1); e["seq"]=True
        self.assertEqual(self.p.consume(e),ConsumeStatus.INVALID,
                         "bool is a Python int subclass and must not be accepted as sequence")

    def test_007_recovery_replaces_visual_baseline(self):
        self.p.recover_from_snapshot({"battle_id":"qa-battle","hp":{"enemy":41},"shield":{"enemy":7},
                                      "outcome":"ONGOING","revision":2}, 9, 2)
        self.assertEqual(self.p.hp_visual["enemy"],41)
        self.assertEqual(self.p.shield_visual["enemy"],7)
        self.assertEqual(self.p.last_seq,8)
        self.assertEqual(self.p.consume(event(9,epoch=2)),ConsumeStatus.QUEUED)

if __name__=="__main__": unittest.main(verbosity=2)
