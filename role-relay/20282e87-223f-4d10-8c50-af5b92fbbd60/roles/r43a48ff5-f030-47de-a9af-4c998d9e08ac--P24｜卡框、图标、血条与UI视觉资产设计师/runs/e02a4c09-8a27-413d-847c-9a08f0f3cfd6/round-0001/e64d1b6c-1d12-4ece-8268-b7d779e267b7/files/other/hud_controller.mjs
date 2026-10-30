import {CONTRACT, ViewError, requireView, clone, freeze, fingerprint, canonical} from './wire.mjs';
import {PresentationBridge} from './presentation_adapter.mjs';

const CLOSED = new Set(['TERMINAL','ABORTED','FAULTED']);
export class HudController {
  constructor({port, guard, mode='isolated', idFactory=()=>`p19:${crypto.randomUUID()}`,
    now=()=>Date.now(), debounceMs=350, timeoutMs=8000, presentation=new PresentationBridge()} = {}) {
    requireView(port && typeof port.read === 'function' && typeof port.submit === 'function','PORT_REQUIRED');
    requireView(mode === 'isolated','PRODUCTION_CONTRACT_UNBOUND');
    this.port = port; this.guard = guard; this.idFactory = idFactory; this.now = now;
    this.debounceMs = debounceMs; this.timeoutMs = timeoutMs; this.presentation = presentation;
    this.snapshot = null; this.context = null; this.snapshotHash = null;
    this.pending = null; this.selection = null; this.targets = [];
    this.connection = 'CONNECTING'; this.stale = true; this.suspended = false;
    this.error = null; this.logs = []; this.listeners = new Set(); this.sentIds = new Set();
    this.lastGesture = null; this.generation = 0; this.readTicket = 0; this.disposed = false; this.loggedSeq = 0;
  }
  subscribe(fn) {this.listeners.add(fn); fn(this.view()); return ()=>this.listeners.delete(fn);}
  emit() {if (!this.disposed) for (const fn of this.listeners) fn(this.view());}
  log(code, data = null) {this.logs.push(freeze({code,data:clone(data)})); this.logs = this.logs.slice(-80);}
  fail(code) {this.error = code; this.emit(); return {sent:false,code};}
  view() {
    const s = this.snapshot, ready = !!s && !CLOSED.has(s.phase) && s.phase === 'PLAYER_READY' &&
      this.connection === 'READY' && !this.stale && !this.suspended && !this.pending;
    const card = this.context?.cards.find(c=>c.instance_id === this.selection) || null;
    const targetValid = card && card.allowed_target_sets.some(set=>sameTargets(set,this.targets));
    return freeze({snapshot:s, context:this.context, snapshotHash:this.snapshotHash,
      selectedCard:this.selection, selectedTargets:[...this.targets], connection:this.connection,
      stale:this.stale, suspended:this.suspended, pending:this.pending ? {command_id:this.pending.command.command_id,state:this.pending.state} : null,
      canSelect:ready && !!this.context, canPlay:!!(ready && card?.enabled && targetValid),
      canEndTurn:ready, error:this.error, logs:[...this.logs], presentationStatus:this.presentation.status});
  }
  async bounded(promise) {
    let timer;
    try {return await Promise.race([promise,new Promise((_,reject)=>{timer=setTimeout(()=>reject(new ViewError('REPLY_TIMEOUT')),this.timeoutMs);})]);}
    finally {clearTimeout(timer);}
  }
  async acceptSnapshot(raw, {context=null, fromRefresh=false} = {}) {
    const generation = this.generation;
    const s = this.guard(raw,'BattleSnapshot');
    const hash = await fingerprint(s);
    if (this.disposed || generation !== this.generation) return 'OBSOLETE';
    if (this.snapshot) {
      requireView(s.battle_id === this.snapshot.battle_id, 'BATTLE_ID_MISMATCH');
      if (s.revision < this.snapshot.revision) return 'STALE_IGNORED';
      if (s.revision === this.snapshot.revision) {
        requireView(hash === this.snapshotHash, 'REVISION_COLLISION');
      } else requireView(s.last_event_seq >= this.snapshot.last_event_seq, 'EVENT_HIGH_WATERMARK_REGRESSION');
    }
    const changed = !this.snapshot || s.revision !== this.snapshot.revision;
    this.snapshot = s; this.snapshotHash = hash;
    // Context failure must never hide a valid authoritative final snapshot.
    try {this.context = context === null ? null : validateContext(context,s,hash);}
    catch (e) {this.context=null; this.error=e.code || 'HUD_CONTEXT_INVALID'; this.log(this.error);}
    if (changed) {this.selection=null; this.targets=[];}
    if (CLOSED.has(s.phase)) {this.selection=null; this.targets=[];}
    if (fromRefresh) {this.presentation.cancel('REFRESH_TO_FINAL'); this.presentation.lastSeq = s.last_event_seq;}
    this.emit(); return changed ? 'APPLIED' : 'IDENTICAL';
  }
  async refresh() {
    const ticket = ++this.readTicket, generation = this.generation;
    this.stale = true; if (this.connection !== 'READY') this.connection='CONNECTING'; this.emit();
    try {
      const frame = await this.bounded(this.port.read());
      if (ticket !== this.readTicket || generation !== this.generation || this.disposed) return false;
      requireView(frame.format === 'P19-HUD-FRAME/0.1.0-proposal', 'FRAME_VERSION');
      const applied = await this.acceptSnapshot(frame.snapshot,{context:frame.context,fromRefresh:true});
      if (ticket !== this.readTicket || generation !== this.generation) return false;
      requireView(applied !== 'STALE_IGNORED', 'STALE_REFRESH');
      this.ingestLog(frame.recent_batches || []);
      if (!this.pending && ['CONNECTION_LOST','STALE_REFRESH','FRAME_VERSION','REPLY_SNAPSHOT_NOT_CURRENT'].includes(this.error)) this.error=null;
      if (this.context && ['HUD_CONTEXT_STALE','HUD_CONTEXT_INVALID'].includes(this.error)) this.error=null;
      this.connection='READY'; this.stale=this.suspended; this.emit(); return true;
    } catch(e) {
      if (ticket !== this.readTicket || generation !== this.generation || this.disposed) return false;
      this.connection='DISCONNECTED'; this.stale=true; this.error=e.code || 'CONNECTION_LOST';
      this.log(this.error); this.presentation.cancel('CONNECTION_LOST'); this.emit(); return false;
    }
  }
  selectCard(instanceId, observedRevision=this.snapshot?.revision) {
    if (!this.view().canSelect) return this.fail('INPUT_LOCKED');
    if (observedRevision !== this.snapshot.revision) return this.fail('STALE_INPUT');
    const card = this.context.cards.find(c=>c.instance_id === instanceId);
    if (!card || !this.snapshot.zones.hand.includes(instanceId)) return this.fail('CARD_NOT_IN_HAND');
    if (!card.enabled) return this.fail(card.reason_code);
    this.selection=instanceId; this.targets=[]; this.error=null; this.emit();
    return {selected:true};
  }
  clearSelection() {this.selection=null; this.targets=[]; this.emit();}
  ingestLog(batches) {
    // Historical event facts are text only; never derive HP/energy from events.
    try {
      const events=[];
      for (const raw of batches) {
        const b=this.guard(raw,'BattleCommitBatch');
        requireView(b.battle_id === this.snapshot.battle_id && b.snapshot.revision <= this.snapshot.revision,'HISTORY_BINDING');
        for (const e of b.events) {
          requireView(e.battle_id === b.battle_id && e.revision === b.snapshot.revision && e.command_id === b.command_id &&
            e.seq <= this.snapshot.last_event_seq,'HISTORY_EVENT_BINDING');
          if (e.seq>this.loggedSeq) events.push(e);
        }
      }
      events.sort((a,b)=>a.seq-b.seq);
      for (const e of events) {
        if (e.seq<=this.loggedSeq) continue;
        if (['DAMAGE_APPLIED','HEAL_APPLIED','SHIELD_CHANGED','BATTLE_FINISHED'].includes(e.event_type)) this.log(e.event_type,e.data);
        this.loggedSeq=e.seq;
      }
    } catch(e) {this.log('HISTORY_UNAVAILABLE');}
  }
  selectTarget(unitId, observedRevision=this.snapshot?.revision) {
    if (!this.view().canSelect || observedRevision !== this.snapshot.revision) return this.fail('STALE_OR_LOCKED_INPUT');
    const card=this.context.cards.find(c=>c.instance_id === this.selection);
    if (!card) return this.fail('SELECT_CARD_FIRST');
    if (!card.allowed_target_sets.some(set=>set.includes(unitId))) return this.fail('TARGET_INVALID');
    const required=card.allowed_target_sets[0]?.length || 0;
    if (required === 1) this.targets=[unitId];
    else if (this.targets.includes(unitId)) this.targets=this.targets.filter(id=>id!==unitId);
    else this.targets=[...this.targets,unitId].slice(-required);
    this.error=null; this.emit(); return {selected:true};
  }
  play(observedRevision=this.snapshot?.revision) {
    if (!this.view().canPlay) return Promise.resolve(this.fail('PLAY_NOT_READY'));
    const inst=this.snapshot.card_instances.find(c=>c.instance_id === this.selection);
    const card=this.context.cards.find(c=>c.instance_id === this.selection);
    const ordered=card.allowed_target_sets.find(set=>sameTargets(set,this.targets));
    return this.dispatch('PLAY_CARD',{actor_id:inst.owner_unit_id,card_instance_id:inst.instance_id,target_ids:[...ordered]},observedRevision);
  }
  endTurn(observedRevision=this.snapshot?.revision) {return this.dispatch('END_TURN',{},observedRevision);}
  async dispatch(kind,payload,observedRevision) {
    if (!['PLAY_CARD','END_TURN'].includes(kind)) return this.fail('USER_COMMAND_ONLY');
    if (!this.view().canEndTurn) return this.fail('INPUT_LOCKED');
    if (observedRevision !== this.snapshot.revision) return this.fail('STALE_INPUT');
    const signature=canonical({kind,payload,revision:observedRevision});
    if (this.lastGesture?.signature === signature && this.now()-this.lastGesture.at < this.debounceMs) return this.fail('INPUT_DEBOUNCED');
    let command;
    try {
      command=this.guard({contract_version:CONTRACT,dto_type:'BattleCommand',battle_id:this.snapshot.battle_id,
        command_id:this.idFactory(),expected_revision:observedRevision,kind,payload},'BattleCommand');
      requireView(!this.sentIds.has(command.command_id),'LOCAL_COMMAND_ID_COLLISION');
      requireView(this.sentIds.size < 4096,'INPUT_HISTORY_CAPACITY');
    } catch(e) {return this.fail(e.code || 'COMMAND_INVALID');}
    this.sentIds.add(command.command_id); this.lastGesture={signature,at:this.now()};
    this.pending={command,state:'SENDING'}; this.error=null; this.emit();
    return this.sendPending();
  }
  async sendPending() {
    const pending=this.pending, generation=this.generation;
    if (!pending) return this.fail('NO_PENDING_COMMAND');
    pending.state='SENDING'; this.error=null; this.emit();
    try {
      const reply=this.guard(await this.bounded(this.port.submit(clone(pending.command))),'BattleReply');
      if (generation !== this.generation || pending !== this.pending || this.disposed) return {sent:true,code:'OBSOLETE_REPLY'};
      const c=pending.command;
      requireView(reply.battle_id === c.battle_id && reply.command_id === c.command_id,'REPLY_ID_MISMATCH');
      if (reply.result === 'COMMITTED') {
        requireView(reply.commit !== null,'MISSING_COMMIT');
        const b=reply.commit;
        requireView(b.command_id === c.command_id && b.battle_id === c.battle_id && b.previous_revision === c.expected_revision &&
          b.snapshot.battle_id === c.battle_id && b.snapshot.revision === c.expected_revision + 1 &&
          b.snapshot.revision === reply.observed_revision,'COMMIT_BINDING');
        const priorSeq=this.snapshot.last_event_seq;
        const accepted=await this.acceptSnapshot(b.snapshot);
        // Event numbers are historical evidence only. They never change final fields.
        if (accepted === 'APPLIED') {
          this.ingestLog([b]);
          void this.presentation.present(b,priorSeq,this.snapshot);
        }
      } else requireView(reply.commit === null,'NONCOMMIT_WITH_BATCH');
      this.log(reply.result,{command_id:reply.command_id,code:reply.code});
      if (reply.result === 'REJECTED') this.error=reply.code;
      const refreshed=await this.refresh();
      requireView(refreshed && this.snapshot.revision >= reply.observed_revision,'REPLY_SNAPSHOT_NOT_CURRENT');
      if (generation !== this.generation || pending !== this.pending) return {sent:true,code:'OBSOLETE_REPLY'};
      this.pending=null; this.emit(); return {sent:true,code:reply.code,result:reply.result};
    } catch(e) {
      if (generation !== this.generation || pending !== this.pending || this.disposed) return {sent:true,code:'OBSOLETE_REPLY'};
      pending.state='UNKNOWN'; this.stale=true; this.error=e.code || 'COMMAND_OUTCOME_UNKNOWN';
      this.log(this.error,{command_id:pending.command.command_id}); this.emit(); return {sent:true,code:this.error,result:'UNKNOWN'};
    }
  }
  retryPending() {
    if (!this.pending || this.pending.state !== 'UNKNOWN' || this.suspended) return Promise.resolve(this.fail('RETRY_NOT_READY'));
    // Same complete immutable command, including original ID and expected revision.
    return this.sendPending();
  }
  setVisibility(hidden) {
    this.suspended=hidden; this.stale=true; this.selection=null; this.targets=[];
    this.presentation.cancel(hidden?'BACKGROUND':'RESUME'); this.emit();
    return hidden ? Promise.resolve(false) : this.refresh();
  }
  setPresentationMode(mode) {this.presentation.setMode(mode); this.emit();}
  skipPresentation() {this.presentation.cancel('SKIPPED_TO_FINAL'); this.emit();}
  dispose() {this.disposed=true; this.generation++; this.readTicket++; this.presentation.dispose(); this.listeners.clear();}
}

function sameTargets(a,b) {return a.length === b.length && a.every(x=>b.includes(x));}
export function validateContext(raw,s,hash) {
  requireView(raw && raw.format === 'P19-HUD-CONTEXT/0.1.0-proposal','HUD_CONTEXT_VERSION');
  requireView(raw.source_kind === 'ISOLATED_FIXTURE_ONLY','HUD_CONTEXT_UNBOUND');
  requireView(raw.battle_id === s.battle_id && raw.revision === s.revision && raw.snapshot_sha256 === hash,'HUD_CONTEXT_STALE');
  requireView(Array.isArray(raw.cards) && raw.cards.length <= s.zones.hand.length && Array.isArray(raw.intents),'HUD_CONTEXT_SHAPE');
  const seen=new Set();
  for (const c of raw.cards) {
    const inst=s.card_instances.find(x=>x.instance_id === c.instance_id);
    requireView(inst && s.zones.hand.includes(c.instance_id) && !seen.has(c.instance_id),'HUD_CARD_REFERENCE'); seen.add(c.instance_id);
    requireView(c.actor_id === inst.owner_unit_id && typeof c.enabled === 'boolean' && typeof c.reason_code === 'string','HUD_CARD_BINDING');
    requireView(typeof c.name === 'string' && typeof c.description === 'string' && typeof c.category === 'string' &&
      Number.isSafeInteger(c.cost) && c.cost >= 0 && Array.isArray(c.allowed_target_sets),'HUD_CARD_DISPLAY');
    requireView(c.allowed_target_sets.length <= 4096 && c.allowed_target_sets.every(set=>Array.isArray(set) && set.length>0 &&
      new Set(set).size === set.length && set.every(id=>s.units.some(u=>u.unit_id === id))),'HUD_TARGET_REFERENCE');
    requireView(!c.enabled || c.allowed_target_sets.length > 0,'HUD_ENABLED_WITHOUT_TARGETS');
  }
  const actors=new Set();
  for (const i of raw.intents) {
    requireView(!actors.has(i.actor_id) && s.units.some(u=>u.unit_id === i.actor_id && u.side === 'ENEMY'),'HUD_INTENT_ACTOR'); actors.add(i.actor_id);
    requireView(i.expected_revision === s.revision && Array.isArray(i.target_ids) && i.target_ids.every(id=>s.units.some(u=>u.unit_id === id)), 'HUD_INTENT_STALE');
    requireView(['SCRIPTED_TEST_ONLY','P16_PREVIEW_CANDIDATE_ONLY'].includes(i.provenance),'INTENT_NOT_COMMITTED');
    requireView(typeof i.label === 'string' && Number.isSafeInteger(i.base_amount) && i.base_amount >= 0 &&
      Number.isSafeInteger(i.hit_count) && i.hit_count >= 0,'HUD_INTENT_VALUE');
    requireView(i.damage_label === 'BASE_DAMAGE_NOT_HP_LOSS','INTENT_DAMAGE_LABEL');
  }
  return freeze(clone(raw));
}
