"""Async dialog helpers for aiowx.

Provides coroutine-based wrappers around wxPython modal and modeless dialogs.
Each helper schedules GUI work on the wx main thread and suspends the awaiter
until the dialog result is available.
"""

from __future__ import annotations

import asyncio

import wx
import wx.html

from aiowx._app import AsyncBind


async def ShowModalAsync(dialog: wx.Dialog) -> int:
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
    """Show a dialog in async modeless mode and wait for its result.

    Raises:
        TypeError: If the dialog type does not support modeless display;
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
            button_id = event.GetId()
            if button_id == dialog.GetAffirmativeId():
                if dialog.Validate() and dialog.TransferDataFromWindow():
                    end_dialog(button_id)
            elif button_id == wx.ID_APPLY:
                if dialog.Validate():
                    dialog.TransferDataFromWindow()
            elif button_id == dialog.GetEscapeId() or (
                button_id == wx.ID_CANCEL and dialog.GetEscapeId() == wx.ID_ANY
            ):
                end_dialog(wx.ID_CANCEL)
            else:
                event.Skip()

        async def on_close(event: wx.CloseEvent) -> None:
            dialog.SetReturnCode(dialog.GetEscapeId() or wx.ID_CANCEL)
            dialog.Hide()
            closed.set()

        AsyncBind(wx.EVT_CLOSE, on_close, dialog)
        AsyncBind(wx.EVT_BUTTON, on_button, dialog)
        dialog.Show()
        await closed.wait()
        return dialog.GetReturnCode()

    raise TypeError(
        "This type of dialog cannot be shown modeless, please use 'AsyncShowDialogModal'"
    )


async def AsyncShowDialogModal(dialog: wx.Dialog) -> int:
    """Show a dialog in modal mode.

    OS-level dialogs (FileDialog, DirDialog, etc.) are run via ShowModalAsync.
    Other dialogs disable parent frames, show modeless, and re-enable on close.
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
        return await ShowModalAsync(dialog)

    frames = set(wx.GetTopLevelWindows()) - {dialog}  # type: ignore
    states = {frame: frame.IsEnabled() for frame in frames}
    try:
        for frame in frames:
            frame.Disable()
        return await AsyncShowDialog(dialog)
    finally:
        for frame in frames:
            if not frame.IsBeingDeleted():
                frame.Enable(states.get(frame, True))
        if not dialog.IsBeingDeleted():
            parent = dialog.GetParent()
            if parent and not parent.IsBeingDeleted():
                parent.SetFocus()
