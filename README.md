# aiowx

> Bridge wxPython with Python asyncio — run `async`/`await` coroutines in your wx GUI.

[![PyPI](https://img.shields.io/pypi/v/aiowx)](https://pypi.org/project/aiowx/)
![Python](https://img.shields.io/badge/python-3.12+-blue)
[![CI](https://github.com/Row0902/aiowx/actions/workflows/ci.yml/badge.svg)](https://github.com/Row0902/aiowx/actions/workflows/ci.yml)

## Installation

### As a dependency

```sh
uv add aiowx
# or with pip:
pip install aiowx
```

### From source

```sh
git clone https://github.com/Row0902/aiowx.git
cd aiowx
uv sync          # install deps + dev deps
uv build         # build wheel + source dist
```

Requires **Python 3.12+**, **wxPython ≥ 4.2.5**, and [uv](https://docs.astral.sh/uv/).

---

## Quick start

```python
import asyncio
import wx
from aiowx import AsyncBind, WxAsyncApp, StartCoroutine


class CounterFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="aiowx counter")
        self.label = wx.StaticText(self, label="0")
        btn = wx.Button(self, label="+1")

        AsyncBind(wx.EVT_BUTTON, self.on_click, btn)
        StartCoroutine(self.tick, self)

    async def on_click(self, _event):
        self.label.SetLabel(str(int(self.label.GetLabel()) + 1))

    async def tick(self):
        while True:
            self.label.SetLabel(str(int(self.label.GetLabel()) + 1))
            await asyncio.sleep(1)


async def main():
    app = WxAsyncApp()
    frame = CounterFrame()
    frame.Show()
    app.SetTopWindow(frame)
    await app.MainLoop()


asyncio.run(main())
```

---

## API

| Function | Purpose | Async |
|----------|---------|-------|
| `WxAsyncApp()` | Drop-in replacement for `wx.App` | — |
| `await app.MainLoop()` | Start the event loop | ✅ |
| `AsyncBind(event, coro, widget)` | Bind a wx event to a coroutine | — |
| `StartCoroutine(coro, window)` | Fire a coroutine attached to a window | — |
| `await AsyncShowDialog(dlg)` | Show a dialog modally (modless path) | ✅ |
| `await AsyncShowDialogModal(dlg)` | Show an OS dialog safely | ✅ |

### WxAsyncApp

Create instead of `wx.App`. Interleaves the wx event loop with asyncio so both GUI events and coroutines run cooperatively.

```python
app = WxAsyncApp()
await app.MainLoop()
```

### AsyncBind

Bind a wx event to an `async` callback. Works alongside regular `wx.Bind`.

```python
AsyncBind(wx.EVT_BUTTON, on_submit, submit_btn)

async def on_submit(event):
    result = await fetch_data()       # non-blocking I/O
    display.SetLabel(f"Got: {result}")
```

### StartCoroutine

Run a coroutine immediately, attached to a `wx.Window`. It is **automatically cancelled** when the window is destroyed — no manual cleanup.

```python
task = StartCoroutine(poll_sensor(sensor), panel)
# ...
task.cancel()   # optional early cancel
```

### AsyncShowDialog / AsyncShowDialogModal

Show dialogs without blocking the event loop.

- `AsyncShowDialog`: works with custom dialogs (modless path).
- `AsyncShowDialogModal`: for OS-native dialogs (`wx.FileDialog`, `wx.DirDialog`, etc.). Runs on the wx main thread (thread-safe).

```python
async def pick_file(parent):
    dlg = wx.FileDialog(parent)
    result = await AsyncShowDialogModal(dlg)
    if result == wx.ID_OK:
        path.SetLabel(dlg.GetPath())
```

> **Note**: the asyncio event loop is blocked while the modal dialog is open. This is expected desktop GUI behavior — identical to how `ShowModal` works in a traditional wx app.

---

## Patterns

### Background task with cancellation

```python
import asyncio
from aiowx import StartCoroutine


class MonitorFrame(wx.Frame):
    def __init__(self):
        super().__init__(None)
        self.running = True
        self.task = StartCoroutine(self.watchdog, self)

    async def watchdog(self):
        while self.running:
            await asyncio.sleep(5)
            if not self.check_health():
                wx.MessageBox("Connection lost")
                break
```

### Dialog with await

```python
async def save_file(parent):
    dlg = wx.FileDialog(
        parent,
        style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
    )
    if await AsyncShowDialogModal(dlg) == wx.ID_OK:
        with open(dlg.GetPath(), "w") as f:
            f.write(data)
```

---

## Performance

Values measured on Windows (Core i7-7700K @ 4.2 GHz):

| Scenario | Latency | Latency at max throughput | Max throughput |
|----------|---------|---------------------------|----------------|
| asyncio only (reference) | 0 ms | 17 ms | 571 325 msg/s |
| wx only (reference) | 0 ms | 19 ms | 94 591 msg/s |
| aiowx (GUI) | 5 ms | 19 ms | 52 304 msg/s |
| aiowx (GUI + asyncio) | 5 ms / 0 ms | 24 ms / 12 ms | 40 302 + 134 000 msg/s |

CPU usage at idle: **0%** on Windows, ~1–2% on macOS.

---

## Requirements

- Python ≥ 3.12
- wxPython ≥ 4.2.5 (4.2.5+ includes Python 3.14 wheels)

---

## Repository

<https://github.com/Row0902/aiowx>
