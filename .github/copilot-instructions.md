# ByteIT — Copilot Instructions

<!--
  MAINTENANCE:
  - Section 1: never change per-task — team decision only.
  - Section 2: update when stack/structure changes.
  - Section 3: append freely (newest first). When > 20 entries, prompt:
    "Compact the Lessons log — merge duplicates, drop resolved items, keep
    only high-signal rules. Max 15 entries." Target: file under 150 lines.
-->

---

## 1 · Global invariants

**Stack** — suggest nothing outside this without being asked:
- Python → [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html), enforced by `ruff`
- TypeScript → [Google TS Style Guide](https://google.github.io/styleguide/tsguide.html), enforced by ESLint
- Terraform → HashiCorp conventions

**Code principles** — every change must move toward simplicity, clarity, maintainability:
- Simplest solution that fully satisfies the requirement. No over-engineering.
- Explicit over implicit. Readable over clever.
- Flat over nested — extract conditions and loops into well-named functions.
- Composition over inheritance.
- Design for the next developer, not just the current task.

**Enforce beyond linters** — ruff/ESLint own style; focus on what they miss:
- Flag complex conditionals that could be simplified or extracted.
- Flag non-obvious intent — add a short *why* comment, not a *what* comment.
- Flag missing error handling around I/O, network calls, external deps — no silent swallows.
- Flag hardcoded secrets, unsanitized input in queries/commands, sensitive data in logs.
- Flag duplicated logic that already exists elsewhere and should be reused.

**Never flag:**
- Style already enforced by ruff or ESLint.
- Idiomatic language patterns that are correct but unfamiliar.
- Micro-optimizations with no impact on scalability or readability.

**Do not touch without explicit task scope:**
- Auth, token handling, session management.
- DB migrations or schema files.
- CI/CD workflow files.
- Any file not referenced in the current task.

**Tone:**
- Direct. Reference exact file + line. One sentence per issue.
- No praise, no filler, no generic suggestions.
- If code is correct and clear, say nothing.

---

## 2 · Repo context

**What this repo does:** Python SDK (`byteit` PyPI package) — HTTP client library for the ByteIT AI document-parsing cloud API; sends files, returns structured text (MD/TXT/JSON/HTML).

**Stack specifics:** Python ≥ 3.8, linted at `py312`; `requests ≥ 2.28`, `tqdm ≥ 4.65`; no web framework, no DB; build via `setuptools + wheel`, publish via `twine`.

**Commands:**
```
build: python -m build
test:  pytest
lint:  ruff check . / ruff format .
```

**Key paths:**
- `byteit/__init__.py` — public API surface
- `byteit/ByteITClient.py` — main client class
- `byteit/models/` — domain models (one file per class, PascalCase filename)
- `byteit/connectors/` — local + S3 I/O adapters
- `byteit/validations.py`, `byteit/exceptions.py`
- `tests/` — unit + integration tests

**Non-obvious conventions:** Integration tests use `@pytest.mark.integration` and require live credentials — excluded from normal runs. `line-length = 90` (not 88). `__version__` in `__init__.py` has a hard-coded fallback: keep in sync with `pyproject.toml` on version bumps.

---

## 3 · Lessons log
<!--
  Format: `- [YYYY-MM] ❌ what happened → ✅ what to do instead`
  Append at top. Compact when > 20 entries.
-->