#!/usr/bin/env python3
"""Tests for confirmed seat plan validation, checking, and atomic persistence."""

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

import symphony_seatplan  # noqa: E402


class SeatPlanTests(unittest.TestCase):
    def test_validate_and_save_under_temp_home(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan_file = Path(tmp) / "seat-plan.json"
            plan = {
                "seats": {
                    "scout": {"engine": "codex", "model": "example-fast", "effort": "low"},
                    "reviewer": {"engine": "native", "model": "host-frontier", "effort": "xhigh"},
                }
            }
            fake_catalogs = {
                "codex": {
                    "ok": True,
                    "models": [{
                        "model": "example-fast",
                        "efforts": ["low", "high"],
                        "default_effort": "low",
                        "is_default": True,
                        "fast": False,
                        "raw": {
                            "model": "example-fast",
                            "supportedReasoningEfforts": [{"reasoningEffort": "low", "description": "fast"}],
                        },
                    }],
                }
            }
            with (
                mock.patch.dict(os.environ, {"SYMPHONY_SEAT_PLAN": str(plan_file)}),
                mock.patch.object(symphony_seatplan, "discover_all", return_value=fake_catalogs),
                mock.patch.object(sys, "argv", ["symphony_seatplan.py", "save", "-"]),
                mock.patch.object(sys, "stdin", new=mock.MagicMock(read=lambda: json.dumps(plan))),
            ):
                rc = symphony_seatplan.main()
            self.assertEqual(rc, 0)
            saved = json.loads(plan_file.read_text(encoding="utf-8"))
            self.assertIn("confirmed_at", saved)
            self.assertEqual(saved["seats"]["scout"]["model"], "example-fast")


if __name__ == "__main__":
    unittest.main()
