# Tasks: OnTaskCompleted Memory Leak (Issue #3)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 60-100 (code + tests) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-always |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Fix Leak A + Leak B with TDD regression tests | PR 1 | base: `main`; single PR, code + tests + spec delta |

## Phase 1: RED — Failing Regression Tests

- [x] 1.1 In `tests/test_coroutine.py` add Leak A test: coroutine raising `ValueError` via `StartCoroutine`; assert task removed from `RunningTasks[obj]` and warning emitted (fails today)
- [x] 1.2 Add Leak B test: `OnDestroy` on window with tracked tasks; assert `obj not in RunningTasks` and `obj not in BoundObjects` (fails today: orphan empty set remains)
- [x] 1.3 Add CancelledError contract test: cancelled tracked task; assert silenced, no warning, task removed (passes today; pins behavior)
- [x] 1.4 Add OnDestroy snapshot race test: `OnTaskCompleted` fires during `OnDestroy` iteration; assert no `RuntimeError` (fails today: live iteration mutates)
- [x] 1.5 Run `uv run pytest` and confirm new tests fail for the expected leak reasons only

## Phase 2: GREEN — Implement Fixes

- [x] 2.1 In `src/wxasync/_core.py` rewrite `OnTaskCompleted` with `try`/`except`/`finally`: `task.result()` in try; `warnings.warn` on non-`CancelledError` in except; `self.RunningTasks.get(obj, set()).discard(task)` + `del` empty set in finally
- [x] 2.2 In `src/wxasync/_core.py` update `OnDestroy`: snapshot `list(self.RunningTasks.get(obj, set()))` before iterating; after cancelling tasks, `del self.RunningTasks[obj]` and `del self.BoundObjects[obj]`
- [x] 2.3 Run `uv run pytest` and confirm all new + existing tests pass

## Phase 3: REFACTOR & Verify

- [x] 3.1 Run `ruff check src/wxasync/_core.py tests/test_coroutine.py` then `ruff format`; fix any findings
- [x] 3.2 Run `uv run pytest --cov=src` and confirm line coverage ≥80%
- [x] 3.3 Verify `OnTaskCompleted` / `OnDestroy` public signatures unchanged (no API break)
- [x] 3.4 Confirm `openspec/changes/on-task-completed-leak/specs/foundation/spec.md` delta still matches implemented T8/T9 behavior (main-spec merge is deferred to sdd-archive)
