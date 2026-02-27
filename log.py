"""
log.py — Tkinter progress window for the LAN scanner.

Runs in a dedicated daemon thread so it never blocks the main scan loop.
All widget updates are marshalled through a Queue to satisfy Tkinter's
single-thread requirement.
"""

import queue
import tkinter as tk
from tkinter import scrolledtext, ttk
from threading import Thread, Lock


class TkinterLogWindow:
    """
    A floating log/progress window that is safe to update from any thread.

    Usage::

        window = TkinterLogWindow()          # window appears immediately
        window.set_total_ips(total)
        window.update_log("some message")    # call from any thread
        window.update_progress()             # call once per scanned IP
        window._thread.join()               # block until user closes window
    """

    def __init__(self) -> None:
        self._queue: queue.Queue = queue.Queue()
        self._lock = Lock()
        self._total: int = 0
        self._scanned: int = 0

        # Tkinter must live on its own thread
        self._thread = Thread(target=self._run, daemon=True, name="TkinterThread")
        self._thread.start()

    # ------------------------------------------------------------------
    # Public API  (thread-safe)
    # ------------------------------------------------------------------

    def set_total_ips(self, total: int) -> None:
        """Set the denominator for the progress bar. Call before scanning."""
        with self._lock:
            self._total = total
            self._scanned = 0

    def update_log(self, text: str) -> None:
        """Append *text* to the scrollable log. Safe to call from any thread."""
        self._queue.put(("log", text))

    def update_progress(self) -> None:
        """Increment the progress counter by one. Safe to call from any thread."""
        with self._lock:
            self._scanned += 1
            scanned = self._scanned
            total = self._total
        self._queue.put(("progress", (scanned, total)))

    # ------------------------------------------------------------------
    # Internal — runs on the Tkinter thread
    # ------------------------------------------------------------------

    def _run(self) -> None:
        self._root = tk.Tk()
        self._root.title("LAN Scanner")
        self._root.resizable(False, False)

        # Log area
        self._log_display = scrolledtext.ScrolledText(
            self._root, width=65, height=22, state="disabled",
            font=("Courier New", 10),
        )
        self._log_display.pack(padx=12, pady=(12, 4))

        # Progress bar
        self._progress_bar = ttk.Progressbar(
            self._root, orient="horizontal", length=440, mode="determinate"
        )
        self._progress_bar.pack(padx=12, pady=4)

        # Status label
        self._status_label = tk.Label(self._root, text="0 / 0", font=("Courier New", 9))
        self._status_label.pack(padx=12, pady=(0, 12))

        self._root.after(100, self._drain_queue)
        self._root.mainloop()

    def _drain_queue(self) -> None:
        """Process all pending UI updates. Scheduled every 100 ms."""
        try:
            while True:
                event, payload = self._queue.get_nowait()
                if event == "log":
                    self._log_display.configure(state="normal")
                    self._log_display.insert(tk.END, payload + "\n")
                    self._log_display.yview(tk.END)
                    self._log_display.configure(state="disabled")
                elif event == "progress":
                    scanned, total = payload
                    pct = (scanned / total * 100) if total else 0
                    self._progress_bar["value"] = pct
                    self._status_label.config(text=f"{scanned} / {total} {"✅" if scanned == total else ""}")
        except queue.Empty:
            pass
        self._root.after(100, self._drain_queue)