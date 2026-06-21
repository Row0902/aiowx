"""Core module for aiowx — bridges wxPython GUI event loop with asyncio.

Provides WxAsyncApp, AsyncBind, StartCoroutine, and async dialog helpers
to run coroutines alongside wxPython's event-driven main loop.
"""

from __future__ import annotations

import asyncio
import inspect
import platform
import warnings
from asyncio import CancelledError
from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import Any

import wx
import wx.html

IS_MAC: bool = platform.system() == "Darwin"

type CoroutineFn = Callable[..., Coroutine[Any, Any, Any]]


class WxAsyncApp(wx.App):
    """Wx.App subclass that runs an async main loop alongside wxPython's event loop.

    Attributes:
        BoundObjects: Tracks registered event bindings per window for cleanup on destroy.
        RunningTasks: Tracks active asyncio tasks per window for cancellation on destroy.
        exiting: Flag to signal MainLoop to stop.
        ui_idle: Tracks whether idle processing is pending.
        sleep_duration: Sleep interval between wx event processing cycles.
        warn_on_cancel_callback: If True, emit warning when canceling a callback on destroy.
    """

    def __init__(
        self,
        warn_on_cancel_callback: bool = False,
        sleep_duration: float = 0.02,
        **kwargs: Any,
    ) -> None:
        self.BoundObjects: dict[wx.Window, dict[int, list[Callable[..., Any]]]] = {}
        self.RunningTasks: defaultdict[wx.Window, set[asyncio.Task[Any]]] = defaultdict(
            set
        )
        self.exiting: bool = False
        self.ui_idle: bool = True
        self.sleep_duration: float = sleep_duration
        self.warn_on_cancel_callback: bool = warn_on_cancel_callback
        super().__init__(**kwargs)
        self.SetExitOnFrameDelete(True)

    async def MainLoop(self) -> None:  # type: ignore
        """Run the wxPython event loop interleaved with asyncio.

        Polls wx.GUIEventLoop for pending events on non-Mac platforms.
        On Mac, uses DispatchTimeout(0) because Pending() always returns True.
        Exits when ExitMainLoop() sets the exiting flag.
        """
        event_loop = wx.GUIEventLoop()
        with wx.EventLoopActivator(event_loop):
            while not self.exiting:
                if IS_MAC:
                    event_loop.DispatchTimeout(0)
                    self.ui_idle = False
                else:
                    while event_loop.Pending():
                        event_loop.Dispatch()
                        await asyncio.sleep(0)
                        self.ui_idle = False
                await asyncio.sleep(self.sleep_duration)
                self.ProcessPendingEvents()
                if not self.ui_idle:
                    event_loop.ProcessIdle()
                    self.ui_idle = True
            self.exiting = False
        self.OnExit()

    def ExitMainLoop(self) -> None:
        """Signal the async MainLoop to exit on its next iteration."""
        self.exiting = True

    def AsyncBind(
        self,
        event_binder: wx.PyEventBinder,
        async_callback: CoroutineFn,
        object: wx.Window,
        source: wx.EvtHandler | None = None,
        id: int = wx.ID_ANY,
        id2: int = wx.ID_ANY,
    ) -> None:
        """Bind a coroutine to a wx Event.

        When the bound wx object is destroyed, any running coroutine is
        cancelled automatically via OnDestroy.

        Raises:
            Exception: If object is not a wx.Window or async_callback is not a coroutine.
        """
        if not isinstance(object, wx.Window):
            raise Exception("object must be a wx.Window")
        if not inspect.iscoroutinefunction(async_callback):
            raise Exception("async_callback is not a coroutine function")
        if object not in self.BoundObjects:
            self.BoundObjects[object] = defaultdict(list)
            object.Bind(
                wx.EVT_WINDOW_DESTROY,
                lambda event: self.OnDestroy(event, object),
                object,
            )
        self.BoundObjects[object][event_binder.typeId].append(async_callback)
        object.Bind(
            event_binder,
            lambda event: StartCoroutine(async_callback(event.Clone()), object),
            source=source,
            id=id,
            id2=id2,
        )

    def StartCoroutine(
        self, coroutine: Coroutine[Any, Any, Any] | CoroutineFn, obj: wx.Window
    ) -> asyncio.Task[Any]:
        """Start and attach a coroutine to a wx object.

        When the object is destroyed, the coroutine is cancelled automatically.
        Returns the asyncio.Task for the running coroutine.

        Raises:
            Exception: If obj is not a wx.Window.
        """
        if not isinstance(obj, wx.Window):
            raise Exception("obj must be a wx.Window")
        if inspect.iscoroutinefunction(coroutine):
            coroutine = coroutine()
        if obj not in self.BoundObjects:
            self.BoundObjects[obj] = defaultdict(list)
            obj.Bind(
                wx.EVT_WINDOW_DESTROY, lambda event: self.OnDestroy(event, obj), obj
            )
        task: asyncio.Task[Any] = asyncio.create_task(coroutine)  # type: ignore
        setattr(task, "obj", obj)
        task.add_done_callback(self.OnTaskCompleted)
        self.RunningTasks[obj].add(task)
        return task

    def OnTaskCompleted(self, task: asyncio.Task[Any]) -> None:
        """Handle completion of a tracked coroutine task.

        Calls task.result() to surface any exception from the coroutine.
        CancelledError is silenced because it's expected when a window is destroyed.
        Other exceptions are surfaced via warnings.warn so cleanup still runs.
        """
        try:
            task.result()
        except CancelledError:
            pass
        except Exception as exc:
            warnings.warn(
                f"Exception in async callback: {exc!r}", RuntimeWarning, stacklevel=2
            )
        finally:
            obj = getattr(task, "obj", None)
            if obj is not None:
                tasks = self.RunningTasks.get(obj)
                if tasks is not None:
                    tasks.discard(task)
                    if not tasks:
                        del self.RunningTasks[obj]

    def OnDestroy(self, event: wx.WindowDestroyEvent, obj: wx.Window) -> None:
        """Cancel all running tasks for a window and clean up its bindings."""
        tasks = list(self.RunningTasks.get(obj, set()))
        for task in tasks:
            if not task.done():
                task.cancel()
                if self.warn_on_cancel_callback:
                    warnings.warn(
                        "cancelling callback" + str(obj) + str(task),
                        stacklevel=2,
                    )
        del self.BoundObjects[obj]
        if obj in self.RunningTasks:
            del self.RunningTasks[obj]


def AsyncBind(
    event: wx.PyEventBinder,
    async_callback: CoroutineFn,
    object: wx.Window,
    source: wx.EvtHandler | None = None,
    id: int = wx.ID_ANY,
    id2: int = wx.ID_ANY,
) -> None:
    """Module-level convenience wrapper for WxAsyncApp.AsyncBind.

    Raises:
        Exception: If no WxAsyncApp instance exists.
    """
    app = wx.App.Get()
    if not isinstance(app, WxAsyncApp):
        raise Exception("Create a 'WxAsyncApp' first")
    app.AsyncBind(event, async_callback, object, source=source, id=id, id2=id2)


def StartCoroutine(
    coroutine: Coroutine[Any, Any, Any] | CoroutineFn, obj: wx.Window
) -> asyncio.Task[Any]:
    """Module-level convenience wrapper for WxAsyncApp.StartCoroutine.

    Raises:
        Exception: If no WxAsyncApp instance exists.
    """
    app = wx.App.Get()
    if not isinstance(app, WxAsyncApp):
        raise Exception("Create a 'WxAsyncApp' first")
    return app.StartCoroutine(coroutine, obj)


async def ShowModalInExecutor(dialog: wx.Dialog) -> int:
    """Show a modal OS dialog on the wx main thread and await its return code.

    Schedules ``dialog.ShowModal()`` via ``wx.CallAfter`` so the GUI call always
    runs on the wx main thread. The result is delivered through an
    ``asyncio.Future``. The asyncio event loop blocks while the modal dialog
    runs its nested wx event loop; this is expected single-threaded modal
    behavior.

    Required for dialogs like wx.FileDialog, wx.DirDialog, etc.
    """
    loop = asyncio.get_running_loop()
    future: asyncio.Future[int] = loop.create_future()

    def on_main_thread() -> None:
        try:
            result = dialog.ShowModal()
        except Exception as exc:
            future.set_exception(exc)
        else:
            future.set_result(result)

    wx.CallAfter(on_main_thread)
    return await future


async def AsyncShowDialog(dialog: wx.Dialog) -> int:
    """Show a dialog in async modless mode and wait for its result.

    Raises:
        Exception: If the dialog type does not support modless display;
                   use AsyncShowDialogModal for those.
    """
    if not isinstance(
        dialog,
        (
            wx.FileDialog,
            wx.DirDialog,
            wx.FontDialog,
            wx.ColourDialog,
            wx.MessageDialog,
        ),
    ):
        closed = asyncio.Event()

        def end_dialog(return_code: int) -> None:
            dialog.SetReturnCode(return_code)
            dialog.Hide()
            closed.set()

        async def on_button(event: wx.CommandEvent) -> None:
            id = event.GetId()
            if id == dialog.GetAffirmativeId():
                if dialog.Validate() and dialog.TransferDataFromWindow():
                    end_dialog(id)
            elif id == wx.ID_APPLY:
                if dialog.Validate():
                    dialog.TransferDataFromWindow()
            elif id == dialog.GetEscapeId() or (
                id == wx.ID_CANCEL and dialog.GetEscapeId() == wx.ID_ANY
            ):
                end_dialog(wx.ID_CANCEL)
            else:
                event.Skip()

        async def on_close(event: wx.CloseEvent) -> None:
            closed.set()
            dialog.Hide()

        AsyncBind(wx.EVT_CLOSE, on_close, dialog)
        AsyncBind(wx.EVT_BUTTON, on_button, dialog)
        dialog.Show()
        await closed.wait()
        return dialog.GetReturnCode()

    raise Exception(
        "This type of dialog cannot be shown modless, please use 'AsyncShowDialogModal'"
    )


async def AsyncShowDialogModal(dialog: wx.Dialog) -> int:
    """Show a dialog in modal mode.

    OS-level dialogs (FileDialog, DirDialog, etc.) are run via ShowModalInExecutor.
    Other dialogs disable parent frames, show modless, and re-enable on close.
    """
    if isinstance(
        dialog,
        (
            wx.html.HtmlHelpDialog,
            wx.FileDialog,
            wx.DirDialog,
            wx.FontDialog,
            wx.ColourDialog,
            wx.MessageDialog,
        ),
    ):
        return await ShowModalInExecutor(dialog)

    frames = set(wx.GetTopLevelWindows()) - {dialog}  # type: ignore
    states = {frame: frame.IsEnabled() for frame in frames}
    try:
        for frame in frames:
            frame.Disable()
        return await AsyncShowDialog(dialog)
    finally:
        for frame in frames:
            frame.Enable(states[frame])
        parent = dialog.GetParent()
        if parent:
            parent.SetFocus()
