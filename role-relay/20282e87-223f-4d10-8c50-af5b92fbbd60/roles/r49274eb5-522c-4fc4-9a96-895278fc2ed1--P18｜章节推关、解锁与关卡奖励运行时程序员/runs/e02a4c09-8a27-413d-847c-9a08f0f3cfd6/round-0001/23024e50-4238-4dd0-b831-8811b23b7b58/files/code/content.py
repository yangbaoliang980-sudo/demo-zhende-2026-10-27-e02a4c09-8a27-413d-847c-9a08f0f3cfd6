"""Immutable P06 content reader. Does not enable, balance or rewrite content."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from .types import AiError, CONTENT_VERSION, integer, identifier, require


def _unique(items, key):
    require(type(items) is list and len(items) <= 4096, 'CONTENT_CAPACITY')
    keys = [x[key] for x in items]
    require(len(keys) == len(set(keys)), 'CONTENT_DUPLICATE_ID')
    for k in keys: identifier(k)
    return dict(zip(keys, items))


def _json(raw):
    def pairs(items):
        out = {}
        for k, v in items:
            require(k not in out, 'DUPLICATE_JSON_KEY'); out[k] = v
        return out
    try:
        return json.loads(raw, object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(AiError('NON_FINITE_JSON')))
    except (ValueError, KeyError, TypeError) as exc:
        if isinstance(exc, AiError): raise
        raise AiError('CONTENT_JSON_INVALID') from exc


def validate_spec(spec):
    try:
        require(spec['format_version'] == CONTENT_VERSION, 'CONTENT_VERSION_UNSUPPORTED')
        require(spec['production_enabled'] is False, 'PRODUCTION_CONTENT_NOT_APPROVED')
        require(spec['policies']['state_writer'] == 'P14_ONLY', 'STATE_OWNER_CONFLICT')
        require(spec['policies']['rng']['draws_per_enemy_decision'] == 0, 'RANDOM_POLICY_UNSUPPORTED')
        require(spec['policies']['targeting']['auto_retarget'] is False, 'RETARGET_POLICY_UNSUPPORTED')
        require(spec['policies']['targeting']['max_party_size'] == 3, 'PARTY_POLICY_UNSUPPORTED')
        policy_digest=hashlib.sha256(json.dumps(spec['policies'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
        require(policy_digest=='31e327ec8ecf6051c85766429adc37e8735c9dde2becc7a39d0b1a273fbc37eb','BEHAVIOR_POLICY_VERSION_UNSUPPORTED')
        skills = _unique(spec['skills'], 'skill_id'); enemies = _unique(spec['enemies'], 'enemy_id')
        require(bool(skills) and bool(enemies), 'EMPTY_CONTENT')
        for skill in skills.values():
            identifier(skill['intent_id'])
            require(skill['action_kind'] in {'STRIKE','SWEEP','CHARGE','RELEASE','RECOVER','ENTRY_WAIT','SKIP','DEGRADED_WAIT'}, 'UNSUPPORTED_ACTION_KIND')
            require(skill['target_policy'] in {'ROTATE_ALIVE_SINGLE','LOCKED_CHARGE_SINGLE','LOCK_ALL_ALIVE','NONE'}, 'UNSUPPORTED_TARGET_POLICY')
            require(skill['production_enabled'] is False and skill['grants_extra_action'] is False and skill['status_applications'] == [], 'UNAPPROVED_MECHANIC')
            require(skill['requires_actor_alive'] is True and skill['no_valid_target'] == 'SKIP_NO_VALID_TARGET', 'UNSUPPORTED_ALIVE_POLICY')
            for k in ('base_amount_per_hit','hit_count','future_release_base_amount','cooldown_on_success_slots'):
                integer(skill[k], 0, 21474836, 'CONTENT_INTEGER_RANGE')
            if skill['action_kind'] in {'STRIKE','SWEEP','RELEASE'}:
                require(skill['effect_code'] == 'DAMAGE' and skill['base_amount_per_hit'] > 0 and skill['hit_count'] == 1, 'UNSUPPORTED_EFFECT_SHAPE')
            else:
                require(skill['effect_code'] == 'NONE' and skill['base_amount_per_hit'] == 0 and skill['hit_count'] == 0, 'UNSUPPORTED_EFFECT_SHAPE')
            mapping = {'STRIKE':'ROTATE_ALIVE_SINGLE','SWEEP':'LOCK_ALL_ALIVE','CHARGE':'ROTATE_ALIVE_SINGLE','RELEASE':'LOCKED_CHARGE_SINGLE','RECOVER':'NONE','ENTRY_WAIT':'NONE','SKIP':'NONE','DEGRADED_WAIT':'NONE'}
            require(skill['target_policy'] == mapping[skill['action_kind']], 'UNSUPPORTED_KIND_TARGET_PAIR')
            if skill['action_kind'] == 'CHARGE':
                require(skill['charge_requirement'] == 'CREATE_IF_HEAVY_CD_ZERO' and skill['cooldown_group'] == 'HEAVY' and skill['cooldown_on_success_slots'] == 0, 'UNSUPPORTED_CHARGE_POLICY')
            elif skill['action_kind'] == 'RELEASE':
                require(skill['charge_requirement'] == 'REQUIRE_COMMITTED_READY_CHARGE' and skill['cooldown_group'] == 'HEAVY' and skill['cooldown_on_success_slots'] == 2, 'UNSUPPORTED_RELEASE_POLICY')
            else:
                require(skill['charge_requirement'] is None and skill['cooldown_group'] is None and skill['cooldown_on_success_slots'] == 0, 'UNSUPPORTED_COOLDOWN_POLICY')
        for enemy in enemies.values():
            require(enemy['tier'] in {'NORMAL','ELITE','BOSS'} and enemy['production_enabled'] is False, 'ENEMY_SCOPE_INVALID')
            for k in ('max_hp','initial_shield','baseline_attack'): integer(enemy[k], 0, 21474836, 'CONTENT_INTEGER_RANGE')
            require(enemy['max_hp'] > 0, 'CONTENT_HP_INVALID')
            require(enemy['on_death_reaction_ids'] == [] and enemy['allowed_new_status_ids'] == [], 'UNAPPROVED_MECHANIC')
            states = _unique(enemy['states'], 'state_id')
            require(enemy['initial_state_id'] in states, 'INITIAL_STATE_UNKNOWN')
            for state in states.values():
                require(state['skill_id'] in skills and state['next_state_id'] in states, 'STATE_REFERENCE_INVALID')
                if skills[state['skill_id']]['action_kind'] == 'CHARGE':
                    release = skills[states[state['next_state_id']]['skill_id']]
                    require(release['action_kind'] == 'RELEASE' and release['base_amount_per_hit'] == skills[state['skill_id']]['future_release_base_amount'], 'CHARGE_RELEASE_MISMATCH')
                if enemy['tier'] == 'BOSS':
                    require(state['phase_id'] in enemy['phase_initial_state_ids'], 'STATE_PHASE_INVALID')
                    require(states[state['next_state_id']]['phase_id'] == state['phase_id'], 'CYCLE_CROSSES_PHASE')
            if enemy['tier'] == 'BOSS':
                require(enemy['degraded_basic_skill_id'] in skills, 'BASELINE_SKILL_MISSING')
                require(skills[enemy['degraded_basic_skill_id']]['action_kind'] == 'STRIKE', 'BASELINE_SKILL_INVALID')
                for pid, state in enemy['phase_initial_state_ids'].items():
                    identifier(pid); require(state in states and states[state]['phase_id'] == pid, 'PHASE_INITIAL_STATE_INVALID')
        for kind in ('SKIP','ENTRY_WAIT','DEGRADED_WAIT'):
            require(sum(s['action_kind'] == kind for s in skills.values()) == 1, 'SPECIAL_SKILL_AMBIGUOUS')
    except (KeyError, TypeError, AttributeError) as exc:
        raise AiError('CONTENT_SHAPE_INVALID') from exc


def validate_graph(spec, graph):
    try:
        require(graph['format_version'] == CONTENT_VERSION, 'GRAPH_VERSION_UNSUPPORTED')
        enemy = next((e for e in spec['enemies'] if e['enemy_id'] == graph['enemy_id']), None)
        require(enemy is not None and enemy['tier'] == 'BOSS', 'GRAPH_ENEMY_MISMATCH')
        require(enemy['phase_graph_id'] == graph['graph_id'], 'GRAPH_ID_MISMATCH')
        phases = _unique(graph['phases'], 'phase_id')
        require(set(phases) == set(enemy['phase_initial_state_ids']), 'GRAPH_PHASE_SET_MISMATCH')
        ordered = sorted(phases.values(), key=lambda x:x['rank'])
        require([p['rank'] for p in ordered] == list(range(len(ordered))), 'GRAPH_RANK_INVALID')
        require(graph['initial_phase_id'] == ordered[0]['phase_id'], 'GRAPH_INITIAL_PHASE_INVALID')
        for phase in phases.values():
            integer(phase['rank'])
            require(phase['initial_state_id'] == enemy['phase_initial_state_ids'][phase['phase_id']], 'GRAPH_STATE_MISMATCH')
            require(phase['entry_damage'] == phase['entry_heal'] == phase['entry_shield'] == 0 and phase['entry_cleanse'] is False and phase['invulnerable'] is False, 'UNAPPROVED_PHASE_EFFECT')
            skill = next((s for s in spec['skills'] if s['skill_id'] == phase['entry_wait_skill_id']), None)
            require(skill is not None and skill['action_kind'] == 'ENTRY_WAIT', 'GRAPH_ENTRY_WAIT_INVALID')
        edges = _unique(graph['transitions'], 'transition_id')
        require(len(edges) == len(phases)-1, 'GRAPH_EDGE_COUNT_INVALID')
        seen=set(); last_threshold=101
        for edge in sorted(edges.values(), key=lambda e:phases.get(e['from_phase_id'],{}).get('rank',-1)):
            src=edge['from_phase_id']; dst=edge['to_phase_id']
            require(src in phases and dst in phases and src not in seen, 'GRAPH_EDGE_INVALID'); seen.add(src)
            require(phases[dst]['rank'] == phases[src]['rank']+1, 'GRAPH_NON_MONOTONIC_OR_CYCLIC')
            frac=edge['threshold_max_hp_fraction']; integer(frac['numerator'],1); integer(frac['denominator'],1)
            integer(edge['threshold_percent'],1,99)
            require(frac['numerator']*100 == edge['threshold_percent']*frac['denominator'], 'GRAPH_THRESHOLD_MISMATCH')
            require(edge['threshold_percent'] < last_threshold, 'GRAPH_THRESHOLD_ORDER'); last_threshold=edge['threshold_percent']
        require(graph['phase_commit_owner'] == 'P14', 'GRAPH_OWNER_CONFLICT')
        require(graph['degraded_exit']['then_skill_id'] == enemy['degraded_basic_skill_id'] and graph['degraded_exit']['reenter_graph_in_same_battle'] is False, 'GRAPH_DEGRADATION_UNSUPPORTED')
    except (KeyError,TypeError,StopIteration,AttributeError) as exc:
        raise AiError('GRAPH_SHAPE_INVALID') from exc


@dataclass(frozen=True, slots=True)
class ContentBlob:
    """P06 content bytes; P13's wire-key profile does not apply to content."""
    raw: bytes

    def __post_init__(self): require(type(self.raw) is bytes,'CONTENT_BYTES_REQUIRED')

    @property
    def value(self): return _json(self.raw)


@dataclass(frozen=True, slots=True)
class Catalog:
    spec: ContentBlob
    graph: ContentBlob | None
    source_sha256: str
    graph_sha256: str | None
    graph_error: str | None

    @classmethod
    def from_bytes(cls, spec_raw, graph_raw=None, *, expected_spec_sha256=None, expected_graph_sha256=None):
        require(type(spec_raw) is bytes, 'CONTENT_BYTES_REQUIRED')
        digest=hashlib.sha256(spec_raw).hexdigest()
        require(expected_spec_sha256 is None or digest == expected_spec_sha256, 'CONTENT_HASH_MISMATCH')
        spec=_json(spec_raw); validate_spec(spec)
        graph=None; graph_digest=None; error='PHASE_GRAPH_MISSING'
        if graph_raw is not None:
            require(type(graph_raw) is bytes, 'CONTENT_BYTES_REQUIRED')
            graph_digest=hashlib.sha256(graph_raw).hexdigest()
            require(expected_graph_sha256 is None or graph_digest == expected_graph_sha256, 'GRAPH_HASH_MISMATCH')
            try:
                graph=_json(graph_raw); validate_graph(spec,graph); error=None
            except AiError as exc:
                error=exc.code; graph=None
        return cls(ContentBlob(spec_raw), None if graph is None else ContentBlob(graph_raw), digest,graph_digest,error)

    @classmethod
    def from_files(cls,spec_path,graph_path=None,**kwargs):
        return cls.from_bytes(Path(spec_path).read_bytes(),None if graph_path is None else Path(graph_path).read_bytes(),**kwargs)

    def skill(self,sid):
        result=next((s for s in self.spec.value['skills'] if s['skill_id']==sid),None)
        require(result is not None,'UNKNOWN_SKILL'); return result

    def enemy(self,eid):
        result=next((e for e in self.spec.value['enemies'] if e['enemy_id']==eid),None)
        require(result is not None,'UNKNOWN_ENEMY'); return result

    def special(self,kind):
        return next(s for s in self.spec.value['skills'] if s['action_kind']==kind)


def bundled_catalog():
    root=Path(__file__).resolve().parents[1]/'upstream/P06/content/enemies'
    return Catalog.from_files(root/'enemy_specs.json',root/'boss_phase_graph.json',
        expected_spec_sha256='bb2586b8fe86ff66810aca4304f675e72c418b4267717eff71a2e17feaff90e7',
        expected_graph_sha256='cf1e96d39a371ef4775a86e2505973968a2580be58a205739e4d5847d5972eaf')
