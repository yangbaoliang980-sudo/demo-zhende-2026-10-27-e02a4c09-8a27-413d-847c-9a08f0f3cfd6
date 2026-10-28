#!/usr/bin/env python3
"""P03-only static content validator. Does NOT implement P15/P14 game runtime."""
from __future__ import annotations
import argparse,collections,copy,csv,hashlib,io,itertools,json,pathlib,sys,zipfile

ROOT=pathlib.Path(__file__).resolve().parents[2]
S={'checks':0,'negative_cases':0}

def need(cond, msg):
    S['checks']+=1
    if not cond: raise AssertionError(msg)

def read(rel): return json.loads((ROOT/rel).read_text(encoding='utf-8'))

def scan_catalog(cat):
    all_ids=[]
    characters=cat['fixture_only_character_slots'];skills=cat['skills'];effects=cat['effects'];cards=cat['cards']
    for group,field in [(characters,'character_id'),(skills,'skill_id'),(effects,'effect_id'),(cards,'card_id')]:
        ids=[x[field] for x in group]
        need(len(set(ids))==len(ids),f'duplicate {field}')
        need(all(isinstance(x,str) and x.startswith('MOCK_P03_') for x in ids),f'nonmock {field}')
        all_ids+=ids
    need(len(set(all_ids))==len(all_ids),'cross-kind duplicate local ID')
    cm={c['character_id']:c for c in characters}; sm={s['skill_id']:s for s in skills}
    em={e['effect_id']:e for e in effects}; cardmap={x['card_id']:x for x in cards}
    need(len(characters)==4,'fixture-only roster must stay explicit')
    need(len(skills)==4,'each fixture slot has one mock skill')
    need(len(cards)==10 and len(effects)==10,'draft size changed without review')
    for s in skills:
        need(s['character_id'] in cm,f'skill owner missing: {s["skill_id"]}')
        need(s['card_id'] in cardmap,f'skill card missing {s["skill_id"]}')
        need(cardmap[s['card_id']]['owner_character_id']==s['character_id'],'skill-card owner mismatch')
    for ch in characters:
        need(ch['skill_id'] in sm and sm[ch['skill_id']]['character_id']==ch['character_id'],'fixture character skill linkage')
        need(ch['signature_card_id'] in cardmap,'fixture character signature reference missing')
        need(sm[ch['skill_id']]['card_id']==ch['signature_card_id'],'character skill-card cross-reference')
    for e in effects:
        need(e['effect_code'] in ('DAMAGE','SHIELD','HEAL','STATUS'),'invalid test effect code')
        need(type(e['amount']) is int and e['amount']>=0,'effect amount must be unsigned integer')
        need(e['target_side'] in ('PLAYER','ENEMY'),'invalid effect target side')
        if e['effect_code']=='STATUS':
            need(e['status_kind'] in ('DOT','BUFF','DEBUFF'),'unknown status kind')
            need(e['status_id'].startswith('MOCK_P03_'),'status namespace')
            need(type(e['remaining_owner_turns']) is int and e['remaining_owner_turns']>0,'invalid mock duration')
            if e['status_kind'] in ('BUFF','DEBUFF'):
                need(e['contract_gate']=='BLOCKED_PENDING_BUFF_DEBUFF_CONTRACT','unapproved modifier gate')
            else:
                need(e['tick_at']=='OWNER_TURN_ENTER','DOT timing misaligned with P02 test')
    active=[]
    for c in cards:
        need(type(c['cost']['amount']) is int and c['cost']['amount']>=0,'card cost nonnegative int required')
        need(c['cost']['resource']=='BATTLE_ENERGY','wrong test resource')
        t=c['target_rule'];need(t['selector']=='EXPLICIT_SINGLE' and t['target_count']==1 and t['living_only'] is True,'invalid target selector')
        need(t['side'] in ('PLAYER','ENEMY'),'invalid target side')
        need(c['effect_ids'] and len(set(c['effect_ids']))==len(c['effect_ids']),'empty/duplicated effect refs')
        for eid in c['effect_ids']:
            need(eid in em,f'dangling effect_id {eid}')
            need(em[eid]['target_side']==t['side'],'card/effect target mismatch')
        need(c['trigger_code']=='ON_PLAY' and c['zone_after_play']=='DISCARD','unsupported content timing/zone')
        if c['scope']=='SIGNATURE':
            need(c['owner_character_id'] in cm and c['skill_id'] in sm,'dangling owner/skill')
            need(sm[c['skill_id']]['character_id']==c['owner_character_id'] and sm[c['skill_id']]['card_id']==c['card_id'],'signature skill reverse mismatch')
        else:
            need(c['owner_character_id'] is None and c['skill_id'] is None,'common draft ownership incorrect')
        if c['mock_playable']:
            active.append(c)
            need(c['gate']=='PROVISIONAL_S01_S02_TEST_ONLY','active card gate')
            need(all(em[eid].get('status_kind') not in ('BUFF','DEBUFF') for eid in c['effect_ids']),'modifier incorrectly activated')
        else:
            need(c['gate']=='BLOCKED_CONTRACT_EXTENSION','missing blocked gate')
            need(all(em[eid].get('status_kind') in ('BUFF','DEBUFF') for eid in c['effect_ids']),'unexpected blocked effect')
    need(len(active)==8,'mock activity scope changed')
    s01=[c for c in cards if c['introduction_stage']=='S01']
    need(len(s01)==3 and all(c['scope']=='COMMON' for c in s01),'S01 not 3 base cards')
    need({c['category'] for c in s01}=={'ATTACK','DEFENSE','HEAL'},'wrong three S01 categories')
    need({c['category'] for c in active}=={'ATTACK','DEFENSE','HEAL','STATUS'},'S02 four mock categories missing')
    return cm,sm,em,cardmap

def check_decks(catalog,decks):
    chars,cskills,eff,bycard=scan_catalog(catalog)
    fixtures=decks['fixtures'];common=decks['common_card_copies']
    need(len(fixtures)==24,'24 mock ordered party enumerations required')
    active={x['card_id'] for x in catalog['cards'] if x['mock_playable']}
    need(all(type(n) is int and n>0 for n in common.values()),'invalid common copies')
    need(sum(common.values())==6,'mock common count mismatch')
    allteams=set(); all_signature_groups=set()
    for fixture in fixtures:
        party=fixture['ordered_party_character_ids'];key=tuple(party)
        need(len(party)==3 and len(set(party))==3 and all(x in chars for x in party),'mock party invalid')
        need(key not in allteams,'duplicate team enumeration')
        allteams.add(key)
        expected=[k for k in common for _ in range(common[k])]
        expected += [chars[c]['signature_card_id'] for c in party]
        deck=fixture['catalog_card_instances']
        templates=[x['card_id'] for x in deck]
        need(templates==expected,'deck construction order/multiset mismatch')
        need(len(deck)==len(set(x['card_instance_id'] for x in deck))==9,'duplicate card instance or wrong deck size')
        need(all(x in bycard and x in active for x in templates),'dangling/inactive deck card')
        need(fixture['signature_card_ids']==[chars[c]['signature_card_id'] for c in party],'signature order mismatch')
        need(fixture['total_cards']==len(deck),'deck total mismatch')
        all_signature_groups.add(frozenset(fixture['signature_card_ids']))
    need(allteams==set(itertools.permutations(chars,3)),'not all ordered fixture parties')
    need(len(all_signature_groups)==4,'four mock role pool differences expected')

def choose(scenario,instance,actor,target,bycard,byeff):
    """Fixed input content-only oracle; never mutates BattleState/deck/energy."""
    cid=scenario['hand'].get(instance);c=bycard.get(cid)
    if c is None:return 'CARD_NOT_IN_HAND',0,0,0,'',scenario['energy']
    price=c['cost']['amount'];ef=byeff[c['effect_ids'][0]]
    if not c['mock_playable']:return 'CONTRACT_BLOCKED',price,0,0,'',scenario['energy']
    if c['scope']=='SIGNATURE' and actor!=c['owner_character_id']:return 'ACTOR_SKILL_MISMATCH',price,0,0,'',scenario['energy']
    u=next((x for x in scenario['units'] if x['unit_id']==target),None)
    if actor not in scenario['party'] or u is None or not u['alive'] or c['target_rule']['side']!=u['side']:
        return 'TARGET_INVALID',price,0,0,'',scenario['energy']
    if scenario['energy']<price:return 'ENERGY_INSUFFICIENT',price,0,0,'',scenario['energy']
    hp,shield,status=0,0,''
    if ef['effect_code']=='DAMAGE':
        absorbed=min(u['shield'],ef['amount']); hp=-min(u['hp'],ef['amount']-absorbed);shield=-absorbed
    elif ef['effect_code']=='SHIELD':shield=ef['amount']
    elif ef['effect_code']=='HEAL':hp=min(ef['amount'],u['max_hp']-u['hp'])
    elif ef['effect_code']=='STATUS' and ef['status_kind']=='DOT':status=ef['status_id']
    else:raise AssertionError('Unsupported effect presented as legal')
    return 'LEGAL_TEST_ONLY',price,hp,shield,status,scenario['energy']-price

def check_choices(cat,samples,tsv_path):
    _,_,eff,cards=scan_catalog(cat)
    samples={s['scenario_id']:s for s in samples['scenarios']}
    cases=list(csv.DictReader(open(tsv_path,encoding='utf-8',newline=''),delimiter='\t'))
    need(len(cases)>=12,'too few legal/illegal choice fixture cases')
    seen=set();legal_by_scenario=collections.defaultdict(list)
    for x in cases:
        need(x['case_id'] not in seen,'duplicate choice case');seen.add(x['case_id'])
        need(x['scenario_id'] in samples,'missing choice scenario')
        s=samples[x['scenario_id']]
        need(s['battle_phase']=='PLAYER_READY','not player phase')
        expected=choose(s,x['card_instance_id'],x['actor_id'],x['target_id'],cards,eff)
        fields=('expected_gate','cost_TEST_ONLY','target_hp_delta','target_shield_delta','expected_status_id','expected_energy_if_selected')
        actual=(x['expected_gate'],int(x['cost_TEST_ONLY']),int(x['target_hp_delta']),int(x['target_shield_delta']),x['expected_status_id'],int(x['expected_energy_if_selected']))
        need(expected==actual, f'choice static expectation mismatch {x["case_id"]}')
        need(x['card_id']==s['hand'].get(x['card_instance_id'],'MISSING_INSTANCE'),'wrong card instance template')
        if expected[0]=='LEGAL_TEST_ONLY':legal_by_scenario[s['scenario_id']].append(cards[x['card_id']]['category'])
    need(len(legal_by_scenario['S-A'])>=2,'S-A no two legal card actions')
    need(len(set(legal_by_scenario['S-A']))>=2,'S-A choices have no tactical differentiation')
    need({'ATTACK','DEFENSE','HEAL','STATUS'}.issubset(set(legal_by_scenario['S-A'])),'four kinds missing in same-scene fixture')
    need({'ATTACK','DEFENSE','HEAL'}.issubset(set(legal_by_scenario['S-B'])),'signature roles insufficiently distinguished')

def check_examples(catalog,examples):
    _,_,effects,cards=scan_catalog(catalog)
    exs=examples['examples'];need(len(exs)==len(cards),'example count must cover each card once')
    for ex in exs:
        need(ex['card_id'] in cards,'example references unknown card')
        need(ex['effect_id'] in effects and ex['effect_id'] in cards[ex['card_id']]['effect_ids'],'example effect not attached')
        e=effects[ex['effect_id']];state=ex['input_context'];result=ex['static_expected']
        if not cards[ex['card_id']]['mock_playable']:
            need(ex['verification_layer'].startswith('NOT_RUN') and result['approval']=='BLOCKED','unapproved status masquerades as tested')
        elif e['effect_code']=='DAMAGE':
            absorbed=min(state['enemy_shield'],e['amount']); loss=min(state['enemy_hp'],e['amount']-absorbed)
            need(result['shield_absorbed']==absorbed and result['hp_loss']==loss and result['enemy_hp_after']==state['enemy_hp']-loss,'damage arithmetic')
        elif e['effect_code']=='SHIELD':
            need(result['ally_shield_after']==state['ally_shield']+e['amount'] and state['cap_policy']=='ASSUME_NO_CAP_FOR_EXAMPLE','shield example assumes no cap')
        elif e['effect_code']=='HEAL':
            healed=min(e['amount'],state['ally_max_hp']-state['ally_hp'])
            need(result['heal_applied']==healed and result['ally_hp_after']==state['ally_hp']+healed,'heal clamp')
        elif e['effect_code']=='STATUS' and e['status_kind']=='DOT':
            need(result['enemy_hp_immediately_after']==state['enemy_hp'],'DOT incorrectly immediate')
            need(result['status_added']==e['status_id'] and result['tick_damage_TEST_ONLY']==e['amount'] and result['owner_turns']==e['remaining_owner_turns'],'status shape mismatch')

def expect_reject(call, phrase):
    try:call()
    except (AssertionError,KeyError,TypeError,ValueError):
        S['negative_cases']+=1;return
    raise AssertionError('NEGATIVE_TEST_FAILED: '+phrase)

def verify_upstream(path):
    with zipfile.ZipFile(path) as z:
        need(z.testzip() is None, f'upstream CRC failed: {path}')
        rows=list(csv.DictReader(io.StringIO(z.read('manifest.sha256.tsv').decode('utf-8-sig')),delimiter='\t'))
        for row in rows:
            bs=z.read(row['relative_path'])
            need(len(bs)==int(row['actual_bytes']),f'wrong source length: {row["relative_path"]}')
            need(hashlib.sha256(bs).hexdigest()==row['sha256'],f'wrong upstream hash: {row["relative_path"]}')
        return len(rows)

def main():
    args=argparse.ArgumentParser()
    args.add_argument('--p01',type=pathlib.Path);args.add_argument('--p02',type=pathlib.Path)
    options=args.parse_args()
    cat=read('content/cards/card_catalog.json')
    decks=read('content/cards/deck_build_fixtures.json')
    scen=read('content/cards/choice_scenarios.json')
    examples=read('content/cards/card_effect_examples.json')
    need(cat['release_status']=='ISOLATED_TEST_ONLY_NOT_APPROVED_FOR_RUNTIME','misleading release status')
    need(not any(cat['approval_flags'].values()),'unexpected policy approval')
    scan_catalog(cat)
    check_decks(cat,decks)
    check_choices(cat,scen,ROOT/'content/cards/card_choice_cases.tsv')
    check_examples(cat,examples)
    # Test the validator fails when core content invariants are deliberately corrupted.
    def mutate_and_scan(mutator):
        clone=copy.deepcopy(cat);mutator(clone);scan_catalog(clone)
    expect_reject(lambda:mutate_and_scan(lambda v:v['cards'].append(copy.deepcopy(v['cards'][0]))),'duplicate card ID')
    expect_reject(lambda:mutate_and_scan(lambda v:v['cards'][0]['effect_ids'].append('MOCK_P03_EF_MISSING')),'dangling effect ID')
    expect_reject(lambda:mutate_and_scan(lambda v:v['cards'][0]['cost'].__setitem__('amount',-1)),'negative fee')
    expect_reject(lambda:mutate_and_scan(lambda v:v['cards'][4].__setitem__('owner_character_id','MOCK_P03_MISSING')),'dangling signature owner')
    expect_reject(lambda:mutate_and_scan(lambda v:v['cards'][8].__setitem__('mock_playable',True)),'unapproved buff enabled')
    def corrupted_deck():
        d=copy.deepcopy(decks);d['fixtures'][0]['catalog_card_instances'][0]['card_id']='MOCK_P03_MISSING';check_decks(cat,d)
    expect_reject(corrupted_deck,'dangling deck template')
    if options.p01:
        need(hashlib.sha256(options.p01.read_bytes()).hexdigest()==cat['source_p01_zip_sha256'],'P01 zip SHA differs')
        count=verify_upstream(options.p01)
        need(count==15,'P01 manifest row count mismatch')
    if options.p02:
        need(hashlib.sha256(options.p02.read_bytes()).hexdigest()==cat['source_p02_zip_sha256'],'P02 zip SHA differs')
        count=verify_upstream(options.p02)
        need(count==14,'P02 manifest row count mismatch')
    print('P03_STATIC_CONTENT_VALIDATION: PASS')
    print(f'cards={len(cat["cards"])} active_mock_cards={len([c for c in cat["cards"] if c["mock_playable"]])} proposed_blocked_cards=2')
    print(f'character_fixture_slots={len(cat["fixture_only_character_slots"])} ordered_parties={len(decks["fixtures"])} choice_cases={len(list(csv.DictReader(open(ROOT/"content/cards/card_choice_cases.tsv",encoding="utf-8"),delimiter=chr(9))))}')
    print(f'effect_examples={len(examples["examples"])} validator_checks={S["checks"]} negative_mutation_tests_rejected={S["negative_cases"]}')
    print(f'upstream_P01_manifest={"15/15 verified" if options.p01 else "NOT_RUN"} upstream_P02_manifest={"14/14 verified" if options.p02 else "NOT_RUN"}')
    print('P13_SCHEMA/P22_GLOBAL_ID/P15_DECKPATCH/P14_RUNTIME/P32_INDEPENDENT/P35_GATE: NOT_RUN_OR_BLOCKED')

if __name__=='__main__':
    try: main()
    except Exception as error:
        print('P03_STATIC_CONTENT_VALIDATION: FAIL',type(error).__name__,str(error),file=sys.stderr)
        raise
