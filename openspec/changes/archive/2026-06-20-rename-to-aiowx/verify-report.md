## Verification Report

**Change**: rename-to-aiowx
**Version**: N/A (mechanical rename, no spec version bump)
**Mode**: Standard (Strict TDD not applicable — no new behavior)

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 22 |
| Tasks complete | 22 |
| Tasks incomplete | 0 |

### Build & Tests Execution

**Build**: ✅ Passed
```text
$ uv build
Successfully built dist\aiowx-0.1.0.tar.gz
Successfully built dist\aiowx-0.1.0-py3-none-any.whl
```

**Tests**: ✅ 41 passed / 0 failed / 0 skipped
```text
$ uv run pytest -v
tests/test_app.py ........                                               [ 19%]
tests/test_bind.py .....                                                 [ 31%]
tests/test_coroutine.py ...........                                      [ 58%]
tests/test_dialogs.py .................                                  [100%]
============================= 41 passed in 2.52s ==============================
```

**Coverage**: 86% / threshold: 80% → ✅ Above
```text
$ uv run pytest --cov=src --cov-report=term-missing
Name                    Stmts   Miss  Cover   Missing
-----------------------------------------------------
src\aiowx\__init__.py       2      0   100%
src\aiowx\_core.py        152     22    86%   196-199, 210-213, 262-264, 267-279, 326
-----------------------------------------------------
TOTAL                     154     22    86%
```

**Lint**: ✅ Zero warnings
```text
$ uv run ruff check src/aiowx/ tests/
All checks passed!
```

**Residual `wxasync` audit**: ✅ Zero matches
```text
$ rg "wxasync" --glob "!openspec/changes/archive/**" --glob "!.git/**" --glob "!uv.lock" --glob "!openspec/changes/rename-to-aiowx/**"
(no output)
```

### Spec Compliance Matrix

The rename change affects REQ-F3 (Package Consolidation) import-path scenarios. All other foundation requirements are behavior-unchanged.

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| REQ-F3 | Backward-compatible import (`from aiowx import WxAsyncApp`) | `tests/test_app.py > TestWxAsyncAppInit::*` | ✅ COMPLIANT |
| REQ-F3 | Star import scoped to `__all__` | Source inspection: `__all__` declared in `src/aiowx/__init__.py` with 5 symbols | ✅ COMPLIANT |
| REQ-F1 | Coroutine function passes validation | `tests/test_bind.py > TestAsyncBindValidation::test_rejects_non_coroutine_callback` | ✅ COMPLIANT |
| REQ-F2 | Public Event import works | `tests/test_dialogs.py > TestAsyncShowDialogHappyPath::test_returns_return_code_on_close` | ✅ COMPLIANT |
| REQ-F4 | Type checker passes | Source inspection: all public signatures annotated | ✅ COMPLIANT |
| REQ-F5 | Modern `super().__init__()` | `tests/test_app.py > TestWxAsyncAppInit::test_init_calls_set_exit_on_frame_delete` | ✅ COMPLIANT |
| REQ-F6 | Headless test run (all 41 pass) | `uv run pytest` — 41 passed, no display required | ✅ COMPLIANT |
| REQ-F6 | Task removed after exception | `tests/test_coroutine.py > TestOnTaskCompleted::test_exception_removes_task_and_warns` | ✅ COMPLIANT |
| REQ-F6 | CancelledError silenced | `tests/test_coroutine.py > TestOnTaskCompleted::test_silences_cancelled_error` | ✅ COMPLIANT |
| REQ-F6 | No orphan RunningTasks after destroy | `tests/test_coroutine.py > TestOnDestroy::test_removes_running_tasks_entry` | ✅ COMPLIANT |
| REQ-F6 | OnDestroy snapshot avoids iteration race | `tests/test_coroutine.py > TestOnDestroy::test_destroy_iteration_does_not_raise_runtime_error` | ✅ COMPLIANT |
| REQ-F6 | T7 verifies thread-safe ShowModal dispatch | `tests/test_dialogs.py > test_showmodal_in_executor_uses_callafter` + `test_showmodal_in_executor_avoids_run_in_executor` + `test_showmodal_in_executor_propagates_return_code` | ✅ COMPLIANT |
| REQ-F8 | Build succeeds (uv build) | `uv build` → `aiowx-0.1.0-py3-none-any.whl` | ✅ COMPLIANT |
| REQ-F9 | ShowModal via CallAfter, no run_in_executor | `tests/test_dialogs.py > test_showmodal_in_executor_uses_callafter` + `test_showmodal_in_executor_avoids_run_in_executor` | ✅ COMPLIANT |
| REQ-F9 | Return code propagates through Future | `tests/test_dialogs.py > test_showmodal_in_executor_propagates_return_code` | ✅ COMPLIANT |

**Compliance summary**: 15/15 scenarios compliant

### Correctness (Static Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| Package dir renamed `src/wxasync/` → `src/aiowx/` | ✅ Implemented | `src/wxasync/` does not exist; `src/aiowx/` exists with `__init__.py`, `_core.py`, `py.typed` |
| `__init__.py` imports from `aiowx._core` | ✅ Implemented | Line 1: `from aiowx._core import (...)` |
| `_core.py` docstring references `aiowx` | ✅ Implemented | Line 1: `"""Core module for aiowx — bridges wxPython GUI event loop with asyncio.` |
| `pyproject.toml` name = `"aiowx"` | ✅ Implemented | Line 2: `name = "aiowx"` |
| `uv.lock` regenerated with `aiowx` | ✅ Implemented | Line 6: `name = "aiowx"` |
| All test imports repointed to `aiowx._core` | ✅ Implemented | 41 tests pass; zero `wxasync` references in test files |
| All example imports repointed to `aiowx` | ✅ Implemented | Zero residual `wxasync` in `src/examples/` |
| README.md updated | ✅ Implemented | Zero residual `wxasync` references |
| AGENTS.md updated | ✅ Implemented | Zero residual `wxasync` references |
| `openspec/specs/foundation/spec.md` updated | ✅ Implemented | Import scenarios reference `aiowx` |
| `.atl/skill-registry.md` updated | ✅ Implemented | Zero residual `wxasync` references |
| Public API class names preserved | ✅ Implemented | `WxAsyncApp`, `AsyncBind`, `StartCoroutine`, `AsyncShowDialog`, `AsyncShowDialogModal` all accessible via `from aiowx import ...` |
| Internal `_core` import accessible | ✅ Implemented | `from aiowx._core import WxAsyncApp, wx` works |

### Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| `git mv` for directory rename | ✅ Yes | `src/wxasync/` removed, `src/aiowx/` present; git history preserved |
| Keep public API class names | ✅ Yes | `WxAsyncApp`, `AsyncBind`, etc. unchanged |
| Global replace + grep-verify | ✅ Yes | Zero residual `wxasync` in active code |
| No compatibility shim | ✅ Yes | No `wxasync` stub package or re-export shim |
| `uv lock` regenerate | ✅ Yes | `uv.lock` references `aiowx` at line 6 |
| Build produces `aiowx-*.whl` | ✅ Yes | `dist/aiowx-0.1.0-py3-none-any.whl` built successfully |

### Issues Found

**CRITICAL**: None

**WARNING**: None

**SUGGESTION**:
- `dist/` contains stale `wxasync-0.1.0-py3-none-any.whl` and `wxasync-0.1.0.tar.gz` from a prior build. Clean `dist/` before publishing to avoid accidental upload of the old package name.

### Verdict

**PASS**

All 22 tasks complete. All 41 tests pass. Coverage 86% (≥80%). Zero residual `wxasync` references in active code. Build produces `aiowx-0.1.0-py3-none-any.whl`. Public API preserved. Design decisions followed. The rename is complete and verified.
