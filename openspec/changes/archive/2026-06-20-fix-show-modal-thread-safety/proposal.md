# Proposal: Fix ShowModal Thread-Safety

## Intent

Fix `ShowModalInExecutor` thread-safety violation: `run_in_executor(None, dialog.ShowModal)` dispatches `ShowModal` to a thread-pool worker, violating wxPython's rule that all GUI operations run on the main thread. This causes crashes on macOS and non-deterministic failures on other platforms.

## Scope

### In Scope
- Rewrite `ShowModalInExecutor` in `src/wxasync/_core.py` to use `wx.CallAfter` + `asyncio.Future` pattern
- Update tests in `tests/test_dialogs.py` to verify thread-safe dispatch (no `run_in_executor`)
- Document that the asyncio event loop blocks during modal dialogs (expected behavior)

### Out of Scope
- `ShowWindowModal` enhancement for non-blocking modal dialogs (separate change)
- Full modless refactoring of OS-dialog lifecycle
- Changes to `AsyncShowDialog` (modless path) or `WxAsyncApp.MainLoop`
- Real wx display integration testing

## Capabilities

### New Capabilities
None — this is a behavioral fix within the existing foundation capability.

### Modified Capabilities
- `foundation`: Add thread-safety requirement to `ShowModalInExecutor` — MUST dispatch `ShowModal` on the wx main thread via `wx.CallAfter`; MUST NOT use `run_in_executor`; MUST return the dialog's `ShowModal` return code via `asyncio.Future`.

## Approach

Replace `loop.run_in_executor(None, dialog.ShowModal)` with:
1. `loop.create_future()` to hold the result
2. `wx.CallAfter` queues `result = dialog.ShowModal(); future.set_result(result)` on the wx main thread (thread-safe)
3. `return await future` retrieves the result asynchronously

The asyncio event loop blocks during the dialog, but this is correct modal-dialog behavior in a single-threaded GUI.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/wxasync/_core.py:216-222` | Modified | `ShowModalInExecutor` — replace executor call with wx.CallAfter + Future |
| `tests/test_dialogs.py` | Modified | Update T7 to mock-verify CallAfter dispatch, not run_in_executor |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Event loop blocking during dialog | Medium | Expected modal behavior; document explicitly |
| wx.CallAfter timing differs across platforms | Low | CallAfter is processed correctly on all platforms |
| Test doesn't validate real thread affinity | High | Mock-based only; no real wx display in CI; manual verification needed |

## Rollback Plan

`git revert` the changes to `_core.py` and `test_dialogs.py`. The old `run_in_executor` path is stable (thread-unsafe but functional in headless/CI contexts).

## Dependencies

- None (standard library: `asyncio.Future`, `wx.CallAfter`)

## Success Criteria

- [ ] `uv run pytest` passes all tests
- [ ] `ShowModalInExecutor` no longer calls `run_in_executor` (mock assertion)
- [ ] `wx.CallAfter` is called exactly once during `ShowModalInExecutor`
- [ ] Return value from mocked `ShowModal` propagates correctly through the Future
