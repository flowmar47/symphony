#!/usr/bin/env python3
"""Tests for dispatcher job resolution, seat plans, repair guards, argv size checks, and signals."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import symphony_dispatch  # noqa: E402
from symphony_engines import ARGV_BRIEF_LIMIT  # noqa: E402


class DispatchTests(unittest.TestCase):
    def test_seat_plan_defaults_and_no_fast_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = root / "spec.md"
            spec.write_text("# Spec\nBuild feature X safely.\n", encoding="utf-8")
            repo = root / "repo"
            repo.mkdir()
            plan = root / "seat-plan.json"
            plan.write_text(json.dumps({
                "seats": {
                    "builder-heavy": {
                        "engine": "cursor",
                        "model": "example-workhorse",
                        "effort": "high",
                        "fast": True,
                    }
                }
            }), encoding="utf-8")
            with mock.patch.dict(os.environ, {"SYMPHONY_SEAT_PLAN": str(plan)}):
                with mock.patch.object(sys, "argv", [
                    "symphony_dispatch.py", "builder", "auto", str(spec), str(repo), "lane-1", "--seat", "builder-heavy",
                ]):
                    engine, job, _, _ = symphony_dispatch.job_for(symphony_dispatch.arguments())
                self.assertEqual(engine.name, "cursor")
                self.assertEqual(job["requested_model"], "example-workhorse")
                self.assertEqual(job["requested_effort"], "high")
                self.assertTrue(job["fast"])

                with mock.patch.object(sys, "argv", [
                    "symphony_dispatch.py", "builder", "xhigh", str(spec), str(repo), "lane-1", "--seat", "builder-heavy", "--no-fast",
                ]):
                    _, job2, _, _ = symphony_dispatch.job_for(symphony_dispatch.arguments())
                self.assertEqual(job2["requested_effort"], "xhigh")
                self.assertFalse(job2["fast"])

    def test_argv_limit_checks_full_prompt_including_overhead(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = root / "spec.md"
            # Just under ARGV_BRIEF_LIMIT by itself, but exceeds once dispatcher prefix and contract are added.
            spec.write_text("x" * (ARGV_BRIEF_LIMIT - 50), encoding="utf-8")
            repo = root / "repo"
            repo.mkdir()
            with mock.patch.object(sys, "argv", [
                "symphony_dispatch.py", "builder", "high", str(spec), str(repo), "lane-1", "--engine", "agy", "--model", "m1",
            ]):
                with self.assertRaisesRegex(ValueError, "full prompt as an argument"):
                    symphony_dispatch.job_for(symphony_dispatch.arguments())

    def test_resume_precheck_refuses_already_claimed_repair_and_handles_legacy_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            attempt = Path(tmp).resolve() / "lane-1-abc"
            attempt.mkdir()
            (attempt / "spec.txt").write_text("Fix bug\n", encoding="utf-8")
            fix = Path(tmp).resolve() / "fix.md"
            fix.write_text("Apply fix\n", encoding="utf-8")
            base = {
                "seat": "scout",
                "directory": str(attempt),
                "lane": "lane-1",
                "sandbox": "read-only",
                "mode": "ask",
                "attempt": 1,
                "resolved_model": "m1",
                "resolved_effort": "low",
                "fast": False,
                "brief_sha256": "abc",
                "route": "codex-cli",
                "thread": "11111111-1111-1111-1111-111111111111",
                "run_id": attempt.name,
                "out": str(attempt / "report.json"),
                "state": "failed",
            }
            (attempt / "request.json").write_text(json.dumps(base), encoding="utf-8")
            (attempt / "result.json").write_text(json.dumps(base), encoding="utf-8")

            with mock.patch.object(sys, "argv", [
                "symphony_dispatch.py", "resume", str(attempt / "result.json"), str(fix),
            ]):
                engine, job, _, _ = symphony_dispatch.job_for(symphony_dispatch.arguments())
            self.assertEqual(engine.name, "codex")
            self.assertEqual(job["attempt"], 2)

            (attempt / "repair-claimed.json").write_text("{}\n", encoding="utf-8")
            with mock.patch.object(sys, "argv", [
                "symphony_dispatch.py", "resume", str(attempt / "result.json"), str(fix),
            ]):
                with self.assertRaisesRegex(ValueError, "already claimed"):
                    symphony_dispatch.job_for(symphony_dispatch.arguments())


if __name__ == "__main__":
    unittest.main()
