"""
tests/test_bind.py — AsyncBind validation, binding, idempotency (T5–T7).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


class TestAsyncBindValidation:
    """T5: AsyncBind rejects non-wx.Window objects and non-coroutine callbacks."""

    def test_rejects_non_window_object(self, wx_app) -> None:
        async def dummy(event):
            pass

        with pytest.raises(Exception, match="object must be a wx.Window"):
            wx_app.AsyncBind(MagicMock(typeId=99), dummy, "not_a_window")

    def test_rejects_non_coroutine_callback(self, wx_app, make_window) -> None:
        def sync_callback(event):
            pass

        win = make_window()
        with pytest.raises(Exception, match="not a coroutine function"):
            wx_app.AsyncBind(MagicMock(typeId=99), sync_callback, win)


class TestAsyncBindBinding:
    """T6: AsyncBind calls object.Bind and records in BoundObjects."""

    def test_binds_event_and_records(self, wx_app, make_window) -> None:
        win = make_window()
        win.Bind = MagicMock()

        async def my_handler(event):
            pass

        binder = MagicMock(typeId=42)
        wx_app.AsyncBind(binder, my_handler, win)

        # object.Bind was called (at least for EVT_WINDOW_DESTROY + user event)
        assert win.Bind.call_count >= 1
        # BoundObjects records the handler under the typeId
        assert 42 in wx_app.BoundObjects[win]
        assert my_handler in wx_app.BoundObjects[win][42]

    def test_multiple_handlers_same_event(self, wx_app, make_window) -> None:
        win = make_window()
        win.Bind = MagicMock()

        async def handler_a(event):
            pass

        async def handler_b(event):
            pass

        binder = MagicMock(typeId=42)
        wx_app.AsyncBind(binder, handler_a, win)
        wx_app.AsyncBind(binder, handler_b, win)

        assert len(wx_app.BoundObjects[win][42]) == 2
        assert handler_a in wx_app.BoundObjects[win][42]
        assert handler_b in wx_app.BoundObjects[win][42]


class TestAsyncBindIdempotency:
    """T7: EVT_WINDOW_DESTROY bound exactly once per window."""

    def test_destroy_bound_once(self, wx_app, make_window) -> None:
        win = make_window()
        bind_calls = []

        def tracking_bind(*args, **kwargs):
            bind_calls.append(args)

        win.Bind = tracking_bind

        async def handler_a(event):
            pass

        async def handler_b(event):
            pass

        binder1 = MagicMock(typeId=10)
        binder2 = MagicMock(typeId=20)

        wx_app.AsyncBind(binder1, handler_a, win)
        wx_app.AsyncBind(binder2, handler_b, win)

        # Count how many times EVT_WINDOW_DESTROY was bound
        import wx

        destroy_binds = [c for c in bind_calls if c[0] is wx.EVT_WINDOW_DESTROY]
        assert len(destroy_binds) == 1, (
            "EVT_WINDOW_DESTROY should be bound exactly once per window"
        )
