# Design: refactor-core

## Technical Approach

Split `src/aiowx/_core.py` into two focused files: `_app.py` (WxAsyncApp with all its methods) and `_dialog.py` (pure dialog helpers). Dialog helpers are genuinely independent — they don't need WxAsyncApp's internal state. Preserve all public symbols by re-exporting from `src/aiowx/__init__.py`. Keep every function's behavior and signature identical except for renaming `ShowModalInExecutor` to `ShowModalAsync`. Update `pyproject.toml` per-file ignores to match the new files.

## Architecture Decisions

### Decision: Split Boundary — Dialog Only

| Option | Tradeoff | Decision |
|--------|----------|----------|
| 4-way split (_app, _bind, _task, _dialog) | Requires mixins or circular imports to share WxAsyncApp scope | Rejected — over-engineering for a 200-line class |
| 2-way split (_app full, _dialog) | Binding and task tracking stay with WxAsyncApp; dialogs extract cleanly | Accepted |
| No split | _core.py stays at 331 lines, sliding toward 500-limit warnings | Rejected — dialog helpers are genuinely independent |

```
_app.py ───────→ __init__.py
  (WxAsyncApp,     ↑
   AsyncBind,       └── re-exports 5 symbols
   StartCoroutine,
   OnTaskCompleted,
   OnDestroy,
   _TrackedTask,
   module wrappers)

_dialog.py
  (ShowModalAsync,
   AsyncShowDialog,
   AsyncShowDialogModal)
```

- `_dialog.py` imports `WxAsyncApp` from `_app` only for type checking in `AsyncShowDialogModal` — a single direction, no cycle.
- `_TrackedTask` lives in `_app.py` as an internal implementation detail of WxAsyncApp's task lifecycle.
- `__init__.py` imports `WxAsyncApp`, `AsyncBind`, `StartCoroutine` from `_app` and `AsyncShowDialog`, `AsyncShowDialogModal` from `_dialog`.

### Decision: `_TrackedTask` Dataclass

Replace `setattr(task, "obj", obj)` with an explicit dataclass that links the task to its owner. Lives in `_app.py` as an internal detail.

```python
@dataclass
class _TrackedTask:
    """Lifecycle handle that connects an asyncio.Task to its wx owner window."""

    task: asyncio.Task[Any]
    obj: wx.Window
```

`RunningTasks` becomes `defaultdict[wx.Window, set[_TrackedTask]]`. `OnTaskCompleted` looks up `tracked.obj`; `OnDestroy` iterates `RunningTasks[obj]` to cancel every tracked task. This preserves the original lifecycle semantics without monkey-patching `asyncio.Task`.

### Decision: Module-Level Wrappers Stay in `_app.py`

The module-level `AsyncBind()` and `StartCoroutine()` wrappers live in `_app.py` alongside `WxAsyncApp`. Both follow the same pattern:

```python
def StartCoroutine(coroutine, obj):
    app = wx.App.Get()
    if not isinstance(app, WxAsyncApp):
        raise Exception("Create a 'WxAsyncApp' first")
    return app.StartCoroutine(coroutine, obj)
```

`AsyncShowDialog` and `AsyncShowDialogModal` remain module-level coroutines in `_dialog.py` and use the module-level `AsyncBind` wrapper for event binding. `_app.py` imports are the only dependency.

### Decision: `ShowModalInExecutor` Rename

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Keep old name for compatibility | Name is misleading because it does not use an executor | Rejected |
| Rename to `ShowModalAsync` with identical signature | Tests update their imports; public API stays stable | Accepted |

The implementation is unchanged: schedule `dialog.ShowModal()` via `wx.CallAfter`, resolve an `asyncio.Future` with the return code, and await it.

## Data Flow

```
User code ──→ __init__.py ──→ _app.py (WxAsyncApp + wrappers)
                             └── _dialog.py (dialog helpers)
                             
              Each module imports wx directly
              _dialog.py imports WxAsyncApp from _app for type checking only
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/aiowx/_core.py` | Delete | Replaced by two focused files |
| `src/aiowx/_app.py` | Create | Full `WxAsyncApp` with `MainLoop`, `ExitMainLoop`, `AsyncBind`, `StartCoroutine`, `OnTaskCompleted`, `OnDestroy`, `_TrackedTask`, module-level wrappers |
| `src/aiowx/_dialog.py` | Create | `ShowModalAsync`, `AsyncShowDialog`, `AsyncShowDialogModal` |
| `src/aiowx/__init__.py` | Modify | Import 5 public symbols from new modules |
| `pyproject.toml` | Modify | Replace `_core.py` per-file ignores with per-module entries |

## Interfaces / Contracts

Public API remains unchanged:

```python
from aiowx import (
    AsyncBind,
    AsyncShowDialog,
    AsyncShowDialogModal,
    StartCoroutine,
    WxAsyncApp,
)
```

Internal contracts:

- `_TrackedTask` lives in `_app.py`, not exposed via `__all__`
- `_TrackedTask.task` is the running `asyncio.Task`
- `_TrackedTask.obj` is the `wx.Window` used for cleanup
- `WxAsyncApp.StartCoroutine` returns `asyncio.Task[Any]` and registers a `_TrackedTask`
- `WxAsyncApp.OnDestroy` cancels all `_TrackedTask` entries for the destroyed window
- `_dialog.py` imports `WxAsyncApp` from `_app.py` only for `isinstance` checks

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Existing tests after import updates | Update imports from `_core` to `_app`/`_dialog`; rename `ShowModalInExecutor` → `ShowModalAsync`; import `wx` directly; run `pytest --cov=src` |
| Static | Ruff, `ty` | `ruff check`, `ruff format`, `ty` on `src/aiowx` |
| Build | Wheel | `uv build` |

Coverage must remain ≥80% on `src/` after the refactor.

## Migration / Rollout

Single PR. Clean revert. No data migration.

## Open Questions

- [ ] Resolve MIG-6 `_app.py` ignore gap: `warn_on_cancel_callback: bool` triggers FBT001/FBT002. Either add `_app.py` to per-file ignores for FBT or refactor the parameter. Current `_core.py` carries FBT ignores — simplest is to carry them forward.
