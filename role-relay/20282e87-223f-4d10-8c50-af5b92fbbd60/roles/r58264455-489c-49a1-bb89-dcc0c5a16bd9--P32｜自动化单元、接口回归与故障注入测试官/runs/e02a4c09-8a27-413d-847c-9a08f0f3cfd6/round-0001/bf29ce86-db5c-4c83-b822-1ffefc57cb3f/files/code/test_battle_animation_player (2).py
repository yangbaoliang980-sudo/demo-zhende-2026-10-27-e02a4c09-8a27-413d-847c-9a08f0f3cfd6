import unittest
from runtime.animation.battle_animation_player import BattleAnimationPlayer, ConsumeStatus, MotionMode

def snap(hp=100,shield=20): return {"battle_id":"battle-001","hp":{"enemy-1":hp},"shield":{"enemy-1":shield},"outcome":"ONGOING","revision":7}
def ev(seq,typ="DAMAGE_APPLIED",epoch=1,**p): return {"seq":seq,"event_id":f"evt-{seq}","event_type":typ,"battle_id":"battle-001","epoch":epoch,"payload":p}
class PlayerTests(unittest.TestCase):
 def setUp(self): self.p=BattleAnimationPlayer(); self.p.recover_from_snapshot(snap(),1,1)
 def test_order_duplicate(self):
  self.assertEqual(self.p.consume(ev(1)),ConsumeStatus.QUEUED); self.assertEqual(self.p.consume(ev(1)),ConsumeStatus.DUPLICATE); self.assertEqual(self.p.consume(ev(2)),ConsumeStatus.QUEUED); self.assertEqual([x.seq for x in self.p.drain() if x.kind=="RESULT_LOG"],[1,2])
 def test_gap_no_advance(self): self.assertEqual(self.p.consume(ev(3)),ConsumeStatus.SYNC_REQUIRED); self.assertEqual(self.p.last_seq,0); self.assertEqual(len(self.p.queue),0)
 def test_stale_and_future_epoch(self): self.assertEqual(self.p.consume(ev(1,epoch=0)),ConsumeStatus.STALE_EPOCH); self.assertEqual(self.p.consume(ev(1,epoch=2)),ConsumeStatus.SYNC_REQUIRED)
 def test_snapshot_recovery_discards_queue(self):
  self.p.consume(ev(1)); self.p.recover_from_snapshot(snap(61,5),8,2); self.assertEqual(self.p.last_seq,7); self.assertEqual(self.p.hp_visual["enemy-1"],61); self.assertFalse(self.p.queue); self.assertEqual(self.p.consume(ev(8,epoch=2)),ConsumeStatus.QUEUED)
 def test_skip_idempotent_preserves_snapshot(self):
  self.p.consume(ev(1)); s=dict(self.p.snapshot); self.p.skip_epoch(); self.p.skip_epoch(); self.assertEqual(self.p.snapshot,s); self.assertFalse(self.p.queue)
 def test_reduced_none_preserve_result_only(self):
  for m in (MotionMode.REDUCED,MotionMode.NONE):
   self.p.set_mode(m); self.p.consume(ev(1,hp_loss=0,shield_absorbed=9)); out=self.p.drain(); self.assertTrue(any(x.kind=="RESULT_LOG" for x in out)); self.assertFalse(any(x.kind=="impact" for x in out)); self.p.recover_from_snapshot(snap(),1,1)
 def test_fast_collapses(self): self.p.set_mode(MotionMode.FAST); self.p.consume(ev(1)); self.assertTrue(any(x.kind=="DECORATION_TERMINAL" for x in self.p.drain()))
 def test_missing_anchors_do_not_guess(self):
  self.p.consume(ev(1,"CARD_PLAYED",target_rect={"x":1})); self.assertTrue(any(x.kind=="card_arrive_without_travel" for x in self.p.drain())); self.p.recover_from_snapshot(snap(),1,1); self.p.consume(ev(1,"DAMAGE_APPLIED",hp_loss=5)); self.assertTrue(any(x.kind=="impact_without_anchor" for x in self.p.drain()))
 def test_hp_interpolation_is_visual_only(self):
  original=snap(); self.assertEqual(self.p.interpolate_hp("enemy-1",60,.5),80); self.assertEqual(original["hp"]["enemy-1"],100); self.assertEqual(self.p.interpolate_hp("enemy-1",60,1),60)
 def test_background_requires_snapshot(self):
  self.p.on_background(); self.assertEqual(self.p.consume(ev(1)),ConsumeStatus.SYNC_REQUIRED); self.p.recover_from_snapshot(snap(88),4,1); self.assertEqual(self.p.hp_visual["enemy-1"],88)
 def test_muted_audio(self):
  self.p.set_muted(True); self.p.consume(ev(1,"AUDIO_CUE",cue="hit")); self.assertFalse(any(x.kind=="audio" for x in self.p.drain()))
 def test_skip_flushes_committed_result_facts(self):
  self.p.consume(ev(1,hp_loss=4,shield_absorbed=2)); self.p.skip_epoch()
  logs=[x for x in self.p.commands if x.kind=="RESULT_LOG"]
  self.assertTrue(any(x.data.get("hp_loss")==4 and x.data.get("shield_absorbed")==2 for x in logs))
 def test_reduced_mode_flushes_pending_facts(self):
  self.p.consume(ev(1,hp_loss=0,shield_absorbed=7)); self.p.set_mode(MotionMode.REDUCED)
  self.assertTrue(any(x.kind=="RESULT_LOG" and x.data.get("shield_absorbed")==7 for x in self.p.commands))
 def test_invalid_event(self): self.assertEqual(self.p.consume({"seq":"bad"}),ConsumeStatus.INVALID)
if __name__=="__main__": unittest.main()
