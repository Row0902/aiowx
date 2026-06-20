# Tasks: Python 3.14 Native Compatibility — Phase 1 (Foundation)

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | ~700 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: consolidation + fixes + type hints (~300 lines), PR 2: tests + CI (~400 lines) |
| Delivery strategy | ask-always |
| Chain strategy | feature-branch-chain |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|---|---|---|---|
| 1 | Package consolidation, import fixes, modern super(), type hints, delete flat file + setup.py | PR 1 | Base: tracker branch; verify: `uv build` + import smoke |
| 2 | Test suite + CI workflow | PR 2 | Base: PR 1 branch; verify: `uv run pytest --cov=src` >=80% |

## Phase 1: Package Consolidation & Import Fixes

- [x] 1.1 Create `src/wxasync/_core.py`: move body of `src/wxasync.py`; add `from __future__ import annotations`; add type imports (`collections.abc`, `typing`, `TypeAlias`)
- [x] 1.2 Fix imports in `_core.py`: replace `iscoroutinefunction` → `inspect.iscoroutinefunction` (both uses); replace `asyncio.locks.Event` + dead `get_event_loop` → `asyncio.Event`; remove duplicate `import asyncio`
- [x] 1.3 Replace `super(WxAsyncApp, self).__init__(**kwargs)` → `super().__init__(**kwargs)` in `_core.py`
- [x] 1.4 Rewrite `__init__.py`: re-export `AsyncBind, AsyncShowDialog, AsyncShowDialogModal, StartCoroutine, WxAsyncApp` from `_core`; declare `__all__`; remove `hello()` placeholder
- [x] 1.5 Annotate all public API per design §4: `__init__`, `MainLoop`, `ExitMainLoop`, `AsyncBind`, `StartCoroutine`, `OnTaskCompleted`, dialog helpers; define `CoroutineFn: TypeAlias`
- [x] 1.6 Delete `src/wxasync.py` and `setup.py`
- [x] 1.7 Verify: `py.typed` marker exists; `uv build` succeeds; `uv run python -c "from wxasync import WxAsyncApp, AsyncBind, StartCoroutine"` passes

## Phase 2: Test Suite (TDD)

- [x] 2.1 Create `tests/conftest.py`: `wx_stub` autouse session fixture — `MagicMock` `wx` module in `sys.modules` (App, Window, GUIEventLoop, Dialog, constants, dialog types); monkeypatch `asyncio.sleep` to bounded no-op; patch `platform.system` per-test for macOS branch
- [x] 2.2 RED `tests/test_app.py`: T1 init attrs + `SetExitOnFrameDelete`, T2 non-Mac `MainLoop`, T3 Mac `DispatchTimeout`, T4 `ExitMainLoop`
- [x] 2.3 GREEN `tests/test_app.py`: pass T1–T4
- [x] 2.4 RED `tests/test_bind.py`: T5 non-`wx.Window`/non-coroutine reject, T6 `object.Bind`+`BoundObjects`, T7 idempotent destroy
- [x] 2.5 GREEN `tests/test_bind.py`: pass T5–T7
- [x] 2.6 RED `tests/test_coroutine.py`: T8 coroutine/callable+Task, T9 `OnDestroy` cancel+warn, T10 `CancelledError` silence+propagate
- [x] 2.7 GREEN `tests/test_coroutine.py`: pass T8–T10
- [x] 2.8 RED `tests/test_dialogs.py`: T11 modless-incompat raise+happy path, T12 OS-dialog→executor+frame disable
- [x] 2.9 GREEN `tests/test_dialogs.py`: pass T11–T12
- [x] 2.10 Verify: `uv run pytest --cov=src` >=80%

## Phase 3: CI & Final Verification

- [x] 3.1 Create `.github/workflows/ci.yml`: `on: [push, pull_request]`, ubuntu-latest, `checkout@v4`, `setup-uv@v4` + cache enable, `uv python install 3.12`, `uv sync --all-extras --dev`, `uv run ruff check`, `uv run pytest --cov=src --cov-report=xml`, `upload-artifact@v4`
- [x] 3.2 Locally verify: `uv run ruff check` zero errors
- [x] 3.3 Locally verify: `uv build` produces valid wheel; `uv run pytest --cov=src` passes
- [x] 3.4 Smoke: `uv run python -c "from wxasync import WxAsyncApp, AsyncBind, StartCoroutine"` succeeds
