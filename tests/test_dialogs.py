"""
tests/test_dialogs.py — AsyncShowDialog + AsyncShowDialogModal (T11–T12).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from unittest.mock import MagicMock, patch

import pytest

import wx
from aiowx._core import (
    AsyncShowDialog,
    AsyncShowDialogModal,
    ShowModalInExecutor,
)

from tests.conftest import (
    WxColourDialog,
    WxDialogStub,
    WxDirDialog,
    WxFileDialog,
    WxFontDialog,
    WxHtmlHelpDialog,
    WxMessageDialog,
    WxWindowStub,
)


class TestAsyncShowDialogValidation:
    """T11: AsyncShowDialog raises for modless-incompatible dialog types."""

    @pytest.mark.parametrize(
        "dialog_cls",
        [WxFileDialog, WxDirDialog, WxFontDialog, WxColourDialog, WxMessageDialog],
    )
    async def test_rejects_modless_incompatible_types(self, dialog_cls, wx_app) -> None:
        dlg = dialog_cls()
        with pytest.raises(Exception, match="cannot be shown modless"):
            await AsyncShowDialog(dlg)


class TestAsyncShowDialogHappyPath:
    """T11: AsyncShowDialog happy path — returns GetReturnCode after close."""

    async def test_returns_return_code_on_close(self, wx_app) -> None:
        dlg = WxDialogStub()
        dlg.Show = MagicMock()
        dlg.Hide = MagicMock()
        dlg.SetReturnCode = MagicMock()
        dlg.GetReturnCode = MagicMock(return_value=5100)

        # Capture handlers bound by AsyncBind
        handlers: dict = {}

        def mock_async_bind(event, handler, obj, **kwargs):
            handlers[event] = handler

        with patch("aiowx._core.AsyncBind", side_effect=mock_async_bind):
            task = asyncio.create_task(AsyncShowDialog(dlg))
            # Yield to let the task run up to await closed.wait()
            await asyncio.sleep(0)

            # dlg.Show() was called
            dlg.Show.assert_called_once()

            # EVT_CLOSE handler was bound
            assert wx.EVT_CLOSE in handlers

            # Trigger the close handler
            close_handler = handlers[wx.EVT_CLOSE]
            mock_event = MagicMock()
            mock_event.Clone.return_value = mock_event
            # close_handler is an async function; we need to call it and await
            # But it's wrapped in a lambda by AsyncBind... actually no,
            # we patched AsyncBind so we get the raw handler
            # The handler is on_close which is async
            await close_handler(mock_event)

            result = await task
            assert result == 5100


class TestAsyncShowDialogModalOSDialogs:
    """T12: OS-dialog types route to ShowModalInExecutor (wx.CallAfter dispatch, no run_in_executor)."""

    @pytest.mark.parametrize(
        "dialog_cls",
        [
            WxFileDialog,
            WxDirDialog,
            WxFontDialog,
            WxColourDialog,
            WxMessageDialog,
            WxHtmlHelpDialog,
        ],
    )
    async def test_os_dialog_routes_through_showmodal(self, dialog_cls, wx_app) -> None:
        """T12: OS dialogs route to ShowModalInExecutor and return its result."""
        dlg = dialog_cls()
        dlg.ShowModal = MagicMock(return_value=42)
        callbacks: list[Callable[[], None]] = []

        def capture_callafter(callback: Callable[[], None]) -> None:
            callbacks.append(callback)

        with patch("wx.CallAfter", side_effect=capture_callafter):
            task = asyncio.create_task(AsyncShowDialogModal(dlg))
            await asyncio.sleep(0)
            callbacks[0]()
            result = await task

        assert result == 42

    async def test_showmodal_in_executor_uses_callafter(self, wx_app) -> None:
        """T7: ShowModalInExecutor schedules dialog.ShowModal via wx.CallAfter."""
        dlg = WxDialogStub()
        dlg.ShowModal = MagicMock(return_value=42)
        callbacks: list[Callable[[], None]] = []

        def capture_callafter(callback: Callable[[], None]) -> None:
            callbacks.append(callback)

        with patch("wx.CallAfter", side_effect=capture_callafter):
            task = asyncio.create_task(ShowModalInExecutor(dlg))
            await asyncio.sleep(0)

            assert len(callbacks) == 1
            callbacks[0]()

            result = await task

        dlg.ShowModal.assert_called_once()
        assert result == 42

    async def test_showmodal_in_executor_avoids_run_in_executor(self, wx_app) -> None:
        """T7: ShowModalInExecutor does not use asyncio's thread executor."""
        dlg = WxDialogStub()
        dlg.ShowModal = MagicMock(return_value=42)
        callbacks: list[Callable[[], None]] = []

        def capture_callafter(callback: Callable[[], None]) -> None:
            callbacks.append(callback)

        with (
            patch("wx.CallAfter", side_effect=capture_callafter),
            patch.object(asyncio.AbstractEventLoop, "run_in_executor") as mock_executor,
        ):
            task = asyncio.create_task(ShowModalInExecutor(dlg))
            await asyncio.sleep(0)
            callbacks[0]()
            result = await task

        mock_executor.assert_not_called()
        assert result == 42

    async def test_showmodal_in_executor_propagates_return_code(self, wx_app) -> None:
        """T7: Return code from dialog.ShowModal propagates to the awaiter."""
        expected_return_code = 5100
        dlg = WxDialogStub()
        dlg.ShowModal = MagicMock(return_value=expected_return_code)
        callbacks: list[Callable[[], None]] = []

        def capture_callafter(callback: Callable[[], None]) -> None:
            callbacks.append(callback)

        with patch("wx.CallAfter", side_effect=capture_callafter):
            task = asyncio.create_task(ShowModalInExecutor(dlg))
            await asyncio.sleep(0)
            callbacks[0]()
            result = await task

        assert result == expected_return_code

    async def test_showmodal_in_executor_propagates_exception(self, wx_app) -> None:
        """T7: Exceptions from dialog.ShowModal propagate through the Future."""
        dlg = WxDialogStub()
        dlg.ShowModal = MagicMock(side_effect=ValueError("modal error"))
        callbacks: list[Callable[[], None]] = []

        def capture_callafter(callback: Callable[[], None]) -> None:
            callbacks.append(callback)

        with patch("wx.CallAfter", side_effect=capture_callafter):
            task = asyncio.create_task(ShowModalInExecutor(dlg))
            await asyncio.sleep(0)
            callbacks[0]()

            with pytest.raises(ValueError, match="modal error"):
                await task


class TestAsyncShowDialogModalRegular:
    """T12: Regular dialogs disable top-level frames and re-enable them."""

    async def test_disables_and_reenables_frames(self, wx_app) -> None:
        dlg = WxDialogStub()
        dlg.Show = MagicMock()
        dlg.Hide = MagicMock()
        dlg.SetReturnCode = MagicMock()
        dlg.GetReturnCode = MagicMock(return_value=5100)
        dlg.GetParent = MagicMock(return_value=None)

        # Capture handlers bound by AsyncBind
        handlers: dict = {}

        def mock_async_bind(event, handler, obj, **kwargs):
            handlers[event] = handler

        # Create mock top-level frames
        frame1 = WxWindowStub()
        frame1.IsEnabled = MagicMock(return_value=True)
        frame1.Disable = MagicMock()
        frame1.Enable = MagicMock()

        frame2 = WxWindowStub()
        frame2.IsEnabled = MagicMock(return_value=False)
        frame2.Disable = MagicMock()
        frame2.Enable = MagicMock()

        with (
            patch.object(wx, "GetTopLevelWindows", return_value=[frame1, frame2, dlg]),
            patch("aiowx._core.AsyncBind", side_effect=mock_async_bind),
        ):
            task = asyncio.create_task(AsyncShowDialogModal(dlg))
            await asyncio.sleep(0)

            # Frames should be disabled
            frame1.Disable.assert_called_once()
            frame2.Disable.assert_called_once()

            # Trigger close handler
            assert wx.EVT_CLOSE in handlers
            close_handler = handlers[wx.EVT_CLOSE]
            mock_event = MagicMock()
            mock_event.Clone.return_value = mock_event
            await close_handler(mock_event)

            result = await task

        assert result == 5100
        # Frames should be re-enabled with their original state
        frame1.Enable.assert_called_once_with(True)
        frame2.Enable.assert_called_once_with(False)
