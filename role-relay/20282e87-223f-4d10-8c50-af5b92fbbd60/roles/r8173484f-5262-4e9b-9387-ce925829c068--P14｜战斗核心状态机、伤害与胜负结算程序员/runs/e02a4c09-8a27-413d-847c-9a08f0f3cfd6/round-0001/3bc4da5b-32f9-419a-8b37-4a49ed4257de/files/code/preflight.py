"""Read the recorded production blockers. Does not launch an engine or write files."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    mapping = json.loads((ROOT / "handoff/path_mapping_request.json").read_text(encoding="utf-8"))
    blockers = json.loads((ROOT / "handoff/blockers.json").read_text(encoding="utf-8"))["items"]
    production = [b for b in blockers if b["stage"] not in (
        "optional-author-crosscheck", "independent-acceptance") and b["status"] == "BLOCKED"]
    # This release contains a request, not a P13-approved mapping. Even editing
    # the boolean locally cannot turn this package into a production approval.
    report = {"status": "BLOCKED", "exit_code": 3,
        "scope": "RECORDED_PRODUCTION_READINESS_ONLY",
        "engine_process": "NOT_RUN", "P32_P33_P35": "NOT_RUN",
        "mapping_status": mapping["status"],
        "production_write_authorized": mapping["production_write_authorized"],
        "actual_production_root": mapping["actual_production_root"],
        "blockers": [{k: b[k] for k in ("id", "owner", "stage", "missing")} for b in production],
        "resolution": "Require new fixed upstream artifacts and approvals; this script does not grant them."}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 3


if __name__ == "__main__":
    sys.exit(main())
