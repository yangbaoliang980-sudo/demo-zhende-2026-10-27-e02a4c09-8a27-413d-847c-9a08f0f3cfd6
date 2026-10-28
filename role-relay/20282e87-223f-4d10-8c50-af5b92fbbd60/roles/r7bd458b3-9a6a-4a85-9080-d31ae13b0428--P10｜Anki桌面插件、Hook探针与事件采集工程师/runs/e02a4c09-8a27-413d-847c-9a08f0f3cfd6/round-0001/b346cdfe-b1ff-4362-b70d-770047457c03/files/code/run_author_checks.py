"""Re-run P10 report checks into a new directory outside this frozen bundle."""
import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(ROOT) or output.exists():
        parser.error("Use a new output directory outside the frozen report bundle.")
    output.mkdir(parents=True)
    consumed = {"anki_hook_probe.py", "verification/run_author_checks.py",
                "verification/test_report_guards.py", "source_input_receipt.json",
                "reference_inputs.json", "prerequisites.json", "sample_inventory.json"}
    fixed = [{"path": str(p.relative_to(ROOT)), "size_bytes": p.stat().st_size,
              "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
             for p in sorted(ROOT.rglob("*")) if p.is_file()
             and (str(p.relative_to(ROOT)) in consumed or p.is_relative_to(ROOT / "sources"))]
    (output / "input_bindings.json").write_text(json.dumps(fixed, ensure_ascii=False, indent=2) + "\n")
    commands = [
        ("preflight", [sys.executable, "-B", "anki_hook_probe.py", "preflight"], 3),
        ("static_reference", [sys.executable, "-B", "anki_hook_probe.py", "scan-reference"], 0),
        ("report_guard_unit", [sys.executable, "-B", "-m", "unittest", "discover", "-s", "verification", "-p", "test_report_guards.py", "-v"], 0),
    ]
    rows = []
    for name, command, expected in commands:
        started = datetime.now(timezone.utc).isoformat()
        result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=60)
        (output / (name + ".stdout.log")).write_bytes(result.stdout)
        (output / (name + ".stderr.log")).write_bytes(result.stderr)
        rows.append({"check": name, "command": command, "cwd": str(ROOT),
                     "started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                     "expected_exit": expected, "actual_exit": result.returncode,
                     "result": ("EXPECTED_BLOCKED" if expected == 3 else "PASS") if result.returncode == expected else "FAIL",
                     "scope": "AUTHOR_REPORT_CHECK_ONLY_NOT_PLUGIN_OR_INDEPENDENT_TEST"})
    drift = [row["path"] for row in fixed if hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest() != row["sha256"]]
    final = {"task_id": "P10-S04-PROBE-001", "runs": rows, "input_drift": drift,
             "status": "PASS_AUTHOR_REPORT_CHECKS" if not drift and all(r["actual_exit"] == r["expected_exit"] for r in rows) else "FAIL",
             "real_anki_runtime": "NOT_RUN", "independent_review": "NOT_RUN"}
    (output / "run_receipt.json").write_text(json.dumps(final, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(final, ensure_ascii=False, indent=2))
    return 0 if final["status"] == "PASS_AUTHOR_REPORT_CHECKS" else 2


if __name__ == "__main__":
    sys.exit(main())
