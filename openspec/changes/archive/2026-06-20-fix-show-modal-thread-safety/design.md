# Design: Fix ShowModal Thread-Safety

## Technical Approach

Replace the thread-pool dispatch in `ShowModalInExecutor` with a main-thread `wx.CallAfter` + `asyncio.Future` handshake. The proposal requires that `ShowModal` always executes on the wxPython main thread, because wxWidgets forbids GUI calls from background threads. The asyncio event loop will block while the modal dialog runs its nested wx event loop; this is accepted single-threaded modal behavior.

## Architecture Decisions

| Decision | Options | Trade-offs | Choice |
|----------|---------|------------|--------|
| Thread dispatch mechanism | A. `run_in_executor(None, dialog.ShowModal)` | Runs `ShowModal` on a worker thread — crashes on macOS and violates wx thread affinity. | **Rejected** |
| | B. `wx.CallAfter` + `asyncio.Future` | Runs `ShowModal` on the wx main thread; blocks asyncio while modal runs; minimal change. | **Accepted** |
| Future result setter | A. `loop.call_soon_threadsafe(...)` | Safe if callback could run on a different thread; unnecessary overhead here. | **Rejected** |
| | B. Direct `future.set_result` inside `CallAfter` | `CallAfter` always executes on the wx main thread, which is the same thread as the running asyncio loop, so no thread-safe call is needed. | **Accepted** |
| Function name | A. Rename to `ShowModalAsync` | More accurate, but breaks public API compatibility. | **Rejected** |
| | B. Keep `ShowModalInExecutor` | Name is now misleading, but preserves backward compatibility. | **Accepted** |

## Data Flow

```
Coroutine                           wx / asyncio main thread
─────────                           ────────────────────────
await ShowModalInExecutor(dialog)
        │
        ├─ loop.create_future() ──→ Future(f)
        │
        ├─ wx.CallAfter(on_main)
        │                          wx event queue
        │                                  │
        │                                  ▼
        │                          on_main() runs
        │                          result = dialog.ShowModal()
        │                          (nested wx event loop)
        │                                  │
        │                                  ▼
        │                          user closes dialog
        │                          future.set_result(result)
        │                                  │
        ▼                                  ▼
return result ◄─────────────────── await future resolves
```

`ShowModal` enters a nested wx event loop, so the main thread is occupied but continues processing wx events. The asyncio loop resumes only after the dialog closes and the future is resolved.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/wxasync/_core.py` | Modify | Rewrite `ShowModalInExecutor` to use `wx.CallAfter` + `asyncio.Future` instead of `loop.run_in_executor`. |
| `tests/test_dialogs.py` | Modify | Update T12 to assert `wx.CallAfter` is called exactly once and `run_in_executor` is not used; verify return-code propagation. |

## Interfaces / Contracts

Signature remains unchanged:

```python
async def ShowModalInExecutor(dialog: wx.Dialog) -> int:
    """Show a modal dialog on the wx main thread and await its return code."""
```

Implementation contract:
- MUST call `wx.CallAfter` exactly once per invocation.
- MUST NOT call `loop.run_in_executor`.
- MUST return the integer result from `dialog.ShowModal()`.
- Exceptions raised by `ShowModal` MUST propagate through the future.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `ShowModalInExecutor` dispatches via `wx.CallAfter` | Patch `wx.CallAfter`, invoke the queued callback manually, assert `ShowModal` is called once. |
| Unit | `run_in_executor` is not used | Patch `asyncio.AbstractEventLoop.run_in_executor` and assert it is never called during the test. |
| Unit | Return code propagates | Mock `dialog.ShowModal` to return a known integer and assert the awaited result equals it. |
| Unit | Exception propagation | Mock `dialog.ShowModal` to raise and assert the coroutine re-raises the same exception. |

Integration and E2E tests are not available per project configuration.

## Migration / Rollout

No migration required. The function signature is unchanged. Downstream callers continue to `await ShowModalInExecutor(dialog)`.

## Open Questions

- None.
