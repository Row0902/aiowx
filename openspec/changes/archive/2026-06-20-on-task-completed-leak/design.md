# Design: OnTaskCompleted Memory Leak (Issue #3)

## Technical Approach

Harden cleanup paths in `WxAsyncApp` so that failed or cancelled coroutines always unregister from `RunningTasks`, and destroying a window always drops the now-empty per-window task set. No public API changes. The work is confined to `src/wxasync/_core.py:148-167` and matching regression tests in `tests/test_coroutine.py`.

## Architecture Decisions

| Decision | Options | Tradeoff | Choice |
|----------|---------|----------|--------|
| Guarantee cleanup when `task.result()` raises | `try/finally` inside `OnTaskCompleted`; split cleanup helper | Helper adds indirection for a single callback; `try/finally` is local and obvious | `try/finally` in `OnTaskCompleted` |
| Defensive removal from `RunningTasks` | Direct `set.remove()`; `dict.get(obj, set())` + `set.discard()` | `remove()` raises `KeyError` if the set or task is missing; `discard()` is idempotent | `self.RunningTasks.get(obj, set()).discard(task)` |
| Delete empty per-window set | `del` in `OnTaskCompleted` finally; `del` in `OnDestroy` only | Deleting in `OnTaskCompleted` prevents Leak A accumulation; deleting in `OnDestroy` prevents Leak B | Both: prune empty set in `OnTaskCompleted`; `del` in `OnDestroy` |
| Iterate safely during cancellation | Iterate `self.RunningTasks[obj]` directly; snapshot with `list()` | Direct iteration can mutate underfoot if a done callback fires concurrently; `list()` copies task references | `tasks = list(self.RunningTasks.get(obj, set()))` |
| Non-`CancelledError` visibility | Re-raise silently; `warnings.warn` before cleanup | Re-raising silently preserves existing behavior but hides failures; warning keeps diagnostics without breaking flow | `warnings.warn` in `except Exception`, then continue cleanup |

## Data Flow

```
StartCoroutine(coroutine, obj)
    │
    ▼
task = asyncio.create_task(coroutine)
task.obj = obj
task.add_done_callback(OnTaskCompleted)
self.RunningTasks[obj].add(task)
    │
    ├── task completes normally ──► OnTaskCompleted(task)
    │                                 try: task.result()
    │                                 finally: discard task, del empty set
    │
    ├── task raises ─────────────► OnTaskCompleted(task)
    │                                 try: task.result() raises
    │                                 except: warnings.warn
    │                                 finally: discard task, del empty set
    │
    └── EVT_WINDOW_DESTROY ──────► OnDestroy(event, obj)
                                     snapshot = list(RunningTasks[obj])
                                     for task in snapshot: task.cancel()
                                     del BoundObjects[obj]
                                     del RunningTasks[obj]
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/wxasync/_core.py:148-167` | Modify | Harden `OnTaskCompleted` and `OnDestroy` cleanup paths |
| `tests/test_coroutine.py` | Modify | Replace "known limitation" test with Leak A/B regression tests |
| `openspec/specs/foundation/spec.md` | Modify | Update Non-Goals and T8 scenario per proposal |

## Interfaces / Contracts

No new public interfaces. The existing `WxAsyncApp.OnTaskCompleted(self, task: asyncio.Task[Any]) -> None` and `WxAsyncApp.OnDestroy(self, event: wx.WindowDestroyEvent, obj: wx.Window) -> None` contracts are tightened:

- `OnTaskCompleted` MUST remove `task` from `RunningTasks` even when `task.result()` raises.
- `OnTaskCompleted` MUST warn once for non-`CancelledError` exceptions, then continue cleanup.
- `OnDestroy` MUST remove the `RunningTasks[obj]` entry after cancelling tasks.
- `RunningTasks` continues to be `defaultdict[wx.Window, set[asyncio.Task[Any]]]`; empty sets may be pruned.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Leak A: exception in coroutine still removes task from `RunningTasks` | Start a coroutine that raises `ValueError`; await it; assert `task not in wx_app.RunningTasks[obj]` and `obj not in wx_app.RunningTasks` |
| Unit | Leak B: `OnDestroy` removes `RunningTasks[obj]` entry | Start long coroutine; call `OnDestroy`; assert `obj not in wx_app.RunningTasks` |
| Unit | CancelledError still swallowed, task removed | Existing T10 test; assert task removed after cancellation |
| Unit | Non-`CancelledError` emits warning and cleans up | `warnings.catch_warnings`; assert warning message contains exception info and task is removed |
| Coverage | `src/` line coverage ≥80% | `uv run pytest --cov=src` |

## Migration / Rollout

No migration required. This is a bug fix within existing behavior. Consumers do not need to change code.

## Open Questions

None.
