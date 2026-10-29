"""Pure PartySnapshot -> uncommitted deck construction.

P03 has no common-card owner assignment. A complete explicit owner-slot list is
required in the isolated recipe; this is not an implicit production policy.
"""
from dataclasses import dataclass
import hashlib
from .content import Catalog
from .deck import CardInstance, DeckState
from .errors import identifier, integer, require, sha256_text
from .rng import RngState
from .wire import FrozenMessage, checked, fingerprint


@dataclass(frozen=True, slots=True)
class CommonCard:
    card_id: str
    owner_slot: int

    def __post_init__(self):
        identifier(self.card_id)
        integer(self.owner_slot, 0, 2)


@dataclass(frozen=True, slots=True)
class SignatureCard:
    character_id: str
    card_id: str

    def __post_init__(self):
        identifier(self.character_id)
        identifier(self.card_id)


@dataclass(frozen=True, slots=True)
class DeckRecipe:
    version: str
    source_sha256: str
    catalog_source_sha256: str
    common: tuple[CommonCard, ...]
    signatures: tuple[SignatureCard, ...]

    def __post_init__(self):
        identifier(self.version)
        sha256_text(self.source_sha256)
        sha256_text(self.catalog_source_sha256)
        require(type(self.common) is tuple and all(isinstance(c, CommonCard) for c in self.common), 'IMMUTABLE_RECIPE_REQUIRED')
        require(type(self.signatures) is tuple and all(isinstance(c, SignatureCard) for c in self.signatures), 'IMMUTABLE_RECIPE_REQUIRED')
        require(len({s.character_id for s in self.signatures}) == len(self.signatures), 'DUPLICATE_CHARACTER_RECIPE')
        integer(len(self.common) + 3, 3, 4096)

    @property
    def sha256(self):
        return fingerprint({'version': self.version, 'source_sha256': self.source_sha256,
            'catalog_source_sha256': self.catalog_source_sha256,
            'common': [{'card_id': c.card_id, 'owner_slot': c.owner_slot} for c in self.common],
            'signatures': [{'character_id': c.character_id, 'card_id': c.card_id} for c in self.signatures]})


def recipe_from_p03(catalog_raw, fixture_raw, *, common_owner_slots, mode):
    require(mode == 'isolated', 'PRODUCTION_RECIPE_UNBOUND')
    require(type(catalog_raw) is bytes and type(fixture_raw) is bytes, 'ORIGINAL_RECIPE_BYTES_REQUIRED')
    c = FrozenMessage(catalog_raw).value
    f = FrozenMessage(fixture_raw).value
    require(f['rules_version'] == 'P03-DECK-0.1.0-MOCK' and f['party_size'] == 3, 'RECIPE_VERSION_UNSUPPORTED')
    specs = {x['card_id']: x for x in c['cards']}
    # Order comes from an explicit upstream array, never from JSON object keys.
    common = tuple(x['card_id'] for x in f['fixtures'][0]['catalog_card_instances']
                   if specs[x['card_id']]['scope'] == 'COMMON')
    require({cid: common.count(cid) for cid in common} == f['common_card_copies'], 'RECIPE_COMMON_COUNTS_MISMATCH')
    require(type(common_owner_slots) is tuple and len(common_owner_slots) == len(common), 'COMMON_CARD_OWNERS_REQUIRED')
    signatures = tuple(SignatureCard(x['character_id'], x['signature_card_id']) for x in c['fixture_only_character_slots'])
    return DeckRecipe(f['rules_version'], hashlib.sha256(fixture_raw).hexdigest(), hashlib.sha256(catalog_raw).hexdigest(),
        tuple(CommonCard(cid, slot) for cid, slot in zip(common, common_owner_slots)), signatures)


@dataclass(frozen=True, slots=True)
class DeckBuildCandidate:
    deck: DeckState
    provenance: FrozenMessage


def build_deck(party, catalog: Catalog, recipe: DeckRecipe, *, battle_id, seed, mode):
    require(mode == 'isolated', 'PRODUCTION_PARTY_UNBOUND')
    identifier(battle_id)
    require(isinstance(catalog, Catalog) and isinstance(recipe, DeckRecipe), 'IMMUTABLE_BUILD_INPUTS_REQUIRED')
    party = checked(party, 'PartySnapshot')
    p = party.value
    require(p['content_version'] == catalog.content_version, 'CONTENT_VERSION_MISMATCH')
    require(recipe.catalog_source_sha256 == catalog.source_sha256, 'RECIPE_CATALOG_MISMATCH')
    members = sorted(p['members'], key=lambda m: m['slot'])
    signatures = {x.character_id: x.card_id for x in recipe.signatures}
    require(all(m['character_id'] in signatures for m in members), 'PARTY_CHARACTER_UNAVAILABLE')
    selected = []
    for entry in recipe.common:
        spec = catalog.card(entry.card_id)
        require(spec.owner_character_id is None, 'COMMON_RECIPE_OWNER_MISMATCH')
        selected.append((spec, members[entry.owner_slot]))
    for member in members:
        spec = catalog.card(signatures[member['character_id']])
        require(spec.owner_character_id == member['character_id'], 'SIGNATURE_RECIPE_OWNER_MISMATCH')
        selected.append((spec, member))
    instances = []
    for index, (spec, member) in enumerate(selected):
        require(spec.playable, 'CONTENT_DISABLED')
        iid = 'p15inst:' + fingerprint({'battle_id': battle_id, 'party_sha256': party.sha256,
            'recipe_sha256': recipe.sha256, 'index': index})
        instances.append(CardInstance(iid, spec.card_id, member['unit_id']))
    deck = DeckState(tuple(instances), tuple(c.instance_id for c in instances), (), (), (), RngState.seeded(seed))
    provenance = FrozenMessage.from_value({'format': 'P15-DECK-BUILD/0.1.0-isolated', 'status': 'CANDIDATE_NOT_COMMITTED',
        'battle_id': battle_id, 'party_sha256': party.sha256, 'recipe_sha256': recipe.sha256,
        'catalog_sha256': catalog.frozen().sha256, 'deck_sha256': fingerprint(deck.value()),
        'real_p17_party_verified': False, 'production_authorized': False})
    return DeckBuildCandidate(deck, provenance)
