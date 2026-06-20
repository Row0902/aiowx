# Proposal: Rename wxasync → aiowx

## Intent

Rename the project from `wxasync` to `aiowx` to establish the fork as an independent project with a distinct, brandable identity. `wxasync` is generic and conflicts with the original upstream project. `aiowx` follows the `aio*` convention common in the Python async ecosystem.

## Scope

### In Scope
- Rename source directory: `src/wxasync/` → `src/aiowx/`
- Update `pyproject.toml` (name, description); regenerate `uv.lock`
- Update all imports in tests (5 files), examples (5 files), legacy files (2 files)
- Update documentation (README, AGENTS.md, notes.txt)
- Update OpenSpec spec references in `openspec/specs/foundation/spec.md`
- Update `.atl/skill-registry.md`
- Rename GitHub repository (manual step, documented)

### Out of Scope
- Renaming API classes (`WxAsyncApp`, `AsyncBind`, `StartCoroutine`, etc.)
- Adding a compatibility shim / `wxasync` stub package on PyPI
- Changing version number scheme
- Modifying archive artifacts (historical audit trail)

## Capabilities

### New Capabilities
None — pure rename, no new capability introduced.

### Modified Capabilities
None — no spec-level behavior changes. Only import path references in existing scenarios are updated.

## Approach

Mechanical find-and-replace rename: `git mv src/wxasync/ src/aiowx/`, then replace all `wxasync` package references with `aiowx` across source, tests, examples, docs, and OpenSpec specs. Run `uv lock` to regenerate lockfile. Verify with `uv run pytest --cov=src` and `uv build`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/wxasync/` | Renamed | Directory → `src/aiowx/` |
| `src/wxasync/__init__.py` | Modified | Internal import path |
| `src/wxasync/_core.py` | Modified | Docstring reference |
| `pyproject.toml` | Modified | Package name, description |
| `tests/*.py` (5 files) | Modified | Import paths (~14 lines) |
| `src/examples/*.py` (5 files) | Modified | Import paths (~5 lines) |
| `README.md`, `AGENTS.md`, `notes.txt` | Modified | Name references (~12 lines) |
| `openspec/specs/foundation/spec.md` | Modified | Import paths in scenarios (3 lines) |
| `uv.lock` | Regenerated | Auto-updated |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Broken imports after rename | Low | `pytest` + `uv build` verify all paths |
| `aiowx` name taken on PyPI | Low | Check before commit; fallback to alt name |
| Missed reference in edge file | Low | Grep for `wxasync` after rename; zero-match |

## Rollback Plan

`git revert` the rename commit. Restores `src/aiowx/` → `src/wxasync/`, reverts all import/docs changes, and restores lockfile.

## Dependencies

- `aiowx` name must be available on PyPI (check before finalizing)

## Success Criteria

- [ ] `uv run pytest --cov=src` passes with >=80% coverage
- [ ] `uv build` produces a valid wheel named `aiowx-*.whl`
- [ ] Zero remaining `wxasync` references in source, tests, examples, docs (archive excluded)
- [ ] `uv lock` regenerates without error
