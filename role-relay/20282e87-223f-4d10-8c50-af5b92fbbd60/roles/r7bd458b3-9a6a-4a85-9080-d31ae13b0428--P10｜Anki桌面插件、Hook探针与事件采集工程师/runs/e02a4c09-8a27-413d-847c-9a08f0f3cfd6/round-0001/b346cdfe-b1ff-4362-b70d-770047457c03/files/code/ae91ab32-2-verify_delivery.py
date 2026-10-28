"""Verify the report bundle's manifest, never grant runtime approval."""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from anki_hook_probe import EvidenceError, confined_file, strict_json, verify_rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        manifest_path = root / "delivery_manifest.sha256.tsv"
        with manifest_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        converted = [{"package_path": row["relative_path"], "sha256": row["sha256"],
                      "size_bytes": int(row["actual_bytes"])} for row in rows]
        verify_rows(root, converted)
        listed = {row["package_path"] for row in converted} | {"delivery_manifest.sha256.tsv"}
        actual = {str(path.relative_to(root)) for path in root.rglob("*") if path.is_file()}
        if listed != actual:
            raise EvidenceError("UNLISTED_OR_MISSING_BUNDLE_FILES")
        for row in rows:
            if row["production_write_authorized"] != "false" or row["independent_acceptance"] != "NOT_RUN":
                raise EvidenceError("INVALID_APPROVAL_CLAIM")
        flag = strict_json(root / "QUARANTINED.json")
        if flag["production_award_authorized"] is not False or flag["supported_runtime_events"] != []:
            raise EvidenceError("QUARANTINE_FLAG_DRIFT")
        print(json.dumps({"status": "PASS_DELIVERY_BYTES_ONLY", "manifest_entries": len(rows),
                          "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                          "runtime": "NOT_RUN", "production_award_authorized": False}, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc), "production_award_authorized": False}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
