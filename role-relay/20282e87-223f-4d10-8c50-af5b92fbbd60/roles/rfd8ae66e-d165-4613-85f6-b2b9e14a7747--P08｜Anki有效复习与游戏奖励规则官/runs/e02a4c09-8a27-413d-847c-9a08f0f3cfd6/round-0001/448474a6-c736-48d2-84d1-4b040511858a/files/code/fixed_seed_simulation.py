#!/usr/bin/env python3
"""P05 isolated deterministic shadow simulator, not P14 gameplay or P11 Anki award code.

No writes to the game repository or real wallet. Inputs are pinned, read-only copies.
Usage from package root:
    python analysis/simulations/fixed_seed_simulation.py --seed 20261028
    python analysis/simulations/fixed_seed_simulation.py --seed 20261028 --verify
    python analysis/simulations/fixed_seed_simulation.py --seed 20261028 --output /tmp/p05.csv
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

VERSION = 'P05-BALANCE-0.1.0-provisional'
ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = ROOT / 'evidence' / 'readonly_upstream'
EXPECTED_HASHES = {
    'p03_card_catalog.json': 'f29c89dbc98eb4d4d048ed58ab03494abbf05a40edfcfa8ada5efc1b16ea829e',
    'p04_character_skeleton.json': '39a7728a53165c9ef8953fa5b232efe900a5d1a4a6fd40ffe038581ea6c39515',
    'p04_progression_costs.tsv': '5c872fb5ac0a0834ecdfe270a6dd81a42c10aaecf8d58559b822b1fcdc4df41f',
    'p04_character_deck_contribution.tsv': '2d4d3e09557d801749d44a24c1da405351e28fcadf0c23be52f0c07088daa06a',
    'p02_effect_priority.tsv': '85867d50fd7ca02d00ef8630a9e201295739a55833207cc6ea4eac89774ccbc5',
    'p01_decisions_pending.tsv': '3acc747185cb78215d30a54c9b855f4d7e34987c9fd46ed6f323752740e498c4',
}
REQUIRED_CARDS = {'MOCK_P03_CARD_STRIKE', 'MOCK_P03_CARD_BARRIER',
                  'MOCK_P03_CARD_RECOVER', 'MOCK_P03_CARD_EMBER',
                  'MOCK_P03_CARD_A_EDGE', 'MOCK_P03_CARD_B_WALL',
                  'MOCK_P03_CARD_C_MEND'}
COLUMNS = ['row_id','group','scenario','model_version','parameters_sha256','source_p03_sha256',
           'source_p04_sha256','source_p02_sha256','seed','status','outcome','turns',
           'enemy_hp_initial','enemy_hp_remaining','party_hp_initial','party_hp_remaining',
           'damage_hp_to_enemy','damage_hp_to_party','damage_absorbed_by_shield',
           'shield_granted','heal_effective','battle_energy_spent','cards_played','dot_ticks',
           'first_round_enemy_hp_damage','max_round_enemy_hp_damage','player_units_alive',
           'study_attempts','valid_unique_events','deduplicated_attempts','id_collisions',
           'untrusted_quarantined','undo_events','shadow_awarded_gross','shadow_undo_reversed',
           'shadow_net','stage_token_income','stage_xp_per_character','token_budget_total',
           'token_spent_on_levels','token_balance','level_upgrades','skill_upgrades',
           'notes']


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha_check() -> None:
    for filename, sha in EXPECTED_HASHES.items():
        candidate = UPSTREAM / filename
        assert candidate.is_file() and digest(candidate) == sha, 'PINNED_INPUT_HASH_MISMATCH:' + filename
    assert ROOT.joinpath('content/balance/balance_parameters.tsv').is_file()


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def load_inputs() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, str]], list[dict[str, str]], dict[str, int]]:
    sha_check()
    cards = json.loads((UPSTREAM / 'p03_card_catalog.json').read_text(encoding='utf-8'))
    people = json.loads((UPSTREAM / 'p04_character_skeleton.json').read_text(encoding='utf-8'))
    deck_rows = read_tsv(UPSTREAM / 'p04_character_deck_contribution.tsv')
    cost_rows = read_tsv(UPSTREAM / 'p04_progression_costs.tsv')
    param_rows = read_tsv(ROOT / 'content/balance/balance_parameters.tsv')
    params = {r['parameter_id']: int(r['value']) for r in param_rows if r['section'] not in ('GROWTH_REFERENCE', 'GROWTH_COST_REFERENCE', 'CARD_REFERENCE', 'EFFECT_REFERENCE')}
    assert len(params) == len([r for r in param_rows if r['section'] not in ('GROWTH_REFERENCE', 'GROWTH_COST_REFERENCE', 'CARD_REFERENCE', 'EFFECT_REFERENCE')]), 'DUPLICATE_PARAM_ID'
    assert len(people['characters']) == 3 and len(cards['cards']) == 10
    active = {c['card_id'] for c in cards['cards'] if c['mock_playable']}
    assert len(active) == 8 and REQUIRED_CARDS <= active
    assert len(cost_rows) == 21
    card_ref = {c['card_id']: c for c in cards['cards']}
    effect_ref = {e['effect_id']: e for e in cards['effects']}
    for r in param_rows:
        name = r['parameter_id']
        if name.startswith('P03/CARD/'):
            card_id = name.split('/')[2]
            assert int(r['value']) == card_ref[card_id]['cost']['amount'], 'P03_CARD_REFERENCE_DRIFT'
        elif name.startswith('P03/EFFECT/'):
            effect_id = name.split('/')[2]
            assert int(r['value']) == effect_ref[effect_id]['amount'], 'P03_EFFECT_REFERENCE_DRIFT'
        elif name.startswith('P04/') and r['section'] == 'GROWTH_REFERENCE':
            c = next(x for x in people['characters'] if x['character_id'] == r['scope'])
            field = r['metric'].removesuffix('_lv1').removesuffix('_per_level')
            src = c['base_stats'] if r['metric'].endswith('_lv1') else c['per_level_growth']
            assert int(r['value']) == src[field], 'P04_GROWTH_REFERENCE_DRIFT'
        elif r['section'] == 'GROWTH_COST_REFERENCE':
            raw = next(x for x in cost_rows if 'P04/COST/' + x['row_id'] == name)
            assert int(r['value']) == int(raw['spend_amount']), 'P04_COST_REFERENCE_DRIFT'
    assert all(0 <= c['cost']['amount'] <= 100 for c in cards['cards'])
    assert all(x['resource'] == 'BATTLE_ENERGY' for x in [c['cost'] for c in cards['cards']])
    assert params['MODEL/energy_per_turn'] > 0 and params['MODEL/draw_per_turn'] > 0
    return cards, people, deck_rows, cost_rows, params


class RNG:
    """xorshift32 v1 shape, 32-bit unsigned, modulo shuffle; P15 RNG contract pending."""
    def __init__(self, seed: int):
        self.value = seed & 0xffffffff
        if self.value == 0:
            raise ValueError('Seed must be nonzero uint32')
        self.draws = 0

    def next(self) -> int:
        v = self.value
        v ^= (v << 13) & 0xffffffff
        v ^= v >> 17
        v ^= (v << 5) & 0xffffffff
        self.value = v & 0xffffffff
        self.draws += 1
        return self.value

    def shuffle(self, cards: list[str]) -> None:
        for i in range(len(cards) - 1, 0, -1):
            j = self.next() % (i + 1)
            cards[i], cards[j] = cards[j], cards[i]


@dataclass
class Unit:
    name: str
    max_hp: int
    hp: int
    shield: int = 0

    @classmethod
    def fresh(cls, name: str, hp: int, shield: int = 0) -> 'Unit':
        return cls(name, hp, hp, shield)


def apply_damage(unit: Unit, amount: int) -> tuple[int, int]:
    assert amount >= 0
    absorbed = min(unit.shield, amount)
    unit.shield -= absorbed
    hp_damage = min(unit.hp, amount - absorbed)
    unit.hp -= hp_damage
    assert 0 <= unit.hp <= unit.max_hp and unit.shield >= 0
    return absorbed, hp_damage


def apply_shield(unit: Unit, amount: int, shield_cap: int) -> int:
    assert amount >= 0 and shield_cap >= 0
    applied = min(amount, max(0, shield_cap - unit.shield))
    unit.shield += applied
    return applied


def apply_heal(unit: Unit, amount: int) -> int:
    assert amount >= 0
    if unit.hp == 0:
        return 0
    applied = min(amount, unit.max_hp - unit.hp)
    unit.hp += applied
    return applied


def build_deck(deck_rows: list[dict[str, str]], catalog: dict[str, Any]) -> list[str]:
    active = {c['card_id'] for c in catalog['cards'] if c['mock_playable']}
    result = []
    roster = {'MOCK_P04_CHAR_001', 'MOCK_P04_CHAR_002', 'MOCK_P04_CHAR_003'}
    for row in deck_rows:
        if row['row_kind'] == 'SIGNATURE':
            assert row['p04_character_id'] in roster
        else:
            assert row['row_kind'] == 'COMMON'
        assert row['p03_card_id'] in active
        result.extend([row['p03_card_id']] * int(row['copies']))
    assert len(result) == 9 and len(set(result)) == 7
    return result


def basic_battle(catalog: dict[str, Any], people: dict[str, Any], deck_rows: list[dict[str, str]],
                 params: dict[str, int], enemy_type: str, seed: int, mode: str = 'balanced',
                 level: int = 1, damage_percent: int = 100, energy_override: int | None = None,
                 shield_override: int | None = None, hp_percent: int = 100) -> dict[str, Any]:
    """Single HP-only enemy, no P06 phases. P03 values unchanged unless explicit sensitivity flag.
    Simplified sequential player+enemy rounds; NOT P02/P14 implementation or game replay.
    """
    assert enemy_type in ('normal', 'elite', 'boss', 'boss_ohko')
    assert mode in ('balanced', 'attack', 'defense', 'heal')
    assert level in (1, 5) and damage_percent in (80, 100, 120)
    assert hp_percent in (80, 100, 120)
    rng = RNG(seed)
    chars = [Unit.fresh(c['character_id'], c['base_stats']['max_hp'] + (level - 1) * c['per_level_growth']['max_hp']) for c in people['characters']]
    key = {'normal':'normal','elite':'elite','boss':'boss','boss_ohko':'boss_ohko'}[enemy_type]
    if key == 'boss_ohko':
        enemy_hp = params['MODEL/boss_ohko_hp']
        enemy_atk = params['MODEL/boss_enemy_atk']
    else:
        enemy_hp = params[f'MODEL/{key}_enemy_hp']
        enemy_atk = params[f'MODEL/{key}_enemy_atk']
    enemy_hp = max(1, enemy_hp * hp_percent // 100)
    enemy = Unit.fresh('SYNTHETIC_' + enemy_type.upper(), enemy_hp, params.get(f'MODEL/{key}_enemy_shield', 0))
    start_hp = sum(c.hp for c in chars)
    energy_per_round = params['MODEL/energy_per_turn'] if energy_override is None else energy_override
    shield_cap = params['MODEL/shield_cap'] if shield_override is None else shield_override
    assert energy_per_round > 0 and shield_cap >= 0
    catalog_ref = {c['card_id']: c for c in catalog['cards']}
    effects = {e['effect_id']: e for e in catalog['effects']}
    draw = build_deck(deck_rows, catalog)
    rng.shuffle(draw)
    discard: list[str] = []
    hand: list[str] = []
    pending_dot = 0
    stats = {k:0 for k in ['damage_hp_to_enemy','damage_hp_to_party','damage_absorbed_by_shield',
                         'shield_granted','heal_effective','battle_energy_spent','cards_played','dot_ticks',
                         'first_round_enemy_hp_damage','max_round_enemy_hp_damage']}
    outcome = 'TURN_LIMIT'; turns = 0

    for turn in range(1, params['MODEL/max_turns'] + 1):
        turns = turn
        # Mock P15 draw/hand/discard rule; neither refill nor draw policy is frozen.
        while len(hand) < params['MODEL/draw_per_turn'] and len(hand) < params['MODEL/hand_limit']:
            if not draw:
                if not discard:
                    break
                draw, discard = discard, []
                rng.shuffle(draw)
            hand.append(draw.pop(0))
        energy = energy_per_round
        damage_this_turn = 0

        def next_enemy_target() -> Unit | None:
            index = (turn-1) % len(chars)
            return next((chars[(index+i) % len(chars)] for i in range(len(chars)) if chars[(index+i) % len(chars)].hp > 0), None)

        for _ in range(len(hand) + 1):
            candidates = []
            for index, card_id in enumerate(hand):
                card = catalog_ref[card_id]
                cost = int(card['cost']['amount'])
                if cost > energy:
                    continue
                assert len(card['effect_ids']) == 1
                effect = effects[card['effect_ids'][0]]
                kind = effect['effect_code']
                amount = int(effect['amount'])
                target: Unit | None = None
                score = 0
                if kind == 'DAMAGE':
                    target = enemy
                    if enemy.hp <= 0: continue
                    actual = amount * damage_percent // 100
                    score = actual * 10 - cost * 4
                    if mode == 'attack':score += 100
                elif kind == 'SHIELD':
                    target = next_enemy_target()
                    if target is None or target.shield >= shield_cap: continue
                    actual = min(amount, shield_cap - target.shield)
                    score = actual * 5 - cost * 5
                    if mode == 'defense':score += 100
                elif kind == 'HEAL':
                    wounded = [c for c in chars if c.hp > 0 and c.hp < c.max_hp]
                    if not wounded: continue
                    target = max(wounded, key=lambda c: ((c.max_hp - c.hp)*1000 // c.max_hp, -chars.index(c)))
                    actual = min(amount, target.max_hp-target.hp)
                    score = actual * 5 - cost * 5
                    if mode == 'heal':score += 100
                elif kind == 'STATUS' and effect.get('status_kind') == 'DOT':
                    # Reapply stack/refresh is explicitly unresolved in P03; do not simulate it.
                    if pending_dot: continue
                    target = enemy
                    score = amount * 8 - cost * 4
                    if mode == 'attack':score += 30
                else:
                    # Draft BUFF/DEBUFF and unsupported effect types must not enter a simulation.
                    continue
                assert target is not None
                candidates.append((score, -cost, -index, index, card_id, effect, target))
            if not candidates:
                break
            _, _, _, index, card_id, effect, target = max(candidates, key=lambda t:(t[0],t[1],t[2]))
            card = catalog_ref[card_id]
            cost = int(card['cost']['amount'])
            assert energy >= cost
            energy -= cost
            stats['battle_energy_spent'] += cost
            stats['cards_played'] += 1
            hand.pop(index)
            discard.append(card_id)
            kind = effect['effect_code']
            amount = int(effect['amount'])
            if kind == 'DAMAGE':
                absorbed, dealt = apply_damage(enemy, amount * damage_percent // 100)
                stats['damage_absorbed_by_shield'] += absorbed
                stats['damage_hp_to_enemy'] += dealt
                damage_this_turn += dealt
            elif kind == 'SHIELD':
                stats['shield_granted'] += apply_shield(target, amount, shield_cap)
            elif kind == 'HEAL':
                stats['heal_effective'] += apply_heal(target, amount)
            else:
                assert kind == 'STATUS' and effect['status_kind'] == 'DOT' and pending_dot == 0
                pending_dot = amount
            if enemy.hp == 0:
                outcome = 'WIN'; break
        if enemy.hp == 0:
            if turn == 1:
                stats['first_round_enemy_hp_damage'] = damage_this_turn
            stats['max_round_enemy_hp_damage'] = max(stats['max_round_enemy_hp_damage'], damage_this_turn)
            break

        # Enemy owner-turn entry DOT occurs before enemy intent/action (P02 direction).
        if pending_dot:
            absorbed, dealt = apply_damage(enemy, pending_dot)
            stats['damage_absorbed_by_shield'] += absorbed
            stats['damage_hp_to_enemy'] += dealt
            damage_this_turn += dealt
            stats['dot_ticks'] += 1
            pending_dot = 0
        if turn == 1:
            stats['first_round_enemy_hp_damage'] = damage_this_turn
        stats['max_round_enemy_hp_damage'] = max(stats['max_round_enemy_hp_damage'], damage_this_turn)
        if enemy.hp == 0:
            outcome = 'WIN'; break
        target = next_enemy_target()
        if target is None:
            outcome = 'LOSS'; break
        absorbed, dealt = apply_damage(target, enemy_atk)
        stats['damage_absorbed_by_shield'] += absorbed
        stats['damage_hp_to_party'] += dealt
        if not any(c.hp > 0 for c in chars):
            outcome = 'LOSS'; break
        # Mock P15 unplayed cards discard; no game-state persistence involved.
        discard.extend(hand)
        hand.clear()
    return {**stats, 'outcome':outcome, 'turns':turns, 'enemy_hp_initial':enemy.max_hp,
            'enemy_hp_remaining':enemy.hp,'party_hp_initial':start_hp,
            'party_hp_remaining':sum(c.hp for c in chars),
            'player_units_alive':sum(c.hp > 0 for c in chars), 'rng_draws':rng.draws}


def make_events(scenario: str) -> list[dict[str, Any]]:
    """Synthetic independent events, NOT actual Anki revlogs/validity proof."""
    ratings = ('Again', 'Hard', 'Good', 'Easy')
    if scenario == 'ZERO': return []
    if scenario in ('AGAIN20', 'AGAIN20_BAD'):
        return [{'id':f'RID_{i:05d}', 'card_id':f'ANKI_CARD_{i%5}', 'rating':'Again', 'trusted':True, 'kind':'REVIEW'} for i in range(20)]
    if scenario == 'GOOD20':
        return [{'id':f'RID_{i:05d}', 'card_id':f'ANKI_CARD_{i%5}', 'rating':'Good', 'trusted':True, 'kind':'REVIEW'} for i in range(20)]
    if scenario in ('LOW12', 'HIGH120', 'MASS1500', 'UNDO6'):
        count = {'LOW12':12,'HIGH120':120,'MASS1500':1500,'UNDO6':12}[scenario]
        ans = [{'id':f'RID_{i:05d}', 'card_id':f'ANKI_CARD_{i%17}', 'rating':ratings[i%4], 'trusted':True,'kind':'REVIEW'} for i in range(count)]
        if scenario == 'UNDO6':
            ans.extend({'id':f'UNDO_{i:05d}', 'source_id':f'RID_{i:05d}', 'kind':'UNDO', 'trusted':True} for i in range(6))
        return ans
    if scenario == 'REPLAY1000':
        e = {'id':'RID_ONCE', 'card_id':'ANKI_CARD_1', 'rating':'Again','trusted':True, 'kind':'REVIEW'}
        return [e.copy() for _ in range(1000)]
    if scenario == 'COLLISION100':
        a = [{'id':'RID_ONCE','card_id':'ANKI_CARD_1','rating':'Again','trusted':True,'kind':'REVIEW'}]
        a.extend({'id':'RID_ONCE','card_id':'ANKI_CARD_1','rating':'Easy','trusted':True,'kind':'REVIEW'} for _ in range(100))
        return a
    if scenario == 'UNTRUSTED100':
        return [{'id':f'RID_U_{i:05d}','card_id':f'ANKI_CARD_{i}','rating':'Good','trusted':False,'kind':'REVIEW'} for i in range(100)]
    raise ValueError('Unknown economy scenario '+scenario)


def shadow_ledger(events: list[dict[str, Any]], rating_weights: dict[str, int]) -> dict[str, int]:
    seen: dict[str, tuple[str, str]] = {}
    undone: set[str] = set()
    undo_seen: set[str] = set()
    stats = dict(study_attempts=len(events),valid_unique_events=0,deduplicated_attempts=0,
                 id_collisions=0,untrusted_quarantined=0,undo_events=0,
                 shadow_awarded_gross=0,shadow_undo_reversed=0,shadow_net=0)
    for e in events:
        if not e['trusted']:
            stats['untrusted_quarantined'] += 1
            continue
        if e['kind'] == 'UNDO':
            if e['id'] in undo_seen:
                stats['deduplicated_attempts'] += 1
                continue
            undo_seen.add(e['id'])
            ref = e['source_id']
            if ref not in seen or ref in undone:
                stats['untrusted_quarantined'] += 1
                continue
            undone.add(ref)
            rating = seen[ref][1]
            stats['undo_events'] += 1
            stats['shadow_undo_reversed'] += rating_weights[rating]
            continue
        assert e['kind'] == 'REVIEW' and e['rating'] in rating_weights
        key = e['id']
        fingerprint = (e['card_id'], e['rating'])
        if key in seen:
            if seen[key] == fingerprint:
                stats['deduplicated_attempts'] += 1
            else:
                stats['id_collisions'] += 1
            continue
        seen[key] = fingerprint
        stats['valid_unique_events'] += 1
        stats['shadow_awarded_gross'] += rating_weights[e['rating']]
    stats['shadow_net'] = stats['shadow_awarded_gross'] - stats['shadow_undo_reversed']
    assert stats['shadow_net'] >= 0
    return stats


def stage_budget(params: dict[str, int], normal: int = 3, elite: int = 1, boss: int = 0,
                 normal_token_override: int | None = None) -> tuple[int, int]:
    nt = params['STAGE/normal_tokens'] if normal_token_override is None else normal_token_override
    return (normal*nt + elite*params['STAGE/elite_tokens'] + boss*params['STAGE/boss_tokens'],
            normal*params['STAGE/normal_xp'] + elite*params['STAGE/elite_xp'] + boss*params['STAGE/boss_xp'])


def project_progression(initial_wallet: int, xp_per_char: int,
                        cost_rows: list[dict[str, str]],
                        character_order: list[str]) -> dict[str, int]:
    """Exercise P04 fixtures: XP only gates, tokens consumed. Does not write P17 wallet."""
    assert initial_wallet >= 0 and xp_per_char >= 0
    stats = {ch:{'level':1,'skill':1} for ch in character_order}
    balance = initial_wallet; level_buys = 0; skill_buys = 0
    by_id = {(c['character_id'],c['kind'],int(c['from_rank'])):c for c in cost_rows}
    for _ in range(20):
        changed = False
        # Round-robin priorities avoid one character monopolizing mock expenditures.
        for ch in character_order:
            level = stats[ch]['level']
            c = by_id.get((ch,'LEVEL',level))
            if c is not None and xp_per_char >= int(c['requires_xp_total']) and balance >= int(c['spend_amount']):
                assert level + 1 == int(c['to_rank'])
                balance -= int(c['spend_amount']); stats[ch]['level'] += 1
                level_buys += 1;changed = True
        if not changed:break
    for _ in range(10):
        changed = False
        for ch in character_order:
            rank = stats[ch]['skill']
            c = by_id.get((ch,'SKILL',rank))
            if (c and stats[ch]['level'] >= int(c['requires_character_level'])
                and balance >= int(c['spend_amount'])):
                balance -= int(c['spend_amount']); stats[ch]['skill'] += 1
                skill_buys += 1;changed = True
        if not changed:break
    return dict(token_spent_on_levels=initial_wallet-balance,token_balance=balance,
                level_upgrades=level_buys,skill_upgrades=skill_buys)


def blank_row(row_id: str, group: str, scenario: str, seed: int, param_sha: str,
              **values: Any) -> dict[str, Any]:
    row: dict[str, Any] = {k:'' for k in COLUMNS}
    row.update(row_id=row_id,group=group,scenario=scenario,model_version=VERSION,
               parameters_sha256=param_sha,source_p03_sha256=EXPECTED_HASHES['p03_card_catalog.json'],
               source_p04_sha256=EXPECTED_HASHES['p04_character_skeleton.json'],
               source_p02_sha256=EXPECTED_HASHES['p02_effect_priority.tsv'], seed=seed,
               status='LOCAL_MOCK_SIMULATION_ONLY')
    row.update({k:v for k,v in values.items() if k in row})
    return row


def make_rows(seed: int = 20261028) -> list[dict[str, Any]]:
    catalog, people, deck_rows, cost_rows, params = load_inputs()
    param_sha = digest(ROOT / 'content/balance/balance_parameters.tsv')
    rows: list[dict[str, Any]] = []
    char_ids = [c['character_id'] for c in people['characters']]
    battles = [('normal_L1','normal','balanced',1,100,100),
               ('elite_L1','elite','balanced',1,100,100),
               ('boss_long_L1','boss','balanced',1,100,100),
               ('boss_long_L5','boss','balanced',5,100,100),
               ('boss_attack_priority','boss','attack',1,100,100),
               ('boss_defense_priority','boss','defense',1,100,100),
               ('boss_heal_priority','boss','heal',1,100,100),
               ('boss_ohko_bad_config','boss_ohko','attack',1,100,100),
               ('boss_long_zero_study','boss','balanced',1,100,100),
               ('boss_long_again20_shadow','boss','balanced',1,100,100)]
    for idx,(name,enemy_type,mode,level,dmg_pct,hp_pct) in enumerate(battles):
        data = basic_battle(catalog,people,deck_rows,params,enemy_type,seed,mode,level,dmg_pct,hp_percent=hp_pct)
        rows.append(blank_row(f'BATTLE_{idx:03d}','BATTLE',name,seed,param_sha,**data,
                              notes=f'P06_SYNTHETIC_ONLY; P03/P04 test fixtures; player_mode={mode}; level={level}; no Boss phases; no real Anki; zero_study_and_again20_have_IDENTICAL_battle_inputs'))
    for idx,name in enumerate(['ZERO','AGAIN20','GOOD20','LOW12','HIGH120','MASS1500',
                                'REPLAY1000','COLLISION100','UNTRUSTED100','UNDO6','AGAIN20_BAD']):
        equal = {r:params['ECON/equal_'+r.lower()] for r in ('Again','Hard','Good','Easy')}
        weights = ({r:params['ECON/bias_'+r.lower()] for r in ('Again','Hard','Good','Easy')}
                   if name.endswith('_BAD') else equal)
        inputs = make_events(name)
        a = shadow_ledger(inputs,weights)
        stage_tokens, xp = stage_budget(params)
        wallet = stage_tokens + a['shadow_net']
        progress = project_progression(wallet,xp,cost_rows,char_ids)
        rows.append(blank_row(f'ECON_{idx:03d}','ECONOMY_SHADOW',name,seed,param_sha,**a,
                              stage_token_income=stage_tokens,stage_xp_per_character=xp,
                              token_budget_total=wallet,**progress,
                              notes='3 synthetic normal+1 elite first-clears; one-time stage grants assumed; XP per each character; never actual Anki awards; '
                                    + ('BAD_INCENTIVE_POLICY_NOT_RECOMMENDED' if name.endswith('_BAD') else 'EQUAL_FOUR_KEY_POLICY_UNAPPROVED')))
    # Extreme stack and budget-gate probes are pure mathematical adversarial fixtures.
    # 100 separate shield cards are NOT 100 cards in the real nine-card hand.
    for idx,cap in enumerate((40,100000)):
        unit = Unit.fresh('SYNTHETIC_DEFENDER', 132)
        shield_total = sum(apply_shield(unit,4,cap) for _ in range(100))
        assert shield_total == unit.shield == (40 if cap == 40 else 400)
        rows.append(blank_row(f'STRESS_STACK_{idx:03d}','ADVERSARIAL_STRESS',
                              'shield_100_casts_cap40' if cap == 40 else 'shield_100_casts_no_practical_cap',
                              seed,param_sha,outcome='MATH_ONLY',shield_granted=shield_total,
                              battle_energy_spent=100,cards_played=100,
                              notes='100 individually paid cards requiring 100 total energy, NOT same turn or actual deck; cap candidate unapproved; shield persists in stress'))
    # The actual nine-card deck cannot contain 100 copies of Strike. 100 requests
    # against one nominal 3-energy budget, without any refill, must refuse 97.
    energy = params['MODEL/energy_per_turn']; accepted = 0; rejected = 0
    for _ in range(100):
        if energy >= 1:
            energy -= 1; accepted += 1
        else: rejected += 1
    assert accepted == 3 and rejected == 97
    rows.append(blank_row('STRESS_COST_000','ADVERSARIAL_STRESS','same_turn_100_card_requests',seed,param_sha,
                          outcome='MATH_ONLY',battle_energy_spent=accepted,cards_played=accepted,
                          damage_hp_to_enemy=accepted*4,
                          notes=f'97 requests rejected by simple energy gate; hypothetical unlimited card instances; no P14 transaction code; rejected={rejected}'))
    # No approved study-event daily cap exists. Illustrate both the uncapped stress
    # and the adverse effect a 40-event cap would have on 1500 legitimate reviews.
    rows.append(blank_row('STRESS_POLICY_000','ADVERSARIAL_STRESS','study_unique_1500_cap40_counterfactual',seed,param_sha,
                          outcome='MATH_ONLY',study_attempts=1500,valid_unique_events=1500,
                          shadow_awarded_gross=40,shadow_net=40,
                          notes='hypothetical 40-event cap denies 1460 valid unique events; NOT RECOMMENDED/APPROVED; compare ECON_MASS1500'))
    for idx,config in enumerate([('damage_80',80,None,None,100),('damage_100',100,None,None,100),
                                  ('damage_120',120,None,None,100),('energy_2',100,2,None,100),
                                  ('energy_3',100,3,None,100),('energy_4',100,4,None,100),
                                  ('shieldcap_20',100,None,20,100),('shieldcap_40',100,None,40,100),
                                  ('shieldcap_80',100,None,80,100),('boss_hp_80',100,None,None,80),
                                  ('boss_hp_100',100,None,None,100),('boss_hp_120',100,None,None,120)]):
        name,damage,energy,cap,hp_pct=config
        data = basic_battle(catalog,people,deck_rows,params,'boss',seed,'balanced',1,
                            damage_percent=damage,energy_override=energy,
                            shield_override=cap,hp_percent=hp_pct)
        rows.append(blank_row(f'SENS_BATTLE_{idx:03d}','SENSITIVITY_BATTLE',name,seed,param_sha,**data,
                              notes=f'ONE_FACTOR_AT_A_TIME: damage_pct={damage}; energy={energy if energy is not None else params["MODEL/energy_per_turn"]}; shield_cap={cap if cap is not None else params["MODEL/shield_cap"]}; enemy_hp_pct={hp_pct}; no permanent P03 change'))
    for idx,nval in enumerate((2,3,4)):
        st,xp=stage_budget(params,normal_token_override=nval)
        projection=project_progression(st,xp,cost_rows,char_ids)
        rows.append(blank_row(f'SENS_ECON_{idx:03d}','SENSITIVITY_ECONOMY',f'normal_stage_tokens_{nval}',seed,param_sha,
                              stage_token_income=st,stage_xp_per_character=xp,token_budget_total=st,
                              shadow_awarded_gross=0,shadow_net=0,**projection,
                              notes=f'ZERO_LEARNING_3_NORMAL_1_ELITE; normal stage grant={nval}; P18/P01 unapproved'))
    for idx,(event_count,base,policy) in enumerate([(20,1,'EQUAL'),(20,2,'BAD_AGAIN_BONUS'),(120,1,'EQUAL'),(120,2,'BAD_AGAIN_BONUS')]):
        # One-key-only counterfactual, not any real user event.
        events = make_events('AGAIN20') if event_count == 20 else [dict(id=f'RID_{i}',card_id=f'CARD_{i%5}',rating='Again',trusted=True,kind='REVIEW') for i in range(event_count)]
        grants = shadow_ledger(events,{'Again':base,'Hard':1,'Good':1,'Easy':1})
        rows.append(blank_row(f'SENS_RATING_{idx:03d}','SENSITIVITY_RATING',f'{policy}_AGAIN_{event_count}',seed,param_sha,
                              **grants, notes='Hypothetical reward weights; numerical incentive only; P08/P01 must sign any policy'))
    return rows


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    buf=io.StringIO(newline='')
    writer=csv.DictWriter(buf,fieldnames=COLUMNS,lineterminator='\n',extrasaction='raise')
    writer.writeheader();writer.writerows(rows)
    return buf.getvalue().encode('utf-8')


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed',type=int,default=20261028)
    parser.add_argument('--output',type=Path,default=ROOT/'analysis/simulations/simulation_results.csv')
    parser.add_argument('--verify',action='store_true',help='Byte-compare generated CSV with output; do not modify')
    args=parser.parse_args()
    rows=make_rows(args.seed);output=csv_bytes(rows)
    if args.verify:
        assert args.output.is_file() and args.output.read_bytes()==output,'REPRODUCIBILITY_MISMATCH'
        print('P05_SIM_VERIFY: PASS; byte-identical CSV; sha256='+hashlib.sha256(output).hexdigest())
    else:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_bytes(output)
        print(f'P05_SIM_GENERATED: rows={len(rows)} seed={args.seed} output={args.output}')
        print('P05_SIM_SHA256: '+hashlib.sha256(output).hexdigest())
    for r in rows:
        if r['group'] in ('BATTLE','ECONOMY_SHADOW'):
            print(f"{r['scenario']}: outcome={r['outcome']} turns={r['turns']} boss_hp_left={r['enemy_hp_remaining']} unique={r['valid_unique_events']} shadow_net={r['shadow_net']} level_upgrades={r['level_upgrades']}")
    return 0

if __name__=='__main__':
    raise SystemExit(main())
