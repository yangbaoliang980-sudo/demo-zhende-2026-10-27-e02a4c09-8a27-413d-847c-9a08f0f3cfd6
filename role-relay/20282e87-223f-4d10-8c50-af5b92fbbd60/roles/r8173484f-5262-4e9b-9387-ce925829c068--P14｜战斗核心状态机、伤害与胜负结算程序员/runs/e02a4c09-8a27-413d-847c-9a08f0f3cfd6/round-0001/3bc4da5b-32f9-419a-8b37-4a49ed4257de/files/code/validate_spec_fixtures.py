#!/usr/bin/env python3
"""P02 STATIC SPEC/EXPECTED-EVENT AUDIT ONLY. This is NOT a battle runtime, replay engine or P32 test suite.

Usage:
  python spec/battle/resolution/validate_spec_fixtures.py --upstream-zip /path/to/P01.zip
Checks byte-identity of P01 manifest, TSVs, fixture shape, proposed expected
snapshots against authored event arithmetic, RNG test-vector math and animation
invariance. Does NOT execute P14 code or any gameplay command interpreter.
"""
import argparse, copy, csv, hashlib, io, json, pathlib, sys, zipfile

ROOT=pathlib.Path(__file__).resolve().parents[3]
RES=ROOT/'spec/battle/resolution'
SM=ROOT/'spec/battle/state_machine'
UPSTREAM_SHA='139034e2179fbe35c4ac5f3240b0df435b03b9a70f5507263ee97b7e8b022a89'
checks=0

def require(cond,message):
    global checks
    checks+=1
    if not cond:
        raise AssertionError(f'CHECK {checks}: {message}')

def sha(raw):return hashlib.sha256(raw).hexdigest()

def canonical_command(c):return sha(json.dumps(c,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8'))

def read_tsv(path,minimum,unique_col):
    raw=path.read_bytes(); txt=raw.decode('utf-8-sig'); rdr=csv.DictReader(io.StringIO(txt),delimiter='\t'); rows=list(rdr)
    require(len(rows)>=minimum,f'{path.name}: expected minimum rows {minimum}, got {len(rows)}')
    require(all(set(r)==set(rdr.fieldnames) and all(v is not None for v in r.values()) for r in rows),f'{path.name}: ragged rows')
    require(len({r[unique_col] for r in rows})==len(rows),f'{path.name}: duplicate {unique_col}')
    return rows

def unitmap(s):return {u['unit_id']:u for u in s['combatants']}

def validate_snapshot(s,case,which,cat):
    for key in ('battle_id','revision','event_cursor','phase','turn_number','energy','combatants','zones','processed_commands','random','terminal_outcome'):
        require(key in s,f'{case} {which} missing {key}')
    require(isinstance(s['energy'],int) and not isinstance(s['energy'],bool) and s['energy']>=0,f'{case} {which}: invalid energy')
    require(isinstance(s['revision'],int) and s['revision']>=0,f'{case} {which}: revision')
    require(isinstance(s['event_cursor'],int) and s['event_cursor']>=0,f'{case} {which}: event cursor')
    require(s['random']['algorithm']=='xorshift32-v1',f'{case} {which}: seed algorithm')
    require(isinstance(s['random']['state_u32'],int) and 0<s['random']['state_u32']<2**32,f'{case} {which}: rng state')
    require(isinstance(s['random']['draw_count'],int) and s['random']['draw_count']>=0,f'{case} {which}: random counter')
    ids=[u['unit_id'] for u in s['combatants']]
    require(len(ids)==len(set(ids)),f'{case} {which}: repeated units')
    require(sum(u['side']=='PLAYER' for u in s['combatants'])==3,f'{case} {which}: need exactly three occupied demo slots')
    require(any(u['side']=='ENEMY' for u in s['combatants']),f'{case} {which}: no enemies in fixture')
    for u in s['combatants']:
        require(isinstance(u['max_hp'],int) and u['max_hp']>0 and 0<=u['hp']<=u['max_hp'],f'{case} {which} {u["unit_id"]}: HP invariant')
        require(isinstance(u['shield'],int) and u['shield']>=0,f'{case} {which} {u["unit_id"]}: shield')
        require(u['alive']==(u['hp']>0),f'{case} {which} {u["unit_id"]}: alive/HP mismatch')
        require(len(u['proposed_phases'])==len(set(u['proposed_phases'])),f'{case} {which}: duplicate boss proposal')
    zones=sum((s['zones'][z] for z in ('hand','draw','discard')),[])
    require(len(zones)==len(set(zones)),f'{case} {which}: duplicated card instance across zones')
    require(all(q in cat for q in zones),f'{case} {which}: unknown TEST ONLY card id')
    live_player=sum(u['alive'] and u['side']=='PLAYER' for u in s['combatants'])
    live_enemy=sum(u['alive'] and u['side']=='ENEMY' for u in s['combatants'])
    if s['phase']=='TERMINAL':
        expected=('DRAW' if not live_player and not live_enemy else ('WIN' if live_player and not live_enemy else ('LOSS' if not live_player and live_enemy else 'INVALID')))
        require(s['terminal_outcome']==expected,f'{case} {which}: invalid terminal result {expected}')
    else:
        require(s['terminal_outcome'] is None,f'{case} {which}: result outside terminal')
    require(s['phase'] in ('CREATED','PLAYER_READY','ENEMY_READY','PLAYER_TURN_PENDING','TERMINAL','ABORTED','FAULTED'),f'{case} {which}: unknown phase')


def xorshift32(x):
    x^=(x<<13)&0xffffffff;x&=0xffffffff
    x^=x>>17;x&=0xffffffff
    x^=(x<<5)&0xffffffff;x&=0xffffffff
    return x


def audit_expected_events_against_expected_snapshot(c,cat):
    """Only audits EXPECTED event-to-EXPECTED snapshot arithmetic, NOT a command interpreter."""
    fid=c['fixture_id'];before=c['initial_state'];after=c['expected']['final_state'];events=c['expected']['logic_events']
    b=unitmap(before);a=unitmap(after)
    projected_hp={uid:u['hp'] for uid,u in b.items()};projected_shield={uid:u['shield'] for uid,u in b.items()}
    projected_energy=before['energy'];rng_start=before['random']['draw_count'];rng_result=before['random']['state_u32']
    r_consumed=0;cards_in_zones=copy.deepcopy(before['zones']);boss_props={uid:list(u['proposed_phases']) for uid,u in b.items()}
    for e in events:
        t=e['type']
        if t=='DAMAGE_APPLIED':
            target=e['target_id'];amount=e['raw_amount'];absorbed=e['shield_absorbed'];hp_loss=e['hp_loss'];overkill=e['overkill']
            require(min(amount,projected_shield[target])==absorbed,f'{fid}: shield is not first')
            require(min(amount-absorbed,projected_hp[target])==hp_loss,f'{fid}: HP not clamped')
            require(amount==absorbed+hp_loss+overkill,f'{fid}: overkill accounting')
            projected_shield[target]-=absorbed;projected_hp[target]-=hp_loss
        elif t=='SHIELD_GRANTED':
            target=e['target_id'];require(e['before']==projected_shield[target],f'{fid}: shield before event')
            projected_shield[target]+=e['amount'];require(e['after']==projected_shield[target],f'{fid}: shield after event')
        elif t=='HEAL_APPLIED':
            target=e['target_id'];require(e['before']==projected_hp[target],f'{fid}: heal before')
            require(e['applied']==min(e['requested'],b[target]['max_hp']-projected_hp[target]),f'{fid}: heal cap')
            projected_hp[target]+=e['applied'];require(e['after']==projected_hp[target],f'{fid}: heal after')
        elif t=='ENERGY_SPENT':
            require(projected_energy==e['before'],f'{fid}: energy before spending')
            projected_energy-=e['amount'];require(projected_energy==e['after'] and projected_energy>=0,f'{fid}: energy after spending')
        elif t=='ENERGY_REFRESHED':
            require(projected_energy==e['before'],f'{fid}: energy before refresh')
            projected_energy=e['after']
        elif t=='CARD_MOVED':
            src=e['from_zone'].lower();dst=e['to_zone'].lower();cid=e['card_instance_id']
            require(cid in cards_in_zones[src],f'{fid}: spent card not in {src}')
            cards_in_zones[src].remove(cid);cards_in_zones[dst].append(cid)
        elif t=='DECK_RECYCLED':
            require(not cards_in_zones['draw'],f'{fid}: recycled while not empty in current fixture')
            require(len(cards_in_zones['discard'])==e['count'],f'{fid}: wrong recycle count')
            cards_in_zones['draw']=cards_in_zones['discard'][:];cards_in_zones['discard']=[]
        elif t=='DECK_SHUFFLED':
            order=cards_in_zones['draw'][:];outputs=[]
            for i in range(len(order)-1,0,-1):
                rng_result=xorshift32(rng_result);outputs.append(rng_result)
                j=rng_result%(i+1);order[i],order[j]=order[j],order[i]
            r_consumed+=len(outputs)
            require(outputs==e['rng_outputs'] and order==e['resulting_order'],f'{fid}: RNG shuffled ordering incorrect')
            cards_in_zones['draw']=order
        elif t=='CARD_DRAWN':
            cid=e['card_instance_id'];require(cards_in_zones['draw'] and cards_in_zones['draw'][0]==cid,f'{fid}: draw must take index0')
            cards_in_zones['hand'].append(cards_in_zones['draw'].pop(0))
        elif t=='BOSS_PHASE_PROPOSED':
            uid=e['boss_id'];require(projected_hp[uid]>0,f'{fid}: dead boss phase proposed')
            require(e['phase_id'] not in boss_props[uid],f'{fid}: duplicate boss proposal')
            boss_props[uid].append(e['phase_id'])
        elif t=='UNIT_DIED':
            uid=e['unit_id'];require(projected_hp[uid]==0,f'{fid}: death event before HP zero')
    for uid in b:
        require(projected_hp[uid]==a[uid]['hp'],f'{fid}: event damage/heal does not reconcile with expected HP for {uid}')
        require(projected_shield[uid]==a[uid]['shield'],f'{fid}: event shield does not reconcile with expected shield for {uid}')
        require(boss_props[uid]==a[uid]['proposed_phases'],f'{fid}: phase proposals not persisted once')
    require(projected_energy==after['energy'],f'{fid}: event fee/refill does not reconcile')
    require(cards_in_zones==after['zones'],f'{fid}: zone movements not reconciled')
    require(r_consumed+ rng_start==after['random']['draw_count'],f'{fid}: RNG draw count wrong')
    require(rng_result==after['random']['state_u32'],f'{fid}: RNG state wrong')


def check_upstream(path):
    if path is None:return
    data=path.read_bytes(); require(sha(data)==UPSTREAM_SHA,'P01 upstream zip sha mismatch')
    with zipfile.ZipFile(path) as z:
        require(z.testzip() is None,'P01 upstream CRC failed')
        manifest=list(csv.DictReader(io.StringIO(z.read('manifest.sha256.tsv').decode('utf-8-sig')),delimiter='\t'))
        require(len(manifest)==15,'P01 zip should list 15 self-excluding files')
        require(len(z.namelist())==16,'P01 zip total file count')
        for m in manifest:
            raw=z.read(m['relative_path'])
            require(len(raw)==int(m['actual_bytes']),f'P01 byte mismatch: {m["relative_path"]}')
            require(sha(raw)==m['sha256'],f'P01 SHA mismatch: {m["relative_path"]}')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--upstream-zip',type=pathlib.Path);args=ap.parse_args()
    check_upstream(args.upstream_zip)
    priority=read_tsv(RES/'effect_priority.tsv',30,'priority_id')
    truth=read_tsv(RES/'terminal_phase_truth_table.tsv',24,'case_id')
    sequence=read_tsv(SM/'turn_sequence.tsv',26,'sequence_id')
    require(all(int(row['priority'])<int(priority[i+1]['priority']) for i,row in enumerate(priority[:-1])), 'priority should be strictly increasing')
    require((SM/'battle_state_machine.md').stat().st_size>10000,'state machine document incomplete')
    require((SM/'battle_state_machine.mmd').read_text(encoding='utf-8').startswith('stateDiagram-v2'), 'Mermaid syntax header missing')
    doc=json.loads((RES/'battle_replay_fixtures.json').read_text(encoding='utf-8'))
    require(doc['status']=='EXPECTED_SPEC_ONLY_NOT_EXECUTED_AGAINST_GAME','fixture provenance ambiguity')
    cases=doc['cases'];require(len(cases)>=30,'not enough boundary fixture cases')
    ids=[c['fixture_id'] for c in cases];require(len(ids)==len(set(ids)),'duplicated fixture ID')
    cat=doc['fixture_card_catalogue']
    for c in cases:
        fid=c['fixture_id'];b=c['initial_state'];a=c['expected']['final_state'];events=c['expected']['logic_events'];cmds=c['commands'];results=c['expected']['command_results']
        validate_snapshot(b,fid,'initial',cat);validate_snapshot(a,fid,'final',cat)
        require(b['battle_id']==a['battle_id'],f'{fid}: altered battle ID')
        require(all(cmd['battle_id']==b['battle_id'] for cmd in cmds),f'{fid}: command battle-id mismatch')
        require(len(cmds)==len(results),f'{fid}: command result count mismatch')
        require(all(x['command_id']==cmd['command_id'] for cmd,x in zip(cmds,results)),f'{fid}: result and command index mismatch')
        require(a['event_cursor']==b['event_cursor']+len(events),f'{fid}: event cursor gap')
        require([e['seq'] for e in events]==list(range(b['event_cursor']+1,a['event_cursor']+1)),f'{fid}: nonmonotonic event seq')
        accepted=[cmd for cmd,r in zip(cmds,results) if r['status']=='ACCEPTED']
        require(a['revision']==b['revision']+len(accepted),f'{fid}: each accepted command must increment revision exactly once')
        require(len([e for e in events if e['type']=='COMMAND_ACCEPTED'])==len(accepted),f'{fid}: COMMAND_ACCEPTED count')
        require(len([e for e in events if e['type']=='COMMAND_COMMITTED'])==len(accepted),f'{fid}: commit marker count')
        require(sum(r['status'] in ('REJECTED','DUPLICATE_NO_OP') for r in results)+len(accepted)==len(results),f'{fid}: invalid result category')
        if len(accepted)==0:
            require(b==a and not events,f'{fid}: reject/duplicate mutated authoritative state')
        if events:
            require(events[-1]['type']=='COMMAND_COMMITTED',f'{fid}: accepted command must end in commit')
        progress_ledger=dict(b['processed_commands'])
        for cc,rs in zip(cmds,results):
            if rs['status']=='ACCEPTED':
                require(cc['command_id'] not in progress_ledger,f'{fid}: new accepted ID already seen')
                progress_ledger[cc['command_id']]=canonical_command(cc)
            elif rs['status']=='DUPLICATE_NO_OP':
                require(cc['command_id'] in progress_ledger,f'{fid}: retry command not in sequential ledger')
                require(progress_ledger[cc['command_id']]==canonical_command(cc),f'{fid}: retry fingerprint differs')
            if rs['error_code']=='COMMAND_ID_COLLISION':
                require(cc['command_id'] in progress_ledger and progress_ledger[cc['command_id']]!=canonical_command(cc),f'{fid}: collision scenario invalid')
        require(progress_ledger==a['processed_commands'],f'{fid}: processed ledger inconsistent after ordered commands')
        exits=[e for e in events if e['type']=='BATTLE_FINISHED']
        require(len(exits)<=1,f'{fid}: repeated terminal')
        require(len([e for e in events if e['type']=='UNIT_DIED'])==len({e['unit_id'] for e in events if e['type']=='UNIT_DIED'}),f'{fid}: repeated death event')
        if a['phase']=='TERMINAL' and b['phase']!='TERMINAL':
            require(len(exits)==1 and exits[0]['outcome']==a['terminal_outcome'],f'{fid}: missing/incorrect one terminal event')
        if a['phase'] not in ('TERMINAL',):
            require(not exits,f'{fid}: battle finished event in nonterminal')
        if exits:
            terminal_seq=exits[0]['seq']
            require(all(e['seq']<terminal_seq for e in events if e['type']=='TRIGGER_STARTED'),f'{fid}: premature battle finish before reaction')
            require(not any(e['type']=='BOSS_PHASE_PROPOSED' for e in events),f'{fid}: boss proposal after terminal')
        if len(cmds)==1 and len(accepted)==1:
            require(events[0]['command_id']==cmds[0]['command_id'],f'{fid}: command accepted ID wrong')
        if 'expected_checkpoints' in c['expected']:
            cps=c['expected']['expected_checkpoints']; require(len(cps)==len(cmds),f'{fid}: checkpoint count')
            require(cps[-1]==a,f'{fid}: final checkpoint mismatch')
            for i in range(1,len(cps)):
                if results[i]['status']!='ACCEPTED': require(cps[i]==cps[i-1],f'{fid}: rejected checkpoint mutated')
        audit_expected_events_against_expected_snapshot(c,cat)
    cases_by_id={c['fixture_id']:c for c in cases}
    require(cases_by_id['F001']['initial_state']==cases_by_id['F019']['initial_state'],'animation invariance: start differ')
    require(cases_by_id['F001']['commands']==cases_by_id['F019']['commands'],'animation invariance: commands differ')
    require(cases_by_id['F001']['expected']==cases_by_id['F019']['expected'],'animation invariance: effects differ')
    require(cases_by_id['F001']['presentation_metadata']!=cases_by_id['F019']['presentation_metadata'],'animation invariance: animation metadata should differ')
    require(any(c['fixture_id']=='F030' for c in cases) and any(x['case_id']=='TP-008' for x in truth),'boss terminal-after-retaliation case coverage')
    require('BOSS_PHASE_PROPOSED' not in [e['type'] for e in cases_by_id['F008']['expected']['logic_events']],'boss lethal proposal invalid')
    require('BOSS_PHASE_PROPOSED' not in [e['type'] for e in cases_by_id['F030']['expected']['logic_events']],'boss lethal retaliation proposal invalid')
    require(cases_by_id['F006']['expected']['final_state']['terminal_outcome']=='DRAW','mutual death outcome')
    require(not any(e['type']=='ENERGY_REFRESHED' for e in cases_by_id['F015']['expected']['logic_events']),'DOT death cannot refresh resources')
    require(not any(e['type']=='CARD_DRAWN' for e in cases_by_id['F031']['expected']['logic_events']),'enemy DOT death cannot draw')
    print('PASS P02 static spec checks (NOT a game runtime/P32/P35 test)')
    print('total_static_assertions='+str(checks))
    print('fixture_cases='+str(len(cases)))
    print('priority_rows='+str(len(priority)))
    print('truth_table_rows='+str(len(truth)))
    print('sequence_rows='+str(len(sequence)))
    print('upstream_zip_checked='+str(bool(args.upstream_zip)).lower())
    print('design_static_audit=PASS')
    print('P14_runtime_replay=NOT_RUN')
    print('P13_DTO_contract=BLOCKED')
    print('P32_independent_test=NOT_RUN')
    print('P35_independent_review=NOT_RUN')

if __name__=='__main__':
    try:main()
    except Exception as e:
        print(f'FAIL P02 static audit: {type(e).__name__}: {e}',file=sys.stderr)
        raise
