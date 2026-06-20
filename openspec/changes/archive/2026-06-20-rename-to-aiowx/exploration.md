## Exploration: Rename wxasync → aiowx

### Current State

The project is a Python library (`wxasync`) at version 0.1.0 that bridges wxPython's GUI event loop with asyncio. It was forked from an original open-source project and has undergone significant rework: package consolidation (`src/wxasync/` with `__init__.py` + `_core.py`), full test suite, CI, and modern `pyproject.toml`-based build via `uv_build`. The project has published to Test PyPI as `wxasync==0.2`.

The name `wxasync` is generic and conflicts/disambiguates poorly against the original upstream project. The proposed rename `aiowx` is more brandable, shorter, and follows the `aio*` naming convention common in the Python async ecosystem.

### Affected Areas

#### Source package (directory rename)
| File | Why Affected | Change |
|------|-------------|--------|
| `src/wxasync/` → `src/aiowx/` | Package directory rename | Git mv |
| `src/wxasync/__init__.py` | Internal import path | `from wxasync._core` → `from aiowx._core` |
| `src/wxasync/_core.py` | Docstring mentions "wxasync" | `Core module for wxasync` → `Core module for aiowx` |
| `src/wxasync/py.typed` | Moves with directory | Handled by directory rename |

#### Config files
| File | Why Affected | Change |
|------|-------------|--------|
| `pyproject.toml` | Package name | `name = "wxasync"` → `name = "aiowx"` |
| `uv.lock` | Contains package name in metadata | Regenerate via `uv lock` |
| `.atl/skill-registry.md` | Title mentions project name | `# Skill Registry — wxasync` → `aiowx` |

#### Tests (import path changes)
| File | Lines Affected | Change |
|------|---------------|--------|
| `tests/conftest.py` | 5 lines (5, 184, 209, 212, 222) | `wxasync._core` → `aiowx._core` |
| `tests/test_app.py` | 4 lines (23, 30, 55, 96) | `from wxasync._core` → `from aiowx._core` |
| `tests/test_bind.py` | 1 line (94) | `from wxasync._core` → `from aiowx._core` |
| `tests/test_coroutine.py` | 1 line (93) | `from wxasync._core` → `from aiowx._core` |
| `tests/test_dialogs.py` | 3 lines (14, 61, 225) | `wxasync._core` → `aiowx._core` |

#### Examples
| File | Lines Affected | Change |
|------|---------------|--------|
| `src/examples/simple.py` | 1 line (2) | `from wxasync import` → `from aiowx import` |
| `src/examples/slider_demo.py` | 1 line (2) | Same |
| `src/examples/server.py` | 1 line (3) | Same |
| `src/examples/dialog.py` | 1 line (2) | Same |
| `src/examples/more_dialogs.py` | 1 line (2) | Same |

#### Legacy files (excluded from ruff but still present)
| File | Lines Affected | Change |
|------|---------------|--------|
| `test/test_perfs.py` | 1 line (1) | `from wxasync import` → `from aiowx import` |
| `test/poc_windows_patch_iocp.py` | 1 line (9) | Same |

#### Documentation
| File | Lines Affected | Change |
|------|---------------|--------|
| `AGENTS.md` | 3 lines (1, 42, 60) | Title, naming convention example, import path example |
| `README.md` | ~8 lines | Title, description, install command, code examples, performance table |
| `notes.txt` | 1 line (10) | `pip install wxasync` → `pip install aiowx` |

#### SDD artifacts (openspec/)
| File | Lines Affected | Change |
|------|---------------|--------|
| `openspec/specs/foundation/spec.md` | 3 lines (13, 51, 56) | `from wxasync import` → `from aiowx import` in spec scenarios |

#### Archive artifacts (read-only, no change needed)
| File | Reference Count | Decision |
|------|----------------|----------|
| `openspec/changes/archive/*` | ~80+ references | **Leave as-is** — these are historical audit records. They document what *was* built |
| `.atl/skill-registry.md` | 1 line | Update |

#### Not affected
- `.github/workflows/ci.yml` — uses `uv run pytest --cov=src`, no `wxasync` string
- `.github/workflows/python-publish.yml` — no `wxasync` reference
- `openspec/config.yaml` — mentions `WxAsyncApp` (class name, not package name)

### Estimated Changed Lines

| Category | Files | Lines Changed |
|----------|-------|-------------|
| Source package | 3 | ~4 |
| Config | 3 | ~3 |
| Tests | 5 | ~14 |
| Examples | 5 | ~5 |
| Legacy tests | 2 | ~2 |
| Documentation | 3 | ~12 |
| OpenSpec spec | 1 | ~3 |
| **Total** | **~22** | **~43** |

**Review Budget Risk**: **Low** — ~43 lines well within the 400-line budget. Fits in a single PR.

### Approaches

1. **Clean rename, no compat shim** — Rename directory, update all imports/docs, regenerate lockfile. Publish `aiowx` as the new package name. Version 0.2.0.
   - Pros: Cleanest break, lowest ongoing maintenance, zero compat complexity
   - Cons: Existing `pip install wxasync` users break; `from wxasync import` will fail
   - Effort: **Low** (~43 lines across 22 files, all mechanical)

2. **Rename + compat shim on PyPI** — Same as above, but also publish a stub `wxasync` package (v0.2.0) that re-exports everything from `aiowx` and prints a deprecation warning. The stub would be: `from aiowx import *` + `warnings.warn("use aiowx instead")`.
   - Pros: Graceful migration for existing users; `pip install wxasync` still works
   - Cons: Extra maintenance burden (two packages to publish), deprecation cycle management, needs PyPI project ownership for both names
   - Effort: **Medium** (setup separate stub project OR include as optional subpackage)

3. **Complete rename + GitHub rename** — Same as approach 1, but also rename the GitHub repository from `wxasync` to `aiowx`.
   - Pros: Full consistency everywhere; clean brand identity
   - Cons: GitHub redirects handle old URLs, but local clones need remote URL update; requires org-level coordination if under an org
   - Effort: **Low-Medium** (repository rename is a GitHub settings toggle + local git remote update)

### Recommendation

**Approach 1 (clean rename, no compat shim)** is the right call for v0.1.0. This project has been completely rewritten from the original fork — the user base is effectively zero, and there is no published PyPI release with real consumers. A compat shim adds deployment complexity with zero measurable benefit. If users request backward compat later, the shim can be added as a separate feather-light package at that point.

Also pair this with **Approach 3 (GitHub rename)** since the repo is under `/wxasync` and the rename should be consistent.

### Risks

- **uv.lock regeneration**: The lockfile contains `name = "wxasync"` in the `[[package]]` table for this package itself. After changing `pyproject.toml`, `uv lock` will regenerate this entry with the new name. No risk, but must be done explicitly.
- **PyPI project name squatting**: The name `aiowx` must be available on PyPI. Check before committing to the rename. If taken, need alternative names.
- **Missing reference in an archive spec**: Archive artifacts are NOT updated — they correctly document history. But any future phase that references the old package name in source-of-truth specs (not archive) also needs updating. Our phase 2/3 deferred work items reference `wxasync` implicitly through the package structure.
- **Class names not renamed**: `WxAsyncApp`, `AsyncBind`, `StartCoroutine` etc. remain as-is. The rename is about the PACKAGE name only, not the public API symbols. This is intentional — `WxAsyncApp` is still a reasonable class name for "wxPython Async App". The package name `aiowx` reflects what it is: "async IO for wxPython".

### Ready for Proposal
Yes — the scope is well-understood, effort is ~43 lines across 22 files, review budget risk is Low. Proceed to sdd-propose.
