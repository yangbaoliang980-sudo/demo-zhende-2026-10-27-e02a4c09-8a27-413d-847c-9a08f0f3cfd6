"""Author tests of the report checker, NOT plugin/outbox/Anki tests.

Malformed snippets below are parser fixtures only, never review events.
"""
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import anki_hook_probe as probe


class ReportGuardTests(unittest.TestCase):
    def test_byte_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sample.txt").write_bytes(b"changed")
            row = {"package_path": "sample.txt", "size_bytes": 8,
                   "sha256": hashlib.sha256(b"original").hexdigest()}
            with self.assertRaises(probe.EvidenceError):
                probe.verify_rows(root, [row])

    def test_size_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sample.txt").write_bytes(b"abc")
            row = {"package_path": "sample.txt", "size_bytes": 4,
                   "sha256": hashlib.sha256(b"abc").hexdigest()}
            with self.assertRaises(probe.EvidenceError):
                probe.verify_rows(root, [row])

    def test_unsafe_paths_rejected(self):
        for path in ("../outside", "/tmp/outside", "C:/outside", "a\\b", "a/../b", "./sample"):
            with self.subTest(path=path), self.assertRaises(probe.EvidenceError):
                probe.confined_file(ROOT, path)

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "real").write_text("data")
            (root / "alias").symlink_to(root / "real")
            with self.assertRaises(probe.EvidenceError):
                probe.confined_file(root, "alias")

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.json"
            path.write_text('{"approved":false,"approved":true}')
            with self.assertRaises(probe.EvidenceError):
                probe.strict_json(path)

    def test_nonfinite_json_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.json"
            path.write_text('{"value":NaN}')
            with self.assertRaises(probe.EvidenceError):
                probe.strict_json(path)

    def test_empty_bindings_rejected(self):
        with self.assertRaises(probe.EvidenceError):
            probe.verify_rows(ROOT, [])

    def test_duplicate_bindings_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a").write_bytes(b"a")
            row = {"package_path": "a", "size_bytes": 1, "sha256": hashlib.sha256(b"a").hexdigest()}
            with self.assertRaises(probe.EvidenceError):
                probe.verify_rows(root, [row, row])

    def test_parser_never_executes_source(self):
        text = 'raise RuntimeError("MUST_NOT_EXECUTE")\nHook(name="state_did_undo", args=["changes: OpChangesAfterUndo"])'
        parsed = probe.hook_definitions(text)
        self.assertEqual(parsed["state_did_undo"]["args"], ["changes: OpChangesAfterUndo"])

    def test_nonliteral_metadata_rejected(self):
        with self.assertRaises(probe.EvidenceError):
            probe.hook_definitions('Hook(name="state_did_undo", args=execute_something())')

    def test_duplicate_hook_declaration_rejected(self):
        with self.assertRaises(probe.EvidenceError):
            probe.hook_definitions('Hook(name="state_did_undo")\nHook(name="state_did_undo")')

    def test_missing_hook_not_claimed_supported(self):
        self.assertEqual(probe.hook_definitions("")["state_did_redo"]["status"],
                         "NOT_DECLARED_IN_THIS_REFERENCE")

    def test_real_reference_signature(self):
        result = probe.scan_reference(ROOT)
        self.assertEqual(result["hooks"]["reviewer_did_answer_card"]["args"],
                         ["reviewer: aqt.reviewer.Reviewer", "card: Card", "ease: Literal[1, 2, 3, 4]"])
        self.assertEqual(result["hooks"]["state_did_undo"]["args"], ["changes: OpChangesAfterUndo"])

    def test_reference_not_promoted_to_target(self):
        result = probe.scan_reference(ROOT)
        self.assertFalse(result["is_approved_target"])
        self.assertIsNone(result["target_version"])
        self.assertFalse(result["production_award_authorized"])
        self.assertEqual(result["supported_runtime_events"], [])

    def test_discovered_module_not_runtime_evidence(self):
        with patch.object(importlib.util, "find_spec", return_value=object()):
            result = probe.environment_probe()
        self.assertEqual(result["modules"]["anki"], "DISCOVERABLE")
        self.assertIsNone(result["target_anki_version"])
        self.assertFalse(result["anki_modules_imported"])

    def test_missing_prerequisites_block(self):
        result = probe.preflight(ROOT)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["exit_code"], 3)
        self.assertTrue(any(x["status"] == "BLOCKED_NOT_RECEIVED" for x in result["prerequisites"]))
        self.assertFalse(result["hook_registered"])

    def test_toggling_boolean_cannot_authorize(self):
        prereqs = probe.strict_json(ROOT / "prerequisites.json")
        prereqs["production_authorized"] = True
        prereqs["checks"] = []
        original = probe.strict_json
        def altered(path):
            return prereqs if path.name == "prerequisites.json" else original(path)
        with patch.object(probe, "strict_json", side_effect=altered):
            result = probe.preflight(ROOT)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["production_award_authorized"])
        self.assertFalse(result["ipc_enabled"])

    def test_sample_inventory_does_not_fabricate_events(self):
        samples = probe.strict_json(ROOT / "sample_inventory.json")
        self.assertEqual(samples["raw_samples"], [])
        self.assertEqual(samples["real_review_sample_count"], 0)
        self.assertTrue(all(x["execution_status"] == "NOT_RUN" for x in samples["cases"]))


if __name__ == "__main__":
    unittest.main()
