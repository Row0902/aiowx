# Design: Python 3.14 Native Compatibility for wxasync — Phase 1 (Foundation)

## 1. Architecture Overview

Phase 1 reshapes the project surface without changing runtime semantics. The single
`src/wxasync.py` module (180 LOC) is moved into a `src/wxasync/` package with a
single implementation file (`_core.py`) and a public re-export `__init__.py` that
declares `__all__`. Deprecated asyncio internals are replaced with public APIs
(`inspect.iscoroutinefunction`, `asyncio.Event`); a mock-based unit test layer and
a headless GitHub Actions CI workflow gate regressions. `setup.py` is deleted so
`uv_build` (declared in `pyproject.toml`) is the single source of truth. Public
imports (`from wxasync import WxAsyncApp, AsyncBind, StartCoroutine`) remain
unchanged.

## 2. Module / Class Design

### 2.1 `WxAsyncApp` (in `src/wxasync/_core.py`)

Subclass of `wx.App`. Owns the asyncio/wx bridge state.

| Attribute | Type | Purpose |
|---|---|---|
| `BoundObjects` | `dict[wx.Window, dict[int, list[Callable]]]` | Per-window coroutine bindings keyed by event `typeId` |
| `RunningTasks` | `defaultdict[wx.Window, set[asyncio.Task]]` | Live tasks per window for `OnDestroy` cleanup |
| `exiting` | `bool` | Toggled by `ExitMainLoop()`; main loop polls this |
| `ui_idle` | `bool` | Tracks whether the loop drained the queue (drives `ProcessIdle`) |
| `sleep_duration` | `float` | `asyncio.sleep` between poll cycles (default `0.02`) |
| `warn_on_cancel_callback` | `bool` | Emit `warnings.warn` when window-destroy cancels a task |

Methods (typed, all coroutine return signatures use `Coroutine[Any, Any, T]`):

```python
def __init__(self, warn_on_cancel_callback: bool = False,
             sleep_duration: float = 0.02, **kwargs: Any) -> None
async def MainLoop(self) -> None                       # bridges wxGUIEventLoop <-> asyncio
def ExitMainLoop(self) -> None                         # sets self.exiting = True
def AsyncBind(self, event_binder, async_callback, object, source=None,
              id: int = wx.ID_ANY, id2: int = wx.ID_ANY) -> None
def StartCoroutine(self, coroutine, obj) -> asyncio.Task
def OnTaskCompleted(self, task: asyncio.Task) -> None  # silences CancelledError
def OnDestroy(self, event, obj) -> None                # cancels every running task
```

`MainLoop` retains the platform fork: macOS uses `evtloop.DispatchTimeout(0)`;
other platforms drain `while evtloop.Pending(): evtloop.Dispatch()`. Both branches
yield with `await asyncio.sleep(0)` and end the cycle with `sleep(sleep_duration)`,
`ProcessPendingEvents()`, and conditional `ProcessIdle()`.

### 2.2 `AsyncBind` (module-level + method)

Validates that `object` is `wx.Window` and `async_callback` is a coroutine
function (via `inspect.iscoroutinefunction`). Binds a one-shot
`EVT_WINDOW_DESTROY` per window (idempotent — guarded by `object not in
self.BoundObjects`) and the user event via `object.Bind(event_binder, lambda
event: StartCoroutine(async_callback(event.Clone()), object), ...)`. The
`event.Clone()` ensures the coroutine sees an event owned by itself.

### 2.3 `StartCoroutine` (module-level + method)

Accepts either a coroutine object or a coroutine function (the function form is
called). Registers the window for `EVT_WINDOW_DESTROY` if not already tracked,
creates the task via `asyncio.create_task(coroutine)`, attaches the destroy
cleanup and `OnTaskCompleted` done-callback, returns the task.

### 2.4 Dialog helpers

`AsyncShowDialog(dlg)` — asserts dlg is NOT a modless-incompatible type
(`FileDialog`, `DirDialog`, `FontDialog`, `ColourDialog`, `MessageDialog`),
binds `EVT_CLOSE` and `EVT_BUTTON` via `AsyncBind`, calls `dlg.Show()`, and
awaits an `asyncio.Event` set by button/close handlers. Returns
`dlg.GetReturnCode()`.

`AsyncShowDialogModal(dlg)` — routes OS-level dialogs (`HtmlHelpDialog`,
`FileDialog`, `DirDialog`, `FontDialog`, `ColourDialog`, `MessageDialog`) to
`ShowModalInExecutor` (which uses `loop.run_in_executor`). For regular
`wx.Dialog` instances, disables sibling top-level frames, runs
`AsyncShowDialog`, and re-enables frames in `finally`.

## 3. Package Layout (target)

```
src/
└── wxasync/
    ├── __init__.py        # re-exports + __all__ (public surface)
    ├── _core.py           # all logic (180 LOC) — internal
    └── py.typed           # PEP 561 marker (already present)
test/
├── conftest.py            # wx_stub fixture + asyncio.sleep patch
├── test_app.py            # WxAsyncApp init / MainLoop / ExitMainLoop
├── test_bind.py           # AsyncBind validation, multi-binding, destroy
├── test_coroutine.py      # StartCoroutine, OnTaskCompleted, CancelledError
├── test_dialogs.py        # AsyncShowDialog + AsyncShowDialogModal
└── test_perfs.py          # marked skip("requires display; manual benchmark")
.github/
└── workflows/
    └── ci.yml             # uv-based pytest + ruff workflow
```

`src/wxasync.py` (flat file) and `setup.py` are deleted.

## 4. API Design (typed signatures)

```python
# src/wxasync/__init__.py
from wxasync._core import (
    AsyncBind, AsyncShowDialog, AsyncShowDialogModal,
    StartCoroutine, WxAsyncApp,
)
__all__ = [
    "AsyncBind", "AsyncShowDialog", "AsyncShowDialogModal",
    "StartCoroutine", "WxAsyncApp",
]
```

Annotated public surface (`from __future__ import annotations` enabled so
forward refs stay strings; the `py.typed` marker ships them to consumers):

```python
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any, TypeAlias

CoroutineFn: TypeAlias = Callable[..., Coroutine[Any, Any, Any]]
WindowType: TypeAlias = wx.Window  # the type alias is for documentation only

class WxAsyncApp(wx.App):
    def __init__(self, warn_on_cancel_callback: bool = False,
                 sleep_duration: float = 0.02, **kwargs: Any) -> None: ...
    async def MainLoop(self) -> None: ...
    def ExitMainLoop(self) -> None: ...
    def AsyncBind(self, event_binder: wx.PyEventBinder,
                  async_callback: CoroutineFn,
                  object: wx.Window, source: wx.EvtHandler | None = None,
                  id: int = wx.ID_ANY, id2: int = wx.ID_ANY) -> None: ...
    def StartCoroutine(self,
                       coroutine: Coroutine[Any, Any, Any] | CoroutineFn,
                       obj: wx.Window) -> asyncio.Task[Any]: ...
    def OnTaskCompleted(self, task: asyncio.Task[Any]) -> None: ...
    def OnDestroy(self, event: wx.WindowDestroyEvent, obj: wx.Window) -> None: ...

def AsyncBind(event: wx.PyEventBinder, async_callback: CoroutineFn,
              object: wx.Window, source: wx.EvtHandler | None = None,
              id: int = wx.ID_ANY, id2: int = wx.ID_ANY) -> None: ...
def StartCoroutine(coroutine: Coroutine[Any, Any, Any] | CoroutineFn,
                   obj: wx.Window) -> asyncio.Task[Any]: ...
async def AsyncShowDialog(dlg: wx.Dialog) -> int: ...
async def AsyncShowDialogModal(dlg: wx.Dialog) -> int: ...
```

`super(WxAsyncApp, self).__init__(**kwargs)` → `super().__init__(**kwargs)`.

## 5. Testing Strategy

**Mock fixture** (`test/conftest.py`): a `wx_stub` autouse session fixture
installs a `MagicMock`-backed `wx` module into `sys.modules` BEFORE any
`wxasync._core` import. The mock exposes `wx.App` (subclassable),
`wx.GUIEventLoop` (whose `Pending()` is a list-iterator that the test
controls), `wx.EventLoopActivator` (a `MagicMock` context manager),
`wx.Window` (a class with `Bind`, `IsEnabled`, `Enable`, `Disable`,
`GetParent`, `SetFocus`, `GetId`, `GetAffirmativeId`, `GetEscapeId`),
plus the constants `ID_ANY`, `ID_CANCEL`, `ID_APPLY`, `EVT_WINDOW_DESTROY`,
`EVT_CLOSE`, `EVT_BUTTON`, and the dialog types. `asyncio.sleep` is
monkeypatched to a no-op awaitable bounded by a counter so `MainLoop`
terminates in tests. `platform.system` is patched per-test to drive the
macOS vs non-macOS branch.

| Test | Target | Key Assertion |
|---|---|---|
| T1 | `WxAsyncApp.__init__` | attrs set, `SetExitOnFrameDelete(True)` called, `super().__init__` called |
| T2 | `MainLoop` (non-Mac) | iterates `Pending()` → `Dispatch()`; exits when `exiting=True` |
| T3 | `MainLoop` (Mac) | calls `DispatchTimeout(0)`; no `Pending()` loop |
| T4 | `ExitMainLoop` | toggles `exiting=True`; loop terminates |
| T5 | `AsyncBind` validation | raises on non-`wx.Window`; raises on non-coroutine |
| T6 | `AsyncBind` | calls `object.Bind`; records in `BoundObjects[obj][typeId]` |
| T7 | `AsyncBind` idempotency | `EVT_WINDOW_DESTROY` bound exactly once per window |
| T8 | `StartCoroutine` | accepts coroutine + callable; returns `asyncio.Task` |
| T9 | `OnDestroy` | cancels each non-done task; respects `warn_on_cancel_callback` |
| T10 | `OnTaskCompleted` | silences `CancelledError`; non-cancel exceptions propagate |
| T11 | `AsyncShowDialog` | modless-incompatible types raise; happy path returns `GetReturnCode` |
| T12 | `AsyncShowDialogModal` | OS-dialog types route to `run_in_executor`; regular dialogs disable frames |

Coverage target: `>= 80%` (`pytest --cov=src`). Strict TDD per
`openspec/config.yaml`.

## 6. CI Pipeline Design

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with: { enable-cache: true }
      - run: uv python install 3.12
      - run: uv sync --all-extras --dev
      - run: uv run ruff check
      - run: uv run pytest --cov=src --cov-report=xml
      - uses: actions/upload-artifact@v4
        with: { name: coverage, path: coverage.xml }
```

No display server needed: tests never construct a real `wx.App`. Python 3.12
is the floor (`pyproject.toml` `requires-python = ">=3.12"`); 3.14 may be
added once `wxpython` publishes a wheel. `python-publish.yml` is unchanged.

## 7. Migration Plan

1. **Create package skeleton.** `src/wxasync/_core.py` receives the entire body
   of `src/wxasync.py`. `src/wxasync/__init__.py` is rewritten with the
   re-exports + `__all__` from §4. The `hello()` placeholder is removed.
2. **Replace deprecated imports.** `from asyncio.coroutines import
   iscoroutinefunction` → `from inspect import iscoroutinefunction`.
   `from asyncio.locks import Event` → `from asyncio import Event`. Drop
   `from asyncio.events import get_event_loop` (dead).
3. **Modernise `super()`.** `super(WxAsyncApp, self).__init__(**kwargs)` →
   `super().__init__(**kwargs)`.
4. **Add type hints** per §4 with `from __future__ import annotations`.
5. **Delete** `src/wxasync.py` and `setup.py`.
6. **Add tests.** `test/conftest.py` with `wx_stub`. Four test modules
   listed in §5. Mark `test/test_perfs.py` skip. Delete
   `test/poc_windows_patch_iocp.py` is **out of scope for Phase 1** (Phase 3).
7. **Add CI.** `.github/workflows/ci.yml` per §6.
8. **Verify locally**: `uv build`, `uv run pytest --cov=src`,
   `uv run ruff check`, `uv run python -c "from wxasync import WxAsyncApp"`.
9. **Smoke-test the examples** (`src/examples/*.py`) under
   `xvfb-run python src/examples/simple.py` to catch any regression
   `MagicMock` cannot see.

Rollback: every step is `git revert`-able; no data migration, no flag
flips, no schema changes. The proposed commit sequence keeps each step
under the 400-line review budget (single-file edits per commit).

## Key Decisions

| Decision | Choice | Tradeoff | Rationale |
|---|---|---|---|
| Module layout | Single `_core.py` re-exported by `__init__.py` | Splitting forces premature module boundaries | 180 LOC fits one file; PR diff stays reviewable |
| Deprecation fix | `inspect.iscoroutinefunction` | Identical semantics | `asyncio.iscoroutinefunction` is removed in 3.16 |
| Public import surface | `from wxasync import …` (flat) | `_core` still importable for tests | Backward-compatible; preserves examples |
| Test mock surface | `MagicMock` `wx` module patched in `conftest.py` | Mock drift risk | wxPython has no headless mode; CI cannot run real `wx.App` |
| Type annotations | `from __future__ import annotations` + `Coroutine`/`Awaitable` | Defer evaluation to strings | PEP 649/749 forward-compat; `py.typed` ships them |
| `__all__` location | `__init__.py` only | `_core.py` stays implicit | Public surface is the re-export, not the implementation |
| `setup.py` fate | Delete | Lose legacy `py_modules` shim | Conflicts with `uv_build` declared in `pyproject.toml` |
| CI Python | 3.12 (floor) | 3.14 blocked on wxpython wheel | Matches `pyproject.toml` `requires-python` |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Mock drift — `MagicMock` allows calls that would fail at runtime | Medium | xvfb-run smoke test of `src/examples/simple.py` and `dialog.py` in pre-merge job |
| `wx.PyEventBinder` type alias is structural; `PyEventBinder` is a C-extension class | Medium | Annotate as `wx.PyEventBinder` directly (public class); fallback to `wx.EvtBinder` if import fails at type-check time |
| `asyncio.iscoroutinefunction` (public, non-deprecated form) is **not** the same as the deprecated one — verify `inspect.iscoroutinefunction` matches existing semantics for async generators | Low | Add a T5 sub-assertion that an `async def` decorated with `@asyncio.coroutine` legacy form still validates |
| PR review budget — single commit moving the 180 LOC file plus new tests exceeds 400 lines | Low | Split into commits: (a) package move, (b) import fix, (c) type hints, (d) tests, (e) CI |
| `uv_build` does not pick up `src/wxasync/__init__.py` because of legacy `py_modules` artifacts | Low | After deleting `setup.py`, `uv build` from clean tree is the verification step |

## Open Questions

- [ ] `from asyncio import Event` vs `from asyncio.locks import Event` — the
      public re-export is preferred; confirm `ruff` rules don't ban it.
- [ ] Whether `py.typed` already exists at `src/wxasync/py.typed` (proposal
      implies yes) — confirm before relying on it for type distribution.
- [ ] Whether to add `loop_factory` support now (Phase 3) or defer — Phase 1
      keeps it out of scope per the proposal.

## Out of Scope (Phases 2–3, referenced for context)

- Async `with` dialog context manager (Phase 2)
- `OnTaskCompleted` exception logging (Phase 2)
- `loop_factory` parameter on `WxAsyncApp.__init__` (Phase 3)
- `poc_windows_patch_iocp.py` archival (Phase 3)
- Eager task factory evaluation (Phase 3)
