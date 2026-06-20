# Tasks: Rename wxasync → aiowx

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~43 across 22 files |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR (atomic) |
| Delivery strategy | ask-always |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Full atomic rename: dir + imports + docs + lockfile + verify | PR 1 (single) | base = main; splitting would create broken intermediate import states |

> Rename `wxasync` → `aiowx` ONLY for the package name. Preserve `WxAsyncApp`, `AsyncBind`, `StartCoroutine`, and all other API/class names. Do NOT touch `openspec/changes/archive/**` (historical audit trail). TDD N/A — no new behavior; existing suite is the import-resolution gate.

## Phase 1: Foundation — Package dir + config

- [x] 1.1 Verify `aiowx` is available on PyPI (pypi.org/project/aiowx); halt and pick alternative if taken
- [x] 1.2 `git mv src/wxasync/ src/aiowx/` (moves `__init__.py`, `_core.py`, `py.typed`)
- [x] 1.3 `src/aiowx/__init__.py:1`: `from wxasync._core import` → `from aiowx._core import`
- [x] 1.4 `src/aiowx/_core.py:1` docstring: `Core module for wxasync` → `Core module for aiowx`
- [x] 1.5 `pyproject.toml:2`: `name = "wxasync"` → `name = "aiowx"`; update description if it names the package
- [x] 1.6 Run `uv lock` to regenerate `uv.lock` (package metadata entry ~line 237)

## Phase 2: Core — Repoint imports in consumers

- [x] 2.1 `tests/conftest.py` lines 5,184,209,212,222: `wxasync._core` → `aiowx._core` (incl. comments + `import wxasync._core as core`)
- [x] 2.2 `tests/test_app.py` lines 23,30,55,96: `from wxasync._core` → `from aiowx._core`
- [x] 2.3 `tests/test_bind.py:94` and `tests/test_coroutine.py:93`: `from wxasync._core` → `from aiowx._core`
- [x] 2.4 `tests/test_dialogs.py` lines 14,61,225: `wxasync._core` → `aiowx._core` (incl. `patch("wxasync._core.AsyncBind", ...)` strings)
- [x] 2.5 `src/examples/{simple,slider_demo,server,dialog,more_dialogs}.py`: `from wxasync import` → `from aiowx import`
- [x] 2.6 Legacy `test/test_perfs.py:1` and `test/poc_windows_patch_iocp.py:9`: `from wxasync import` → `from aiowx import`

## Phase 3: Docs / Specs / Registry

- [x] 3.1 `README.md` lines 1,4,9,13,54,108,109: title, description, `pip install`, code example, perf table — package refs only; keep `WxAsyncApp`
- [x] 3.2 `AGENTS.md` lines 1,42,60: title, naming example, import-path example — `wxasync` → `aiowx`
- [x] 3.3 `notes.txt:10`: `pip install wxasync` → `pip install aiowx`
- [x] 3.4 `openspec/specs/foundation/spec.md` lines 13,51,56: package/path refs `wxasync`→`aiowx`; preserve `WxAsyncApp` class name
- [x] 3.5 `.atl/skill-registry.md:1`: `# Skill Registry — wxasync` → `aiowx`

## Phase 4: Verification

- [x] 4.1 `rg "wxasync"` excluding `openspec/changes/archive/**`, `.git/**`, `uv.lock` → expect ZERO matches
- [x] 4.2 `uv run pytest --cov=src` → all pass, coverage >=80%
- [x] 4.3 `ruff check` (zero warnings) then `ruff format`
- [x] 4.4 `uv build` → produces valid `aiowx-*.whl`

## Phase 5: Manual follow-up (out-of-band, non-blocking)

- [x] 5.1 Rename GitHub repo `wxasync` → `aiowx`; update local `git remote` URL; document in README
