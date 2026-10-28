"""P09 deterministic offline reference. Synthetic fixtures only; no Anki I/O.

This module does not authorize rewards, create review identities, or persist data.
All JSON output uses canonical UTF-8 for digests. See field_protocol_proposal.md.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

CATEGORIES = ("NOUN", "VERB", "I_ADJECTIVE", "NA_ADJECTIVE", "ADVERB", "GRAMMAR", "SENTENCE", "UNKNOWN")
LEXICAL = frozenset(CATEGORIES[:5])
ROLES = dict(zip(CATEGORIES, ("GUARD_MATERIAL", "ATTACK_MATERIAL", "SUPPORT_MATERIAL", "SUPPORT_MATERIAL", "TACTIC_MATERIAL", "TACTIC_MATERIAL", "GENERAL_MATERIAL", "GENERAL_MATERIAL")))
INPUT_VERSION = "P09-FIELD-OBS/0.1.0-proposal"
OUTPUT_VERSION = "P09-MAPPING-RESULT/0.1.0-proposal"
RULES_VERSION = "P09-POS-MAP/0.1.0-proposal"
OVERRIDE_VERSION = "P09-OVERRIDE/0.1.0-proposal"
STATES = frozenset(("READABLE", "MISSING", "UNOBSERVABLE", "READ_ERROR", "NOT_AUTHORIZED"))
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
SEPARATORS = re.compile(r"[;/|,、・；，\n]+")


class ContractError(ValueError):
    """Carries a reason code, never source content."""


class OverrideError(ContractError):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def strict_json(text):
    try:
        return json.loads(text, object_pairs_hook=_unique_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ContractError("NONFINITE_JSON")))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ContractError("INVALID_JSON") from exc


class _LabelHTML(HTMLParser):
    inline = frozenset(("b", "strong", "i", "em", "span"))
    blocks = frozenset(("div", "p"))

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.stack = [], []
        self.invalid = False

    def handle_starttag(self, tag, attrs):
        if attrs or tag not in self.inline | self.blocks | {"br"}:
            self.invalid = True
            return
        if tag == "br":
            self.parts.append("\n")
        else:
            if tag in self.blocks:
                self.parts.append("\n")
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        if tag == "br" and not attrs:
            self.parts.append("\n")
        else:
            self.invalid = True

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.invalid = True
            return
        self.stack.pop()
        if tag in self.blocks:
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)

    def handle_comment(self, data):
        self.invalid = True

    def handle_decl(self, decl):
        self.invalid = True

    def handle_pi(self, data):
        self.invalid = True


def normalize_label(value):
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ContractError("INVALID_FIELD_VALUE")
    if len(value) > 512:
        raise ContractError("LABEL_TOO_LONG")
    p = _LabelHTML()
    try:
        p.feed(value)
        p.close()
    except Exception as exc:
        raise ContractError("UNSUPPORTED_LABEL_MARKUP") from exc
    if p.invalid or p.stack:
        raise ContractError("UNSUPPORTED_LABEL_MARKUP")
    s = unicodedata.normalize("NFKC", "".join(p.parts))
    if any(unicodedata.category(c) in {"Cf", "Cs"} or (unicodedata.category(c) == "Cc" and c not in "\t\r\n") for c in s):
        raise ContractError("UNSUPPORTED_LABEL_CONTROL")
    # Preserve line boundaries as category separators; never join split labels.
    s = "\n".join(" ".join(line.split()) for line in s.splitlines()).strip()
    return s.casefold()


@dataclass(frozen=True)
class Rules:
    data: dict
    sha256: str
    semantic_sha256: str

    @property
    def version(self):
        return self.data["mapping_version"]


def validate_rules(data):
    if not isinstance(data, dict) or data.get("mapping_version") not in {RULES_VERSION, "P09-POS-MAP/0.0.0-synthetic"}:
        raise ContractError("MAPPING_VERSION_UNSUPPORTED")
    if data.get("production_authorized") is not False or data.get("usage") != "SYNTHETIC_REFERENCE_ONLY":
        raise ContractError("MAPPING_AUTHORITY_INVALID")
    if data.get("precedence") != ["BOUND_MANUAL_OVERRIDE", "CATEGORY_LABEL", "UNIT_KIND", "POS_LABEL", "UNKNOWN"]:
        raise ContractError("MAPPING_PRECEDENCE_INVALID")
    if data.get("normalization_id") != "P09-LABEL-NORM/1" or data.get("unknown_category") != "UNKNOWN":
        raise ContractError("MAPPING_POLICY_INVALID")
    categories = data.get("categories")
    if not isinstance(categories, list) or [c.get("code") for c in categories if isinstance(c, dict)] != list(CATEGORIES):
        raise ContractError("MAPPING_CATEGORIES_INVALID")
    for c in categories:
        if c.get("resource_role_proposal") != ROLES[c["code"]] or c.get("formal_resource_id") is not None or c.get("quantity") is not None:
            raise ContractError("MAPPING_REWARD_BOUNDARY_INVALID")
    for key, allowed in (("category_aliases", set(CATEGORIES)), ("unit_aliases", {"WORD", "GRAMMAR", "SENTENCE", "MIXED", "UNKNOWN"})):
        aliases = data.get(key)
        if not isinstance(aliases, dict) or not aliases:
            raise ContractError("MAPPING_ALIASES_INVALID")
        for k, v in aliases.items():
            if not isinstance(k, str) or not k or normalize_label(k) != k or v not in allowed:
                raise ContractError("MAPPING_ALIASES_INVALID")
    compounds = data.get("compound_pos_labels")
    if not isinstance(compounds, dict):
        raise ContractError("MAPPING_COMPOUNDS_INVALID")
    for k, v in compounds.items():
        if normalize_label(k) != k or not isinstance(v, list) or not v or len(v) != len(set(v)) or not set(v) <= LEXICAL:
            raise ContractError("MAPPING_COMPOUNDS_INVALID")
    for k in set(compounds) & set(data["category_aliases"]):
        if compounds[k] != [data["category_aliases"][k]]:
            raise ContractError("MAPPING_ALIAS_COLLISION")
    return data


def load_rules(path, expected_sha256=None, expected_version=None):
    raw = Path(path).read_bytes()
    h = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None and h != expected_sha256:
        raise ContractError("MAPPING_HASH_MISMATCH")
    data = validate_rules(strict_json(raw))
    if expected_version is not None and data["mapping_version"] != expected_version:
        raise ContractError("MAPPING_VERSION_MISMATCH")
    return Rules(data, h, digest(data))


def _result(rules, category, reason, tier=None, candidates=(), observation_sha256=None, override_event_id=None, warnings=()):
    return {
        "schema_version": OUTPUT_VERSION,
        "mapping_version": rules.version if rules else None,
        "mapping_sha256": rules.sha256 if rules else None,
        "mapping_status": "BLOCKED" if category is None else ("UNKNOWN" if category == "UNKNOWN" else "CLASSIFIED"),
        "category": category,
        "reason_code": reason,
        "selected_tier": tier,
        "candidates": sorted(set(candidates)),
        "observation_sha256": observation_sha256,
        "override_event_id": override_event_id,
        "warnings": list(warnings),
        "resource_role_proposal": ROLES.get(category),
        "formal_resource_id": None,
        "quantity": None,
        "production_award_authorized": False,
        "reward_effect": "NONE_PREVIEW_ONLY",
    }


def validate_record(record, profile):
    required = {"schema_version", "source_kind", "profile_id", "scope_ref", "subject_ref", "fields"}
    if not isinstance(record, dict) or set(record) != required:
        raise ContractError("INPUT_SHAPE_INVALID")
    if record["schema_version"] != INPUT_VERSION:
        raise ContractError("INPUT_VERSION_UNSUPPORTED")
    if record["source_kind"] != "SYNTHETIC":
        raise ContractError("REAL_PROFILE_NOT_VALIDATED")
    if not isinstance(profile, dict) or profile.get("usage") != "SYNTHETIC_ONLY" or profile.get("authorization_ref") != "SYNTHETIC_FIXTURE_NO_REAL_GRANT":
        raise ContractError("PROFILE_NOT_AUTHORIZED")
    if record["profile_id"] != profile.get("profile_id") or record["scope_ref"] != profile.get("scope_ref"):
        raise ContractError("PROFILE_SCOPE_MISMATCH")
    if not isinstance(record["subject_ref"], str) or not re.fullmatch(r"syn:[A-Za-z0-9._:-]{1,100}", record["subject_ref"]):
        raise ContractError("SUBJECT_REF_INVALID")
    bindings = profile.get("bindings")
    if not isinstance(bindings, dict) or set(bindings) != {"category_label", "unit_kind", "pos_label", "lemma", "context"}:
        raise ContractError("PROFILE_BINDINGS_INVALID")
    names = list(bindings.values())
    allowlist = profile.get("allowed_fields")
    if not all(isinstance(s, str) and s for s in names) or len(names) != len(set(names)) or not isinstance(allowlist, list) or len(allowlist) != len(set(allowlist)) or not set(allowlist) <= set(names):
        raise ContractError("PROFILE_BINDINGS_INVALID")
    fields = record["fields"]
    if not isinstance(fields, dict):
        raise ContractError("INPUT_FIELDS_INVALID")
    # Check names before touching any values; do not examine unapproved content.
    if not set(fields) <= set(allowlist):
        raise ContractError("UNAPPROVED_FIELD_PRESENT")
    for name, f in fields.items():
        if not isinstance(f, dict) or not {"state"} <= set(f) or not set(f) <= {"state", "value"} or f["state"] not in STATES:
            raise ContractError("OBSERVATION_STATE_INVALID")
        if f["state"] != "READABLE":
            if "value" in f and f["value"] is not None:
                raise ContractError("UNOBSERVABLE_VALUE_PRESENT")
            continue
        if "value" not in f or (f["value"] is not None and not isinstance(f["value"], str)):
            raise ContractError("INVALID_FIELD_VALUE")
        limit = 4096 if name in (bindings["lemma"], bindings["context"]) else 512
        if isinstance(f["value"], str) and len(f["value"]) > limit:
            raise ContractError("FIELD_SIZE_LIMIT")
        if isinstance(f["value"], str) and any(unicodedata.category(c) == "Cs" for c in f["value"]):
            raise ContractError("INVALID_UNICODE")
    return digest(record)


def binding_for(record, profile, rules, observation_sha256):
    return {"scope_ref": record["scope_ref"], "subject_ref": record["subject_ref"],
            "profile_id": record["profile_id"], "profile_sha256": digest(profile),
            "observation_sha256": observation_sha256, "mapping_version": rules.version,
            "mapping_sha256": rules.sha256}


def _parse_label(value, rules, tier):
    normalized = normalize_label(value)
    if not normalized:
        return (None, "EMPTY", [])
    aliases = rules.data["unit_aliases" if tier == "UNIT_KIND" else "category_aliases"]
    tokens = [s.strip() for s in SEPARATORS.split(normalized) if s.strip()]
    if not tokens:
        return ("UNKNOWN", "UNRECOGNIZED_LABEL", [])
    values, unknown = set(), False
    for token in tokens:
        if tier == "POS_LABEL" and token in rules.data["compound_pos_labels"]:
            values.update(rules.data["compound_pos_labels"][token])
        elif token in aliases:
            values.add(aliases[token])
        else:
            unknown = True
    if unknown:
        return ("UNKNOWN", "UNRECOGNIZED_LABEL", sorted(values))
    if tier == "POS_LABEL" and not values <= LEXICAL | {"UNKNOWN"}:
        return ("UNKNOWN", "NON_LEXICAL_POS_LABEL", sorted(values))
    if len(values) != 1:
        return ("UNKNOWN", "AMBIGUOUS_LABEL", sorted(values))
    value = next(iter(values))
    if value == "UNKNOWN":
        return (value, "EXPLICIT_UNKNOWN", [value])
    if value == "MIXED":
        return ("UNKNOWN", "MIXED_STUDY_UNIT", [])
    return (value, "EXACT_LABEL", [value])


def _classify(record, rules, profile, override_events=None):
    if rules is None:
        return _result(None, None, "MAPPING_CONTRACT_MISSING")
    try:
        validate_rules(rules.data)
        if digest(rules.data) != rules.semantic_sha256:
            raise ContractError("MAPPING_IN_MEMORY_MUTATION")
    except (ContractError, TypeError, AttributeError):
        return _result(None, None, "MAPPING_CONTRACT_INVALID")
    try:
        observation_sha = validate_record(record, profile)
    except (ContractError, TypeError) as exc:
        code = str(exc) if isinstance(exc, ContractError) else "INPUT_SHAPE_INVALID"
        return _result(rules, "UNKNOWN", code)
    warnings = []
    if override_events is not None:
        try:
            states, history = replay_overrides(override_events)
            binding = binding_for(record, profile, rules, observation_sha)
            current = states.get(digest(binding))
            if current and current["category"] is not None:
                return _result(rules, current["category"], "MANUAL_OVERRIDE", "BOUND_MANUAL_OVERRIDE",
                               [current["category"]], observation_sha, current["head"])
            if not current and any(e["binding"]["scope_ref"] == record["scope_ref"] and e["binding"]["subject_ref"] == record["subject_ref"] for e in history.values()):
                warnings.append("STALE_OVERRIDE_NOT_APPLIED")
        except (OverrideError, TypeError, KeyError, ValueError):
            return _result(rules, "UNKNOWN", "OVERRIDE_LOG_INVALID", observation_sha256=observation_sha)
    fields = record["fields"]
    missing = []
    for key, tier in (("category_label", "CATEGORY_LABEL"), ("unit_kind", "UNIT_KIND"), ("pos_label", "POS_LABEL")):
        name = profile["bindings"][key]
        f = fields.get(name, {"state": "MISSING"})
        state = f["state"] if name in profile["allowed_fields"] else "NOT_AUTHORIZED"
        if state != "READABLE":
            missing.append(state)
            continue
        try:
            category, reason, candidates = _parse_label(f.get("value"), rules, tier)
        except ContractError as exc:
            return _result(rules, "UNKNOWN", str(exc), tier, observation_sha256=observation_sha, warnings=warnings)
        if category is None:
            missing.append("EMPTY")
            continue
        if tier == "UNIT_KIND" and category == "WORD":
            continue
        return _result(rules, category, reason, tier, [c for c in candidates if c in CATEGORIES], observation_sha, warnings=warnings)
    priority = ("NOT_AUTHORIZED", "UNOBSERVABLE", "READ_ERROR", "EMPTY", "MISSING")
    why = next((s for s in priority if s in missing), "MISSING")
    reason = {"NOT_AUTHORIZED": "NO_AUTHORIZED_CLASSIFICATION_FIELD", "UNOBSERVABLE": "FIELD_UNOBSERVABLE",
              "READ_ERROR": "FIELD_READ_ERROR", "EMPTY": "EMPTY_CLASSIFICATION_FIELDS", "MISSING": "NO_CLASSIFICATION_FIELDS"}[why]
    return _result(rules, "UNKNOWN", reason, observation_sha256=observation_sha, warnings=warnings)


def classify(record, rules, profile, override_events=None):
    result = _classify(record, rules, profile, override_events)
    valid = result["observation_sha256"] is not None
    result.update({"profile_id": profile["profile_id"] if valid else None,
                   "profile_sha256": digest(profile) if valid else None,
                   "scope_ref": record["scope_ref"] if valid else None,
                   "subject_ref": record["subject_ref"] if valid else None})
    return result


def replay_overrides(events):
    if not isinstance(events, list):
        raise OverrideError("OVERRIDE_LIST_INVALID")
    states, history, last_hash = {}, {}, None
    required = {"schema_version", "source_kind", "sequence", "event_id", "previous_event_sha256", "event_sha256", "binding", "action", "expected_head", "before_category", "after_category", "target_event_id", "actor_ref", "authorization_ref", "reason_code", "recorded_at"}
    bkeys = {"scope_ref", "subject_ref", "profile_id", "profile_sha256", "observation_sha256", "mapping_version", "mapping_sha256"}
    for seq, e in enumerate(events, 1):
        if not isinstance(e, dict) or set(e) != required or type(e["sequence"]) is not int or e["sequence"] != seq:
            raise OverrideError("OVERRIDE_SHAPE_OR_SEQUENCE_INVALID")
        if e["schema_version"] != OVERRIDE_VERSION or e["source_kind"] != "SYNTHETIC":
            raise OverrideError("OVERRIDE_VERSION_OR_SOURCE_INVALID")
        if e["event_id"] in history or not isinstance(e["event_id"], str) or not e["event_id"].startswith("syn:"):
            raise OverrideError("OVERRIDE_ID_INVALID")
        if e["previous_event_sha256"] != last_hash or digest({k:v for k,v in e.items() if k != "event_sha256"}) != e["event_sha256"]:
            raise OverrideError("OVERRIDE_HASH_CHAIN_INVALID")
        b = e["binding"]
        if not isinstance(b, dict) or set(b) != bkeys or not all(isinstance(v, str) and v for v in b.values()):
            raise OverrideError("OVERRIDE_BINDING_INVALID")
        if not all(HEX64.fullmatch(b[k]) for k in ("profile_sha256", "observation_sha256", "mapping_sha256")):
            raise OverrideError("OVERRIDE_BINDING_INVALID")
        if not all(isinstance(e[k], str) and e[k] for k in ("actor_ref", "authorization_ref", "reason_code", "recorded_at")):
            raise OverrideError("OVERRIDE_AUDIT_FIELDS_MISSING")
        try:
            timestamp = datetime.fromisoformat(e["recorded_at"].replace("Z", "+00:00"))
            if timestamp.utcoffset() is None:
                raise ValueError("timezone missing")
        except ValueError as exc:
            raise OverrideError("OVERRIDE_TIMESTAMP_INVALID") from exc
        if e["authorization_ref"] != "SYNTHETIC_MANUAL_ACTION_NO_REAL_GRANT":
            raise OverrideError("OVERRIDE_AUTHORIZATION_UNSUPPORTED")
        key = digest(b)
        current = states.get(key, {"head": None, "category": None})
        if e["expected_head"] != current["head"] or e["before_category"] != current["category"]:
            raise OverrideError("OVERRIDE_CONCURRENT_EDIT")
        action, after = e["action"], e["after_category"]
        if action == "SET":
            if after not in CATEGORIES or e["target_event_id"] is not None:
                raise OverrideError("OVERRIDE_SET_INVALID")
        elif action == "CLEAR":
            if after is not None or e["target_event_id"] is not None:
                raise OverrideError("OVERRIDE_CLEAR_INVALID")
        elif action == "ROLLBACK":
            target = history.get(e["target_event_id"])
            if not target or target["binding"] != b or target["after_category"] != after:
                raise OverrideError("OVERRIDE_ROLLBACK_TARGET_INVALID")
        else:
            raise OverrideError("OVERRIDE_ACTION_INVALID")
        states[key] = {"head": e["event_id"], "category": after}
        history[e["event_id"]] = e
        last_hash = e["event_sha256"]
    return states, history


def make_override(events, binding, action, category=None, target_event_id=None):
    """Synthetic fixture helper, pure in-memory; not a user authorization API."""
    states, history = replay_overrides(events)
    current = states.get(digest(binding), {"head": None, "category": None})
    if action == "ROLLBACK":
        if target_event_id not in history:
            raise OverrideError("OVERRIDE_ROLLBACK_TARGET_INVALID")
        category = history[target_event_id]["after_category"]
    elif action == "CLEAR":
        category = None
    e = {"schema_version": OVERRIDE_VERSION, "source_kind": "SYNTHETIC", "sequence": len(events)+1,
         "event_id": f"syn:override-{len(events)+1:04d}", "previous_event_sha256": events[-1]["event_sha256"] if events else None,
         "binding": binding, "action": action, "expected_head": current["head"], "before_category": current["category"],
         "after_category": category, "target_event_id": target_event_id, "actor_ref": "syn:manual-reviewer",
         "authorization_ref": "SYNTHETIC_MANUAL_ACTION_NO_REAL_GRANT", "reason_code": "SYNTHETIC_CORRECTION_EXAMPLE",
         "recorded_at": "2026-10-28T00:00:00Z"}
    e["event_sha256"] = digest(e)
    replay_overrides(events+[e])
    return e
