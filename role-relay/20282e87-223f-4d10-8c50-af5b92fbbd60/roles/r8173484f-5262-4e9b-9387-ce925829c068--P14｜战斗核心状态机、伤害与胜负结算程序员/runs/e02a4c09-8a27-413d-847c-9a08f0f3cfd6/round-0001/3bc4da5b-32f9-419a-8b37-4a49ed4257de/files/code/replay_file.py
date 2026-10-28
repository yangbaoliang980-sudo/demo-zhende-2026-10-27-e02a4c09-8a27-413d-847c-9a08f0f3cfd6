"""Re-execute an exported P14 input chain, optionally compare frozen outputs."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from battle_core.replay import replay
from battle_core.wire import FrozenMessage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--expected-state", type=Path)
    parser.add_argument("--expected-snapshot", type=Path)
    parser.add_argument("--expected-result", type=Path)
    parser.add_argument("--expected-execution", type=Path)
    args = parser.parse_args()
    core = replay(json.loads(args.input.read_text(encoding="utf-8")))
    state = core.state()
    snapshot = core.snapshot(state.value["snapshot"]["battle_id"])
    result = core.result()
    comparisons = []
    for kind, path, current in (("state", args.expected_state, state),
                                ("snapshot", args.expected_snapshot, snapshot),
                                ("result", args.expected_result, result)):
        if path is not None:
            if current is None or path.read_bytes() != current.raw:
                raise ValueError("REPLAY_OUTPUT_BYTES_MISMATCH: " + kind)
            comparisons.append({"output": kind, "comparison": "EXACT_FILE_BYTES", "status": "PASS"})
    batches = core.committed_batches()
    if args.expected_execution is not None:
        expected = json.loads(args.expected_execution.read_text(encoding="utf-8"))
        frozen = tuple(FrozenMessage.from_value(b).raw for b in expected["batches"])
        if tuple(b.raw for b in batches) != frozen:
            raise ValueError("REPLAY_BATCH_BYTES_MISMATCH")
        comparisons.append({"output": "all_batches", "comparison": "EXACT_CANONICAL_BYTES", "status": "PASS"})
    report = {"status": "PASS", "scope": "P14_AUTHOR_ISOLATED_REEXECUTION",
        "input_file_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "replay_input_sha256": core.export_replay().sha256,
        "commits": len(batches), "events": sum(len(b.value["events"]) for b in batches),
        "state_sha256": state.sha256, "snapshot_sha256": snapshot.sha256,
        "result_sha256": None if result is None else result.sha256,
        "outcome": snapshot.value["outcome"], "comparisons": comparisons}
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, indent=2))
        sys.exit(1)
