# Delta for Foundation

## ADDED Requirements

### Requirement: REQ-F9 ShowModalInExecutor Thread-Safety

`ShowModalInExecutor` MUST dispatch `dialog.ShowModal()` on the wx main thread via `wx.CallAfter`. It MUST NOT use `loop.run_in_executor` for GUI operations (wxPython is not thread-safe). It MUST deliver the `ShowModal` return code via an `asyncio.Future`. The asyncio event loop blocks while the modal dialog is shown — this is expected modal behavior in a single-threaded GUI and MUST be documented.

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

## MODIFIED Requirements

### REQ-F6: Unit Tests

Unit tests under `tests/` via pytest + pytest-asyncio with mocked wxPython for headless execution and >=80% coverage. `ShowModalInExecutor` tests MUST mock-verify `wx.CallAfter` dispatch and assert `run_in_executor` is NOT used; the return code MUST propagate through the `asyncio.Future`. `OnTaskCompleted` MUST remove the task from `RunningTasks` even when `task.result()` raises a non-`CancelledError` exception, and MUST warn for such exceptions. `OnDestroy` MUST delete the `RunningTasks[obj]` entry after cancelling tracked tasks, leaving no orphan entries.
(Previously: T7 described the "executor path for OS dialogs"; now verifies thread-safe `CallAfter` dispatch with no `run_in_executor`.)

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
