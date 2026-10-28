"""Verify the portable delivery and original upstream bytes; standard library only.

The manifest deliberately excludes itself. Its bytes and the enclosing ZIP are
bound by the external delivery_receipt.json, avoiding circular hashes.
"""
from pathlib import Path, PurePosixPath
import csv
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "delivery_manifest.sha256.tsv"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contained_file(name):
    pure = PurePosixPath(name)
    if pure.is_absolute() or not pure.parts or any(p in (".", "..") for p in pure.parts):
        raise ValueError("UNSAFE_MANIFEST_PATH: " + name)
    if pure.as_posix() != name or "\\" in name:
        raise ValueError("NON_CANONICAL_MANIFEST_PATH: " + name)
    path = ROOT.joinpath(*pure.parts)
    for ancestor in (path, *path.parents):
        if ancestor == ROOT:
            break
        if ancestor.is_symlink():
            raise ValueError("SYMLINK_NOT_ALLOWED: " + name)
    if ROOT not in path.resolve().parents:
        raise ValueError("PATH_OUTSIDE_PACKAGE: " + name)
    if not path.is_file():
        raise ValueError("MISSING_FILE: " + name)
    return path


def verify():
    manifest = ROOT / MANIFEST
    if not manifest.is_file():
        raise ValueError("MANIFEST_MISSING")
    with manifest.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if not rows:
        raise ValueError("EMPTY_MANIFEST")
    required = {"relative_path", "size_bytes", "sha256", "format", "version",
                "source_input_hashes", "owner", "recipients", "modification_whitelist",
                "validation_scope"}
    if set(rows[0]) != required:
        raise ValueError("MANIFEST_COLUMNS")
    names = set()
    total_bytes = 0
    for row in rows:
        name = row["relative_path"]
        if name == MANIFEST or name in names:
            raise ValueError("SELF_OR_DUPLICATE_MANIFEST_ENTRY: " + name)
        names.add(name)
        path = contained_file(name)
        if path.stat().st_size != int(row["size_bytes"]):
            raise ValueError("SIZE_MISMATCH: " + name)
        if digest(path) != row["sha256"]:
            raise ValueError("SHA256_MISMATCH: " + name)
        total_bytes += path.stat().st_size
    observed = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*")
                if p.is_file() and "__pycache__" not in p.parts}
    if observed != names | {MANIFEST}:
        raise ValueError("FILE_SET_MISMATCH: " + json.dumps({
            "unlisted": sorted(observed - names - {MANIFEST}),
            "missing": sorted(names - observed)}, ensure_ascii=False))
    receipt = json.loads((ROOT / "evidence/source_input_receipt.json").read_text(encoding="utf-8"))
    sources = receipt["sources"]
    seen_sources = set()
    for source in sources:
        name = source["package_path"]
        if name in seen_sources:
            raise ValueError("DUPLICATE_SOURCE_RECORD: " + name)
        seen_sources.add(name)
        path = contained_file(name)
        if path.stat().st_size != source["size_bytes"] or digest(path) != source["sha256"]:
            raise ValueError("UPSTREAM_BYTES_CHANGED: " + name)
    return {"status": "PASS", "manifest_entries": len(rows),
            "package_files_including_manifest": len(observed),
            "listed_size_bytes": total_bytes, "preserved_original_sources": len(sources),
            "manifest_sha256": digest(manifest),
            "scope": "BYTE_INTEGRITY_ONLY_NOT_INDEPENDENT_GAME_ACCEPTANCE",
            "ignored_generated_directories": ["__pycache__"]}


if __name__ == "__main__":
    try:
        report = verify()
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, indent=2))
        sys.exit(1)
    print(json.dumps(report, ensure_ascii=False, indent=2))
