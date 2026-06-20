## Exploration: ShowModalInExecutor Thread-Safety (Issue #5)

### Current State

`ShowModalInExecutor` at `src/wxasync/_core.py:216-222` runs `dialog.ShowModal()` via `loop.run_in_executor(None, dialog.ShowModal)`, dispatching the call to a `ThreadPoolExecutor` worker thread. This violates wxPython's fundamental thread-affinity rule: **wx GUI operations MUST execute on the main thread** (the thread that created the wx.App and owns the wx event loop).

`AsyncShowDialogModal` (line 279-309) dispatches OS-dialog types (`wx.FileDialog`, `wx.DirDialog`, `wx.FontDialog`, `wx.ColourDialog`, `wx.MessageDialog`, `wx.html.HtmlHelpDialog`) to `ShowModalInExecutor`. Regular dialogs follow a different path — they disable top-level frames, delegate to the modless `AsyncShowDialog` (which uses `asyncio.Event` + wx event bindings), and re-enable frames on close.

The `WxAsyncApp.MainLoop` interleaves wx event processing with asyncio by polling `wx.GUIEventLoop.Pending()/Dispatch()` and calling `ProcessPendingEvents()`/`ProcessIdle()` between `await asyncio.sleep(...)` yields. This means any blocking call in the main thread stalls the asyncio event loop.

The current tests in `test_dialogs.py` mock `ShowModal` as a `MagicMock`, which returns immediately without doing any wx work, so the thread-safety violation is never exercised. Tests pass but do not validate correct thread affinity.

`wx.CallAfter` is available (used in legacy `test/test_perfs.py`) and is thread-safe — it posts a function to the wx event queue for execution on the main thread.

### Affected Areas

- `src/wxasync/_core.py:216-222` — `ShowModalInExecutor`: the function that runs `dialog.ShowModal()` in a thread pool, the root cause of the bug
- `src/wxasync/_core.py:279-309` — `AsyncShowDialogModal`: dispatches OS dialogs to `ShowModalInExecutor`; callers expect `dialog.ShowModal()` semantics
- `src/wxasync/_core.py:225-276` — `AsyncShowDialog`: modless event-driven path, reference pattern for correct main-thread behavior
- `src/wxasync/_core.py:55-79` — `WxAsyncApp.MainLoop`: the event loop structure that constrains what's possible (blocking vs non-blocking approaches)
- `tests/test_dialogs.py` — Tests need updating to verify thread-safe behavior, not just mock bypass

### Approaches

1. **wx.CallAfter + asyncio.Future** — Replace `run_in_executor(None, dialog.ShowModal)` with a `wx.CallAfter` + `asyncio.Future` pattern. `wx.CallAfter` queues the `ShowModal` call on the wx main thread (respecting thread affinity). A `Future` signals completion when `ShowModal` returns. The asyncio event loop is blocked during the dialog (like any modal dialog in a single-threaded GUI), but this is expected desktop behavior.
   - **Pros**: Minimal code change (replace ~5 lines), thread-safe, works on all platforms, no new event handling, preserves exact API (returns `int`)
   - **Cons**: Blocks asyncio event loop while dialog is open (background tasks pause); `ShowModal` on the main thread still enters a nested event loop internally, so the dialog IS responsive
   - **Effort**: Low

2. **ShowWindowModal + asyncio.Event** — Use wxPython's built-in `wx.Dialog.ShowWindowModal()` API (available since wxPython 4.x, requires `wxpython>=4.2.5` per project). Shows a non-blocking window-modal dialog and posts `wx.EVT_WINDOW_MODAL_DIALOG_CLOSED` when dismissed. Bind to that event, signal an `asyncio.Event`, and await it. The event loop continues running during the dialog.
   - **Pros**: Non-blocking (event loop runs), thread-safe (all main-thread), clean OS-native behavior on Windows (Vista+) and macOS (sheets), preserves return-code API
   - **Cons**: Platform-dependent — on Linux/GTK behavior may fall back to app-modal or vary; may not be supported for all `wx.FileDialog`/`wx.DirDialog` variants on all platforms; requires testing across platforms; slightly more code (event binding + signaling)
   - **Effort**: Medium

3. **Full modless event-driven for OS dialogs** — Extend the `AsyncShowDialog` modless pattern to handle OS dialogs. Show them with `dialog.Show()` instead of `ShowModal()`, intercept button events and close events, map to return codes. Every dialog type needs its own event-handling logic.
   - **Pros**: Fully async-friendly, most portable (no platform-specific APIs), consistent with existing `AsyncShowDialog` pattern
   - **Cons**: High effort — each OS dialog type (`FileDialog`, `DirDialog`, `FontDialog`, etc.) behaves differently when shown modless and needs individual event-handling; changes dialog lifecycle (dialog not destroyed, just hidden); existing users may rely on `dialog.ShowModal()` semantics; risk of platform-specific event propagation differences
   - **Effort**: High

### Recommendation

**Adopt Approach 1 (wx.CallAfter + asyncio.Future)** as the immediate fix.

Rationale:
- **Minimal risk**: It's a straightforward replacement of the thread-pool call with a main-thread-queued call. The only behavioral change is that the asyncio event loop pauses during the dialog — which is the correct, expected behavior for a modal dialog in a single-threaded GUI framework.
- **Thread safety**: Eliminates the crash vector completely. `wx.CallAfter` is documented as thread-safe and ensures the dialog runs on the wx main thread.
- **API preservation**: The return type (`int`) and function signature don't change. No caller migration needed.
- **Low effort**: ~5 lines changed in one function.

Approach 2 (ShowWindowModal) is viable as a subsequent enhancement for users who need background async tasks to continue during a dialog, but it needs platform verification first and is higher risk as a first fix.

Approach 3 is overkill for a thread-safety fix. It's a larger refactoring that should be a separate change if pursued.

### Risks

- **Event loop blocking**: The asyncio event loop is blocked while `ShowModal` runs on the main thread. For short-lived modal dialogs (file pickers, color pickers, message boxes), this is negligible. For users running background asyncio tasks, this may be a regression from the current (broken) thread-pool behavior. Mitigation: document this as expected modal-dialog behavior; users who need concurrent dialogs can use `AsyncShowDialog` (modless path) for custom dialogs.
- **`wx.CallAfter` execution timing**: On Mac, `DispatchTimeout(0)` + `ProcessPendingEvents()` is the path for CallAfter events, while on other platforms it's `Pending()/Dispatch()`. The function is processed correctly on all platforms, but the timing might differ (next event loop iteration vs immediate). This is acceptable.
- **No test coverage for real wx**: The headless test suite mocks wx completely, so the fix can only be verified by the mock passing the right calls. True thread-safety validation requires a real wxPython display environment (manual testing or e2e CI with display).

### Ready for Proposal

Yes. The fix is well-understood, low-risk, and has a clear implementation path. The orchestrator should tell the user:
- The root cause is confirmed: `run_in_executor` violates wxPython thread affinity
- Recommended fix: replace with `wx.CallAfter` + `asyncio.Future` pattern
- Opens the possibility of a `ShowWindowModal` enhancement later for non-blocking modal dialogs
