# Tasks: refactor-core

## Review Workload Forecast

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

| Field | Value |
|-------|-------|
| Estimated changed lines | ~300 bruto (~+180 add, ~-120 del) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR (size-exception) |
| Delivery strategy | ask-on-risk |
| Chain strategy | size-exception |

## Phase 1: Foundation

- [x] 1.1 Create `src/aiowx/_app.py` with full `WxAsyncApp`: `__init__`, `MainLoop`, `ExitMainLoop`, `AsyncBind`, `StartCoroutine`, `OnTaskCompleted`, `OnDestroy`, `_TrackedTask` dataclass, module-level `AsyncBind()` and `StartCoroutine()` wrappers
- [x] 1.2 Apply modern Python: PEP 695 `type CoroutineFn = ...`, `Self` return type on `WxAsyncApp` methods, `@override` decorator, `_TrackedTask` dataclass replacing `setattr(task, "obj", obj)`

## Phase 2: Dialog Module

- [x] 2.1 Create `src/aiowx/_dialog.py` with `ShowModalAsync` (rename from `ShowModalInExecutor`), `AsyncShowDialog`, `AsyncShowDialogModal`
- [x] 2.2 Import `WxAsyncApp` from `_app` for `isinstance` checks only

## Phase 3: Wiring

- [x] 3.1 Update `src/aiowx/__init__.py`: import 5 public symbols from `_app` and `_dialog`
- [x] 3.2 Delete `src/aiowx/_core.py`
- [x] 3.3 Update `pyproject.toml` per-file ignores: replace `_core.py` block with `_app.py` (FBT001-003, A001-A002, PLR0913) and `_dialog.py` (FBT001-003)

## Phase 4: Testing

- [x] 4.1 Update `tests/conftest.py`: import `wx` directly, update `_core` → `_app` imports
- [x] 4.2 Update `tests/test_app.py`: import `WxAsyncApp` from `_app`, rename `ShowModalInExecutor` → `ShowModalAsync`
- [x] 4.3 Update `tests/test_coroutine.py`: import `StartCoroutine` from `_app`
- [x] 4.4 Update `tests/test_bind.py`: import `AsyncBind` from `_app`, import `wx` directly
- [x] 4.5 Update `tests/test_dialogs.py`: rename `ShowModalInExecutor` → `ShowModalAsync`, import `wx` directly
- [x] 4.6 Update `tests/test_pyproject_ruff.py`: update per-file ignore expectations

## Phase 5: Verification

- [x] 5.1 `ruff check` — fix any new violations
- [x] 5.2 `ruff format` — ensure clean formatting
- [x] 5.3 `ty` on `src/aiowx/` — zero type errors
- [x] 5.4 `pytest --cov=src` — ≥80% coverage, all tests passing
- [x] 5.5 `uv build` — produces valid wheel
- [x] 5.6 Grep for remaining `_core`, `ShowModalInExecutor`, `from aiowx._core import wx` — zero matches