"""Application core for aiowx — bridges wxPython GUI event loop with asyncio.

Provides ``WxAsyncApp`` plus module-level ``AsyncBind`` and ``StartCoroutine``
wrappers. Dialog helpers live in ``aiowx._dialog`` so this module stays focused
on application lifecycle and task tracking.
"""

from __future__ import annotations

import asyncio
import inspect
import platform
import warnings
from asyncio import CancelledError
from collections import defaultdict
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

import wx
import wx.html

IS_MAC: bool = platform.system() == "Darwin"

type CoroutineFn = Callable[..., Coroutine[Any, Any, Any]]


@dataclass(frozen=True)
class _TrackedTask:
    """Lifecycle handle that connects an asyncio.Task to its wx owner window."""

    task: asyncio.Task[Any]
    obj: wx.Window


class WxAsyncApp(wx.App):
    """Wx.App subclass that runs an async main loop alongside wxPython's event loop.

    Attributes:
        BoundObjects: Tracks registered event bindings per window for cleanup on destroy.
        RunningTasks: Tracks active asyncio tasks per window for cancellation on destroy.
        _task_index: Reverse mapping from asyncio.Task to _TrackedTask for O(1) completion lookup.
        exiting: Flag to signal MainLoop to stop.
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
        self.RunningTasks: defaultdict[wx.Window, set[_TrackedTask]] = defaultdict(set)
        self._task_index: dict[asyncio.Task[Any], _TrackedTask] = {}
        self.exiting: bool = False
        self.sleep_duration: float = sleep_duration
        self.warn_on_cancel_callback: bool = warn_on_cancel_callback
        super().__init__(**kwargs)
        self.SetExitOnFrameDelete(True)

    async def MainLoop(self) -> None:  # type: ignore
        """Run the wxPython event loop interleaved with asyncio.

        Polls wx.GUIEventLoop for pending events on non-Mac platforms.
        On Mac, uses DispatchTimeout(0) because Pending() always returns True.
        Exits when ExitMainLoop() sets the exiting flag.

        Unlike the original aiowx implementation, this loop processes
        **all** pending wx events in a batch before yielding to asyncio,
        instead of yielding after every single event.  This eliminates
        the micro-latency that the per-event yield introduced during
        rapid input sequences (keyboard repeat, mouse scrolling).
        """
        event_loop = wx.GUIEventLoop()
        with wx.EventLoopActivator(event_loop):
            while not self.exiting:
                processed = False
                if IS_MAC:
                    event_loop.DispatchTimeout(0)
                    processed = True
                else:
                    while event_loop.Pending():
                        event_loop.Dispatch()
                        processed = True
                # Yield to asyncio once after processing all pending wx
                # events.  When no events were processed, sleep the full
                # polling interval to avoid busy-waiting.
                if processed:
                    await asyncio.sleep(0)
                else:
                    await asyncio.sleep(self.sleep_duration)
                    event_loop.ProcessIdle()
                self.ProcessPendingEvents()
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
            TypeError: If object is not a wx.Window or async_callback is not a coroutine.
        """
        if not isinstance(object, wx.Window):
            raise TypeError("object must be a wx.Window")
        if not inspect.iscoroutinefunction(async_callback):
            raise TypeError("async_callback is not a coroutine function")
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
            TypeError: If obj is not a wx.Window.
        """
        if not isinstance(obj, wx.Window):
            raise TypeError("obj must be a wx.Window")
        if inspect.iscoroutinefunction(coroutine):
            coroutine = coroutine()
        if obj not in self.BoundObjects:
            self.BoundObjects[obj] = defaultdict(list)
            obj.Bind(
                wx.EVT_WINDOW_DESTROY, lambda event: self.OnDestroy(event, obj), obj
            )
        task: asyncio.Task[Any] = asyncio.create_task(coroutine)  # type: ignore
        tracked = _TrackedTask(task=task, obj=obj)
        task.add_done_callback(self.OnTaskCompleted)
        self.RunningTasks[obj].add(tracked)
        self._task_index[task] = tracked
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
            tracked = self._task_index.pop(task, None)
            if tracked is not None:
                obj = tracked.obj
                tracked_set = self.RunningTasks.get(obj)
                if tracked_set is not None:
                    tracked_set.discard(tracked)
                    if not tracked_set:
                        del self.RunningTasks[obj]

    def OnDestroy(self, event: wx.WindowDestroyEvent, obj: wx.Window) -> None:
        """Cancel all running tasks for a window and clean up its bindings."""
        tracked_tasks = list(self.RunningTasks.get(obj, set()))
        for tracked in tracked_tasks:
            self._task_index.pop(tracked.task, None)
            if not tracked.task.done():
                tracked.task.cancel()
                if self.warn_on_cancel_callback:
                    warnings.warn(
                        "cancelling callback " + str(obj) + " " + str(tracked.task),
                        stacklevel=2,
                    )
        self.BoundObjects.pop(obj, None)
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
        RuntimeError: If no WxAsyncApp instance exists.
    """
    app = wx.App.Get()
    if not isinstance(app, WxAsyncApp):
        raise RuntimeError("Create a 'WxAsyncApp' first")
    app.AsyncBind(event, async_callback, object, source=source, id=id, id2=id2)


def StartCoroutine(
    coroutine: Coroutine[Any, Any, Any] | CoroutineFn, obj: wx.Window
) -> asyncio.Task[Any]:
    """Module-level convenience wrapper for WxAsyncApp.StartCoroutine.

    Raises:
        RuntimeError: If no WxAsyncApp instance exists.
    """
    app = wx.App.Get()
    if not isinstance(app, WxAsyncApp):
        raise RuntimeError("Create a 'WxAsyncApp' first")
    return app.StartCoroutine(coroutine, obj)
