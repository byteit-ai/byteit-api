---
name: sdk-release-readiness
description: Prepare and validate a ByteIT SDK release with synchronized versions, changelog, build checks, and release commit title.
---

# SDK Release Readiness Skill

Use this skill before opening a release PR or creating a release tag.

## Objective

Ensure the SDK release is consistent and publishable without using sensitive data.

## Required Checks

1. Version consistency:
- `pyproject.toml` `[project].version` is valid semver.
- `byteit/__init__.py` fallback `__version__` matches `pyproject.toml`.

2. Changelog quality:
- `CHANGELOG.md` contains `## [Unreleased]`.
- `CHANGELOG.md` contains a dated release section: `## [X.Y.Z] - YYYY-MM-DD`.

3. Build and package validation:
- Build artifacts: `python -m build --sdist --wheel --outdir dist`
- Metadata check: `python -m twine check dist/*`

4. Release commit title:
- Must be exactly: `chore(release): X.Y.Z`
- `X.Y.Z` must match `pyproject.toml` version.

## Local Automation

Run hooks:

```bash
pre-commit run --all-files
```

Release checks are implemented by:
- `scripts/release_preflight.py --pre-commit`
- `scripts/release_preflight.py --commit-msg <message-file>`

## Standard Commit Title

```text
chore(release): X.Y.Z
```

Example:

```text
chore(release): 1.0.1
```

## Notes

- Do not upload to PyPI from local checks.
- Do not include credentials, tokens, or private endpoints in commits.
