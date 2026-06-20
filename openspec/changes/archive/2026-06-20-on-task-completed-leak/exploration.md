# Exploration: OnTaskCompleted Memory Leak (Issue #3)

## Current State

`WxAsyncApp` tracks running coroutine tasks per-window via `self.RunningTasks` (a `defaultdict[wx.Window, set[asyncio.Task]]`). When a task completes, `OnTaskCompleted` fires via `add_done_callback`, which calls `task.result()` to surface exceptions and then removes the task from the set.

The current implementation has two related leaks:

### Leak A: Exception escape prevents cleanup

```python
def OnTaskCompleted(self, task: asyncio.Task[Any]) -> None:
    try:
        _res = task.result()          # ← raises on non-Cancel exception
    except CancelledError:
        pass
    self.RunningTasks[task.obj].remove(task)  # ← never reached if ValueError etc.
```

If the coroutine raises any exception other than `CancelledError`, `task.result()` re-raises it and the method exits **before** `remove()`. The task remains in `RunningTasks[obj]` forever — a zombie entry. This was documented as a known limitation in the Phase 1 test suite (`test_coroutine.py:166-168`) and deferred to Phase 2 in the archive report.

### Leak B: Empty `RunningTasks` sets accumulate

`OnDestroy` explicitly cleans up `BoundObjects[obj]` but **never** removes `RunningTasks[obj]`. Even in the normal flow (all tasks complete or are cancelled), the empty set persists in the `defaultdict` for the lifetime of the `WxAsyncApp` instance. Over time, every window that is created and destroyed leaves a `{window: set()}` entry that never gets collected.

### Current data flow

```
StartCoroutine(coro, obj)
  → task = asyncio.create_task(coro)
  → task.obj = obj                                   # monkey-patched reference
  → task.add_done_callback(self.OnTaskCompleted)     # registers cleanup callback
  → self.RunningTasks[obj].add(task)                 # tracks the task

OnTaskCompleted(task)
  → task.result()                                     # may raise
  → RunningTasks[task.obj].remove(task)               # cleanup (unreachable if raise)

OnDestroy(event, obj)
  → for task in RunningTasks[obj]: task.cancel()      # cancels running tasks
  → del BoundObjects[obj]                             # cleans up bindings
  → RunningTasks[obj] left as empty set               # ← LEAK B
```

## Affected Areas

- `src/wxasync/_core.py` — `OnTaskCompleted` method (line 148–158), `OnDestroy` method (line 160–167), and `RunningTasks` lifecycle management
- `tests/test_coroutine.py` — `TestOnTaskCompleted` class documents the current leak at lines 166–168; tests must be updated to assert new behavior
- `openspec/specs/foundation/spec.md` — The foundation spec's Non-Goals section explicitly defers "OnTaskCompleted exception logging" to Phase 2; this changes that
- `openspec/changes/archive/2026-06-13-python-3.14-native-compat/archive-report.md` — Phase 2 deferred items reference this fix

## Approaches

### 1. **try/finally guard + empty-set cleanup** — Minimal surgical fix

Wrap `OnTaskCompleted` body in `try/finally` to ensure cleanup always runs. Use `dict.get()` + `set.discard()` instead of direct subscript + `.remove()` for defensive access. Clean up the dict entry when its set becomes empty. Add `del self.RunningTasks[obj]` in `OnDestroy`.

```python
def OnTaskCompleted(self, task: asyncio.Task[Any]) -> None:
    try:
        _res = task.result()
    except CancelledError:
        pass
    finally:
        obj = getattr(task, 'obj', None)
        if obj is not None:
            tasks = self.RunningTasks.get(obj)
            if tasks is not None:
                tasks.discard(task)
                if not tasks:
                    del self.RunningTasks[obj]
```

- **Pros**: Minimal diff (∼10 lines changed); preserves all existing behavior; fixes both leaks; defensive patterns prevent KeyError if `task.obj` is missing; cleanly handles all exception types
- **Cons**: Still re-raises non-Cancel exceptions through the done callback (asyncio catches them in its exception handler, so no crash, but users who inspect done callback errors will see them); does not add logging
- **Effort**: **Low**

### 2. **Exception-first + logging** — Cleanup before re-raise with diagnostic logging

Move the `remove()` call BEFORE `task.result()`, and add `warnings.warn` when non-cancel exceptions are caught. This ensures cleanup happens before any exception propagates.

```python
def OnTaskCompleted(self, task: asyncio.Task[Any]) -> None:
    # Clean up FIRST — before any exception can escape
    obj = getattr(task, 'obj', None)
    if obj is not None:
        tasks = self.RunningTasks.get(obj)
        if tasks is not None:
            tasks.discard(task)
            if not tasks:
                del self.RunningTasks[obj]
    # Then handle exceptions
    try:
        _res = task.result()
    except CancelledError:
        pass
    except Exception:
        warnings.warn(f"Unhandled exception in coroutine task: ...", ..., stacklevel=2)
```

- **Pros**: Cleanup is guaranteed by ordering (not by `finally`); adds logging for non-cancel exceptions (diagnostic improvement); allows users to see errors without crashing the callback
- **Cons**: Changes the exception propagation behavior (exception no longer surfaces through the done callback to asyncio's exception handler); ordering is fragile — if someone later adds code between cleanup and exception handling, the pattern breaks; more lines changed than Approach 1
- **Effort**: **Low**

### 3. **Structured concurrency with TaskGroup** — Architectural refactor

Replace manual `RunningTasks` tracking with `asyncio.TaskGroup` per window. Use the TaskGroup context manager to join all tasks on window destroy.

- **Pros**: Eliminates manual task tracking entirely; idiomatic Python 3.11+; TaskGroup handles cancellation and cleanup natively; no empty-set accumulation
- **Cons**: Requires window-level `TaskGroup` lifecycle management (creating TaskGroups on-demand, joining on destroy); changes the fire-and-forget semantics of `StartCoroutine`; larger diff; more complex than the problem warrants for a simple leak fix; TaskGroup exceptions might be harder to route to done-callback consumers
- **Effort**: **High**

## Recommendation

**Approach 1** — the `try/finally` guard with defensive access patterns.

Reasons:
1. **Minimal diff**: ∼10 lines changed in `_core.py`, small test adjustments. Easy to review.
2. **No semantic change**: The behavior is identical for consumers — `task.result()` still surfaces exceptions, `CancelledError` is silenced, the task is still awaitable.
3. **Fixes both leaks**: The `finally` block always runs (fixes Leak A), and empty-set cleanup prevents accumulation (fixes Leak B).
4. **Defensive**: Using `.get()` + `.discard()` means `OnTaskCompleted` won't crash even if `RunningTasks` state is inconsistent (e.g., if `OnDestroy` already cleaned up).
5. **Matches the deferred design**: The Phase 2 deferred item explicitly says "fix exception propagation (task.result() runs before RunningTasks cleanup)" — this is exactly what `try/finally` addresses.

## Risks

- **Concurrent modification during OnDestroy**: `OnDestroy` iterates `RunningTasks[obj]` and cancels tasks. `OnTaskCompleted` fires asynchronously (on next event loop iteration) and removes tasks from the same set. With the current CPython asyncio implementation, done callbacks are not called synchronously during `task.cancel()`, so iteration is safe. But this is an implementation detail. Using `list(RunningTasks[obj])` in `OnDestroy` to snapshot the iteration would eliminate the risk. Consider adding this as a secondary fix.
- **Existing test asserts current leak behavior**: `test_coroutine.py:166-168` explicitly notes the zombie task as a "known limitation." That test's NOTE comment must be updated after the fix.
- **Edge case — task.obj missing**: If a future version of CPython adds `obj` as an actual Task attribute or a third-party subclass overrides it, `getattr` silently returns `None`. This is acceptable — the task simply stays in `RunningTasks` rather than crashing.

## Ready for Proposal

**Yes.** The leaks are well-understood, the fix is minimal and well-bounded, and the affected areas are confined to two methods in a single file. Ready to proceed to proposal.
