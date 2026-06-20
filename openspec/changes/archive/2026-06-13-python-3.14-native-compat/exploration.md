# Exploration: Python 3.14 Native Compatibility for wxasync

## Executive Summary

wxasync is a single-module library (~180 LOC) that bridges wxPython's GUI event loop with Python's asyncio by polling wx events via `wx.GUIEventLoop` in a custom coroutine-based `MainLoop()`. The project already requires `>=3.14` in `pyproject.toml`, but the actual code targets Python 3.7+ semantics — it uses none of 3.14's native features and imports from deprecated asyncio internals. Key findings: (1) `asyncio.iscoroutinefunction` is deprecated in 3.14 (use `inspect.iscoroutinefunction`), (2) imports use private asyncio submodules (`asyncio.locks`, `asyncio.coroutines`, `asyncio.events`), (3) no type hints, zero tests, and a stale `setup.py` that conflicts with the modern `pyproject.toml`-based build.

## Current Architecture

### How It Works

The library provides a polling-based cooperative event loop bridge:

1. **`WxAsyncApp(MainLoop)`** — a coroutine that creates a `wx.GUIEventLoop`, activates it, then loops:
   - On **macOS**: calls `evtloop.DispatchTimeout(0)` (since `Pending()` always returns True)
   - On **other platforms**: drains pending wx events via `while Pending(): Dispatch() + await asyncio.sleep(0)`
   - Then `await asyncio.sleep(sleep_duration)` (default 20ms) to yield to the asyncio scheduler
   - Then `ProcessPendingEvents()` and `ProcessIdle()` for wx idle processing
   - Exits when `self.exiting` flag is set by `ExitMainLoop()`

2. **`AsyncBind(event_binder, async_callback, object, ...)`** — binds a coroutine function to a wx event, tracking it per-window for automatic cleanup on `EVT_WINDOW_DESTROY`

3. **`StartCoroutine(coroutine, obj)`** — wraps a coroutine in `asyncio.create_task()`, attaches it to a `wx.Window`, auto-cancels on window destruction

4. **Dialog helpers**:
   - `AsyncShowDialog(dlg)` — shows modless dialogs using `asyncio.Event()` to await user response
   - `AsyncShowDialogModal(dlg)` — shows OS-level dialogs (FileDialog, etc.) via `loop.run_in_executor()`; regular wx.Dialogs via frame-disabling + AsyncShowDialog

### Key Components

| Component | Role |
|---|---|
| `WxAsyncApp` | Main app class, extends `wx.App`, provides async `MainLoop()` |
| `AsyncBind()` (module + method) | Bind wx events to coroutine callbacks |
| `StartCoroutine()` (module + method) | Fire-and-forget coroutine attached to a wx.Window |
| `BoundObjects` dict | Tracks which coroutines are bound to which windows |
| `RunningTasks` dict | Tracks live asyncio.Tasks per window for lifecycle management |
| `OnDestroy()` handler | Auto-cancels all running tasks when a window is destroyed |
| `AsyncShowDialog*` | awaitable dialog wrappers |

### Public API Surface

```python
class WxAsyncApp(wx.App):
    def __init__(self, warn_on_cancel_callback=False, sleep_duration=0.02, **kwargs)
    async def MainLoop(self)
    def ExitMainLoop(self)
    def AsyncBind(self, event_binder, async_callback, object, source=None, id=wx.ID_ANY, id2=wx.ID_ANY)
    def StartCoroutine(self, coroutine, obj) -> asyncio.Task

# Module-level convenience wrappers:
AsyncBind(event, async_callback, object, source=None, id=wx.ID_ANY, id2=wx.ID_ANY)
StartCoroutine(coroutine, obj) -> asyncio.Task

# Dialog helpers:
async def AsyncShowDialog(dlg) -> int
async def AsyncShowDialogModal(dlg) -> int
```

### Package Structure

```
src/
  wxasync.py           # Main module (180 LOC) — all logic lives here
  wxasync/__init__.py  # Empty package — just has def hello(): return "Hello from wxasync!"
  examples/            # Usage examples (simple.py, dialog.py, server.py, slider_demo.py, more_dialogs.py)
test/
  test_perfs.py        # Manual performance benchmarks (needs display, not automated)
  poc_windows_patch_iocp.py  # Proof of concept for IOCP patching on Windows (outdated)
pyproject.toml         # Modern build config (uv_build, requires-python >=3.14)
setup.py               # Legacy build config (requires-python >=3.7, py_modules=['wxasync'])
```

## Python 3.14 Opportunities

### 1. Deprecated `asyncio.iscoroutinefunction` (MUST FIX)

- **Status**: `asyncio.iscoroutinefunction` is **deprecated in Python 3.14** and scheduled for removal in 3.16
- **Current code**: `from asyncio.coroutines import iscoroutinefunction` (private module import)
- **Fix**: Replace with `from inspect import iscoroutinefunction`
- **Impact**: Direct — used in both `AsyncBind` and `StartCoroutine` validation
- **Severity**: HIGH — will break in 3.16

### 2. Private module imports (SHOULD FIX)

| Current Import | Should Be |
|---|---|
| `from asyncio.events import get_event_loop` | Not used at all — **dead code** |
| `from asyncio.locks import Event` | `from asyncio import Event` |
| `from asyncio.coroutines import iscoroutinefunction` | `from inspect import iscoroutinefunction` |

These private modules (`asyncio.events`, `asyncio.locks`, `asyncio.coroutines`) are implementation details that could change in 3.14 without notice.

### 3. Policy system deprecation (AFFECTS DOCS / EXAMPLES)

- Python 3.14 deprecates the entire `asyncio` policy system (`DefaultEventLoopPolicy`, `WindowsSelectorEventLoopPolicy`, `WindowsProactorEventLoopPolicy`)
- The old PoC (`poc_windows_patch_iocp.py`) directly patches `_overlapped.GetQueuedCompletionStatus` — deeply tied to the proactor internals
- The recommended replacement is `asyncio.run(main(), loop_factory=...)`

**Action**: Remove or archive the PoC. Document the new `loop_factory` pattern.

### 4. Eager Task Factory (COULD LEVERAGE)

- Python 3.11+ includes `asyncio.eager_task_factory` which starts coroutines synchronously when possible
- wxasync's `StartCoroutine` creates tasks via `asyncio.create_task()` — could optionally use eager task factory for short-lived coroutines
- Low priority — the library doesn't control the event loop policy directly

### 5. Type hints (SHOULD ADD)

- The library has **zero type hints** — every function is untyped
- Python 3.14 continues the typing ecosystem improvements
- Adding type hints would make the library more maintainable and IDE-friendly
- Consider using `from __future__ import annotations` for forward compatibility

### 6. `super()` modernisation

- `super(WxAsyncApp, self).__init__(**kwargs)` → `super().__init__(**kwargs)` (Python 3 syntax)
- Minor but consistent with modern style

### 7. Structured concurrency patterns (NICE TO HAVE)

- The manual task tracking (`RunningTasks`, `BoundObjects`, `OnDestroy`) could potentially use higher-level constructs
- However, the current pattern of tracking tasks per-wx.Window for lifecycle management is fundamentally sound and TaskGroup doesn't map directly to window-level grouping

### 8. Async context manager for dialogs (NICE TO HAVE)

- `AsyncShowDialog` and `AsyncShowDialogModal` are plain async functions
- Could provide `async with AsyncDialog(dlg) as result:` pattern for resource management

## Pain Points

### P1: No automated tests — ZERO test coverage
- `test/` contains only manual performance benchmarks (`test_perfs.py`) and an abandoned PoC
- These require a display/GUI — can't run in headless CI
- No unit tests for: `AsyncBind`, `StartCoroutine`, dialog helpers, task lifecycle
- **Openspec config sets coverage threshold at 80%** but there's nothing to measure

### P2: Empty/broken `wxasync/__init__.py`
- The package `__init__.py` only has `def hello() -> str: return "Hello from wxasync!"` — does not re-export `WxAsyncApp`, `AsyncBind`, etc.
- Module-level imports (`from wxasync import WxAsyncApp`) work only because `setup.py` uses `py_modules=['wxasync']`, which picks up `src/wxasync.py`
- With `uv_build` (pyproject.toml), this may resolve differently — the `wxasync/` package directory and `wxasync.py` module coexist, creating potential ambiguity

### P3: Dead code — unused import
- `from asyncio.events import get_event_loop` is imported at line 1 of `wxasync.py` but never called

### P4: Stale `setup.py` vs `pyproject.toml` conflict
- `setup.py` says `python_requires=">=3.7"` and `py_modules=['wxasync']`
- `pyproject.toml` says `requires-python = ">=3.14"` and uses `uv_build`
- The two build systems can disagree on how the module is exposed

### P5: `OnTaskCompleted` swallows non-CancelledError exceptions
- `task.result()` raises on exception, which propagates through the done callback
- If the user's coroutine raises anything else, it's silently lost (or crashes the event loop depending on handler)

### P6: Missing `__all__` / public interface declaration
- No `__all__` in either `wxasync.py` or `wxasync/__init__.py`

### P7: `type()` check in PoC
- `poc_windows_patch_iocp.py` uses `type(app) is not WxAsyncApp` — should use `isinstance()`

## Testing Gaps

| Area | What's Missing | Priority |
|---|---|---|
| Unit tests for WxAsyncApp | Initialization, ExitMainLoop, sleep_duration param | HIGH |
| AsyncBind tests | Binding coroutines, parameter passing, event cloning | HIGH |
| StartCoroutine tests | Task creation, return type, cancellation | HIGH |
| Task lifecycle tests | Auto-cancel on EVT_WINDOW_DESTROY | HIGH |
| Dialog helper tests | AsyncShowDialog, AsyncShowDialogModal | MEDIUM |
| Error handling tests | Coroutine that raises, CancelledError propagation | MEDIUM |
| macOS branch tests | DispatchTimeout path | LOW |
| Performance benchmarks | Convert to automated tests that run without display | MEDIUM |
| CI integration | No test workflow exists | HIGH |

### Testing Viability

wxPython requires a display. Testing strategies:
- **Unit-level**: Mock `wx.App`, `wx.GUIEventLoop`, etc. Use dependency injection for the event loop handling.
- **Integration**: Use `xvfb-run` on Linux, or test windows-specific logic directly on Windows CI runners.
- **Skip actual GUI tests** on non-GUI CI and run only mock-based unit tests.

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| **`asyncio.iscoroutinefunction` removal in 3.16** | HIGH — breaking change | Switch to `inspect.iscoroutinefunction` now |
| **Private asyncio module changes in 3.14** | MEDIUM | Use public API only |
| **`wxasync.py` vs `wxasync/` package ambiguity** | MEDIUM — import could break | Restructure to proper package layout |
| **No CI test workflow** | HIGH — regressions invisible | Add pytest CI workflow |
| **wxPython may not have 3.14 wheels** | HIGH — library unusable | Verify wxPython 4.2.5+ compatibility with 3.14 |
| **`setup.py` conflict with `pyproject.toml`** | LOW — uv build ignores setup.py | Archive/remove setup.py |
| **`ShowModalInExecutor` thread-safety** | MEDIUM — wx not thread-safe | Document known limitation |
| **Deprecated policy system** | LOW — library doesn't use policies | Update PoC and examples only |

## Recommended Approach

### Phase 1: Foundation (low risk, high value)
1. Fix deprecated APIs: replace `asyncio.coroutines.iscoroutinefunction` → `inspect.iscoroutinefunction`
2. Clean up imports: remove dead `get_event_loop` import, use `asyncio.Event` directly
3. Modernize `super()` call
4. Fix `wxasync/__init__.py` to properly re-export public API with `__all__`
5. Add type hints to all public functions and methods
6. Create unit tests with mocked wxPython for headless CI
7. Add pytest CI workflow

### Phase 2: Structure (medium risk)
8. Resolve `wxasync.py` vs `wxasync/` package layout
9. Archive/remove `setup.py`
10. Add `async with` context manager for dialogs
11. Add proper exception handling in `OnTaskCompleted` to log non-CancelledError exceptions

### Phase 3: Polish (optional)
12. Support `loop_factory` parameter for asyncio.Runner compatibility
13. Remove/archive PoC files
14. Evaluate eager task factory for StartCoroutine optimization

### Ordering Rationale
Phase 1 addresses the **must-fix** 3.14 compatibility issues (deprecated APIs) and the **must-have** quality (tests, types, CI). Phase 2 fixes structural issues. Phase 3 adds optional optimizations.

## Ready for Proposal

**Yes.** Core findings are clear: the library has concrete deprecated APIs that must be fixed for 3.14 compatibility (primarily `asyncio.iscoroutinefunction`), structural issues with the package layout, and zero testing that blocks any safe refactoring. The recommended approach has clear phases with risk separation.
