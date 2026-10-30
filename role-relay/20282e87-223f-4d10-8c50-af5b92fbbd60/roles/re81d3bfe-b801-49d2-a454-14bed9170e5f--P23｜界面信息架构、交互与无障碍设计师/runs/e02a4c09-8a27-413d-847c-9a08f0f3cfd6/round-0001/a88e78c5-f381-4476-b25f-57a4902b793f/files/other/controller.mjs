import {INTENT_VERSION,ROUTES,binding,canonical,copy,freeze,identityKey,requireValue,sha256,validateView} from './model.mjs';
export const NAV_KEY='p20.navigation.v1';
export const PENDING_KEY='p20.pending.v1';
const KINDS=['SET_PARTY','LEVEL_UP','SET_EQUIPMENT','ENTER_STAGE','CLAIM_STAGE_REWARD'];
export class MetaController {
  constructor({port,storage,idFactory=()=>`p20.${crypto.randomUUID()}`,onChange=()=>{}}) {
    this.port=port;this.storage=storage;this.idFactory=idFactory;this.onChange=onChange;
    this.view=null;this.phase='LOADING';this.pending=null;this.error='';this.message='';this.route='home';
    this.selectedCharacter=null;this.selectedStage=null;this.partyDraft=[null,null,null];this.draftDirty=false;
    this.storageFault=false;this.navEpoch=0;this.readSerial=0;this.disposed=false;
    try {
      const nav=JSON.parse(storage.getItem(NAV_KEY)||'null');
      if(nav && nav.version===1 && ROUTES.includes(nav.route)) {this.route=nav.route;this.selectedCharacter=nav.character_id;this.selectedStage=nav.stage_id;}
    } catch {this.message='页面位置未恢复，将从首页开始。';}
    try {
      const pending=JSON.parse(storage.getItem(PENDING_KEY)||'null');
      if(pending){requireValue(pending.version===1 && pending.intent?.schema_version===INTENT_VERSION && KINDS.includes(pending.intent.kind) && /^[0-9a-f]{64}$/.test(pending.sha256),'E_PENDING_RECORD');this.pending=freeze(pending);}
    } catch {this.storageFault=true;this.error='未决操作记录不可读取，需要核对后才能继续提交。';}
  }
  emit(){if(!this.disposed)this.onChange(this);}
  get canMutate(){return !this.disposed && this.phase==='READY' && !this.pending && !this.storageFault && this.view?.mode==='FIXTURE' && this.view.capabilities.write_allowed && this.view.save.state==='READY';}
  get activeBattle(){return this.view?.stage_progress?.active_battle_id || null;}
  get selected(){return this.view?.characters.find(c=>c.character_id===this.selectedCharacter)||null;}
  persistNav(){try{this.storage.setItem(NAV_KEY,JSON.stringify({version:1,route:this.route,character_id:this.selectedCharacter,stage_id:this.selectedStage}));}catch{this.message='页面位置无法保存；当前页面仍可浏览。';}}
  navigate(route){if(!ROUTES.includes(route))return false;this.route=route;this.navEpoch++;this.persistNav();this.emit();return true;}
  selectCharacter(id){if(!this.view?.characters.some(c=>c.character_id===id))return false;this.selectedCharacter=id;this.persistNav();this.emit();return true;}
  selectStage(id){if(!this.view?.stage_details.some(s=>s.stage_id===id))return false;this.selectedStage=id;this.persistNav();this.emit();return true;}
  setSlot(index,id){
    if(!this.canMutate || this.activeBattle || !Number.isInteger(index)||index<0||index>2)return false;
    if(id!==null&&!this.view.characters.some(c=>c.character_id===id))return false;
    const draft=[...this.partyDraft];const other=draft.indexOf(id);
    if(id!==null && other>=0 && other!==index)draft[other]=draft[index];
    draft[index]=id;this.partyDraft=draft;this.draftDirty=true;this.emit();return true;
  }
  resetDraft(){this.partyDraft=[...(this.view?.party.slots||[null,null,null])];this.draftDirty=false;this.emit();}
  adoptView(raw){
    const next=validateView(raw),old=this.view;
    if(old && identityKey(old)===identityKey(next)){
      if(next.sequence<old.sequence)return false;
      requireValue(next.sequence!==old.sequence||canonical(next)===canonical(old),'E_SAME_SEQUENCE_CONFLICT');
      requireValue(['meta','wallet','stage'].every(k=>next.revisions[k]>=old.revisions[k]),'E_REVISION_ROLLBACK');
    } else if(old) {
      this.draftDirty=false;this.selectedCharacter=null;this.selectedStage=null;
      if(this.pending)this.message='存储实例已变化；保留原操作，等待核对。';
    }
    this.view=next;
    if(!next.characters.some(c=>c.character_id===this.selectedCharacter))this.selectedCharacter=next.characters[0]?.character_id||null;
    if(!next.stage_details.some(s=>s.stage_id===this.selectedStage))this.selectedStage=next.stage_details[0]?.stage_id||null;
    if(!this.draftDirty)this.partyDraft=[...next.party.slots];
    // A stale local draft is never a domain fact and must not contain removed members.
    if(this.partyDraft.some(c=>c!==null&&!next.characters.some(x=>x.character_id===c)))this.resetDraft();
    return true;
  }
  async refresh(){
    const serial=++this.readSerial;
    if(!this.pending && this.phase!=='SENDING')this.phase='LOADING';this.emit();
    try{
      const raw=await this.port.read();if(this.disposed||serial!==this.readSerial)return false;
      const accepted=this.adoptView(raw);
      if(this.phase!=='SENDING')this.phase=this.pending?'UNKNOWN':'READY';
      if(!this.storageFault)this.error='';
      if(this.pending)this.message='有一笔操作结果待确认，请先查询原操作。';
      this.emit();return accepted;
    }catch(e){if(this.disposed||serial!==this.readSerial)return false;this.phase=this.pending?'UNKNOWN':'DISCONNECTED';this.error=`读取失败：${e.message}`;this.emit();return false;}
  }
  allowed(kind,payload){
    if(!this.canMutate)return false;
    if(['SET_PARTY','LEVEL_UP','SET_EQUIPMENT'].includes(kind)&&this.activeBattle)return false;
    if(kind==='SET_PARTY')return Array.isArray(payload.ordered_character_ids)&&payload.ordered_character_ids.length===3&&new Set(payload.ordered_character_ids).size===3&&payload.ordered_character_ids.every(id=>this.view.characters.some(c=>c.character_id===id));
    if(kind==='LEVEL_UP'){const c=this.view.characters.find(c=>c.character_id===payload.character_id);return !!c?.level_action.available && payload.from_rank===c.level_action.from_rank && payload.to_rank===c.level_action.to_rank;}
    if(kind==='SET_EQUIPMENT')return this.view.capabilities.equipment_enabled && this.view.characters.some(c=>c.character_id===payload.character_id);
    if(kind==='ENTER_STAGE')return !this.activeBattle && this.view.party.valid && this.view.stage_details.some(s=>s.stage_id===payload.stage_id&&s.action_enabled);
    if(kind==='CLAIM_STAGE_REWARD')return this.view.settlement?.claimable===true && payload.battle_id===this.view.settlement.battle_id;
    return false;
  }
  async dispatch(kind,payload){
    if(!this.allowed(kind,payload))return {status:'BLOCKED_UI'};
    // Synchronous lock before hashing, persistence, or any network await.
    this.phase='SENDING';this.error='';this.message='正在提交，请勿重复操作。';this.emit();
    const navEpoch=this.navEpoch;
    const intent=freeze({schema_version:INTENT_VERSION,request_id:this.idFactory(),binding:binding(this.view),kind,payload:copy(payload)});
    let sent=false;
    try{
      const digest=await sha256(intent);
      if(this.disposed)return {status:'DISPOSED'};
      const pending=freeze({version:1,intent,sha256:digest});
      this.storage.setItem(PENDING_KEY,JSON.stringify(pending));this.pending=pending;
      sent=true;const response=await this.port.submit(intent);
      if(this.disposed)return {status:'DISPOSED'};
      await this.consumeResponse(response,navEpoch);
      return response;
    }catch(e){
      if(this.disposed)return {status:'DISPOSED'};
      if(sent){this.phase='UNKNOWN';this.message='操作可能已处理，请先查询原操作。';}
      else{this.phase='READY';this.storageFault=true;this.message='未发送操作：无法可靠保存恢复记录。';}
      this.error=e.message;this.emit();return {status:sent?'UNKNOWN':'BLOCKED_STORAGE'};
    }
  }
  async consumeResponse(r,navEpoch=this.navEpoch){
    const pending=this.pending;requireValue(!!pending,'E_NO_PENDING');
    requireValue(r?.request_id===pending.intent.request_id && r.request_sha256===pending.sha256,'E_REPLY_BINDING');
    requireValue(['COMMITTED_SIMULATION','DUPLICATE_NO_OP','REJECTED','BLOCKED','UNKNOWN'].includes(r.status),'E_REPLY_STATUS');
    if(r.status==='UNKNOWN'){this.phase='UNKNOWN';this.error=r.reason||'E_LOOKUP_UNKNOWN';this.emit();return;}
    requireValue(r.durable===false,'E_ISOLATED_RECEIPT_SCOPE');
    requireValue(r.view && identityKey(r.view)===canonical(pending.intent.binding.identity),'E_REPLY_STORE_FENCE');
    requireValue(this.adoptView(r.view),'E_REPLY_STALE_VIEW');
    this.storage.removeItem(PENDING_KEY);this.pending=null;this.phase='READY';this.error='';
    const success=['COMMITTED_SIMULATION','DUPLICATE_NO_OP'].includes(r.status);
    this.message=success?'演练操作已确认；当前数值来自重新读取。':`操作未完成：${r.reason}`;
    if(success && pending.intent.kind==='SET_PARTY'){this.draftDirty=false;this.partyDraft=[...this.view.party.slots];}
    if(success && navEpoch===this.navEpoch){
      if(pending.intent.kind==='ENTER_STAGE')this.route='handoff';
      if(pending.intent.kind==='CLAIM_STAGE_REWARD')this.route='settlement';
    }
    this.persistNav();this.emit();
  }
  async lookupPending(){
    if(!this.pending||this.phase==='SENDING'||this.phase==='QUERYING'||this.storageFault)return false;
    this.phase='QUERYING';this.emit();
    try{
      requireValue(await sha256(this.pending.intent)===this.pending.sha256,'E_PENDING_HASH');
      const result=await this.port.lookup(this.pending.intent);if(this.disposed)return false;
      await this.consumeResponse(result);return result.status!=='UNKNOWN';
    }catch(e){if(!this.disposed){this.phase='UNKNOWN';this.error=e.message;this.emit();}return false;}
  }
  pause(){if(this.phase==='READY')this.phase='STALE';this.emit();}
  dispose(){this.disposed=true;this.readSerial++;}
}
