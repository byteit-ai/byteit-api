#!/usr/bin/env python3
"""Release validation checks shared by pre-commit hooks and CI workflows."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
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


def _run(command: list[str], label: str) -> None:
    completed = subprocess.run(command, cwd=ROOT, check=False, text=True)
    if completed.returncode != 0:
        _fail(f"{label} failed with exit code {completed.returncode}")


def _get_head_commit_message() -> str | None:
    result = subprocess.run(
        ["git", "log", "-1", "--pretty=%s"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _get_latest_tag() -> str | None:
    result = subprocess.run(
        ["git", "tag", "-l", "v*", "--sort=-v:refname"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    tags = [t.strip() for t in result.stdout.splitlines() if t.strip()]
    return tags[0] if tags else None


def _extract_pyproject_version() -> str:
    content = _read_text(PYPROJECT)
    match = re.search(r'^version\s*=\s*"(\d+\.\d+\.\d+)"\s*$', content, re.MULTILINE)
    if not match:
        _fail("Could not extract version from pyproject.toml")
    return match.group(1)


def _extract_init_fallback_version() -> str:
    content = _read_text(INIT_FILE)
    match = re.search(
        r'__version__\s*=\s*"(\d+\.\d+\.\d+)"',
        content,
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


def _check_unreleased_empty() -> None:
    content = _read_text(CHANGELOG)
    lines = content.splitlines()
    in_unreleased = False
    for line in lines:
        stripped = line.strip()
        if stripped == "## [Unreleased]":
            in_unreleased = True
            continue
        if in_unreleased:
            if stripped.startswith("## ["):
                break
            if stripped and not stripped.startswith("#"):
                _fail(
                    "[Unreleased] section still has content. "
                    "Move all entries to the new release section before cutting a release."
                )


def _check_build_integrity() -> None:
    dist_dir = ROOT / "dist"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)

    _run(
        [sys.executable, "-m", "build", "--sdist", "--wheel", "--outdir", "dist"],
        "python -m build",
    )

    dist_files = sorted(str(p) for p in dist_dir.glob("*"))
    if not dist_files:
        _fail("No files were produced in dist/ by python -m build")

    _run([sys.executable, "-m", "twine", "check", *dist_files], "twine check")


def _check_ruff() -> None:
    _run([sys.executable, "-m", "ruff", "check", "."], "ruff check")
    _run([sys.executable, "-m", "ruff", "format", "--check", "."], "ruff format --check")


def _validate_commit_message(version: str, commit_msg: str | None) -> None:
    if commit_msg is None:
        _fail("Could not read HEAD commit message")
    match = RELEASE_TITLE_RE.match(commit_msg)
    if not match:
        _fail(f"Commit title must be exactly: chore(release): {version}")
    msg_version = match.group(1)
    if msg_version != version:
        _fail(
            f"Commit title version ({msg_version}) does not match pyproject.toml ({version})"
        )
    print(f"  ✓ commit title: {commit_msg}")


def _validate_semver_bump(version: str) -> None:
    latest_tag = _get_latest_tag()
    if latest_tag is None:
        print("  ✓ no previous release tag found; skipping bump validation")
        return

    prev_version = latest_tag.lstrip("v")
    if not SEMVER_RE.match(prev_version):
        print(
            f"  ⚠ previous tag {latest_tag} is not valid semver; skipping bump validation"
        )
        return

    prev_x, prev_y, prev_z = map(int, prev_version.split("."))
    curr_x, curr_y, curr_z = map(int, version.split("."))

    valid = (
        (curr_x == prev_x + 1 and curr_y == 0 and curr_z == 0)
        or (curr_x == prev_x and curr_y == prev_y + 1 and curr_z == 0)
        or (curr_x == prev_x and curr_y == prev_y and curr_z == curr_z + 1)
    )
    if not valid:
        _fail(
            f"Invalid semver bump: {prev_version} -> {version}. "
            "Expected exactly one valid bump: major (+1.0.0), minor (+0.1.0), or patch (+0.0.1)."
        )
    print(
        f"  ✓ valid {_bump_type(prev_x, prev_y, prev_z, curr_x, curr_y, curr_z)} bump from {prev_version}"
    )


def _bump_type(px, py, pz, cx, cy, cz) -> str:
    if cx == px + 1:
        return "major"
    if cy == py + 1:
        return "minor"
    return "patch"


def _check_tag_not_exists(version: str) -> None:
    tag = f"v{version}"
    result = subprocess.run(
        ["git", "rev-parse", f"refs/tags/{tag}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if result.returncode == 0:
        _fail(f"Tag {tag} already exists — this version was already released")


def _check_version_consistency(version: str) -> None:
    init_version = _extract_init_fallback_version()
    if init_version != version:
        _fail(
            "Version mismatch: byteit/__init__.py fallback "
            f"({init_version}) != pyproject.toml ({version})"
        )
    print(f"  ✓ versions consistent: {version}")


def run_pre_commit(version: str) -> None:
    _check_version_consistency(version)
    _check_unreleased_empty()
    _check_changelog_entry(version)
    _check_ruff()
    _check_build_integrity()


def run_ci(version: str, commit_msg: str | None) -> None:
    _check_version_consistency(version)
    _check_unreleased_empty()
    _check_changelog_entry(version)
    _check_ruff()
    _check_build_integrity()
    _validate_commit_message(version, commit_msg)
    _validate_semver_bump(version)
    _check_tag_not_exists(version)


def run_commit_msg(message_file: Path) -> None:
    cmd = ["git", "diff", "--cached", "--name-only"]
    result = subprocess.run(cmd, cwd=ROOT, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        return

    staged = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    release_files = {"pyproject.toml", "byteit/__init__.py", "CHANGELOG.md"}
    if staged.isdisjoint(release_files):
        print("No release files staged; skipping release commit-title check")
        return

    version = _extract_pyproject_version()
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
    parser = argparse.ArgumentParser(description="Release validation checks")
    parser.add_argument("--ci", action="store_true", help="Run full CI validation")
    parser.add_argument(
        "--pre-commit", action="store_true", help="Run pre-commit validation"
    )
    parser.add_argument(
        "--commit-msg",
        action="store_true",
        help="Validate release commit message (commit-msg hook)",
    )
    parser.add_argument(
        "message_file",
        nargs="?",
        help="Path to commit message file (provided by commit-msg hook)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if args.pre_commit:
        version = _extract_pyproject_version()
        if not SEMVER_RE.match(version):
            _fail(f"Invalid semver in pyproject.toml: {version}")
        run_pre_commit(version)
        print("Release preflight checks passed")
        return

    if args.ci:
        version = _extract_pyproject_version()
        if not SEMVER_RE.match(version):
            _fail(f"Invalid semver in pyproject.toml: {version}")
        commit_msg = _get_head_commit_message()
        run_ci(version, commit_msg)
        print("Release CI checks passed")
        return

    if args.commit_msg:
        if not args.message_file:
            _fail("commit-msg mode requires the commit message file path")
        run_commit_msg(Path(args.message_file))
        return

    _fail("Specify one of: --pre-commit, --ci, or --commit-msg")


if __name__ == "__main__":
    main()
