const text=(tag,value,cls)=>{const e=document.createElement(tag);e.textContent=value;if(cls)e.className=cls;return e;};
const PHASE={CREATED:'战斗准备',PLAYER_READY:'你的回合',ENEMY_READY:'敌方回合',PLAYER_TURN_PENDING:'等待下一回合',TERMINAL:'战斗结束',ABORTED:'战斗中止',FAULTED:'战斗异常'};
const OUTCOME={WIN:'战斗胜利',LOSS:'战斗失败',DRAW:'平局',ABORTED:'已中止',FAULTED:'战斗异常'};
const CATEGORY={ATTACK:['攻击','攻'],DEFENSE:['防御','守'],HEAL:['治疗','愈'],STATUS:['状态','术']};
export const ERRORS={ENERGY_INSUFFICIENT:'费用不足。',TARGET_INVALID:'该目标不能被这张牌选中。',ACTOR_INVALID:'出牌角色当前不可操作。',
  STATUS_REAPPLY_UNDEFINED:'此状态暂不支持重复施加。',PLAY_NOT_READY:'请先选择可用卡牌和完整目标。',SELECT_CARD_FIRST:'请先选择卡牌。',
  INPUT_LOCKED:'状态尚未就绪或上一操作尚未确认。',STALE_INPUT:'状态已更新，请重新选择。',STALE_OR_LOCKED_INPUT:'状态已更新或输入暂不可用。',
  INPUT_DEBOUNCED:'已忽略短时间内的重复输入。',REVISION_CONFLICT:'战斗状态已变化，已请求刷新。',ALREADY_CLOSED:'本场战斗已经结束。',
  CONNECTION_LOST:'连接中断，请刷新状态。',REPLY_TIMEOUT:'操作结果尚未确认，请查询本次操作。',COMMAND_OUTCOME_UNKNOWN:'操作结果未知，请查询本次操作。',
  HUD_CONTEXT_STALE:'卡牌或意图信息尚未与当前状态同步。',HUD_CONTEXT_UNBOUND:'显示接口尚未绑定。',REVISION_COLLISION:'收到同版本但内容冲突的快照，操作已暂停。',
  REPLY_SNAPSHOT_NOT_CURRENT:'尚未取得最新快照，请查询本次操作。',CARD_NOT_IN_HAND:'这张牌已不在手牌中。',PHASE_INVALID:'当前阶段不能出牌。'};
export const errorText=code=>ERRORS[code] || `操作未完成：${code}`;

export function mountHud(controller) {
  const $=id=>document.getElementById(id);
  const label=(view,id)=>view.context?.unit_labels?.find(x=>x.unit_id === id)?.name || id;
  let latest=null;
  const unitNode=(u,v,enemy=false)=>{
    const card=v.context?.cards.find(c=>c.instance_id === v.selectedCard);
    const targetable=!!(v.canSelect && card?.allowed_target_sets.some(set=>set.includes(u.unit_id)));
    const selected=v.selectedTargets.includes(u.unit_id);
    const button=document.createElement('button');button.type='button';button.className=`unit ${enemy?'enemy-card':''} ${targetable?'targetable':''} ${selected?'selected-target':''} ${u.hp===0?'dead':''}`;
    button.dataset.unitId=u.unit_id;button.dataset.focusKey='unit:'+u.unit_id;button.dataset.hp=String(u.hp);button.dataset.shield=String(u.shield);
    button.disabled=!targetable;button.setAttribute('aria-pressed',String(selected));
    button.setAttribute('aria-label',`${label(v,u.unit_id)}，生命 ${u.hp}/${u.max_hp}，护盾 ${u.shield}${u.hp===0?'，已倒下':''}${targetable?'，可选目标':''}`);
    button.onclick=()=>controller.selectTarget(u.unit_id,v.snapshot.revision);
    if(enemy){button.append(text('div','ENEMY / 占位卡面','enemy-kind'));const emblem=text('div','','enemy-emblem');emblem.append(text('span',String(u.slot+1).padStart(2,'0')));button.append(emblem,text('div',label(v,u.unit_id),'unit-name'));}
    else {const top=text('div','','unit-top');top.append(text('div',String.fromCharCode(65+u.slot),`portrait char-${String.fromCharCode(97+u.slot)}`));const names=text('div','');names.append(text('div',label(v,u.unit_id),'unit-name'),text('div',`阵位 ${u.slot+1} · ${u.hp===0?'已倒下':'参战中'}`,'unit-sub'));top.append(names);button.append(top);}
    const stats=text('div','','unit-values');stats.append(text('span',`HP ${u.hp} / ${u.max_hp}`,'hp-label'),text('span',`护盾 ${u.shield}`,'shield-label'));button.append(stats);
    const bar=text('div','','hp-track');bar.setAttribute('role','progressbar');bar.setAttribute('aria-label',`${label(v,u.unit_id)}生命`);bar.setAttribute('aria-valuenow',String(u.hp));bar.setAttribute('aria-valuemin','0');bar.setAttribute('aria-valuemax',String(u.max_hp));
    const fill=text('div','','hp-fill');fill.style.transform=`scaleX(${u.hp/u.max_hp})`;bar.append(fill);button.append(bar);
    const statuses=text('div','','status-list');for(const s of u.statuses)statuses.append(text('span',`${s.status_id} ×${s.stacks} · 剩余 ${s.remaining_triggers}`,'status-pill'));
    const boss=v.snapshot.boss_states.find(b=>b.unit_id===u.unit_id);if(boss)statuses.append(text('span',`当前阶段 ${boss.current_phase_id}`,'status-pill'));
    if(statuses.childNodes.length)button.append(statuses);
    if(targetable)button.append(text('div',selected?'已选择目标':'点击选择目标','target-help'));
    return button;
  };
  const render=v=>{
    latest=v;const focused=document.activeElement?.dataset?.focusKey;
    const s=v.snapshot;
    $('energy').textContent=s?String(s.energy):'—';$('phase-label').textContent=s?PHASE[s.phase]:'正在连接';
    $('turn-label').textContent=s?`第 ${s.turn_number} 回合`:'第 — 回合';$('revision-label').textContent=s?`状态版本 ${s.revision}`:'等待快照';
    const banner=$('connection-banner');banner.classList.toggle('warning',v.connection!=='READY'||v.stale||!!v.pending);
    banner.textContent=v.pending?.state==='UNKNOWN'?'操作结果未知。保留本次操作编号，请点击“查询本次操作”。':v.pending?'正在等待操作结果，暂时停止新的出牌。':v.suspended?'窗口已进入后台，恢复后将重新同步。':v.connection==='DISCONNECTED'?'连接中断，显示的是最后一次已确认状态。':v.stale?'正在同步最新战斗状态…':'状态已同步。数字与血条均显示已提交终态，关闭演出也可操作。';
    $('transport-label').textContent=v.connection==='READY'?'本地验证台 · 已同步':'本地验证台 · 等待同步';
    $('party').replaceChildren();$('enemies').replaceChildren();$('hand').replaceChildren();$('pile-counts').replaceChildren();
    if(s){
      s.units.filter(u=>u.side==='PLAYER').sort((a,b)=>a.slot-b.slot).forEach(u=>$('party').append(unitNode(u,v)));
      for(const u of s.units.filter(u=>u.side==='ENEMY').sort((a,b)=>a.slot-b.slot)){
        const wrapper=text('div','','enemy-wrapper');wrapper.append(unitNode(u,v,true));
        const i=v.context?.intents.find(i=>i.actor_id===u.unit_id);const intent=text('div','','enemy-intent');intent.dataset.intentFor=u.unit_id;
        if(i){intent.append(text('strong',`${i.label} · 基础 ${i.base_amount} × ${i.hit_count}`),text('div',`目标：${i.target_ids.map(id=>label(v,id)).join('、')||'无'}`,'intent-targets'),text('small',i.provenance==='P16_PREVIEW_CANDIDATE_ONLY'?'P16 候选预告 · 尚未由核心提交':'脚本测试预告 · 基础值不是实际掉血'));}
        else intent.append(text('span',s.outcome==='ONGOING'?'意图尚未同步':'本场已结束'));
        wrapper.append(intent);$('enemies').append(wrapper);
      }
      const viewMap=new Map((v.context?.cards||[]).map(c=>[c.instance_id,c]));
      for(const iid of s.zones.hand){
        const inst=s.card_instances.find(c=>c.instance_id===iid), card=viewMap.get(iid);
        const b=document.createElement('button');b.type='button';b.className='hand-card'+(v.selectedCard===iid?' selected-card':'');b.dataset.cardId=iid;b.dataset.focusKey='card:'+iid;b.dataset.category=card?.category||'';
        b.disabled=!(v.canSelect&&card?.enabled);b.setAttribute('aria-pressed',String(v.selectedCard===iid));
        b.onclick=()=>controller.selectCard(iid,s.revision);
        const [kind,glyph]=CATEGORY[card?.category]||['待同步','?'];const top=text('div','','card-top');top.append(text('span',card?String(card.cost):'?','card-cost'),text('span',kind,'card-kind'));b.append(top,text('div',glyph,'card-ornament'),text('div',card?.name||inst.card_id,'card-name'),text('div',card?.description||'等待只读显示信息','card-desc'));
        if(card&&!card.enabled)b.append(text('div',errorText(card.reason_code),'card-disabled-reason'));
        b.append(text('div',`归属 · ${label(v,inst.owner_unit_id)}`,'card-owner'));b.setAttribute('aria-label',`${card?.name||inst.card_id}，费用 ${card?.cost??'待同步'}，${card?.description||''}${card&&!card.enabled?'，'+errorText(card.reason_code):''}`);$('hand').append(b);
      }
      if(!s.zones.hand.length)$('hand').append(text('p',s.outcome==='ONGOING'?'手牌为空，可结束回合。':'本场战斗结束。','empty-state'));
      for(const [key,name] of [['draw','抽牌堆'],['discard','弃牌堆'],['exhaust','移除']]){const e=text('span',name);e.append(text('b',String(s.zones[key].length)));e.dataset.pile=key;$('pile-counts').append(e);}
    }
    $('hand-count').textContent=s?String(s.zones.hand.length):'0';
    const chosen=v.context?.cards.find(c=>c.instance_id===v.selectedCard);
    $('selection-hint').textContent=chosen?`已选 ${chosen.name} · ${v.selectedTargets.length?'目标：'+v.selectedTargets.map(id=>label(v,id)).join('、'):'请选择描边标记的目标'}`:'选择卡牌，再选择目标。';
    $('play').disabled=!v.canPlay;$('end-turn').disabled=!v.canEndTurn;
    $('play').onclick=()=>controller.play(s?.revision);$('end-turn').onclick=()=>controller.endTurn(s?.revision);
    $('retry').hidden=v.pending?.state!=='UNKNOWN';$('retry').disabled=v.suspended;
    $('refresh').disabled=v.pending?.state==='SENDING';
    $('input-status').textContent=v.pending?'正在确认操作，请稍候。':v.canPlay?'卡牌与目标已选定，点击“确认出牌”。':s?.outcome!=='ONGOING'&&s?'战斗已结束。':v.canSelect?'选择手牌和目标后确认出牌。':'等待可操作状态。';
    $('error-message').hidden=!v.error;$('error-message').textContent=v.error?errorText(v.error):'';
    $('outcome').hidden=!s||s.outcome==='ONGOING';$('outcome').textContent=s?OUTCOME[s.outcome]||'':'';
    $('presentation-note').textContent='无动效降级可用 · 终态由快照直接展示';
    $('battle-log').replaceChildren();
    const logs=v.logs.filter(l=>!['COMMITTED','DUPLICATE_NO_OP'].includes(l.code)).slice(-8).reverse();
    for(const l of logs){const li=text('li','');const d=l.data||{};
      if(l.code==='DAMAGE_APPLIED'){li.append(text('span','实际伤害','log-label'),text('span',`${label(v,d.target_unit_id)}：HP -${d.hp_loss}，护盾吸收 ${d.absorbed}`));}
      else if(l.code==='HEAL_APPLIED'){li.append(text('span','治疗结算','log-label'),text('span',`${label(v,d.target_unit_id)}：${formatData(d)}`));}
      else if(l.code==='SHIELD_CHANGED'){li.append(text('span','护盾结算','log-label'),text('span',`${label(v,d.target_unit_id)}：${formatData(d)}`));}
      else if(l.code==='BATTLE_FINISHED')li.append(text('span','战斗结束','log-label'),text('span',OUTCOME[d.outcome]||d.outcome));
      else li.append(text('span','操作提示','log-label'),text('span',errorText(l.code)));
      $('battle-log').append(li);
    }
    if(!logs.length)$('battle-log').append(text('li','出牌后在此查看实际结算记录。'));
    if(focused){const next=[...document.querySelectorAll('[data-focus-key]')].find(e=>e.dataset.focusKey===focused&&!e.disabled);if(next)next.focus({preventScroll:true});else {$('input-status').tabIndex=-1;$('input-status').focus({preventScroll:true});}}
  };
  $('refresh').onclick=()=>controller.refresh();$('retry').onclick=()=>controller.retryPending();
  $('motion-mode').onchange=e=>controller.setPresentationMode(e.target.value);$('skip-motion').onclick=()=>controller.skipPresentation();
  const keyHandler=e=>{if(e.repeat&&['Enter',' '].includes(e.key))e.preventDefault();if(e.key==='Escape')controller.clearSelection();};
  document.addEventListener('keydown',keyHandler);
  const unsubscribe=controller.subscribe(render);
  return {unmount(){unsubscribe();document.removeEventListener('keydown',keyHandler);}, anchors(){const result={units:[],cards:[]};for(const [selector,key,id]of [['[data-unit-id]','units','unitId'],['[data-card-id]','cards','cardId']])for(const e of document.querySelectorAll(selector)){const r=e.getBoundingClientRect();result[key].push({id:e.dataset[id],x:Math.round(r.x),y:Math.round(r.y),width:Math.round(r.width),height:Math.round(r.height)});}return result;},current:()=>latest};
}
function formatData(d){if(d.hp_after!==undefined)return `该次结算后 HP ${d.hp_after}`;if(d.shield_after!==undefined)return `该次结算后护盾 ${d.shield_after}`;return '已结算';}
