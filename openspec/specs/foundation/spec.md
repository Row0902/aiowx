# Foundation Specification

## Purpose

Phase 1 foundation: deprecated API replacement, import cleanup, package consolidation, type hints, modern idioms, unit tests, CI, cleanup. Target: Python >=3.12. Public API preserved.

## Requirements

| ID | Requirement | RFC 2119 |
|----|------------|----------|
| REQ-F1 | Replace `asyncio.iscoroutinefunction` with `inspect.iscoroutinefunction`; remove `asyncio.coroutines` import | MUST |
| REQ-F2 | Replace `from asyncio.locks import Event` → `from asyncio import Event`; remove dead `get_event_loop` import; use only public asyncio API | MUST |
| REQ-F3 | Consolidate `src/aiowx.py` into `src/aiowx/` package; `__init__.py` re-exports all public symbols with `__all__`; remove flat file; preserve `from aiowx import WxAsyncApp` | MUST |
| REQ-F4 | Type hints on all public API (`__init__`, `MainLoop`, `ExitMainLoop`, `AsyncBind`, `StartCoroutine`, `AsyncShowDialog`, `AsyncShowDialogModal`, `OnTaskCompleted`) using `Coroutine`, `Awaitable`, `Callable`; return types annotated | MUST |
| REQ-F5 | Replace `super(WxAsyncApp, self).__init__()` with `super().__init__()` | MUST |
| REQ-F6 | Unit tests under `tests/` via pytest + pytest-asyncio with mocked wxPython for headless execution and >=80% coverage. `ShowModalInExecutor` tests MUST mock-verify `wx.CallAfter` dispatch and assert `run_in_executor` is NOT used; the return code MUST propagate through the `asyncio.Future`. `OnTaskCompleted` MUST remove the task from `RunningTasks` even when `task.result()` raises a non-`CancelledError` exception, and MUST warn for such exceptions. `OnDestroy` MUST delete the `RunningTasks[obj]` entry after cancelling tracked tasks, leaving no orphan entries. | MUST |
| REQ-F7 | `.github/workflows/ci.yml` on push/PR: checkout, Python 3.12, uv, deps, ruff check, pytest --cov=src, upload coverage; no display required | MUST |
| REQ-F8 | Delete `setup.py`; build via `uv_build` only; update docs if import paths change | MUST |
| REQ-F9 | `ShowModalInExecutor` MUST dispatch `dialog.ShowModal()` on the wx main thread via `wx.CallAfter`. It MUST NOT use `loop.run_in_executor` for GUI operations (wxPython is not thread-safe). It MUST deliver the `ShowModal` return code via an `asyncio.Future`. The asyncio event loop blocks while the modal dialog is shown — this is expected modal behavior in a single-threaded GUI and MUST be documented. | MUST |

## Scenarios

### REQ-F1: Deprecated API Replacement

#### Scenario: Coroutine function passes validation
- GIVEN an `async def` function
- WHEN `AsyncBind` validates it via `inspect.iscoroutinefunction`
- THEN accepted; no exception raised

#### Scenario: Regular function rejected
- GIVEN a non-coroutine function
- WHEN `AsyncBind` validates it
- THEN `Exception("async_callback is not a coroutine function")` raised

### REQ-F2: Private Imports Cleanup

#### Scenario: Public Event import works
- GIVEN `from asyncio import Event`
- WHEN `AsyncShowDialog` creates `Event()` for dialog-close signaling
- THEN `await closed.wait()` behaves identically

#### Scenario: Dead import removed
- GIVEN the cleaned module
- WHEN scanning imports
- THEN no `from asyncio.events import get_event_loop` exists

### REQ-F3: Package Consolidation

#### Scenario: Backward-compatible import
- GIVEN `__init__.py` re-exports all public symbols
- WHEN `from aiowx import WxAsyncApp` executes
- THEN the class resolves correctly

#### Scenario: Star import scoped to __all__
- GIVEN `__all__` declared in `__init__.py`
- WHEN `from aiowx import *` executes
- THEN only declared names are imported

### REQ-F4: Type Hints

#### Scenario: Type checker passes
- GIVEN all public functions have type annotations
- WHEN a static type checker inspects the module
- THEN no missing-annotation errors are reported

### REQ-F5: Modern super()

#### Scenario: Initialization succeeds
- GIVEN `WxAsyncApp(redirect=True)`
- WHEN `super().__init__(**kwargs)` executes
- THEN init completes; `SetExitOnFrameDelete(True)` is called

### REQ-F6: Unit Tests

| Test | Area | Key Assertion |
|------|------|---------------|
| T1 | WxAsyncApp init | Attributes set; `SetExitOnFrameDelete` called |
| T2 | MainLoop exit | `ExitMainLoop()` sets `exiting=True`; loop terminates |
| T3 | AsyncBind | Coroutine bound; params forwarded via `event.Clone()` |
| T4 | AsyncBind cancel | `EVT_WINDOW_DESTROY` cancels running tasks for window |
| T5 | StartCoroutine | Returns `asyncio.Task`; wraps callable coroutine |
| T6 | AsyncShowDialog | Event-based flow; return code matches `SetReturnCode` |
| T7 | AsyncShowDialogModal | Frame disable/enable; `CallAfter` dispatch for OS dialogs (no `run_in_executor`) |
| T8 | OnTaskCompleted | `CancelledError` silenced; non-cancel exceptions warned; task removed even on exception |
| T9 | OnDestroy dict cleanup | `RunningTasks[obj]` deleted after cancellation; no orphan entries |

#### Scenario: Headless test run
- GIVEN mocked wxPython components
- WHEN `uv run pytest --cov=src tests/` executes
- THEN all tests pass; no display required

#### Scenario: Task removed after exception (Leak A regression)
- GIVEN a coroutine that raises `ValueError` is started via `StartCoroutine`
- WHEN the task completes and `OnTaskCompleted` fires
- THEN the task is no longer in `RunningTasks[win]`
- AND a warning is emitted describing the `ValueError`

#### Scenario: CancelledError still silenced
- GIVEN a tracked task is cancelled
- WHEN `OnTaskCompleted` fires
- THEN `CancelledError` is silenced with no warning and no propagation
- AND the task is removed from `RunningTasks[win]`

#### Scenario: No orphan RunningTasks after destroy (Leak B regression)
- GIVEN a window with tracked tasks is destroyed via `OnDestroy`
- WHEN `OnDestroy` cancels all tracked tasks
- THEN `RunningTasks` no longer contains an entry for that window
- AND `BoundObjects` no longer contains an entry for that window

#### Scenario: OnDestroy snapshot avoids iteration race

- GIVEN `OnDestroy` is cancelling tasks while `OnTaskCompleted` fires mid-iteration
- WHEN `OnDestroy` iterates `RunningTasks[obj]`
- THEN iteration runs over a snapshot and does not raise `RuntimeError`

#### Scenario: T7 verifies thread-safe ShowModal dispatch

- GIVEN mocked `wx.CallAfter` and `dialog.ShowModal` returning a known return code
- WHEN T7 exercises `ShowModalInExecutor(dialog)`
- THEN the test asserts `wx.CallAfter` was called exactly once
- AND asserts `loop.run_in_executor` was NOT called for the dialog
- AND the return code propagates to the awaiter

### REQ-F7: CI Workflow

#### Scenario: CI passes on PR
- GIVEN a pull request against `main`
- WHEN CI workflow executes
- THEN ruff exits 0; pytest exits 0; coverage report uploaded

### REQ-F8: Cleanup

#### Scenario: Build succeeds after setup.py removal
- GIVEN `setup.py` is deleted
- WHEN `uv build` executes
- THEN a valid wheel is produced

### REQ-F9: ShowModalInExecutor Thread-Safety

#### Scenario: ShowModal dispatched on main thread via CallAfter

- GIVEN `ShowModalInExecutor(dialog)` is awaited
- WHEN the coroutine schedules `dialog.ShowModal()`
- THEN `wx.CallAfter` is invoked exactly once, queuing `ShowModal` on the wx main thread
- AND `loop.run_in_executor` is NOT called

#### Scenario: Return code propagates through Future

- GIVEN `wx.CallAfter` runs `dialog.ShowModal()` which returns `wx.ID_OK`
- WHEN the `CallAfter` callback resolves the `asyncio.Future` with the return code
- THEN `await ShowModalInExecutor(dialog)` returns `wx.ID_OK`

#### Scenario: Event loop blocks during modal dialog

- GIVEN `ShowModalInExecutor(dialog)` is awaiting the `asyncio.Future`
- WHEN the modal dialog is open and not yet dismissed
- THEN the asyncio event loop does not process other coroutines until the dialog closes

## Non-Goals

Phase 1 does NOT cover: async dialog context manager (Phase 2), loop_factory (Phase 3), PoC archival (Phase 3), eager task factory (Phase 3), wxPython 3.14 wheel verification.
