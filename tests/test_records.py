#!/usr/bin/env python3
"""Tests for canonical/symlink directory rules, atomic JSON writes, and status/acceptance commands."""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import symphony_records  # noqa: E402
import symphony_status  # noqa: E402


class RecordsAndStatusTests(unittest.TestCase):
    def test_owned_directory_resolves_parent_symlink_and_blocks_leaf_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            real_parent = root / "real-parent"
            real_parent.mkdir()
            linked_parent = root / "linked-parent"
            linked_parent.symlink_to(real_parent)
            leaf = symphony_records.owned_directory(linked_parent / "sub" / "runs")
            self.assertEqual(leaf, real_parent / "sub" / "runs")
            self.assertTrue(leaf.is_dir())

            leaf_symlink = root / "sym-leaf"
            leaf_symlink.symlink_to(real_parent)
            with self.assertRaisesRegex(ValueError, "symlink leaf"):
                symphony_records.owned_directory(leaf_symlink)

    def test_status_filters_summary_and_mark_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp).resolve() / "runs"
            runs.mkdir(mode=0o700)
            attempt = runs / "lane-1-xyz"
            attempt.mkdir(mode=0o700)
            result = {
                "run_id": "lane-1-xyz",
                "at": "2026-09-20T00:00:00+00:00",
                "engine": "codex",
                "seat": "builder",
                "lane": "lane-1",
                "state": "completed",
                "route": "codex-cli",
                "requested_model": "m1",
                "requested_effort": "high",
                "fast": False,
                "resolved_model": "m1",
                "resolved_effort": "high",
                "reported_model": "m1",
                "reported_effort": "high",
                "elapsed_seconds": 12.5,
                "routing_elapsed_seconds": 0.4,
                "attempt": 1,
                "exit": 0,
                "acceptance": "pending",
                "frontier_review": "pending",
                "out": str(attempt / "report.json"),
            }
            (attempt / "result.json").write_text(json.dumps(result), encoding="utf-8")
            failed_result = {**result, "run_id": "lane-2-fail", "lane": "lane-2", "state": "failed", "exit": 1}
            failed_attempt = runs / "lane-2-fail"
            failed_attempt.mkdir(mode=0o700)
            (failed_attempt / "result.json").write_text(json.dumps(failed_result), encoding="utf-8")

            ledger = runs / "ledger.jsonl"
            with mock.patch.dict(os.environ, {"SYMPHONY_OUT": str(runs), "SYMPHONY_LEDGER": str(ledger)}):
                symphony_records.append_record({**result, "state": "started"})
                symphony_records.append_record(result)
                symphony_records.append_record(failed_result)

                with mock.patch.object(sys, "argv", ["symphony_status.py", "mark", "lane-1-xyz", "--acceptance", "accepted", "--review", "completed", "--note", "verified"]):
                    out = io.StringIO()
                    with mock.patch.object(sys, "stdout", out):
                        rc = symphony_status.main()
                self.assertEqual(rc, 0)
                updated = json.loads((attempt / "result.json").read_text(encoding="utf-8"))
                self.assertEqual(updated["acceptance"], "accepted")
                self.assertEqual(updated["frontier_review"], "completed")

                with mock.patch.object(sys, "argv", ["symphony_status.py", "mark", "lane-2-fail", "--acceptance", "accepted"]):
                    with self.assertRaisesRegex(ValueError, "Cannot mark a failed attempt accepted"):
                        symphony_status.main()

                with mock.patch.object(sys, "argv", ["symphony_status.py", "--summary"]):
                    summary_buf = io.StringIO()
                    with mock.patch.object(sys, "stdout", summary_buf):
                        symphony_status.main()
                summary = json.loads(summary_buf.getvalue())
                self.assertEqual(summary["total_runs"], 2)
                self.assertEqual(summary["by_acceptance"]["accepted"], 1)


if __name__ == "__main__":
    unittest.main()
