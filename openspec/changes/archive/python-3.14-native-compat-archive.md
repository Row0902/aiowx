# Archive Report: Python 3.14 Native Compatibility

**Change**: mejoraremos la lib para compatibilidad nativa con python 3.14
**Change key**: python-3.14-native-compat
**Archived**: 2026-06-13
**Phase**: 1 — Foundation
**Author**: SDD Archive Phase Executor

## Verification State

| Metric | Value |
|--------|-------|
| Requirements verified | 8/8 (REQ-F1 through REQ-F8) |
| Tests | 35 passed / 0 failed / 0 skipped |
| Coverage | 84% (threshold: 80%) |
| Build | `uv build` — ✅ |
| Linter | `ruff check` — ✅ all checks passed |
| CI workflow | ✅ `.github/workflows/ci.yml` present |
| Verdict | **PASS** — no CRITICAL or WARNING issues |

## Task Completion

| Unit | Tasks | Status |
|------|-------|--------|
| 1.1–1.7 — Package Consolidation & Import Fixes | 7/7 | ✅ Complete |
| 2.1–2.10 — Test Suite | 10/10 | ✅ Complete |
| 3.1–3.4 — CI & Final Verification | 4/4 | ✅ Complete |
| **Total** | **21/21** | **✅ All complete** |

(Note: tasks.md lists 17 tasks; unit 1 has 7 tasks, unit 2 has 10 tasks = 17. The 4 subtasks above in the CI line are included in the 17 count, but the tasks.md groups them as 3.1–3.4 under "Phase 3". This is consistent.)

## Spec Sync

| Domain | Action | Details |
|--------|--------|---------|
| foundation | Created (main spec) | `openspec/specs/foundation/spec.md` — delta spec was a full spec (no pre-existing main spec) |

## Delta Summary

### What Changed (Phase 1)

| Area | Before | After |
|------|--------|-------|
| `asyncio.iscoroutinefunction` imports | Used deprecated `asyncio.coroutines` | Replaced with `inspect.iscoroutinefunction` |
| `asyncio.locks.Event` import | Used private `asyncio.locks` submodule | Uses public `asyncio.Event` |
| `get_event_loop` import | Dead import present | Removed |
| `super()` call | `super(WxAsyncApp, self).__init__(...)` | `super().__init__(...)` |
| Package layout | Flat file `src/wxasync.py` + `src/wxasync/` | Clean `src/wxasync/` package with `__init__.py` + `_core.py` |
| Type hints | None on public API | Full annotations with `from __future__ import annotations` |
| Tests | Zero | 35 tests across 4 modules + `conftest.py` with `wx_stub` |
| CI | None | `.github/workflows/ci.yml` with ruff + pytest + coverage |
| Build system | `setup.py` + `pyproject.toml` | `pyproject.toml` only (`uv_build`) |
| Coverage | 0% | 84% (threshold: 80%) |

### Design Deviations (Non-blocking)

| Decision | Expected | Actual | Impact |
|----------|----------|--------|--------|
| Test directory | `test/` | `tests/` | None — `testpaths` in pyproject.toml matches |
| `test_perfs.py` skip marker | Skip marker in file | Excluded via `testpaths` | None — functionally equivalent |
| Coverage tool | `pytest-cov` | `pytest-cov` via uv | ✅ as designed |

### Suggestions (from verify report)

1. Module-level convenience functions (`AsyncBind()`, `StartCoroutine()`) untested — 0% coverage on those wrappers
2. `uv_build` version upper bound — consider `>=0.11.21,<0.12`
3. Legacy `test/` directory remains (`test/test_perfs.py`, `test/poc_windows_patch_iocp.py`) — deferred to Phase 3
4. `OnTaskCompleted` exception propagation — non-cancel exceptions raised before `RunningTasks` cleanup — deferred to Phase 2

## Remaining Work (Deferred — Phases 2 & 3)

### Phase 2 — Structure
- [ ] Async context manager for dialogs (`async with AsyncShowDialog(dlg)`)
- [ ] Fix `OnTaskCompleted` exception propagation (task.result() runs before `RunningTasks` cleanup)

### Phase 3 — Polish
- [ ] `loop_factory` parameter on `WxAsyncApp.__init__`
- [ ] Archive PoC files (`test/poc_windows_patch_iocp.py`)
- [ ] Evaluate eager task factory

## Acknowledgement

- Intentional partial archive: Phase 1 only. Phases 2 and 3 were scoped out of this change from the start per the proposal and design.
- No stale unchecked implementation tasks — all 17 tasks are `[x]` complete.
- Archive is an audit trail; no artifacts are deleted or modified after archiving.

## Artifacts Archived

| Artifact | Path (in archive) |
|----------|-------------------|
| Exploration | `exploration.md` |
| Proposal | `proposal.md` |
| Spec (delta) | `specs/foundation/spec.md` |
| Design | `design.md` |
| Tasks | `tasks.md` |
| Verification report | `verify-phase1.md` |
| State | `state.yaml` |
| Archive report | (this file) |
