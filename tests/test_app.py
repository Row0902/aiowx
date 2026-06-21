"""
tests/test_app.py — WxAsyncApp init, MainLoop, ExitMainLoop (T1–T4).
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch


class TestWxAsyncAppInit:
    """T1: WxAsyncApp.__init__ sets attributes and calls SetExitOnFrameDelete."""

    def test_init_sets_default_attributes(self, wx_app) -> None:
        assert wx_app.exiting is False
        assert wx_app.ui_idle is True
        assert wx_app.sleep_duration == 0.02
        assert wx_app.warn_on_cancel_callback is False
        assert isinstance(wx_app.BoundObjects, dict)
        assert len(wx_app.BoundObjects) == 0

    def test_init_custom_params(self) -> None:
        from aiowx._app import WxAsyncApp

        app = WxAsyncApp(warn_on_cancel_callback=True, sleep_duration=0.05)
        assert app.warn_on_cancel_callback is True
        assert app.sleep_duration == 0.05

    def test_init_calls_set_exit_on_frame_delete(self) -> None:
        from aiowx._app import WxAsyncApp

        spy = MagicMock()
        app = WxAsyncApp.__new__(WxAsyncApp)
        app.SetExitOnFrameDelete = spy
        app.__init__()
        spy.assert_called_once_with(True)


class TestMainLoopNonMac:
    """T2: MainLoop (non-Mac) iterates Pending() → Dispatch(); exits when exiting=True."""

    async def test_mainloop_exits_when_exiting_true(self, wx_app, set_is_mac) -> None:
        set_is_mac(False)
        wx_app.exiting = True
        await wx_app.MainLoop()
        # MainLoop resets exiting to False after the while loop
        assert wx_app.exiting is False

    async def test_mainloop_drains_pending_then_exits(
        self, wx_app, set_is_mac, monkeypatch
    ) -> None:
        """Non-Mac path: Pending() returns True once → Dispatch() called → then exits."""
        set_is_mac(False)

        import wx

        dispatch_spy = MagicMock()
        pending_calls = [True, False]  # First call: True, second: False

        def pending_side_effect():
            if pending_calls:
                return pending_calls.pop(0)
            return False

        # Create a controlled event loop stub
        evtloop = wx.GUIEventLoop()
        evtloop.Pending = MagicMock(side_effect=pending_side_effect)
        evtloop.Dispatch = dispatch_spy

        # Make sleep count calls and exit after 2 iterations
        sleep_count = 0

        async def counting_sleep(duration=0):
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count >= 2:
                wx_app.exiting = True

        monkeypatch.setattr(asyncio, "sleep", counting_sleep)

        with patch.object(wx, "GUIEventLoop", return_value=evtloop):
            await wx_app.MainLoop()

        # Dispatch was called at least once (from Pending=True)
        dispatch_spy.assert_called()


class TestMainLoopMac:
    """T3: MainLoop (Mac) calls DispatchTimeout(0); no Pending() loop."""

    async def test_mainloop_mac_calls_dispatch_timeout(
        self, wx_app, set_is_mac, monkeypatch
    ) -> None:
        set_is_mac(True)

        import wx

        dispatch_timeout_spy = MagicMock()
        pending_spy = MagicMock()

        evtloop = wx.GUIEventLoop()
        evtloop.DispatchTimeout = dispatch_timeout_spy
        evtloop.Pending = pending_spy

        # Make sleep exit after 1 iteration
        async def one_shot_sleep(*_a, **_kw):
            wx_app.exiting = True

        monkeypatch.setattr(asyncio, "sleep", one_shot_sleep)

        with patch.object(wx, "GUIEventLoop", return_value=evtloop):
            await wx_app.MainLoop()

        # Mac path: DispatchTimeout was called
        dispatch_timeout_spy.assert_called_with(0)
        # Mac path: Pending was NOT called (Mac skips the Pending loop)
        pending_spy.assert_not_called()


class TestExitMainLoop:
    """T4: ExitMainLoop sets exiting=True."""

    def test_exit_main_loop_sets_exiting(self, wx_app) -> None:
        assert wx_app.exiting is False
        wx_app.ExitMainLoop()
        assert wx_app.exiting is True

    async def test_exit_main_loop_terminates_loop(
        self, wx_app, set_is_mac, monkeypatch
    ) -> None:
        set_is_mac(False)

        async def one_shot_sleep(*_a, **_kw):
            wx_app.ExitMainLoop()

        monkeypatch.setattr(asyncio, "sleep", one_shot_sleep)
        await wx_app.MainLoop()
        # After MainLoop exits, exiting is reset to False
        assert wx_app.exiting is False
