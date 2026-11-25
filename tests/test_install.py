#!/usr/bin/env python3
"""Tests for install_skill packaging, $CLAUDE_CONFIG_DIR support, --check, and --uninstall."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import install_skill  # noqa: E402


class InstallerTests(unittest.TestCase):
    def test_install_check_and_uninstall_in_clean_temp_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            repo = root / "repo"
            (repo / "skills/symphony/references").mkdir(parents=True)
            (repo / "score").mkdir()
            (repo / "scripts").mkdir()
            (repo / "examples").mkdir()
            (repo / "agents").mkdir()
            (repo / "skills/symphony/SKILL.md").write_text("# Symphony\n", encoding="utf-8")
            (repo / "score/OPERATING.md").write_text("# Score\n", encoding="utf-8")
            (repo / "agents/symphony-builder.md").write_text("# Builder\n", encoding="utf-8")
            (repo / "LICENSE").write_text("MIT\n", encoding="utf-8")

            subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
            subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "init"], check=True)

            home = root / "home"
            home.mkdir(mode=0o700)
            codex_home = root / "codex_home"
            claude_dir = root / "claude_cfg"
            env = {"HOME": str(home), "CODEX_HOME": str(codex_home), "CLAUDE_CONFIG_DIR": str(claude_dir)}

            with (
                mock.patch.dict(os.environ, env),
                mock.patch.object(install_skill, "REPO", repo),
            ):
                with mock.patch.object(sys, "argv", ["install_skill.py"]):
                    self.assertEqual(install_skill.main(), 0)
                self.assertTrue((codex_home / "skills/symphony").is_symlink())
                self.assertTrue((claude_dir / "skills/symphony").is_symlink())
                self.assertTrue((claude_dir / "agents/symphony-builder.md").is_symlink())

                with mock.patch.object(sys, "argv", ["install_skill.py", "--check"]):
                    self.assertEqual(install_skill.main(), 0)

                with mock.patch.object(sys, "argv", ["install_skill.py", "--uninstall"]):
                    self.assertEqual(install_skill.main(), 0)
                self.assertFalse((codex_home / "skills/symphony").exists())
                self.assertFalse((claude_dir / "agents/symphony-builder.md").exists())


if __name__ == "__main__":
    unittest.main()
