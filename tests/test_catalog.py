#!/usr/bin/env python3
"""Catalog helpers must stay model-agnostic: no remembered effort names."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import symphony_catalog  # noqa: E402
from symphony_catalog import CatalogError, is_nested_effort, select  # noqa: E402


def model_with_effort(name: str, description: str = "", **extra):
    option = {"reasoningEffort": name, "description": description, **extra}
    return {
        "model": "example-model",
        "isDefault": True,
        "defaultReasoningEffort": name,
        "supportedReasoningEfforts": [option],
    }, option


class NestedEffortTests(unittest.TestCase):
    def test_name_ultra_is_not_inherently_nested(self) -> None:
        model, option = model_with_effort("ultra", "maximum non-delegating reasoning")
        self.assertFalse(is_nested_effort(model, "ultra", option))

    def test_description_delegation_is_nested(self) -> None:
        model, option = model_with_effort("high", "May delegate to subagents")
        self.assertTrue(is_nested_effort(model, "high", option))

    def test_boolean_catalog_field_is_nested(self) -> None:
        model, option = model_with_effort("max", isDelegating=True)
        self.assertTrue(is_nested_effort(model, "max", option))

    def test_new_effort_name_passes_without_skill_edit(self) -> None:
        model, _ = model_with_effort("example-effort", "plain reasoning")
        _, effort, nested = select([model], None, "auto")
        self.assertEqual(effort, "example-effort")
        self.assertFalse(nested)

    def test_auto_nested_default_is_refused(self) -> None:
        model, _ = model_with_effort("high", "spawns nested agents")
        with self.assertRaisesRegex(ValueError, "may delegate"):
            select([model], None, "auto")

    def test_broken_pipe_raises_catalog_error(self) -> None:
        fake_proc = mock.MagicMock()
        fake_proc.pid = 99999
        fake_proc.poll.return_value = 1
        fake_proc.stdin.write.side_effect = BrokenPipeError("broken pipe")
        fake_selector = mock.MagicMock()
        with (
            mock.patch.object(symphony_catalog.subprocess, "Popen", return_value=fake_proc),
            mock.patch.object(symphony_catalog.selectors, "DefaultSelector", return_value=fake_selector),
        ):
            with self.assertRaisesRegex(CatalogError, "closed stdin unexpectedly"):
                symphony_catalog.discover("codex", ".")


if __name__ == "__main__":
    unittest.main()
