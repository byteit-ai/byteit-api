#!/usr/bin/env python3
"""Local release readiness checks for ByteIT SDK.

This script is intended to be run by pre-commit hooks.
It validates release metadata consistency and package build integrity
without requiring any sensitive credentials.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
INIT_FILE = ROOT / "byteit" / "__init__.py"
CHANGELOG = ROOT / "CHANGELOG.md"

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
RELEASE_TITLE_RE = re.compile(r"^chore\(release\): (\d+\.\d+\.\d+)$")


def _fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def _read_text(path: Path) -> str:
    if not path.exists():
        _fail(f"Missing required file: {path}")
    return path.read_text(encoding="utf-8")


def _extract_pyproject_version() -> str:
    content = _read_text(PYPROJECT)
    match = re.search(r'^version\s*=\s*"(\d+\.\d+\.\d+)"\s*$', content, re.MULTILINE)
    if not match:
        _fail("Could not extract version from pyproject.toml")
    return match.group(1)


def _extract_init_fallback_version() -> str:
    content = _read_text(INIT_FILE)
    match = re.search(
        r'^\s*__version__\s*=\s*"(\d+\.\d+\.\d+)"\s*#\s*fallback',
        content,
        re.MULTILINE,
    )
    if not match:
        _fail("Could not extract fallback __version__ from byteit/__init__.py")
    return match.group(1)


def _check_changelog_entry(version: str) -> None:
    content = _read_text(CHANGELOG)
    pattern = rf"^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}$"
    if not re.search(pattern, content, re.MULTILINE):
        _fail(
            "CHANGELOG.md is missing a dated entry for "
            f"{version} (expected: ## [{version}] - YYYY-MM-DD)"
        )


def _check_unreleased_section_present() -> None:
    content = _read_text(CHANGELOG)
    if not re.search(r"^## \[Unreleased\]\s*$", content, re.MULTILINE):
        _fail("CHANGELOG.md should include a '## [Unreleased]' section")


def _run(command: list[str], label: str) -> None:
    completed = subprocess.run(command, cwd=ROOT, check=False, text=True)
    if completed.returncode != 0:
        _fail(f"{label} failed with exit code {completed.returncode}")


def _check_build_integrity() -> None:
    """Build source and wheel distributions, then validate metadata."""
    dist_dir = ROOT / "dist"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)

    _run(
        [
            sys.executable,
            "-m",
            "build",
            "--sdist",
            "--wheel",
            "--outdir",
            "dist",
        ],
        "python -m build",
    )

    dist_files = sorted(str(path) for path in dist_dir.glob("*"))
    if not dist_files:
        _fail("No files were produced in dist/ by python -m build")

    _run([sys.executable, "-m", "twine", "check", *dist_files], "twine check")


def _print_release_summary(version: str) -> None:
    print("Release preflight checks passed")
    print(f"- version: {version}")
    print(f"- changelog: {CHANGELOG.name} contains [{version}] entry")
    print(f"- date checked: {date.today().isoformat()}")


def run_pre_commit() -> None:
    """Run release validation checks used by the pre-commit stage."""
    version = _extract_pyproject_version()
    if not SEMVER_RE.match(version):
        _fail(f"Invalid semver in pyproject.toml: {version}")

    init_version = _extract_init_fallback_version()
    if init_version != version:
        _fail(
            "Version mismatch: byteit/__init__.py fallback "
            f"({init_version}) != pyproject.toml ({version})"
        )

    _check_unreleased_section_present()
    _check_changelog_entry(version)
    _check_build_integrity()
    _print_release_summary(version)


def _get_release_version_from_staged_files() -> str | None:
    cmd = ["git", "diff", "--cached", "--name-only"]
    completed = subprocess.run(
        cmd,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None

    staged = {line.strip() for line in completed.stdout.splitlines() if line.strip()}
    release_files = {"pyproject.toml", "byteit/__init__.py", "CHANGELOG.md"}
    if staged.isdisjoint(release_files):
        return None

    return _extract_pyproject_version()


def run_commit_msg(message_file: Path) -> None:
    """Validate release commit title format for staged release changes."""
    version = _get_release_version_from_staged_files()
    if version is None:
        print("No release files staged; skipping release commit-title check")
        return

    message = _read_text(message_file).splitlines()[0].strip()
    match = RELEASE_TITLE_RE.match(message)
    if not match:
        _fail(f"Release commit title must be exactly: chore(release): {version}")

    msg_version = match.group(1)
    if msg_version != version:
        _fail(
            "Commit title version "
            f"({msg_version}) does not match pyproject.toml ({version})"
        )

    print(f"Release commit title validated: {message}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local release readiness checks")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--pre-commit",
        action="store_true",
        help="Run release preflight checks",
    )
    mode.add_argument(
        "--commit-msg",
        action="store_true",
        help="Validate release commit message",
    )
    parser.add_argument(
        "message_file",
        nargs="?",
        help="Path to commit message file (provided by commit-msg hook)",
    )
    return parser.parse_args()


def main() -> None:
    """Dispatch to the requested pre-commit integration mode."""
    args = _parse_args()

    if args.pre_commit:
        run_pre_commit()
        return

    if args.commit_msg:
        if not args.message_file:
            _fail("commit-msg mode requires the commit message file path")
        run_commit_msg(Path(args.message_file))
        return


if __name__ == "__main__":
    main()
