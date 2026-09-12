#!/usr/bin/env python3
"""Install an exact committed, complete Symphony package without changing host config."""
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
        elif path.startswith(("score/", "scripts/", "examples/")) or path == "LICENSE":
            target = path
        else:
            continue
        if kind != "blob" or mode not in ("100644", "100755") or target in files:
            raise ValueError("Package must contain uniquely mapped regular tracked files")
        data = git("cat-file", "blob", blob)
        files[target] = (data, 0o755 if mode == "100755" else 0o644)
    if "SKILL.md" not in files or "score/OPERATING.md" not in files:
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex", action="store_true")
    parser.add_argument("--claude", action="store_true")
    args = parser.parse_args()
    os.umask(0o077)
    if git("status", "--porcelain=v1").strip():
        raise ValueError("Install only from a clean committed checkout")
    commit = git("rev-parse", "HEAD").decode().strip()
    data_root = owned_directory(Path.home() / ".symphony")
    packages = private_directory(data_root / "packages")
    package = packages / commit / "symphony"
    destinations = []
    both = not args.codex and not args.claude
    if both or args.codex:
        destinations.append(Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser().absolute() / "skills/symphony")
    if both or args.claude:
        destinations.append(Path.home() / ".claude/skills/symphony")
    original = REPO / "skills/symphony"
    old_links = {}
    # Inspect every destination before building or changing any installation.
    for destination in destinations:
        if not os.path.lexists(destination):
            old_links[destination] = None
            continue
        if not destination.is_symlink():
            raise ValueError(f"Refusing unexpected installation: {destination}")
        target = destination.resolve()
        managed = target.parent.parent == packages and target.name == "symphony" and (target / ".symphony-package.json").is_file()
        if target != original and not managed:
            raise ValueError(f"Refusing unrelated link: {destination}")
        old_links[destination] = os.readlink(destination)
    files = package_files(commit)
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
    for index, destination in enumerate(destinations):
        destination.parent.mkdir(parents=True, exist_ok=True)
        if old_links[destination] is not None:
            if not destination.is_symlink() or os.readlink(destination) != old_links[destination]:
                raise ValueError("Installation changed during update; stop without overwriting it")
            if destination.resolve() == package:
                print(f"unchanged {destination} -> {package}")
                continue
            destination.rename(backup / f"previous-{index}")
        try:
            destination.symlink_to(package, target_is_directory=True)
        except OSError:
            prior = backup / f"previous-{index}"
            if prior.is_symlink() and not os.path.lexists(destination):
                prior.rename(destination)
            raise
        if destination.resolve() != package:
            raise ValueError("Installed link readback mismatch")
        print(f"installed {destination} -> {package}")
    print(f"Content identity confirmed: {len(files)} files, source {commit}")
    print(f"Previous links/provenance retained at {backup}")
    print("Behavioral validation deferred. No hooks or host configuration changed.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"symphony install: {error}", file=sys.stderr)
        sys.exit(1)
