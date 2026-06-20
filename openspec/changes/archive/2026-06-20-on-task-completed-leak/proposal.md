# Proposal: OnTaskCompleted Memory Leak (Issue #3)

## Intent

Fix two memory leaks in `WxAsyncApp` where (A) exceptions in `OnTaskCompleted` skip task removal from `RunningTasks`, and (B) `OnDestroy` never cleans up empty `RunningTasks[obj]` entries, causing unbounded dict growth over a session's lifetime. Blocks production readiness.

## Scope

### In Scope
- Leak A: `try/finally` guard so cleanup runs even when `task.result()` raises
- Leak B: `del self.RunningTasks[obj]` in `OnDestroy` + empty-set cleanup in `OnTaskCompleted`
- `warnings.warn` for non-`CancelledError` exceptions (diagnostic improvement)
- Regression tests proving both leaks are fixed

### Out of Scope
- `TaskGroup` refactor (architectural, not justified for this fix)
- Global exception handler customization
- Public API signature changes

## Capabilities

### New Capabilities
None

### Modified Capabilities
- `foundation`: REQ-F6 T8 scenario updated — task removed from `RunningTasks` even on exception. Non-Goals section updated — exception logging no longer deferred.

## Approach

**Leak A**: Wrap `OnTaskCompleted` in `try/finally`; `remove()` in `finally` always runs. Use `dict.get()` + `set.discard()` for defensive access.

**Leak B**: Add `del self.RunningTasks[obj]` in `OnDestroy` after cancelling tasks. Also prune empty sets in `OnTaskCompleted`'s `finally` block.

**Defensive**: Snapshot `RunningTasks[obj]` with `list()` in `OnDestroy` before iterating, to avoid races when `OnTaskCompleted` fires during cancellation.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/wxasync/_core.py:148-158` | Modified | `OnTaskCompleted` — `try/finally` guard |
| `src/wxasync/_core.py:160-167` | Modified | `OnDestroy` — add dict cleanup |
| `tests/test_coroutine.py` | Modified | Regression tests for both leaks |
| `openspec/specs/foundation/spec.md` | Modified | Update Non-Goals + T8 scenario |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `OnDestroy` iterates while callback removes tasks | Low | `list()` snapshot before iteration |
| `task.obj` attribute missing | Low | Defensive `getattr` + `dict.get` |

## Rollback Plan

Revert `_core.py` and test changes. Restore "known limitation" comments. Single-commit change — clean revert.

## Dependencies

None.

## Success Criteria

- [ ] Task removed from `RunningTasks` after exception (regression test, Leak A)
- [ ] No orphan `RunningTasks` entries after window destruction (regression test, Leak B)
- [ ] `uv run pytest` passes
- [ ] `uv run pytest --cov=src` ≥80%
