"""Comprehensive aiowx demo app — exercises all public APIs.

Run with: uv run python src/examples/demo_app.py

Covers:
  - WxAsyncApp + async MainLoop
  - AsyncBind (wx event → coroutine)
  - StartCoroutine (background task + auto-cancel on destroy)
  - AsyncShowDialog (custom dialog, modless path)
  - AsyncShowDialogModal (OS-native file dialog)
  - Multiple windows with independent task lifecycles
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

import wx

from aiowx import (
    AsyncBind,
    AsyncShowDialog,
    AsyncShowDialogModal,
    StartCoroutine,
    WxAsyncApp,
)


# ── helpers ────────────────────────────────────────────────────────

@dataclass
class SensorReading:
    """Mock sensor data for demonstration."""

    temperature: float
    humidity: float
    timestamp: float


async def mock_sensor() -> SensorReading:
    """Simulate a non-blocking I/O sensor read."""
    await asyncio.sleep(0.3)
    return SensorReading(
        temperature=20.0 + (time.time() % 10),
        humidity=40.0 + (time.time() % 20),
        timestamp=time.time(),
    )


# ── Main Frame ─────────────────────────────────────────────────────

class MainFrame(wx.Frame):
    """Main window showing all aiowx capabilities."""

    def __init__(self) -> None:
        super().__init__(None, title="aiowx Demo — v0.3.0", size=(600, 500))
        self._build_ui()
        self._bind_events()
        # Start background tasks bound to THIS window's lifecycle.
        # When this frame is closed, both tasks auto-cancel.
        self._clock_task = StartCoroutine(self._update_clock, self)
        self._sensor_task = StartCoroutine(self._poll_sensor, self)
        self.Bind(wx.EVT_CLOSE, self._on_close)

    # ── UI setup ───────────────────────────────────────────────────

    def _build_ui(self) -> None:
        panel = wx.Panel(self)
        root = wx.BoxSizer(wx.VERTICAL)

        # --- Clock section ---
        clock_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "⏱️ Live Clock (StartCoroutine)")
        self.clock_label = wx.StaticText(
            panel, style=wx.ALIGN_CENTRE_HORIZONTAL,
        )
        clock_box.Add(self.clock_label, 0, wx.EXPAND | wx.ALL, 8)
        root.Add(clock_box, 0, wx.EXPAND | wx.ALL, 6)

        # --- Sensor section ---
        sensor_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "📡 Mock Sensor (StartCoroutine)")
        self.sensor_label = wx.StaticText(
            panel, style=wx.ALIGN_CENTRE_HORIZONTAL,
        )
        sensor_box.Add(self.sensor_label, 0, wx.EXPAND | wx.ALL, 8)
        root.Add(sensor_box, 0, wx.EXPAND | wx.ALL, 6)

        # --- Button section ---
        btn_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "🖱️ Events (AsyncBind)")
        self.btn_click = wx.Button(panel, label="Click me (async callback)")
        self.click_result = wx.StaticText(panel, style=wx.ALIGN_CENTRE_HORIZONTAL)
        btn_box.Add(self.btn_click, 0, wx.EXPAND | wx.ALL, 4)
        btn_box.Add(self.click_result, 0, wx.EXPAND | wx.ALL, 4)
        root.Add(btn_box, 0, wx.EXPAND | wx.ALL, 6)

        # --- Dialog section ---
        dlg_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "💬 Dialogs (AsyncShowDialog)")
        self.btn_custom_dlg = wx.Button(panel, label="Open custom dialog (modless path)")
        self.btn_file_dlg = wx.Button(panel, label="Open file dialog (modal path)")
        self.dlg_result = wx.StaticText(panel, style=wx.ALIGN_CENTRE_HORIZONTAL)
        dlg_box.Add(self.btn_custom_dlg, 0, wx.EXPAND | wx.ALL, 4)
        dlg_box.Add(self.btn_file_dlg, 0, wx.EXPAND | wx.ALL, 4)
        dlg_box.Add(self.dlg_result, 0, wx.EXPAND | wx.ALL, 4)
        root.Add(dlg_box, 0, wx.EXPAND | wx.ALL, 6)

        # --- Spawn window ---
        spawn_box = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_spawn = wx.Button(panel, label="Spawn child window (tests auto-cancel)")
        self.btn_spawn_all = wx.Button(panel, label="Spawn 5 windows")
        spawn_box.Add(self.btn_spawn, 1, wx.EXPAND | wx.RIGHT, 4)
        spawn_box.Add(self.btn_spawn_all, 1, wx.EXPAND | wx.LEFT, 4)
        root.Add(spawn_box, 0, wx.EXPAND | wx.ALL, 6)

        # --- Status bar ---
        self.CreateStatusBar(1)
        self.SetStatusText("Ready")

        panel.SetSizer(root)
        panel.Layout()

    # ── Event bindings ─────────────────────────────────────────────

    def _bind_events(self) -> None:
        AsyncBind(wx.EVT_BUTTON, self._on_click, self.btn_click)
        AsyncBind(wx.EVT_BUTTON, self._on_custom_dialog, self.btn_custom_dlg)
        AsyncBind(wx.EVT_BUTTON, self._on_file_dialog, self.btn_file_dlg)
        AsyncBind(wx.EVT_BUTTON, self._on_spawn, self.btn_spawn)
        AsyncBind(wx.EVT_BUTTON, self._on_spawn_five, self.btn_spawn_all)

    # ── Background tasks ───────────────────────────────────────────

    async def _update_clock(self) -> None:
        """Tick every second — bound to this window; auto-cancelled on close."""
        while True:
            self.clock_label.SetLabel(time.strftime("%H:%M:%S"))
            await asyncio.sleep(1)

    async def _poll_sensor(self) -> None:
        """Poll mock sensor every 2 s — bound to this window; auto-cancelled on close."""
        while True:
            reading = await mock_sensor()
            self.sensor_label.SetLabel(
                f"🌡️ {reading.temperature:.1f}°C  💧 {reading.humidity:.1f}%",
            )
            self.SetStatusText(f"Sensor @ {time.strftime('%H:%M:%S')}")
            await asyncio.sleep(2)

    # ── Event handlers ─────────────────────────────────────────────

    async def _on_click(self, event: wx.CommandEvent) -> None:
        """Demonstrate AsyncBind with an async callback."""
        self.click_result.SetLabel("⏳ Working...")
        self.SetStatusText("Async callback running...")
        await asyncio.sleep(0.5)
        self.click_result.SetLabel("✅ Done!")
        await asyncio.sleep(2)
        self.click_result.SetLabel("")
        self.SetStatusText("Ready")
        event.Skip()

    async def _on_custom_dialog(self, event: wx.CommandEvent) -> None:
        """Open a custom dialog via AsyncShowDialog (modless path)."""
        dlg = wx.TextEntryDialog(
            self, "Enter some text:", "Custom Dialog Demo",
        )
        result = await AsyncShowDialog(dlg)
        if result == wx.ID_OK:
            self.dlg_result.SetLabel(f"You entered: {dlg.GetValue()}")
        else:
            self.dlg_result.SetLabel("Dialog cancelled")
        dlg.Destroy()

    async def _on_file_dialog(self, event: wx.CommandEvent) -> None:
        """Open an OS-native file dialog via AsyncShowDialogModal."""
        dlg = wx.FileDialog(
            self,
            message="Pick a file",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        result = await AsyncShowDialogModal(dlg)
        if result == wx.ID_OK:
            self.dlg_result.SetLabel(f"Selected: {dlg.GetPath()}")
        else:
            self.dlg_result.SetLabel("File dialog cancelled")
        dlg.Destroy()

    async def _on_spawn(self, event: wx.CommandEvent) -> None:
        """Spawn one child window — closing it tests auto-cancel."""
        child = ChildFrame(self)
        child.Show()

    async def _on_spawn_five(self, event: wx.CommandEvent) -> None:
        """Spawn 5 child windows at once — tests parallel StartCoroutine."""
        for i in range(5):
            child = ChildFrame(self, suffix=f" #{i + 1}")
            child.Show()
            await asyncio.sleep(0.1)

    def _on_close(self, event: wx.CloseEvent) -> None:
        """Clean shutdown — all tasks auto-cancel via OnDestroy."""
        self.Destroy()


# ── Child Frame ────────────────────────────────────────────────────

_CHILD_COUNTER = 0


class ChildFrame(wx.Frame):
    """Child window with its own independent lifecycle.

    Close it → all its StartCoroutine tasks cancel automatically.
    """

    def __init__(self, parent: wx.Window, suffix: str = "") -> None:
        global _CHILD_COUNTER
        _CHILD_COUNTER += 1
        self._index = _CHILD_COUNTER
        title = f"Child {self._index}{suffix}"
        super().__init__(parent, title=title, size=(300, 120))

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.label = wx.StaticText(panel, label=title, style=wx.ALIGN_CENTRE_HORIZONTAL)
        sizer.Add(self.label, 0, wx.EXPAND | wx.ALL, 10)

        self.timer_label = wx.StaticText(
            panel, label="Starting...", style=wx.ALIGN_CENTRE_HORIZONTAL,
        )
        sizer.Add(self.timer_label, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(sizer)

        # This task auto-cancels when this child window closes.
        StartCoroutine(self._child_tick, self)
        self.Show()

    async def _child_tick(self) -> None:
        """Infinite counter — bound to this child window only."""
        count = 0
        while True:
            count += 1
            self.timer_label.SetLabel(f"Tick {count}")
            await asyncio.sleep(1)


# ── Entry point ────────────────────────────────────────────────────

async def main() -> None:
    app = WxAsyncApp()
    frame = MainFrame()
    frame.Show()
    app.SetTopWindow(frame)
    await app.MainLoop()


if __name__ == "__main__":
    asyncio.run(main())
