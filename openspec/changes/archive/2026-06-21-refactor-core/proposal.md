# Proposal: refactor-core

## Intent

`src/aiowx/_core.py` (331 lines) mixes 4 responsibilities (app lifecycle, event binding, task tracking, dialog helpers). Split into focused internal modules with modern Python features. Zero public API changes.

## Scope

### In Scope
- Split `_core.py` → `_app.py` (WxAsyncApp core), `_dialog.py` (dialog helpers)
- `__init__.py` re-exports same 5 symbols from new modules
- Update `pyproject.toml` per-file ignores
- `ShowModalInExecutor` → `ShowModalAsync`
- `_TrackedTask` dataclass, `@override`, `Self` return types

### Out of Scope
- Public API signature changes
- New capabilities or spec-level req changes
- Test file restructuring

## Capabilities

### New
None — pure refactor.

### Modified
None — no spec-level behavior changes.

## Approach

1. `_app.py`: Full `WxAsyncApp` with `MainLoop`, `ExitMainLoop`, `AsyncBind`, `StartCoroutine`, `OnTaskCompleted`, `OnDestroy`, `_TrackedTask` dataclass + module-level wrappers
2. `_dialog.py`: `ShowModalAsync` (rename from `ShowModalInExecutor`), `AsyncShowDialog`, `AsyncShowDialogModal`
3. **`_core.py`** → deleted (no shim). All modules import `wx` directly.
4. Update `pyproject.toml` per-file ignores — **evaluate each module individually**
5. **Tests** update import paths; import `wx` directly instead of from `aiowx._core`
6. `ruff check + format`, `ty`, `pytest --cov=src`

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `_core.py` | Modified | Re-export shim |
| `_app.py` | New | WxAsyncApp full (lifecycle, binding, task tracking) |
| `_dialog.py` | New | Dialog helpers |
| `pyproject.toml` | Modified | Re-scope per-file ignores |
| `__init__.py` | Modified | Import sources |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Test imports break | Medium | Keep `_core.py` shim; run tests before/after |
| Lint gaps from stale ignores | Low | `ruff check` pre-commit |
| `wx` re-export lost | Low | Each new module imports `wx` directly |

## Rollback Plan

Revert the PR. Single-commit change — clean revert. No data migration.

## Dependencies

None.

## Success Criteria

- [ ] `ruff check` exits 0
- [ ] `ruff format` produces no changes
- [ ] `ty` passes on `src/aiowx/`
- [ ] `pytest --cov=src` ≥80%
- [ ] `uv build` produces valid wheel
- [ ] All 5 public symbols importable from `aiowx`
