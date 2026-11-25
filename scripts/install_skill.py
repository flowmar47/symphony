#!/usr/bin/env python3
"""Install, verify, or uninstall an exact committed Symphony package without changing host config."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import uuid

from symphony_records import owned_directory, private_directory, write_new

REPO = Path(__file__).resolve().parent.parent


def git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args])


def claude_dir():
    return Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude"))).expanduser().absolute()


def codex_dir():
    return Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser().absolute()


def target_destinations(codex_only, claude_only, no_agents, files):
    destinations = {}
    both = not codex_only and not claude_only
    if both or codex_only:
        destinations[codex_dir() / "skills/symphony"] = ""
    if both or claude_only:
        cdir = claude_dir()
        destinations[cdir / "skills/symphony"] = ""
        if not no_agents:
            for name in sorted(files):
                if name.startswith("agents/") and name.endswith(".md"):
                    destinations[cdir / "agents" / Path(name).name] = name
    return destinations


def package_files(commit):
    files = {}
    for record in git("ls-tree", "-r", "-z", commit).split(b"\0"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        mode, kind, blob = metadata.decode().split()
        path = raw_path.decode()
        if path.startswith("skills/symphony/"):
            target = path[len("skills/symphony/"):]
        elif path.startswith(("score/", "scripts/", "examples/", "agents/")) or path == "LICENSE":
            target = path
        else:
            continue
        if kind != "blob" or mode not in ("100644", "100755") or target in files:
            raise ValueError("Package must contain uniquely mapped regular tracked files")
        data = git("cat-file", "blob", blob)
        files[target] = (data, 0o755 if mode == "100755" else 0o644)
    if "SKILL.md" not in files or "score/OPERATING.md" not in files or not any(name.startswith("agents/") for name in files):
        raise ValueError("Complete skill resources are missing")
    return files


def verify_package(package, files, manifest):
    found = set()
    for path in package.rglob("*"):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
            raise ValueError("Installed package contains a link or special filesystem node")
        if path.is_file():
            found.add(path.relative_to(package).as_posix())
    if found != set(files) | {".symphony-package.json"}:
        raise ValueError("Installed package file set differs from the committed source")
    for relative, (data, mode) in files.items():
        path = package / relative
        if path.read_bytes() != data or stat.S_IMODE(path.stat().st_mode) != mode:
            raise ValueError(f"Installed content/mode mismatch: {relative}")
    if json.loads((package / ".symphony-package.json").read_text()) != manifest:
        raise ValueError("Installed provenance differs from the committed source")


def is_managed_target(destination, relative, packages, original):
    target = destination.resolve()
    package_root = target if relative == "" else target.parents[len(Path(relative).parts) - 1]
    managed = (
        package_root.parent.parent == packages
        and package_root.name == "symphony"
        and (package_root / ".symphony-package.json").is_file()
    )
    if relative == "":
        return target == original.resolve() or managed
    return managed and target == package_root / relative


def run_check(destinations, packages, original):
    problems = []
    for destination, relative in destinations.items():
        if not os.path.lexists(destination):
            problems.append(f"missing: {destination}")
            continue
        if not destination.is_symlink():
            problems.append(f"not a symlink: {destination}")
            continue
        if not is_managed_target(destination, relative, packages, original):
            problems.append(f"foreign link: {destination} -> {os.readlink(destination)}")
            continue
        target = destination.resolve()
        package_root = target if relative == "" else target.parents[len(Path(relative).parts) - 1]
        manifest_path = package_root / ".symphony-package.json"
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            commit = manifest.get("commit")
            if isinstance(commit, str) and commit:
                verify_package(package_root, package_files(commit), manifest)
        print(f"ok {destination} -> {target}")
    if problems:
        for problem in problems:
            print(f"symphony check: {problem}", file=sys.stderr)
        return 1
    return 0


def run_uninstall(destinations, packages, original, data_root):
    removed = {}
    for destination, relative in destinations.items():
        if not os.path.lexists(destination):
            continue
        if not destination.is_symlink() or not is_managed_target(destination, relative, packages, original):
            raise ValueError(f"Refusing to remove unmanaged installation: {destination}")
        removed[str(destination)] = os.readlink(destination)
    if not removed:
        print("No Symphony links present to remove.")
        return 0
    backup = private_directory(data_root / "backups") / str(uuid.uuid4())
    backup.mkdir(mode=0o700)
    write_new(backup / "removed.json", removed)
    for destination in destinations:
        if str(destination) in removed:
            destination.unlink()
            print(f"removed {destination}")
    print(f"Uninstall record written to {backup / 'removed.json'}")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex", action="store_true")
    parser.add_argument("--claude", action="store_true")
    parser.add_argument("--no-agents", action="store_true",
                        help="Skip linking the Symphony seat definitions into $CLAUDE_CONFIG_DIR/agents")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Verify installed links and package hashes without modifying anything")
    mode.add_argument("--uninstall", action="store_true", help="Remove Symphony-managed symlinks without touching foreign files")
    args = parser.parse_args()
    os.umask(0o077)
    data_root = owned_directory(Path.home() / ".symphony")
    packages = private_directory(data_root / "packages")
    original = REPO / "skills/symphony"

    agent_files = [str(p.relative_to(REPO)) for p in sorted((REPO / "agents").glob("*.md"))] if (REPO / "agents").is_dir() else []
    destinations = target_destinations(args.codex, args.claude, args.no_agents, agent_files)
    if args.check:
        return run_check(destinations, packages, original)
    if args.uninstall:
        return run_uninstall(destinations, packages, original, data_root)

    if git("status", "--porcelain=v1").strip():
        raise ValueError("Install only from a clean committed checkout")
    commit = git("rev-parse", "HEAD").decode().strip()
    files = package_files(commit)
    destinations = target_destinations(args.codex, args.claude, args.no_agents, files)
    package = packages / commit / "symphony"
    old_links = {}
    for destination, relative in destinations.items():
        if not os.path.lexists(destination):
            old_links[destination] = None
            continue
        if not destination.is_symlink():
            raise ValueError(f"Refusing unexpected installation: {destination}")
        if not is_managed_target(destination, relative, packages, original):
            raise ValueError(f"Refusing unrelated link: {destination}")
        old_links[destination] = os.readlink(destination)
    manifest = {"commit": commit, "files": {name: {"sha256": hashlib.sha256(data).hexdigest(), "mode": oct(mode)} for name, (data, mode) in files.items()}}
    if not package.exists():
        if os.path.lexists(package):
            raise ValueError("Package destination is an unexpected link")
        private_directory(package.parent)
        package.mkdir(mode=0o700)
        for name, (data, mode) in files.items():
            path = package / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as output:
                output.write(data)
            path.chmod(mode)
        write_new(package / ".symphony-package.json", manifest)
    if package.resolve() != package:
        raise ValueError("Package path must not contain symbolic links")
    verify_package(package, files, manifest)
    backup = private_directory(data_root / "backups") / str(uuid.uuid4())
    backup.mkdir(mode=0o700)
    write_new(backup / "links.json", {str(path): target for path, target in old_links.items()})
    for index, (destination, relative) in enumerate(destinations.items()):
        target = package / relative if relative else package
        destination.parent.mkdir(parents=True, exist_ok=True)
        if old_links[destination] is not None:
            if not destination.is_symlink() or os.readlink(destination) != old_links[destination]:
                raise ValueError("Installation changed during update; stop without overwriting it")
            if destination.resolve() == target.resolve():
                print(f"unchanged {destination} -> {target}")
                continue
            destination.rename(backup / f"previous-{index}")
        try:
            destination.symlink_to(target, target_is_directory=not relative)
        except OSError:
            prior = backup / f"previous-{index}"
            if prior.is_symlink() and not os.path.lexists(destination):
                prior.rename(destination)
            raise
        if destination.resolve() != target.resolve():
            raise ValueError("Installed link readback mismatch")
        print(f"installed {destination} -> {target}")
    print(f"Content identity confirmed: {len(files)} files, source {commit}")
    print(f"Previous links/provenance retained at {backup}")
    print("No hooks or host configuration changed. Seat definitions apply to new Claude Code sessions.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"symphony install: {error}", file=sys.stderr)
        sys.exit(1)
