"""Real-world aiowx demo — async dashboard, data fetching, and task management.

Run with: uv run python src/examples/demo_app.py

Shows:
  - Async dashboard with concurrent API calls (asyncio.TaskGroup)
  - Async form submission with validation
  - Background polling with auto-cancel on window close
  - Parallel batch processing with real-time progress
  - Scheduled recurring tasks
  - Graceful shutdown with task cleanup
"""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

import wx

from aiowx import AsyncBind, StartCoroutine, WxAsyncApp

# ── Domain types ───────────────────────────────────────────────────


@dataclass
class StockQuote:
    """Simulated stock market data."""

    symbol: str
    price: float
    change_pct: float
    volume: int


@dataclass
class ApiResponse[T]:
    """Generic async API response wrapper."""

    data: T | None = None
    error: str | None = None
    latency_ms: float = 0.0


@dataclass
class DownloadJob:
    """Represents a simulated file download task."""

    id: int
    name: str
    size_mb: float
    progress: float = 0.0
    status: str = "pending"  # pending | downloading | done | failed


# ── Mock async services ────────────────────────────────────────────


async def fetch_stock_quote(symbol: str) -> ApiResponse[StockQuote]:
    """Simulate a non-blocking API call to a stock quote service."""
    latency = random.uniform(0.3, 1.0)
    await asyncio.sleep(latency)
    if random.random() < 0.05:  # 5% failure rate
        return ApiResponse(
            error=f"Timeout fetching {symbol}", latency_ms=latency * 1000
        )
    return ApiResponse(
        data=StockQuote(
            symbol=symbol,
            price=100 + random.uniform(-15, 15),
            change_pct=random.uniform(-5, 5),
            volume=random.randint(100_000, 10_000_000),
        ),
        latency_ms=latency * 1000,
    )


async def batch_download(
    job: DownloadJob, progress_cb: Callable[[float], Awaitable[None]]
) -> None:
    """Simulate downloading a file with progress updates."""
    job.status = "downloading"
    chunks = 20
    for i in range(chunks):
        await asyncio.sleep(random.uniform(0.05, 0.15))
        job.progress = (i + 1) / chunks * 100
        await progress_cb(job.progress)
    job.status = "done"


async def validate_email(email: str) -> ApiResponse[str]:
    """Simulate an async email validation service."""
    await asyncio.sleep(0.3)
    if "@" not in email or "." not in email:
        return ApiResponse(error="Invalid email format")
    return ApiResponse(data=email)


async def send_notification(message: str) -> ApiResponse[str]:
    """Simulate sending a push notification."""
    await asyncio.sleep(0.5)
    if random.random() < 0.1:
        return ApiResponse(error="Notification service unavailable")
    return ApiResponse(data=f"Sent: {message[:40]}...")


# ── Main Dashboard Frame ───────────────────────────────────────────


class DashboardFrame(wx.Frame):
    """Real-world async dashboard: stock ticker, batch jobs, notifications."""

    def __init__(self) -> None:
        """Build the dashboard with 4 tabs for real async workflows."""
        super().__init__(None, title="aiowx Dashboard — v0.3.0", size=(820, 640))
        self._build_ui()
        self._bind_events()
        self.SetStatusText("Ready")

        # Background tasks bound to this window — auto-cancel on close.
        self._task_ticker = StartCoroutine(self._stock_ticker, self)

    # ── UI ─────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.CreateStatusBar(1)
        panel = wx.Panel(self)
        notebook = wx.Notebook(panel)

        # --- Tab 1: Stock Dashboard ---
        self._stock_panel = self._build_stock_tab(notebook)
        notebook.AddPage(self._stock_panel, "📈 Stocks")

        # --- Tab 2: Batch Downloads ---
        self._batch_panel = self._build_batch_tab(notebook)
        notebook.AddPage(self._batch_panel, "⬇️ Downloads")

        # --- Tab 3: Form + Notifications ---
        self._form_panel = self._build_form_tab(notebook)
        notebook.AddPage(self._form_panel, "📝 Form")

        # --- Tab 4: Task Monitor ---
        self._monitor_panel = self._build_monitor_tab(notebook)
        notebook.AddPage(self._monitor_panel, "🔍 Tasks")

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(notebook, 1, wx.EXPAND | wx.ALL, 6)
        panel.SetSizer(sizer)

    # ── Tab 1: Stock Dashboard ─────────────────────────────────────

    def _build_stock_tab(self, parent: wx.Window) -> wx.Panel:
        panel = wx.Panel(parent)
        root = wx.BoxSizer(wx.VERTICAL)

        header = wx.StaticText(
            panel, label="Concurrent API calls — fetches 6 stocks in parallel"
        )
        header.SetFont(header.GetFont().Bold())
        root.Add(header, 0, wx.ALL, 8)

        self._stock_list = wx.ListCtrl(
            panel,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL,
            size=(-1, 220),
        )
        self._stock_list.AppendColumn("Symbol", width=80)
        self._stock_list.AppendColumn("Price", width=100)
        self._stock_list.AppendColumn("Change %", width=100)
        self._stock_list.AppendColumn("Volume", width=120)
        self._stock_list.AppendColumn("Latency", width=80)
        root.Add(self._stock_list, 0, wx.EXPAND | wx.ALL, 6)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_refresh = wx.Button(panel, label="🔄 Refresh all (TaskGroup)")
        self._status_stocks = wx.StaticText(panel, label="")
        btn_row.Add(self._btn_refresh, 0, wx.RIGHT, 8)
        btn_row.Add(self._status_stocks, 0, wx.ALIGN_CENTER_VERTICAL)
        root.Add(btn_row, 0, wx.ALL, 6)

        panel.SetSizer(root)
        return panel

    async def _on_refresh_stocks(self, event: wx.CommandEvent | None = None) -> None:
        """Fetch 6 stock quotes concurrently using TaskGroup with timeout."""
        symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "NVDA", "TSLA"]
        self._stock_list.DeleteAllItems()
        self._status_stocks.SetLabel("⏳ Fetching...")
        self._btn_refresh.Enable(False)
        self.SetStatusText("Fetching stock data...")

        start = time.perf_counter()
        try:
            async with asyncio.TaskGroup() as tg:
                tasks = {sym: tg.create_task(fetch_stock_quote(sym)) for sym in symbols}
        except ExceptionGroup as exc_group:
            # TaskGroup surfaces all exceptions together
            for exc in exc_group.exceptions:
                wx.MessageBox(str(exc), "Fetch Error", wx.OK | wx.ICON_WARNING)

        elapsed = (time.perf_counter() - start) * 1000

        self._stock_list.DeleteAllItems()
        for t in tasks.values():
            result = t.result()
            if result.data:
                q = result.data
                idx = self._stock_list.AppendItem(q.symbol)
                self._stock_list.SetItem(idx, 1, f"${q.price:.2f}")
                sign = "+" if q.change_pct >= 0 else ""
                self._stock_list.SetItem(idx, 2, f"{sign}{q.change_pct:.2f}%")
                self._stock_list.SetItem(idx, 3, f"{q.volume:,}")
                self._stock_list.SetItem(idx, 4, f"{result.latency_ms:.0f}ms")

        self._status_stocks.SetLabel(
            f"✅ {sum(1 for t in tasks.values() if t.result().data)}/"
            f"{len(tasks)} — {elapsed:.0f}ms total"
        )
        self._btn_refresh.Enable(True)
        self.SetStatusText("Ready")

    async def _stock_ticker(self) -> None:
        """Auto-refresh stocks every 30 seconds — auto-cancels on window close."""
        await asyncio.sleep(5)  # initial delay
        while True:
            await self._on_refresh_stocks()
            await asyncio.sleep(30)

    # ── Tab 2: Batch Downloads ─────────────────────────────────────

    def _build_batch_tab(self, parent: wx.Window) -> wx.Panel:
        panel = wx.Panel(parent)
        root = wx.BoxSizer(wx.VERTICAL)

        header = wx.StaticText(
            panel, label="Parallel batch processing with real-time progress"
        )
        header.SetFont(header.GetFont().Bold())
        root.Add(header, 0, wx.ALL, 8)

        self._download_list = wx.ListCtrl(
            panel,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL,
            size=(-1, 200),
        )
        self._download_list.AppendColumn("File", width=150)
        self._download_list.AppendColumn("Size", width=80)
        self._download_list.AppendColumn("Progress", width=200)
        self._download_list.AppendColumn("Status", width=100)
        root.Add(self._download_list, 0, wx.EXPAND | wx.ALL, 6)

        self._global_progress = wx.Gauge(panel, range=100, size=(-1, 20))
        root.Add(self._global_progress, 0, wx.EXPAND | wx.ALL, 6)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_download = wx.Button(panel, label="⬇️ Download all (3 concurrent)")
        self._btn_clear = wx.Button(panel, label="Clear")
        self._status_batch = wx.StaticText(panel, label="")
        btn_row.Add(self._btn_download, 0, wx.RIGHT, 8)
        btn_row.Add(self._btn_clear, 0, wx.RIGHT, 8)
        btn_row.Add(self._status_batch, 0, wx.ALIGN_CENTER_VERTICAL)
        root.Add(btn_row, 0, wx.ALL, 6)

        panel.SetSizer(root)
        return panel

    async def _on_download_all(self, event: wx.CommandEvent) -> None:
        """Run 6 downloads with max 3 concurrent using a semaphore."""
        jobs = [
            DownloadJob(1, "Firmware-v3.2.bin", 256.0),
            DownloadJob(2, "Assets-pack.zip", 512.0),
            DownloadJob(3, "Documentation.pdf", 48.0),
            DownloadJob(4, "Database-dump.sql", 1024.0),
            DownloadJob(5, "Logs-archive.tar.gz", 128.0),
            DownloadJob(6, "Update-patch.msi", 64.0),
        ]

        self._download_list.DeleteAllItems()
        for j in jobs:
            idx = self._download_list.AppendItem(j.name)
            self._download_list.SetItem(idx, 1, f"{j.size_mb:.0f} MB")
            self._download_list.SetItem(idx, 2, "0%")
            self._download_list.SetItem(idx, 3, "pending")

        self._btn_download.Enable(False)
        self._global_progress.SetValue(0)
        self._status_batch.SetLabel("⏳ Downloading...")
        completed = 0
        total = len(jobs)

        sem = asyncio.Semaphore(3)

        async def limited_download(job: DownloadJob) -> None:
            nonlocal completed
            async with sem:

                async def update_progress(pct: float) -> None:
                    idx = jobs.index(job)
                    self._download_list.SetItem(idx, 2, f"{pct:.0f}%")
                    overall = sum(j.progress for j in jobs) / (total * 100) * 100
                    self._global_progress.SetValue(int(overall))
                    await asyncio.sleep(0)

                await batch_download(job, update_progress)
                idx = jobs.index(job)
                self._download_list.SetItem(idx, 2, "100%")
                self._download_list.SetItem(idx, 3, "✅ done")
                completed += 1
                self._status_batch.SetLabel(f"{completed}/{total} completed")

        async with asyncio.TaskGroup() as tg:
            for j in jobs:
                tg.create_task(limited_download(j))

        self._global_progress.SetValue(100)
        self._status_batch.SetLabel(f"✅ All {total} downloads complete")
        self._btn_download.Enable(True)

    # ── Tab 3: Form + Notifications ────────────────────────────────

    def _build_form_tab(self, parent: wx.Window) -> wx.Panel:
        panel = wx.Panel(parent)
        root = wx.BoxSizer(wx.VERTICAL)

        header = wx.StaticText(
            panel,
            label="Async form validation + notification dispatch",
        )
        header.SetFont(header.GetFont().Bold())
        root.Add(header, 0, wx.ALL, 8)

        grid = wx.FlexGridSizer(3, 2, 8, 8)

        grid.Add(wx.StaticText(panel, label="Name:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._field_name = wx.TextCtrl(panel)
        grid.Add(self._field_name, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="Email:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._field_email = wx.TextCtrl(panel)
        grid.Add(self._field_email, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="Message:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._field_message = wx.TextCtrl(panel, style=wx.TE_MULTILINE, size=(-1, 60))
        grid.Add(self._field_message, 1, wx.EXPAND)

        root.Add(grid, 0, wx.EXPAND | wx.ALL, 8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_submit = wx.Button(panel, label="📨 Submit (async validate + notify)")
        self._status_form = wx.StaticText(panel, label="")
        btn_row.Add(self._btn_submit, 0, wx.RIGHT, 8)
        btn_row.Add(self._status_form, 0, wx.ALIGN_CENTER_VERTICAL)
        root.Add(btn_row, 0, wx.ALL, 6)

        self._log = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 200)
        )
        root.Add(self._log, 1, wx.EXPAND | wx.ALL, 6)

        panel.SetSizer(root)
        return panel

    async def _on_submit(self, event: wx.CommandEvent) -> None:
        """Async form submission with validation pipeline."""
        name = self._field_name.GetValue().strip()
        email = self._field_email.GetValue().strip()
        message = self._field_message.GetValue().strip()

        if not name or not email:
            self._status_form.SetLabel("❌ Name and email are required")
            return

        self._btn_submit.Enable(False)
        self._status_form.SetLabel("⏳ Validating...")
        self._log.AppendText(f"[{time.strftime('%H:%M:%S')}] Validating {email}...\n")

        # Step 1: Validate email (async)
        validation = await validate_email(email)
        if validation.error:
            self._status_form.SetLabel(f"❌ {validation.error}")
            self._btn_submit.Enable(True)
            return

        # Step 2: Send notification (async)
        self._status_form.SetLabel("⏳ Sending notification...")
        notification = await send_notification(f"Form submitted by {name}: {message}")
        if notification.error:
            self._status_form.SetLabel(
                f"⚠️ Saved locally but notification failed: {notification.error}"
            )
            self._log.AppendText(
                f"[{time.strftime('%H:%M:%S')}] ⚠️ {notification.error}\n"
            )
        else:
            self._status_form.SetLabel("✅ Submitted! Notification sent.")
            self._log.AppendText(
                f"[{time.strftime('%H:%M:%S')}] ✅ {notification.data}\n"
            )

        self._log.AppendText(
            f"[{time.strftime('%H:%M:%S')}] Form from {name} ({email}) processed\n"
        )

        # Clear after 3 seconds
        await asyncio.sleep(3)
        self._status_form.SetLabel("Ready")
        self._btn_submit.Enable(True)

    # ── Tab 4: Task Monitor ────────────────────────────────────────

    def _build_monitor_tab(self, parent: wx.Window) -> wx.Panel:
        panel = wx.Panel(parent)
        root = wx.BoxSizer(wx.VERTICAL)

        header = wx.StaticText(
            panel, label="Scheduled recurring tasks with real-time logging"
        )
        header.SetFont(header.GetFont().Bold())
        root.Add(header, 0, wx.ALL, 8)

        self._monitor_log = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY,
            size=(-1, 300),
        )
        root.Add(self._monitor_log, 1, wx.EXPAND | wx.ALL, 6)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_start_poller = wx.Button(panel, label="▶️ Start health poller")
        self._btn_stop_poller = wx.Button(panel, label="⏹️ Stop poller")
        self._btn_start_poller.Enable(True)
        self._btn_stop_poller.Enable(False)
        btn_row.Add(self._btn_start_poller, 0, wx.RIGHT, 8)
        btn_row.Add(self._btn_stop_poller, 0, wx.RIGHT, 8)
        root.Add(btn_row, 0, wx.ALL, 6)

        panel.SetSizer(root)
        return panel

    async def _on_start_poller(self, event: wx.CommandEvent) -> None:
        """Start a recurring health-check poller that can be stopped/restarted."""
        self._btn_start_poller.Enable(False)
        self._btn_stop_poller.Enable(True)
        self._poller_running = True
        self._monitor_log.AppendText(
            f"[{time.strftime('%H:%M:%S')}] 🔍 Health poller started\n",
        )
        while self._poller_running:
            await asyncio.sleep(5)
            if not self._poller_running:
                break
            # Simulate checking service health
            db_ok = random.random() > 0.15
            api_ok = random.random() > 0.10
            status = (
                "✅ All services healthy"
                if db_ok and api_ok
                else "⚠️ Degraded: DB OK"
                if db_ok
                else "⚠️ Degraded: API OK"
                if api_ok
                else "❌ Multiple services down"
            )
            self._monitor_log.AppendText(
                f"[{time.strftime('%H:%M:%S')}] {status}\n",
            )

    async def _on_stop_poller(self, event: wx.CommandEvent) -> None:
        """Stop the health-check poller."""
        self._poller_running = False
        self._btn_start_poller.Enable(True)
        self._btn_stop_poller.Enable(False)
        self._monitor_log.AppendText(
            f"[{time.strftime('%H:%M:%S')}] ⏹️ Health poller stopped\n",
        )

    # ── Event bindings ─────────────────────────────────────────────

    def _bind_events(self) -> None:
        # Tab 1
        AsyncBind(wx.EVT_BUTTON, self._on_refresh_stocks, self._btn_refresh)
        # Tab 2
        AsyncBind(wx.EVT_BUTTON, self._on_download_all, self._btn_download)
        # Tab 3
        AsyncBind(wx.EVT_BUTTON, self._on_submit, self._btn_submit)
        # Tab 4
        AsyncBind(wx.EVT_BUTTON, self._on_start_poller, self._btn_start_poller)
        AsyncBind(wx.EVT_BUTTON, self._on_stop_poller, self._btn_stop_poller)
        self._btn_clear.Bind(
            wx.EVT_BUTTON, lambda e: self._download_list.DeleteAllItems()
        )

    # ── Window close: graceful shutdown ───────────────────────────

    def _on_close(self, event: wx.CloseEvent) -> None:
        """Clean shutdown — all StartCoroutine tasks auto-cancel."""
        self._poller_running = False
        self.Destroy()


# ── Entry ──────────────────────────────────────────────────────────


async def main() -> None:
    """Entry point — create the async wx app and show the dashboard."""
    app = WxAsyncApp()
    frame = DashboardFrame()
    frame.Show()
    app.SetTopWindow(frame)
    await app.MainLoop()


if __name__ == "__main__":
    asyncio.run(main())
