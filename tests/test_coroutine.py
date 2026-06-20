"""
tests/test_coroutine.py — StartCoroutine, OnDestroy, OnTaskCompleted (T8–T10).
"""

from __future__ import annotations

import asyncio
import warnings
from unittest.mock import MagicMock

import pytest

import wx


class TestStartCoroutine:
    """T8: StartCoroutine accepts coroutine and callable; returns asyncio.Task."""

    async def test_accepts_coroutine_object(self, wx_app, make_window) -> None:
        win = make_window()

        async def my_coro():
            return 42

        task = wx_app.StartCoroutine(my_coro(), win)
        assert isinstance(task, asyncio.Task)
        result = await task
        assert result == 42

    async def test_accepts_coroutine_function(self, wx_app, make_window) -> None:
        win = make_window()

        async def my_coro():
            return 99

        task = wx_app.StartCoroutine(my_coro, win)
        assert isinstance(task, asyncio.Task)
        result = await task
        assert result == 99

    def test_rejects_non_window_object(self, wx_app) -> None:
        async def my_coro():
            pass

        coro = my_coro()
        try:
            with pytest.raises(Exception, match="obj must be a wx.Window"):
                wx_app.StartCoroutine(coro, "not_a_window")
        finally:
            coro.close()

    async def test_task_tracked_in_running_tasks(self, wx_app, make_window) -> None:
        win = make_window()

        async def long_coro():
            await asyncio.sleep(999)

        task = wx_app.StartCoroutine(long_coro(), win)
        assert task in wx_app.RunningTasks[win]
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


class TestOnDestroy:
    """T9: OnDestroy cancels each non-done task; respects warn_on_cancel_callback."""

    async def test_cancels_running_tasks(self, wx_app, make_window) -> None:
        win = make_window()

        async def long_coro():
            await asyncio.sleep(999)

        task1 = wx_app.StartCoroutine(long_coro(), win)
        task2 = wx_app.StartCoroutine(long_coro(), win)

        # Simulate destroy event
        mock_event = MagicMock()
        wx_app.OnDestroy(mock_event, win)

        # Await tasks to let cancellation propagate
        with pytest.raises(asyncio.CancelledError):
            await task1
        with pytest.raises(asyncio.CancelledError):
            await task2

        assert task1.cancelled()
        assert task2.cancelled()
        # BoundObjects entry removed
        assert win not in wx_app.BoundObjects

    async def test_warn_on_cancel_callback(self) -> None:
        from aiowx._core import WxAsyncApp

        app = WxAsyncApp(warn_on_cancel_callback=True)
        win = wx.Window()

        async def long_coro():
            await asyncio.sleep(999)

        task = app.StartCoroutine(long_coro(), win)

        mock_event = MagicMock()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            app.OnDestroy(mock_event, win)
            assert len(w) == 1
            assert "cancelling callback" in str(w[0].message)

        # Clean up
        with pytest.raises(asyncio.CancelledError):
            await task

    async def test_no_warn_when_disabled(self, wx_app, make_window) -> None:
        win = make_window()

        async def long_coro():
            await asyncio.sleep(999)

        task = wx_app.StartCoroutine(long_coro(), win)

        mock_event = MagicMock()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            wx_app.OnDestroy(mock_event, win)
            assert len(w) == 0

        with pytest.raises(asyncio.CancelledError):
            await task

    async def test_removes_running_tasks_entry(self, wx_app, make_window) -> None:
        win = make_window()

        async def long_coro():
            await asyncio.sleep(999)

        task = wx_app.StartCoroutine(long_coro(), win)

        mock_event = MagicMock()
        wx_app.OnDestroy(mock_event, win)

        # Leak B regression: empty set must not be left behind
        assert win not in wx_app.RunningTasks
        assert win not in wx_app.BoundObjects

        with pytest.raises(asyncio.CancelledError):
            await task


class TestOnTaskCompleted:
    """T10: OnTaskCompleted silences CancelledError and warns other exceptions."""

    async def test_silences_cancelled_error(self, wx_app, make_window) -> None:
        win = make_window()

        async def cancel_me():
            await asyncio.sleep(999)

        task = wx_app.StartCoroutine(cancel_me(), win)
        task.cancel()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            # Await the task to let cancellation complete
            with pytest.raises(asyncio.CancelledError):
                await task

        assert task.cancelled()
        # Task removed from RunningTasks
        assert task not in wx_app.RunningTasks[win]
        # CancelledError is silenced without warning
        assert len(w) == 0

    async def test_exception_removes_task_and_warns(self, wx_app, make_window) -> None:
        win = make_window()

        async def raise_value_error():
            raise ValueError("boom")

        task = wx_app.StartCoroutine(raise_value_error(), win)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            # Await the task to let it complete and fire the done callback
            with pytest.raises(ValueError, match="boom"):
                await task

        assert task.done()
        # Leak A regression: task removed from RunningTasks even on exception
        assert win not in wx_app.RunningTasks
        # Non-CancelledError is surfaced via warning
        assert len(w) == 1
        assert "ValueError" in str(w[0].message)
        assert "boom" in str(w[0].message)

    async def test_destroy_iteration_does_not_raise_runtime_error(
        self, wx_app, make_window, monkeypatch
    ) -> None:
        win = make_window()

        async def long_coro():
            await asyncio.sleep(999)

        async def immediate_coro():
            return 42

        task1 = wx_app.StartCoroutine(long_coro(), win)
        task2 = wx_app.StartCoroutine(immediate_coro(), win)
        # Let task2 complete and fire its done callback, then re-insert it
        # to simulate a callback that fires mid-iteration during OnDestroy.
        await task2
        wx_app.RunningTasks[win].add(task2)

        original_cancel = task1.cancel

        def cancel_with_concurrent_completion():
            wx_app.OnTaskCompleted(task2)
            return original_cancel()

        monkeypatch.setattr(task1, "cancel", cancel_with_concurrent_completion)

        mock_event = MagicMock()
        # Race regression: must not raise RuntimeError from live-set mutation
        wx_app.OnDestroy(mock_event, win)

        assert win not in wx_app.RunningTasks
        assert win not in wx_app.BoundObjects
