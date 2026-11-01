"""P29 isolated presentation-only event player; provisional adapter contract."""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Optional, Callable

class MotionMode(str, Enum):
    NORMAL="normal"; FAST="fast"; REDUCED="reduced"; NONE="none"
class ConsumeStatus(str, Enum):
    QUEUED="QUEUED"; DUPLICATE="DUPLICATE"; STALE_EPOCH="STALE_EPOCH"; SYNC_REQUIRED="SYNC_REQUIRED"; INVALID="INVALID"
@dataclass(frozen=True)
class BattleEvent:
    seq:int; event_id:str; event_type:str; battle_id:str; epoch:int; payload:Mapping[str,Any]
    @classmethod
    def parse(cls,x):
        if not all(k in x for k in ("seq","event_id","event_type","battle_id","epoch")): raise ValueError("missing event field")
        if not isinstance(x["seq"],int) or x["seq"]<0 or not isinstance(x["epoch"],int) or x["epoch"]<0: raise ValueError("invalid sequence/epoch")
        if not isinstance(x.get("payload",{}),Mapping): raise ValueError("payload must be mapping")
        return cls(x["seq"],str(x["event_id"]),str(x["event_type"]),str(x["battle_id"]),x["epoch"],dict(x.get("payload",{})))
@dataclass(frozen=True)
class Command:
    kind:str; seq:int; epoch:int; data:Mapping[str,Any]
class BattleAnimationPlayer:
    EFFECTS={"CARD_PLAYED":"card_travel","CARD_COMMITTED":"card_travel","DAMAGE_APPLIED":"impact","SHIELD_ABSORBED":"shield_absorb","HEAL_APPLIED":"heal","STATUS_APPLIED":"status_fly_in","STATUS_REMOVED":"status_fade","ENTITY_DEFEATED":"death_dissolve","ENEMY_INTENT_REVEALED":"intent_emphasis","BATTLE_FINISHED":"battle_finished","AUDIO_CUE":"audio"}
    def __init__(self,emit:Optional[Callable]=None):
        self.battle_id=None; self.epoch=0; self.last_seq=-1; self.needs_snapshot=True
        self.mode=MotionMode.NORMAL; self.muted=False; self.queue=[]; self.snapshot=None
        self.hp_visual={}; self.shield_visual={}; self.seen_ids=set(); self.commands=[]; self.emit_callback=emit
    def _emit(self,kind,seq,data=None):
        c=Command(kind,seq,self.epoch,dict(data or {})); self.commands.append(c)
        if self.emit_callback: self.emit_callback(c)
        return c
    def set_mode(self,mode):
        self.mode=MotionMode(mode)
        if self.mode in (MotionMode.REDUCED,MotionMode.NONE):
            self._flush_result_logs(); self._emit("CANCEL_DECORATION",self.last_seq,{"mode":self.mode.value,"preserve_result_log":True})
            self._emit("SHOW_STATIC_RESULT",self.last_seq,{"snapshot":self.snapshot})
        elif self.mode==MotionMode.FAST: self._emit("FAST_FORWARD_DECORATION",self.last_seq)
    def set_muted(self,value): self.muted=bool(value)
    def consume(self,raw):
        try: e=raw if isinstance(raw,BattleEvent) else BattleEvent.parse(raw)
        except (ValueError,TypeError): return ConsumeStatus.INVALID
        if self.battle_id is not None and e.battle_id!=self.battle_id: return ConsumeStatus.SYNC_REQUIRED
        if e.epoch<self.epoch: return ConsumeStatus.STALE_EPOCH
        if e.epoch>self.epoch: return ConsumeStatus.SYNC_REQUIRED
        if e.seq<=self.last_seq or e.event_id in self.seen_ids: return ConsumeStatus.DUPLICATE
        if self.needs_snapshot or e.seq!=self.last_seq+1: return ConsumeStatus.SYNC_REQUIRED
        self.queue.append(e); self.last_seq=e.seq; self.seen_ids.add(e.event_id)
        return ConsumeStatus.QUEUED
    def recover_from_snapshot(self,snapshot,next_seq,epoch):
        if not isinstance(next_seq,int) or next_seq<0 or not snapshot.get("battle_id"): raise ValueError("invalid authoritative snapshot")
        self.queue.clear(); self.battle_id=str(snapshot["battle_id"]); self.epoch=int(epoch); self.last_seq=next_seq-1
        self.needs_snapshot=False; self.snapshot=dict(snapshot)
        self.hp_visual={str(k):float(v) for k,v in snapshot.get("hp",{}).items()}
        self.shield_visual={str(k):float(v) for k,v in snapshot.get("shield",{}).items()}
        self.seen_ids.clear(); self._emit("SNAPSHOT_RESET",self.last_seq,{"snapshot":dict(snapshot),"authoritative":True})
    def drain(self,max_events=None):
        n=len(self.queue) if max_events is None else min(len(self.queue),max(0,max_events)); out=[]
        for _ in range(n): out.extend(self._present(self.queue.pop(0)))
        return out
    def _present(self,e):
        p=dict(e.payload); effect=self.EFFECTS.get(e.event_type,"event_log")
        facts={k:p.get(k) for k in ("target_id","hp_loss","shield_absorbed","hp_after","shield_after","amount","status_id","status_stacks")}; facts["event_type"]=e.event_type
        out=[Command("RESULT_LOG",e.seq,e.epoch,facts)]
        if self.mode in (MotionMode.REDUCED,MotionMode.NONE): return out
        if e.event_type=="AUDIO_CUE" and self.muted: return out
        if self.mode==MotionMode.FAST:
            out.append(Command("DECORATION_TERMINAL",e.seq,e.epoch,{"effect":effect,**p})); return out
        if effect=="card_travel" and not p.get("source_rect"): effect="card_arrive_without_travel"
        if effect=="impact" and p.get("target_rect") is None: effect="impact_without_anchor"
        out.append(Command(effect,e.seq,e.epoch,p)); return out
    def _flush_result_logs(self):
        # Preserve readable facts for already-consumed events when decoration is cancelled.
        pending, self.queue = self.queue, []
        for e in pending:
            p=dict(e.payload)
            facts={k:p.get(k) for k in ("target_id","hp_loss","shield_absorbed","hp_after","shield_after","amount","status_id","status_stacks")}
            facts["event_type"]=e.event_type
            self._emit("RESULT_LOG",e.seq,facts)
    def skip_epoch(self):
        self._flush_result_logs()
        self._emit("CANCEL_DECORATION",self.last_seq,{"epoch":self.epoch,"idempotent":True,"preserve_result_log":True})
    def on_background(self): self.skip_epoch(); self.needs_snapshot=True
    def on_resume(self): self.needs_snapshot=True
    def interpolate_hp(self,entity_id,target,alpha):
        a=max(0.0,min(1.0,float(alpha))); cur=self.hp_visual.get(entity_id,float(target)); v=cur+(float(target)-cur)*a; self.hp_visual[entity_id]=v; return v
    def interpolate_shield(self,entity_id,target,alpha):
        a=max(0.0,min(1.0,float(alpha))); cur=self.shield_visual.get(entity_id,float(target)); v=cur+(float(target)-cur)*a; self.shield_visual[entity_id]=v; return v
