"""Explicit adapter to the hash-bound P14 0.1 isolated Python port.

Only proposes an existing P13 DeckPatchCandidate. Never calls submit(), writes
BattleState, or publishes events. P14 owns its Python exception protocol.
"""
from .commands import DeckPlanner
from .errors import DeckRejected, require
from .wire import checked


def verify_p14_rules(context, rules):
    p, catalog = context.policy, context.catalog
    require((rules.rules_version, rules.content_version, rules.deck_policy_version) ==
            (p.rules_version, p.content_version, p.version), 'P14_RULES_BINDING_MISMATCH')
    # P14 0.1 has one static requested count shared by both entry kinds.
    require(rules.entry_draw_requested == p.initial_draw == p.turn_draw, 'P14_ENTRY_DRAW_REPORT_UNBOUND')
    expected = {c.card_id: c for c in catalog.cards if c.playable}
    actual = {a.action_id: a for a in rules.cards if a.playable}
    require(set(actual) == set(expected), 'P14_CARD_SET_MISMATCH')
    require(any(b.sha256 == catalog.source_sha256 for b in rules.source_bindings), 'P14_CATALOG_SOURCE_UNBOUND')
    dots = {d.status_id: d for d in rules.statuses}
    for card_id, spec in expected.items():
        action = actual[card_id]
        require((action.target_side, action.target_count, action.owner_definition_id, action.after_play_zone) ==
                (spec.target_side, spec.target_count, spec.owner_character_id, spec.after_play_zone), 'P14_ACTION_BINDING_MISMATCH')
        expected_effects = []
        for index, effect in enumerate(spec.effects.value):
            kind = effect['effect_code']
            if kind == 'STATUS':
                dot = dots.get(effect['status_id'])
                require(dot is not None and (dot.amount, dot.duration) ==
                        (effect['amount'], effect['remaining_owner_turns']), 'P14_STATUS_BINDING_MISMATCH')
                expected_effects.append((index, kind, 0, effect['status_id']))
            else:
                expected_effects.append((index, kind, effect['amount'], None))
        require([(e.effect_index, e.kind, e.amount, e.status_id) for e in action.effects] == expected_effects, 'P14_EFFECT_BINDING_MISMATCH')


class P14DeckAdapter:
    def __init__(self, planner, rules, *, rejection_type):
        # The caller supplies the actual P14 owner's class. Importing identical
        # source under a second package name creates a different exception type.
        # Hard-coding a vendored exception can turn a rejection into FAULTED.
        require(isinstance(planner, DeckPlanner), 'PLANNER_REQUIRED')
        require(isinstance(rejection_type, type) and issubclass(rejection_type, Exception), 'P14_REJECTION_TYPE_REQUIRED')
        verify_p14_rules(planner.context, rules)
        self._planner = planner
        self._rejection_type = rejection_type

    @property
    def planner(self):
        return self._planner

    def propose(self, command, snapshot):
        try:
            basis = checked(snapshot, 'BattleSnapshot')
            decision = self._planner.evaluate(command, basis)
            candidate = decision.candidate
            if candidate is None:
                raise self._rejection_type(decision.code)
            if candidate.value['snapshot_sha256'] != basis.sha256:
                raise self._rejection_type('CACHED_CANDIDATE_BASIS_CHANGED')
            return candidate
        except DeckRejected as exc:
            raise self._rejection_type(exc.code) from exc
