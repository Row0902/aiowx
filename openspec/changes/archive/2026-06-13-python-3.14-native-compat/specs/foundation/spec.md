# Foundation Specification

## Purpose

Phase 1 foundation: deprecated API replacement, import cleanup, package consolidation, type hints, modern idioms, unit tests, CI, cleanup. Target: Python >=3.12. Public API preserved.

## Requirements

| ID | Requirement | RFC 2119 |
|----|------------|----------|
| REQ-F1 | Replace `asyncio.iscoroutinefunction` with `inspect.iscoroutinefunction`; remove `asyncio.coroutines` import | MUST |
| REQ-F2 | Replace `from asyncio.locks import Event` → `from asyncio import Event`; remove dead `get_event_loop` import; use only public asyncio API | MUST |
| REQ-F3 | Consolidate `src/wxasync.py` into `src/wxasync/` package; `__init__.py` re-exports all public symbols with `__all__`; remove flat file; preserve `from wxasync import WxAsyncApp` | MUST |
| REQ-F4 | Type hints on all public API (`__init__`, `MainLoop`, `ExitMainLoop`, `AsyncBind`, `StartCoroutine`, `AsyncShowDialog`, `AsyncShowDialogModal`, `OnTaskCompleted`) using `Coroutine`, `Awaitable`, `Callable`; return types annotated | MUST |
| REQ-F5 | Replace `super(WxAsyncApp, self).__init__()` with `super().__init__()` | MUST |
| REQ-F6 | Unit tests under `tests/` via pytest + pytest-asyncio; mock wxPython for headless execution; >=80% coverage | MUST |
| REQ-F7 | `.github/workflows/ci.yml` on push/PR: checkout, Python 3.12, uv, deps, ruff check, pytest --cov=src, upload coverage; no display required | MUST |
| REQ-F8 | Delete `setup.py`; build via `uv_build` only; update docs if import paths change | MUST |

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
- WHEN `from wxasync import WxAsyncApp` executes
- THEN the class resolves correctly

#### Scenario: Star import scoped to __all__
- GIVEN `__all__` declared in `__init__.py`
- WHEN `from wxasync import *` executes
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
|------|------|--------------|
| T1 | WxAsyncApp init | Attributes set; `SetExitOnFrameDelete` called |
| T2 | MainLoop exit | `ExitMainLoop()` sets `exiting=True`; loop terminates |
| T3 | AsyncBind | Coroutine bound; params forwarded via `event.Clone()` |
| T4 | AsyncBind cancel | `EVT_WINDOW_DESTROY` cancels running tasks for window |
| T5 | StartCoroutine | Returns `asyncio.Task`; wraps callable coroutine |
| T6 | AsyncShowDialog | Event-based flow; return code matches `SetReturnCode` |
| T7 | AsyncShowDialogModal | Frame disable/enable; executor path for OS dialogs |
| T8 | OnTaskCompleted | `CancelledError` silenced; other exceptions propagate |

#### Scenario: Headless test run
- GIVEN mocked wxPython components
- WHEN `uv run pytest --cov=src tests/` executes
- THEN all tests pass; no display required

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

## Non-Goals

Phase 1 does NOT cover: async dialog context manager (Phase 2), OnTaskCompleted exception logging (Phase 2), loop_factory (Phase 3), PoC archival (Phase 3), eager task factory (Phase 3), wxPython 3.14 wheel verification.
