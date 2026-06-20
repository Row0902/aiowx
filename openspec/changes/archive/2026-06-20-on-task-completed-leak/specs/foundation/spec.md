# Delta for Foundation

## MODIFIED Requirements

### Requirement: REQ-F6 Unit Tests

The system MUST provide unit tests under `tests/` via pytest + pytest-asyncio with mocked wxPython for headless execution and >=80% coverage. `OnTaskCompleted` MUST remove the task from `RunningTasks` even when `task.result()` raises a non-`CancelledError` exception, and MUST emit a warning for such exceptions instead of letting them escape the done-callback. `OnDestroy` MUST delete the `RunningTasks[obj]` entry after cancelling tracked tasks, leaving no orphan empty-set entries in the defaultdict.

(Previously: REQ-F6 mandated unit tests only; T8 asserted `CancelledError` silenced and other exceptions propagate, with cleanup-on-exception documented as a known limitation; `OnDestroy` left an empty `RunningTasks[obj]` set behind.)

| Test | Area | Key Assertion |
|------|------|---------------|
| T1 | WxAsyncApp init | Attributes set; `SetExitOnFrameDelete` called |
| T2 | MainLoop exit | `ExitMainLoop()` sets `exiting=True`; loop terminates |
| T3 | AsyncBind | Coroutine bound; params forwarded via `event.Clone()` |
| T4 | AsyncBind cancel | `EVT_WINDOW_DESTROY` cancels running tasks for window |
| T5 | StartCoroutine | Returns `asyncio.Task`; wraps callable coroutine |
| T6 | AsyncShowDialog | Event-based flow; return code matches `SetReturnCode` |
| T7 | AsyncShowDialogModal | Frame disable/enable; executor path for OS dialogs |
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

## Non-Goals Update

The Phase 1 Non-Goals entry "OnTaskCompleted exception logging (Phase 2)" is REMOVED — exception surfacing via `warnings.warn` is now delivered in Phase 1 as part of this change.

Remaining Phase 1 Non-Goals unchanged: async dialog context manager (Phase 2), loop_factory (Phase 3), PoC archival (Phase 3), eager task factory (Phase 3), wxPython 3.14 wheel verification.
