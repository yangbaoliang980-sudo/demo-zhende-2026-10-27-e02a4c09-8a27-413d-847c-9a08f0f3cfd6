// P20 owns display validation and labels only. No wallet, growth or unlock arithmetic.
export const VIEW_VERSION = 'P20-META-VIEW/0.1.0-proposal';
export const INTENT_VERSION = 'P20-META-INTENT/0.1.0-proposal';
export const ROUTES = ['home','characters','party','growth','chapters','handoff','settlement','learning'];
const STATES = ['APPLIED','REVERTED','QUARANTINED','PENDING_RECONCILIATION','REJECTED','NOT_FOUND','UNKNOWN'];
const SAVE_STATES = ['READY','READ_ONLY','MIGRATING','RECOVERY_REQUIRED','UNAVAILABLE'];
const STAGE_STATES = ['AVAILABLE','LOCKED','CLEARED','REVIEW_REQUIRED','IN_PROGRESS','PENDING_RECONCILIATION'];
const TRANSPORT = ['DISCONNECTED','CONNECTED','REDELIVERY','RECONCILING'];
const ID = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$/;
const HASH = /^[0-9a-f]{64}$/;
export function requireValue(ok, reason) { if (!ok) throw new Error(reason); }
export function isInt(v) { return Number.isSafeInteger(v) && v >= 0; }
const obj = v => v !== null && typeof v === 'object' && !Array.isArray(v);
const id = v => typeof v === 'string' && ID.test(v);
const arr = (v, n = 4096) => Array.isArray(v) && v.length <= n;
const unique = a => new Set(a).size === a.length;
const text = v => typeof v === 'string' && v.length <= 512;
export function canonical(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  return '{' + Object.keys(value).sort().map(k => JSON.stringify(k)+':'+canonical(value[k])).join(',') + '}';
}
export async function sha256(value) {
  const bytes = new TextEncoder().encode(typeof value === 'string' ? value : canonical(value));
  return [...new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256',bytes))].map(n=>n.toString(16).padStart(2,'0')).join('');
}
export function freeze(value) { if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); } return value; }
export function copy(value) { return JSON.parse(JSON.stringify(value)); }
export function identityKey(v) { return canonical(v.identity); }
export function binding(v) { return {identity:copy(v.identity),revisions:copy(v.revisions),source_hashes:copy(v.source_hashes)}; }
export function validateView(v) {
  requireValue(obj(v) && v.schema_version === VIEW_VERSION,'E_VIEW_VERSION');
  requireValue(['UNBOUND','FIXTURE'].includes(v.mode),'E_VIEW_MODE');
  requireValue(isInt(v.sequence),'E_VIEW_SEQUENCE');
  requireValue(obj(v.identity) && ['profile_id','store_instance','continuity_ref','session_id'].every(k=>id(v.identity[k])),'E_VIEW_IDENTITY');
  requireValue(obj(v.revisions) && ['meta','wallet','stage'].every(k=>isInt(v.revisions[k])),'E_VIEW_REVISION');
  requireValue(obj(v.source_hashes) && ['meta','stage','content'].every(k=>HASH.test(v.source_hashes[k])),'E_VIEW_SOURCE_HASH');
  requireValue(obj(v.capabilities) && typeof v.capabilities.write_allowed === 'boolean' && typeof v.capabilities.equipment_enabled === 'boolean','E_CAPABILITIES');
  requireValue(v.mode !== 'UNBOUND' || v.capabilities.write_allowed === false,'E_UNBOUND_WRITE');
  requireValue(obj(v.save) && v.save.contract_version === 'YLTT-INTERNAL/0.1.0-isolated' && v.save.dto_type === 'SaveStatusView' && SAVE_STATES.includes(v.save.state),'E_SAVE_STATE');
  requireValue(v.save.store_instance === null || v.save.store_instance === v.identity.store_instance,'E_SAVE_STORE_BINDING');
  requireValue(text(v.save.reason_code) && (v.save.high_watermark === null || isInt(v.save.high_watermark)),'E_SAVE_FIELDS');
  requireValue(v.wallet === null || (obj(v.wallet) && v.wallet.dto_type === 'WalletSnapshot' && v.wallet.contract_version === 'YLTT-INTERNAL/0.1.0-isolated'),'E_WALLET_TYPE');
  if (v.wallet) {
    requireValue(v.wallet.beneficiary_id === v.identity.profile_id && v.wallet.revision === v.revisions.wallet,'E_WALLET_BINDING');
    requireValue(arr(v.wallet.balances) && unique(v.wallet.balances.map(x=>x.resource_id)),'E_WALLET_ROWS');
    v.wallet.balances.forEach(x=>requireValue(id(x.resource_id) && isInt(x.available) && isInt(x.reserved),'E_WALLET_BALANCE'));
  }
  requireValue(arr(v.characters,512) && unique(v.characters.map(c=>c.character_id)),'E_CHARACTER_ROWS');
  for (const c of v.characters) {
    requireValue(id(c.character_id) && text(c.display_name) && text(c.role) && isInt(c.level) && c.level > 0 && isInt(c.xp_total) && isInt(c.skill_rank),'E_CHARACTER_FIELDS');
    requireValue(obj(c.stats) && ['max_hp','attack','defense','support'].every(k=>isInt(c.stats[k])),'E_CHARACTER_STATS');
    requireValue(c.source_revision === v.revisions.meta && c.source_sha256 === v.source_hashes.meta,'E_CHARACTER_BINDING');
    requireValue(arr(c.equipment,16) && arr(c.equipment_options,64),'E_EQUIPMENT_ROWS');
    c.equipment.forEach(e=>requireValue(id(e.slot) && id(e.instance_id),'E_EQUIPMENT_ITEM'));
    c.equipment_options.forEach(e=>requireValue(id(e.slot) && id(e.instance_id) && text(e.name) && typeof e.available === 'boolean' && text(e.reason),'E_EQUIPMENT_OPTION'));
    const a = c.level_action;
    requireValue(obj(a) && typeof a.available === 'boolean' && text(a.reason) && isInt(a.from_rank) && isInt(a.to_rank) && isInt(a.requires_xp_total) && arr(a.costs,64),'E_LEVEL_ACTION');
    a.costs.forEach(x=>requireValue(id(x.resource_id) && isInt(x.amount),'E_LEVEL_COST'));
    requireValue(!a.available || (a.from_rank === c.level && a.to_rank === c.level+1),'E_LEVEL_BINDING');
  }
  const owned = new Set(v.characters.map(c=>c.character_id));
  requireValue(obj(v.party) && arr(v.party.slots,3) && v.party.slots.length === 3 && typeof v.party.valid === 'boolean','E_PARTY_SHAPE');
  requireValue(v.party.slots.every(c=>c === null || owned.has(c)) && unique(v.party.slots.filter(c=>c !== null)),'E_PARTY_MEMBER');
  requireValue(v.party.valid === v.party.slots.every(c=>c !== null),'E_PARTY_VALID');
  requireValue(arr(v.stage_details,512) && unique(v.stage_details.map(s=>s.stage_id)),'E_STAGE_DETAILS');
  for (const s of v.stage_details) {
    requireValue(id(s.stage_id) && text(s.name) && text(s.subtitle) && typeof s.action_enabled === 'boolean' && text(s.reason) && arr(s.reward_preview,16),'E_STAGE_DETAIL');
    s.reward_preview.forEach(r=>requireValue(text(r.label) && isInt(r.amount),'E_REWARD_PREVIEW'));
  }
  if (v.stage_progress !== null) {
    const p = v.stage_progress;
    requireValue(obj(p) && p.schema_version === 'P18-PROGRESS-VIEW/0.1.0-proposal','E_STAGE_TYPE');
    requireValue(p.player_save_scope_id === v.identity.profile_id && p.revision === v.revisions.stage && p.source_snapshot_sha256 === v.source_hashes.stage,'E_STAGE_BINDING');
    requireValue(p.active_battle_id === null || id(p.active_battle_id),'E_ACTIVE_BATTLE');
    requireValue(arr(p.stages,512) && unique(p.stages.map(s=>s.stage_id)),'E_STAGE_ROWS');
    requireValue(canonical(p.stages.map(s=>s.stage_id).sort()) === canonical(v.stage_details.map(s=>s.stage_id).sort()),'E_STAGE_CATALOG_BINDING');
    for (const s of p.stages) {
      requireValue(id(s.stage_id) && id(s.chapter_id) && STAGE_STATES.includes(s.status) && ['unlocked','valid_confirmed_clear','first_clear_consumed','review_required'].every(k=>typeof s[k] === 'boolean'),'E_STAGE_FIELDS');
      requireValue(!(s.status === 'LOCKED' && s.unlocked) && !(s.review_required && !['REVIEW_REQUIRED','PENDING_RECONCILIATION','IN_PROGRESS'].includes(s.status)),'E_STAGE_INCONSISTENT');
      requireValue(!v.stage_details.find(d=>d.stage_id===s.stage_id).action_enabled || (s.unlocked && !s.review_required && ['AVAILABLE','CLEARED'].includes(s.status) && p.active_battle_id === null),'E_STAGE_ACTION_BINDING');
    }
  } else requireValue(v.stage_details.length === 0,'E_STAGE_DATA_MISSING');
  const l = v.learning;
  requireValue(obj(l) && TRANSPORT.includes(l.connection) && isInt(l.pending_count),'E_LEARNING_TRANSPORT');
  if (l.query !== null) {
    requireValue(obj(l.query) && STATES.includes(l.query.state) && text(l.query.reason) && text(l.query.evidence_scope),'E_LEARNING_STATUS');
    if (l.query.receipt !== null) {
      const r = l.query.receipt;
      requireValue(obj(r) && typeof r.durable === 'boolean' && text(r.origin) && id(r.transaction_id) && HASH.test(r.request_sha256) && id(r.store_instance) && isInt(r.sequence),'E_LEARNING_RECEIPT');
    }
  }
  if (v.settlement !== null) {
    const s = v.settlement;
    requireValue(obj(s) && id(s.battle_id) && id(s.stage_id) && ['WIN','LOSS','DRAW','ABORTED','FAULTED'].includes(s.outcome) && typeof s.claimable === 'boolean' && text(s.decision) && text(s.origin),'E_SETTLEMENT');
    requireValue(s.receipt === null || (obj(s.receipt) && s.receipt.durable === false && ['COMMITTED_SIMULATION','DUPLICATE_NO_OP'].includes(s.receipt.status)),'E_SETTLEMENT_RECEIPT');
    requireValue(!(s.claimable && s.receipt !== null),'E_SETTLEMENT_DOUBLE_STATE');
    requireValue(s.reward_status === undefined || ['PREVIEW','SIMULATED','QUARANTINED','NONE'].includes(s.reward_status),'E_SETTLEMENT_REWARD');
  }
  requireValue(v.mode!=='UNBOUND' || (v.wallet===null && v.characters.length===0 && v.stage_progress===null && v.settlement===null),'E_UNBOUND_PLACEHOLDER_DATA');
  return freeze(copy(v));
}
export function learningLabel(learning, mode='UNBOUND') {
  const q = learning?.query;
  const transport = {DISCONNECTED:'Anki 未连接',CONNECTED:'Anki 连接可用',REDELIVERY:'等待补发',RECONCILING:'正在核对'}[learning?.connection] || '连接状态未知';
  if (!q) return {key:'DISCONNECTED',title:transport,detail:'尚未取得可核验的学习记录。',tone:'muted',credited:false,transport};
  const labels = {
    QUARANTINED:['待核对 · 已隔离','该记录没有计入可用奖励。','warning'],
    PENDING_RECONCILIATION:['待核对','记录或回执尚未核对完成。','warning'],
    REJECTED:['已拒绝','该记录未发放奖励，可查看原因。','danger'],
    REVERTED:['已撤回','原学习记录已撤销；余额以当前钱包为准。','muted'],
    NOT_FOUND:['待补发','尚未查到记录，等待来源端补发。','warning'],
    UNKNOWN:['结果待确认','当前查询无法确认处理结果。','warning'],
  };
  if (q.state === 'APPLIED') {
    // The isolated P20 build deliberately has no production acknowledgement path.
    const simulation = mode === 'FIXTURE' || q.evidence_scope !== 'P21_PRODUCTION' || q.receipt?.origin !== 'P21_PRODUCTION';
    if (simulation) return {key:'APPLIED_SIMULATION',title:'测试记录已处理',detail:'隔离验证记录，不代表真实学习收益。',tone:'info',credited:false,transport};
    return {key:'APPLIED_UNVERIFIED',title:'待核对提交证明',detail:'正式身份与持久提交适配尚未接入。',tone:'warning',credited:false,transport};
  }
  const [title,detail,tone] = labels[q.state] || labels.UNKNOWN;
  return {key:q.state,title,detail,tone,credited:false,transport};
}
export function stageLabel(row) {
  return {AVAILABLE:'可挑战',LOCKED:'未解锁',CLEARED:'已通关',REVIEW_REQUIRED:'进度待核对',IN_PROGRESS:'进行中',PENDING_RECONCILIATION:'结算已隔离'}[row?.status] || '资料未就绪';
}
export const REASONS = {
  E_UNBOUND:'接口尚未接入',E_FEATURE_DISABLED:'装备功能尚未开放',E_XP_INSUFFICIENT:'累计经验不足',
  E_INSUFFICIENT_AVAILABLE:'可用资源不足',E_WALLET_INSUFFICIENT:'可用资源不足',E_LEVEL_CAP:'已达当前等级上限',
  E_LOCKED_STAGE:'请先通关前置关卡',E_STAGE_UNDER_REVIEW:'关卡进度待核对',E_PREREQUISITE_UNDER_REVIEW:'前置关卡正在核对',
  E_ACTIVE_BATTLE_EXISTS:'已有进行中的战斗',E_PARTY_REQUIRED:'请先保存完整三人编队',E_MUTATION_BLOCKED_ACTIVE_BATTLE:'战斗进行中，暂不能变更编队或养成',
  E_SAVE_UNAVAILABLE:'存档尚不可写',E_VIEW_STALE:'数据已变化，请刷新后重新操作',E_REVISION_CONFLICT:'数据版本已变化',
  E_EQUIPMENT_IN_USE:'装备已被其他角色使用',E_EQUIPMENT_LEVEL_GATED:'尚未达到装备等级',E_EQUIPMENT_ROLE:'不适用于该角色',
};
export function reasonText(code) { return REASONS[code] || code || '资料待核对'; }
