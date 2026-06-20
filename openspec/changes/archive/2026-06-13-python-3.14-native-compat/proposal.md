# Proposal: Python 3.14 Native Compatibility for wxasync

## Intent

wxasync imports from deprecated asyncio internals (`asyncio.coroutines`, `asyncio.locks`),
lacks type hints, has zero test coverage, and uses a conflicting flat-file + package layout.
Python 3.14 deprecates `asyncio.iscoroutinefunction` (removed in 3.16). This change fixes
these issues, consolidates the package, and adds tests, CI, and type hints.

## Scope

### In Scope
- Replace `asyncio.coroutines.iscoroutinefunction` → `inspect.iscoroutinefunction`
- Fix imports: remove dead `get_event_loop`, use `asyncio.Event` directly
- Modernize `super()` call; fix `__init__.py` with re-exports + `__all__`
- Type hints on all public API
- Unit tests with mocked wxPython (pytest + pytest-asyncio)
- GitHub Actions CI workflow (pytest step)
- Delete `setup.py`
- Consolidate `src/wxasync.py` + `src/wxasync/` into clean package
- Async context manager for dialogs; fix OnTaskCompleted exception handling
- Support `loop_factory`; archive PoC files

### Out of Scope
- Structured concurrency (TaskGroup) — doesn't map to window-level task lifecycle
- wxPython 3.14 wheel compatibility — external dependency
- macOS-specific testing infrastructure

## Capabilities

### New Capabilities
None — pure compat/quality refactor; public API behavior is preserved.

### Modified Capabilities
None — no existing specs to modify.

## Approach

**Phase 1 — Foundation**: Fix deprecated APIs, imports, super(), __init__.py. Add type hints. Build mock-based unit tests and CI workflow. Delete setup.py.

**Phase 2 — Structure**: Consolidate into clean `src/wxasync/` package. Add `async with` dialog context manager. Fix silent exception loss in OnTaskCompleted.

**Phase 3 — Polish**: Support `loop_factory` param. Archive PoC files. Evaluate eager task factory.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/wxasync.py` | Modified | Type hints, import fixes, super() |
| `src/wxasync/__init__.py` | Modified | Re-exports + `__all__` |
| `src/wxasync/` | Modified | Package consolidation |
| `setup.py` | Removed | Conflicts with pyproject.toml |
| `test/` | New | Unit tests with mocked wxPython |
| `.github/workflows/ci.yml` | New | pytest CI workflow |
| `poc_windows_patch_iocp.py` | Removed | Archived |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Package restructure breaks imports | Medium | Keep re-exports; test against examples |
| wxPython lacks 3.14 wheels | High | Pin known-working Python; document |
| Mock tests miss real GUI issues | Medium | Manual smoke test on GUI-capable runner |

## Rollback Plan

Phase revert: Phase 1 — restore imports and undo type hints (safe). Phase 2 — restore flat file, delete package dir. Phase 3 — revert loop_factory, restore PoC. Full rollback: `git revert`.

## Dependencies

- wxPython >=4.2.5 (must support Python 3.14)
- pytest 9.1+, pytest-asyncio, pytest-cov (dev)
- Python 3.12+ runtime

## Decision Records

| Decision | Value | Rationale |
|----------|-------|-----------|
| Target Python | >=3.12 | Matches pyproject.toml; enables modern features |
| Package layout | `src/wxasync/` package | Resolves flat-file vs package ambiguity |
| Testing | pytest + pytest-asyncio + pytest-cov | Industry standard for async Python |
| CI | GitHub Actions | No existing CI; de facto standard |
| Build | uv_build only | setup.py removed; uv_build is modern |
| Type hints | All public API | Maintainability and IDE support |

## Success Criteria

- [ ] `uv run pytest --cov=src` passes with >=80% coverage
- [ ] `uv build` succeeds
- [ ] `from wxasync import WxAsyncApp, AsyncBind, StartCoroutine` works
- [ ] No deprecated asyncio internals remain
- [ ] GitHub Actions CI passes on every PR
