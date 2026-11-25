#!/usr/bin/env python3
"""Tests for multi-engine catalog parsing, variant folding, scope guards, and report extraction."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import symphony_engines  # noqa: E402
from symphony_engines import (  # noqa: E402
    Agy,
    CLAUDE_ALIASES,
    Claude,
    Codex,
    Cursor,
    EngineError,
    check_extra_args,
    discover_all,
    extract_report,
    group_variants,
    resolve_variant,
)


class EngineTests(unittest.TestCase):
    def test_extra_arg_guards(self) -> None:
        for flag in ("--model=foo", "-mfoo", "--effort=high", "--config=a=b", "-cfoo", "--full-auto", "--tools=bash", "--sandbox=danger-full-access", "-p"):
            with self.assertRaises(EngineError, msg=f"expected refusal for {flag}"):
                check_extra_args("builder", [flag], engine="codex")
        with self.assertRaises(EngineError):
            check_extra_args("scout", ["--dangerously-skip-permissions"], engine="agy")
        with self.assertRaises(EngineError):
            check_extra_args("builder", ["--dangerously-skip-permissions"], engine="codex")
        # Permitted only for agy builder lanes
        check_extra_args("builder", ["--dangerously-skip-permissions"], engine="agy")

    def test_variant_grouping_and_auto_resolution(self) -> None:
        rows = group_variants(["qwen-max", "mistral-medium", "model-a", "model-a-high", "model-a-high-fast"])
        by_name = {row["model"]: row for row in rows}
        self.assertIn("qwen-max", by_name)
        self.assertIn("mistral-medium", by_name)
        self.assertEqual(by_name["qwen-max"]["efforts"], ["default"])
        self.assertEqual(by_name["model-a"]["efforts"], ["default", "high"])
        self.assertEqual(resolve_variant(rows, "model-a", "auto", False), ("model-a", "default", False))
        self.assertEqual(resolve_variant(rows, "model-a", "high", True), ("model-a-high-fast", "high", False))

    def test_codex_resolve_uses_live_metadata_for_nested_effort(self) -> None:
        codex = Codex()
        rows = [{
            "model": "example-model",
            "is_default": True,
            "default_effort": "ultra",
            "efforts": ["low", "ultra", "xhigh"],
            "fast": False,
            "raw": {
                "model": "example-model",
                "isDefault": True,
                "defaultReasoningEffort": "ultra",
                "supportedReasoningEfforts": [
                    {"reasoningEffort": "low", "description": "fast"},
                    {"reasoningEffort": "ultra", "description": "deep non-delegating reasoning"},
                    {"reasoningEffort": "xhigh", "description": "spawns sub-agents", "isDelegating": True},
                ],
            },
        }]
        self.assertEqual(codex.resolve(rows, None, "auto", False), ("example-model", "ultra", False))
        self.assertEqual(codex.resolve(rows, None, "xhigh", False), ("example-model", "xhigh", True))

    def test_claude_aliases_have_no_fable_and_parse_help_efforts(self) -> None:
        self.assertNotIn("fable", CLAUDE_ALIASES)
        claude = Claude()
        with (
            mock.patch.object(symphony_engines.shutil, "which", return_value="/usr/local/bin/claude"),
            mock.patch.object(symphony_engines, "capture", side_effect=[
                "2.1.330",
                "Options:\n  --effort <level>  Effort level (low, medium, high, xhigh, turbo)\n",
            ]),
        ):
            rows = claude.discover(".")
        self.assertEqual(rows[0]["efforts"], ["low", "medium", "high", "xhigh", "turbo"])
        self.assertEqual(claude.resolve(rows, "opus", "turbo", False), ("opus", "turbo", False))

    def test_agy_inspect_handles_null_num_turns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            attempt = Path(tmp)
            (attempt / "events.jsonl").write_text(json.dumps({
                "status": "SUCCESS",
                "conversation_id": "conv-1",
                "num_turns": None,
                "response": '```json\n{"status": "completed", "summary": "ok", "files": [], "evidence": [], "not_run": []}\n```',
            }), encoding="utf-8")
            insp = Agy().inspect(attempt)
            self.assertEqual(insp["terminal"], "failed")
            self.assertTrue(insp["event_error"])

    def test_extract_report_handles_case_and_balanced_inline_json(self) -> None:
        fenced = 'Done.\n```JSON\n{"status": "completed", "summary": "ok", "files": [], "evidence": ["x"], "not_run": []}\n```'
        self.assertEqual(extract_report(fenced)["summary"], "ok")
        inline = 'Prose {not json} and result: {"status": "partial", "summary": "with } brace", "files": [], "evidence": [], "not_run": ["test"]}'
        self.assertEqual(extract_report(inline)["status"], "partial")

    def test_discover_all_records_errors_per_engine(self) -> None:
        with (
            mock.patch.object(symphony_engines.ENGINES["codex"], "discover", return_value=[{"model": "m1"}]),
            mock.patch.object(symphony_engines.ENGINES["agy"], "discover", side_effect=EngineError("missing")),
            mock.patch.object(symphony_engines.shutil, "which", return_value=None),
        ):
            out = discover_all(".", names=["codex", "agy"])
        self.assertTrue(out["codex"]["ok"])
        self.assertFalse(out["agy"]["ok"])
        self.assertEqual(out["agy"]["error"], "missing")


if __name__ == "__main__":
    unittest.main()
