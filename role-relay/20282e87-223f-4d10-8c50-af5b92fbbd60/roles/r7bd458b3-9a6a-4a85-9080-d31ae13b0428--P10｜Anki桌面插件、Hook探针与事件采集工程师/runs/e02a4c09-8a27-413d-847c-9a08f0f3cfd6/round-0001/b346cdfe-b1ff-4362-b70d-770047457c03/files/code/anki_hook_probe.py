"""P10 report appendix: static source inspection and environment preflight.

This is NOT an Anki add-on, runtime Hook probe, outbox, IPC implementation,
or evidence of a completed review. It never imports or executes Anki code,
opens a collection, installs a hook, sends an event, or authorizes rewards.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import platform
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

VERSION = "P10-REPORT-PROBE/0.1.0"
ROOT = Path(__file__).resolve().parent
HOOK_NAMES = (
    "reviewer_will_answer_card", "reviewer_did_answer_card", "state_did_undo",
    "state_did_redo", "state_did_revert", "operation_did_execute",
    "undo_state_did_change", "collection_did_load", "profile_did_open",
    "profile_will_close", "backup_did_complete",
    "collection_will_temporarily_close", "collection_did_temporarily_close",
)


class EvidenceError(ValueError):
    """Input cannot be treated as intact report evidence."""


def strict_json(path: Path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise EvidenceError("DUPLICATE_JSON_KEY")
            result[key] = value
        return result

    def nonfinite(_):
        raise EvidenceError("NONFINITE_JSON_NUMBER")

    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs,
                          parse_constant=nonfinite)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(type(exc).__name__) from exc


def confined_file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise EvidenceError("INVALID_RELATIVE_PATH")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts or str(pure) != relative:
        raise EvidenceError("UNSAFE_RELATIVE_PATH")
    root = root.resolve()
    target = root.joinpath(*pure.parts)
    for item in [target, *target.parents]:
        if item == root:
            break
        if item.is_symlink():
            raise EvidenceError("SYMLINK_NOT_ALLOWED")
    if not target.resolve().is_relative_to(root) or not target.is_file():
        raise EvidenceError("MISSING_OR_ESCAPING_FILE")
    return target


def verify_rows(root: Path, rows: list[dict]) -> list[dict]:
    if not isinstance(rows, list) or not rows:
        raise EvidenceError("EMPTY_SOURCE_BINDINGS")
    result, seen = [], set()
    for row in rows:
        relative = row["package_path"]
        if relative in seen:
            raise EvidenceError("DUPLICATE_FILE_BINDING")
        seen.add(relative)
        expected_hash = row["sha256"]
        if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise EvidenceError("INVALID_SHA256")
        expected_size = row["size_bytes"]
        if type(expected_size) is not int or expected_size < 0:
            raise EvidenceError("INVALID_SIZE")
        data = confined_file(root, relative).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != expected_hash or len(data) != expected_size:
            raise EvidenceError("SOURCE_BYTES_MISMATCH:" + relative)
        result.append({"path": relative, "sha256": digest, "size_bytes": len(data),
                       "status": "PASS_BYTES_ONLY"})
    return result


def quarantine_facts() -> dict:
    return {
        "source_generation": "UNVERIFIED",
        "review_event_identity": "UNVERIFIED",
        "undo_target_association": "UNVERIFIED",
        "real_review_sample_count": 0,
        "supported_runtime_events": [],
        "runtime_hook_execution": "NOT_RUN",
        "collection_opened": False,
        "anki_database_modified": False,
        "hook_registered": False,
        "ipc_enabled": False,
        "outbox_implemented": False,
        "production_award_authorized": False,
        "installable": False,
        "disposition": "QUARANTINED",
    }


def environment_probe() -> dict:
    """Only inspect this Python process's installation discovery, not user data."""
    modules = {}
    for name in ("anki", "aqt"):
        try:
            modules[name] = "DISCOVERABLE" if importlib.util.find_spec(name) else "NOT_FOUND"
        except (ImportError, ValueError, AttributeError):
            modules[name] = "DISCOVERY_ERROR"
    return {
        "evidence_kind": "EXECUTION_HOST_ONLY_NOT_USER_TARGET",
        "os": platform.system(), "os_release": platform.release(),
        "architecture": platform.machine(), "python_version": platform.python_version(),
        "modules": modules, "anki_executable_on_path": shutil.which("anki") is not None,
        "anki_executable_launched": False, "anki_modules_imported": False,
        "target_anki_version": None, "target_os": None,
        "limitation": "Module/PATH discovery is not a machine-wide search or a target runtime test.",
    }


def hook_definitions(text: str) -> dict:
    """Parse declarations with AST; never import, exec or eval a source file."""
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        raise EvidenceError("REFERENCE_SYNTAX_ERROR") from exc
    found = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "Hook":
            continue
        keywords = {kw.arg: kw.value for kw in node.keywords if kw.arg}
        name_node = keywords.get("name")
        if not isinstance(name_node, ast.Constant) or name_node.value not in HOOK_NAMES:
            continue
        name = name_node.value
        if name in found:
            raise EvidenceError("DUPLICATE_HOOK_DECLARATION")
        item = {"status": "DECLARED_IN_REFERENCE", "line": node.lineno}
        for key in ("args", "return_type", "legacy_hook"):
            if key in keywords:
                try:
                    value = ast.literal_eval(keywords[key])
                except (ValueError, TypeError) as exc:
                    raise EvidenceError("NONLITERAL_HOOK_METADATA") from exc
                if key == "args" and (not isinstance(value, list) or not all(isinstance(x, str) for x in value)):
                    raise EvidenceError("INVALID_HOOK_ARGUMENTS")
                if key != "args" and not isinstance(value, str):
                    raise EvidenceError("INVALID_HOOK_METADATA")
                item[key] = value
        item.setdefault("args", [])
        found[name] = item
    return {name: found.get(name, {"status": "NOT_DECLARED_IN_THIS_REFERENCE"}) for name in HOOK_NAMES}


def scan_reference(root: Path) -> dict:
    bindings = strict_json(root / "reference_inputs.json")
    checked = verify_rows(root, bindings["files"])
    source = confined_file(root, "sources/anki_reference/qt/tools/genhooks_gui.py")
    return {
        "schema_version": VERSION, "evidence_kind": "STATIC_SOURCE_REVIEW",
        "status": "PASS_STATIC_EXTRACTION_ONLY", "reference_commit": bindings["commit"],
        "source_declared_version": bindings["source_declared_version"],
        "is_approved_target": False, "target_version": None,
        "files_checked": checked, "hooks": hook_definitions(source.read_text(encoding="utf-8")),
        **quarantine_facts(),
    }


def preflight(root: Path) -> dict:
    source_receipt = strict_json(root / "source_input_receipt.json")
    checked = verify_rows(root, source_receipt["consumed_sources"])
    prereqs = strict_json(root / "prerequisites.json")
    checks = []
    for item in prereqs["checks"]:
        row = dict(item)
        ref = row.get("evidence_ref")
        if ref is None:
            row["status"] = "BLOCKED_NOT_RECEIVED"
        else:
            verify_rows(root, [{"package_path": ref, "sha256": row["sha256"],
                               "size_bytes": row["size_bytes"]}])
            row["status"] = "RECEIVED_NOT_APPROVED_FOR_RUNTIME"
        checks.append(row)
    return {
        "schema_version": VERSION, "task_id": "P10-S04-PROBE-001",
        "evidence_kind": "ENVIRONMENT_AND_INPUT_PREFLIGHT_NOT_REVIEW_LOG",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "BLOCKED", "exit_code": 3,
        "environment": environment_probe(), "source_checks": checked,
        "prerequisites": checks,
        "permanent_guard": "This report utility has no runtime/authorization implementation. Supplying files or changing approval booleans cannot enable collection, transport, or awards.",
        **quarantine_facts(),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("preflight", "scan-reference"))
    parser.add_argument("--root", type=Path, default=ROOT,
                        help="Root of an extracted P10 report bundle, not an Anki profile")
    args = parser.parse_args(argv)
    try:
        output = preflight(args.root) if args.mode == "preflight" else scan_reference(args.root)
        code = 3 if args.mode == "preflight" else 0
    except (EvidenceError, KeyError, TypeError) as exc:
        output = {"schema_version": VERSION, "status": "FAIL_INPUT_INTEGRITY",
                  "error": str(exc), **quarantine_facts()}
        code = 2
    print(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
