# Tasks: Fix ShowModal Thread-Safety

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 40-70 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | single PR |
| Delivery strategy | ask-always |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | RED tests for thread-safe dispatch | PR 1 | single PR; base = main |
| 2 | GREEN fix + REFACTOR polish | PR 1 | same PR; TDD cycle in one PR |

## Phase 1: RED — Failing Tests for Thread-Safe Dispatch

- [x] 1.1 Update `tests/test_dialogs.py` `TestAsyncShowDialogModalOSDialogs` class docstring to reference `wx.CallAfter` dispatch (no `run_in_executor`)
- [x] 1.2 Add test in `TestAsyncShowDialogModalOSDialogs`: patch `wx.CallAfter` to capture callback, invoke it manually, assert `dialog.ShowModal` called exactly once for `ShowModalInExecutor`
- [x] 1.3 Add test: patch `asyncio.AbstractEventLoop.run_in_executor`, assert NOT called during `ShowModalInExecutor`
- [x] 1.4 Add test: mock `dialog.ShowModal` returns known int (e.g. `wx.ID_OK`); assert awaited result equals it
- [x] 1.5 Add test: mock `dialog.ShowModal` raises `ValueError`; assert `ShowModalInExecutor` re-raises same exception via Future
- [x] 1.6 Run `uv run pytest` — confirm new tests FAIL (red), existing tests still pass

## Phase 2: GREEN — Implement CallAfter + Future Fix

- [x] 2.1 Rewrite `ShowModalInExecutor` in `src/wxasync/_core.py:216-222`: `loop.create_future()`, `wx.CallAfter(callback)` where callback runs `result = dialog.ShowModal()` then `future.set_result(result)`, `return await future`
- [x] 2.2 Update docstring: document main-thread dispatch via `wx.CallAfter`, expected event-loop blocking during modal, exception propagation through Future
- [x] 2.3 Run `uv run pytest` — confirm ALL tests PASS (green)

## Phase 3: REFACTOR — Lint, Coverage, API Verification

- [x] 3.1 Run `ruff check` — zero warnings; `ruff format` — apply definitive style
- [x] 3.2 Run `uv run pytest --cov=src` — verify `>=80%` line coverage maintained on `src/`
- [x] 3.3 Verify public signature unchanged: `async def ShowModalInExecutor(dialog: wx.Dialog) -> int`
- [x] 3.4 Verify `src/wxasync/__init__.py` `__all__` unchanged — no new public exports leaked
