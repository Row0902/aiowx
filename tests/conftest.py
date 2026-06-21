"""
conftest.py — wx stub infrastructure for headless unit tests.

Installs a MagicMock-backed ``wx`` module into ``sys.modules`` **before**
any ``aiowx._core`` import happens during test collection.
"""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from aiowx._core import WxAsyncApp

# ---------------------------------------------------------------------------
# Stub classes — real types so isinstance() and type() checks work correctly
# ---------------------------------------------------------------------------


class WxAppStub:
    """Minimal wx.App stand-in.  Subclassable by WxAsyncApp."""

    _instance: WxAppStub | None = None

    def __init__(self, **kwargs) -> None:
        WxAppStub._instance = self

    # wx.App public surface used by _core.py
    def SetExitOnFrameDelete(self, flag: bool) -> None: ...
    def ProcessPendingEvents(self) -> None: ...
    def OnExit(self) -> None: ...

    @staticmethod
    def Get() -> WxAppStub | None:
        return WxAppStub._instance


class WxWindowStub:
    """Minimal wx.Window stand-in."""

    def Bind(self, *args, **kwargs) -> None: ...
    def Unbind(self, *args, **kwargs) -> bool:
        return True

    def IsEnabled(self) -> bool:
        return True

    def Enable(self, state: bool = True) -> None: ...
    def Disable(self) -> None: ...
    def GetParent(self) -> WxWindowStub | None:
        return None

    def SetFocus(self) -> None: ...
    def GetId(self) -> int:
        return 0

    def GetAffirmativeId(self) -> int:
        return 5100

    def GetEscapeId(self) -> int:
        return 5101

    def Show(self) -> bool:
        return True

    def Hide(self) -> bool:
        return True

    def Destroy(self) -> bool:
        return True

    def Validate(self) -> bool:
        return True

    def TransferDataFromWindow(self) -> bool:
        return True

    def SetReturnCode(self, rc: int) -> None: ...
    def GetReturnCode(self) -> int:
        return 0

    def Skip(self) -> None: ...


class WxDialogStub(WxWindowStub):
    """Minimal wx.Dialog stand-in (inherits Window)."""


class WxFileDialog(WxDialogStub): ...


class WxDirDialog(WxDialogStub): ...


class WxFontDialog(WxDialogStub): ...


class WxColourDialog(WxDialogStub): ...


class WxMessageDialog(WxDialogStub): ...


class WxHtmlHelpDialog(WxDialogStub): ...


class WxGUIEventLoopStub:
    """Minimal wx.GUIEventLoop stand-in."""

    def Pending(self) -> bool:
        return False

    def Dispatch(self) -> bool:
        return True

    def DispatchTimeout(self, timeout: int) -> int:
        return 0

    def ProcessIdle(self) -> bool:
        return False


class WxEventLoopActivatorStub:
    """Context-manager stub for wx.EventLoopActivator."""

    def __init__(self, loop) -> None: ...
    def __enter__(self) -> WxEventLoopActivatorStub:
        return self

    def __exit__(self, *args) -> None: ...


# ---------------------------------------------------------------------------
# Event binder stubs — each has a distinct typeId
# ---------------------------------------------------------------------------


class _PyEventBinder:
    def __init__(self, type_id: int) -> None:
        self.typeId = type_id


_EVT_WINDOW_DESTROY = _PyEventBinder(1)
_EVT_CLOSE = _PyEventBinder(2)
_EVT_BUTTON = _PyEventBinder(3)

# ---------------------------------------------------------------------------
# Build the wx module mock
# ---------------------------------------------------------------------------

wx_mock = MagicMock()
wx_mock.App = WxAppStub
wx_mock.Window = WxWindowStub
wx_mock.Dialog = WxDialogStub
wx_mock.GUIEventLoop = WxGUIEventLoopStub
wx_mock.EventLoopActivator = WxEventLoopActivatorStub

# Dialog types (distinct classes so `type(dlg) in [...]` works)
wx_mock.FileDialog = WxFileDialog
wx_mock.DirDialog = WxDirDialog
wx_mock.FontDialog = WxFontDialog
wx_mock.ColourDialog = WxColourDialog
wx_mock.MessageDialog = WxMessageDialog

# Constants
wx_mock.ID_ANY = -1
wx_mock.ID_CANCEL = 5101
wx_mock.ID_APPLY = 5102

# Event binders
wx_mock.EVT_WINDOW_DESTROY = _EVT_WINDOW_DESTROY
wx_mock.EVT_CLOSE = _EVT_CLOSE
wx_mock.EVT_BUTTON = _EVT_BUTTON

# Top-level windows helper
wx_mock.GetTopLevelWindows = MagicMock(return_value=[])

# wx.html sub-module
wx_html_mock = MagicMock()
wx_html_mock.HtmlHelpDialog = WxHtmlHelpDialog
wx_mock.html = wx_html_mock

# Install into sys.modules BEFORE any test collection imports aiowx
sys.modules["wx"] = wx_mock
sys.modules["wx.html"] = wx_html_mock

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _patch_asyncio_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace asyncio.sleep with a yielding no-op so tasks get scheduled."""

    async def _noop_sleep(*_args, **_kwargs) -> None:
        # Yield control by awaiting a future resolved via call_soon
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[None] = loop.create_future()
        loop.call_soon(fut.set_result, None)
        await fut

    monkeypatch.setattr(asyncio, "sleep", _noop_sleep)


@pytest.fixture()
def set_is_mac(monkeypatch: pytest.MonkeyPatch):
    """Fixture to control IS_MAC flag in aiowx._core per-test."""

    def _set(is_mac: bool) -> None:
        import aiowx._core as core

        monkeypatch.setattr(core, "IS_MAC", is_mac)

    return _set


@pytest.fixture()
def wx_app() -> WxAsyncApp:
    """Create a fresh WxAsyncApp instance for each test."""
    from aiowx._core import WxAsyncApp

    app = WxAsyncApp()
    return app


@pytest.fixture()
def make_window():
    """Factory fixture: returns a new WxWindowStub instance."""

    def _factory() -> WxWindowStub:
        return WxWindowStub()

    return _factory
