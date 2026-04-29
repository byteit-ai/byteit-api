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

### 1. Think Before Coding

*Don't assume. Don't hide confusion. Surface tradeoffs.*

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

*Minimum code that solves the problem. Nothing speculative.*

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

*Touch only what you must. Clean up only your own mess.*

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

*Define success criteria. Loop until verified.*

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

**Stack** — suggest nothing outside this without being asked:
- Python → [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html), enforced by `ruff`
- TypeScript → [Google TS Style Guide](https://google.github.io/styleguide/tsguide.html), enforced by ESLint
- Terraform → HashiCorp conventions

Linters own style. Flag what they miss:
- Complex conditionals that could be simplified or extracted.
- Non-obvious intent — add a short *why* comment, not a *what* comment.
- Missing error handling around I/O, network calls, external deps — no silent swallows.
- Hardcoded secrets, unsanitized input in queries/commands, sensitive data in logs.
- Duplicated logic that already exists elsewhere and should be reused.

**Never flag:** linter-owned style, idiomatic patterns, micro-optimizations.

**Code principles** — every change must move toward simplicity, clarity, maintainability:
- Explicit over implicit. Readable over clever.
- Flat over nested — extract conditions and loops into well-named functions.
- Composition over inheritance.
- Design for the next developer, not just the current task.

**Off-limits without explicit scope:** auth/token/session, DB migrations or schema files, CI/CD workflow files.

**Tone:** Direct. Exact file + line. One sentence per issue. No praise or filler. Silence if code is correct and clear.

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