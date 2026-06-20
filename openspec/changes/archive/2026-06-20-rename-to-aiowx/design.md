# Design: Rename wxasync → aiowx

## Technical Approach

Pure mechanical rename with zero behavior change. Move `src/wxasync/` to `src/aiowx/`, then replace every package-level string `wxasync` with `aiowx` in imports, docstrings, configs, and docs. Public API class names (`WxAsyncApp`, `AsyncBind`, `StartCoroutine`, `AsyncShowDialog`, `AsyncShowDialogModal`) remain unchanged. Verify with `uv run pytest --cov=src`, `uv build`, `ruff check`, and a final grep proving zero remaining package references.

## Architecture Decisions

| Decision | Options | Tradeoffs | Choice |
|----------|---------|-----------|--------|
| Package directory rename | `git mv src/wxasync src/aiowx` vs. copy-delete | `git mv` preserves history and blame; copy-delete loses lineage | `git mv` |
| Public API class names | Keep `WxAsyncApp`/`AsyncBind` vs. rename to `AioWxApp` | Renaming would break every consumer; keeping preserves backward compatibility at the class level | Keep existing names |
| Import string replacement | Global `wxasync` → `aiowx` vs. selective per-file | Global is faster and safe because class names are distinct (`WxAsyncApp` ≠ `wxasync`); selective risks misses | Global replace, then grep-verify |
| Compatibility shim | Add `wxasync` stub package vs. none | Shim eases migration but adds maintenance; proposal explicitly excludes it | No shim |
| Build lockfile | `uv lock` regenerate vs. manual edit | Regenerate is authoritative and updates package metadata | `uv lock` |

## Data Flow

No runtime data flow changes. The rename only affects import resolution:

```
Consumer / Test / Example
         │
         ▼
   import aiowx           ← previously import wxasync
         │
         ▼
   src/aiowx/__init__.py  ← previously src/wxasync/__init__.py
         │
         ▼
   src/aiowx/_core.py     ← unchanged logic, only docstring/package refs
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/wxasync/` | Rename → `src/aiowx/` | Package directory via `git mv` |
| `src/aiowx/__init__.py` | Modify | Internal import `from wxasync._core` → `from aiowx._core` |
| `src/aiowx/_core.py` | Modify | Module docstring `wxasync` → `aiowx` |
| `pyproject.toml` | Modify | `name = "wxasync"` → `"aiowx"`; update description/authors |
| `tests/conftest.py` | Modify | Imports and docstring `wxasync._core` → `aiowx._core` |
| `tests/test_app.py` | Modify | Import `wxasync._core` → `aiowx._core` |
| `tests/test_bind.py` | Modify | Import `wxasync._core` → `aiowx._core` |
| `tests/test_coroutine.py` | Modify | Import `wxasync._core` → `aiowx._core` |
| `tests/test_dialogs.py` | Modify | Imports and patch paths `wxasync._core` → `aiowx._core` |
| `src/examples/simple.py` | Modify | `from wxasync` → `from aiowx` |
| `src/examples/slider_demo.py` | Modify | `from wxasync` → `from aiowx` |
| `src/examples/server.py` | Modify | `from wxasync` → `from aiowx` |
| `src/examples/dialog.py` | Modify | `from wxasync` → `from aiowx` |
| `src/examples/more_dialogs.py` | Modify | `from wxasync` → `from aiowx` |
| `README.md` | Modify | Title, install command, package references → `aiowx` (keep `WxAsyncApp` in usage) |
| `AGENTS.md` | Modify | Package-name examples and title → `aiowx` |
| `notes.txt` | Modify | `pip install wxasync==0.2` → `aiowx` |
| `openspec/specs/foundation/spec.md` | Modify | Import scenarios `from wxasync` → `from aiowx` |
| `.atl/skill-registry.md` | Modify | Title `wxasync` → `aiowx` |
| `uv.lock` | Regenerate | `uv lock` after pyproject.toml name change |

## Interfaces / Contracts

No new interfaces. Public API contract is unchanged:

```python
from aiowx import WxAsyncApp, AsyncBind, StartCoroutine, AsyncShowDialog, AsyncShowDialogModal
```

Internal test imports become:

```python
from aiowx._core import WxAsyncApp, wx
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | All existing tests pass after import rename | `uv run pytest --cov=src` must pass with ≥80% coverage |
| Build | Wheel produced with new package name | `uv build` produces `aiowx-*.whl` |
| Lint/Format | No style regressions | `uv run ruff check` and `uv run ruff format` |
| Reference audit | Zero remaining `wxasync` package refs | `git grep -n "wxasync"` excluding archive/.github returns empty |

## Migration / Rollout

No runtime migration. For consumers, update install command to `pip install aiowx` and imports to `from aiowx import ...`. Repository rename on GitHub is a manual step documented in the proposal. Rollback: `git revert` the rename commit.

## Open Questions

- [ ] Confirm `aiowx` is available on PyPI before final publish (not blocking implementation).
