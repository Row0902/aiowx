# Delta: refactor-core — Module Split Migration

## ADDED Requirements
(None — pure refactor, no new behavioral capabilities)

## MODIFIED Requirements
(None — public API behavior unchanged)

## REMOVED Requirements
(None — no capability removed)

## Migration Rules

### Rule MIG-1: Public API Preservation
The `aiowx` package MUST continue to export exactly these 5 symbols:
`AsyncBind`, `StartCoroutine`, `AsyncShowDialog`, `AsyncShowDialogModal`, `WxAsyncApp`.

### Rule MIG-2: Internal Module Isolation
Each new internal module MUST import `wx` directly. No module MUST rely on another internal module's imports.

### Rule MIG-3: Name Migration
`show_modal_in_executor` references in tests MUST be updated to `ShowModalAsync`. The old name MUST NOT appear in the codebase after the refactor.

### Rule MIG-4: No Circular Imports
The new internal modules MUST form a DAG with no circular imports. `_app.py` MUST NOT import from `_bind.py`, `_task.py`, or `_dialog.py`. The module-level convenience wrappers (`AsyncBind`, `StartCoroutine`) import from `_app` only.

### Rule MIG-5: Task Tracking State
The `_TrackedTask` dataclass or equivalent mechanism MUST track the same lifecycle state as the current `setattr(task, "obj", obj)` approach. `RunningTasks` and `Boundobjects` MUST be managed with the same semantics.

### Rule MIG-6: Per-file Ignore Scoping
Each new internal module MUST have only the per-file ignores it actually needs:
- `_bind.py`: A001, A002 (wx `id` param), FBT001-003 (boolean flags in Bind signature), PLR0913 (multi-param Bind)
- `_dialog.py`: FBT001-003 (wx dialog API conventions)
- `_app.py`: none expected
- `_task.py`: none expected (B010 becomes unnecessary when `setattr` is replaced with dataclass)

## Scenarios
(None — behavioral coverage is unchanged from foundation spec)
