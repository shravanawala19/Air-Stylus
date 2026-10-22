"""Main application window.

Hosts the live preview, settings panel, status bar, and calibration launcher.
"""
from __future__ import annotations

import customtkinter as ctk

from app.config import Config, save_config
from app.core.engine import ControlEngine
from app.ui.preview import PreviewPanel
from app.ui.settings import SettingsPanel


class MainWindow(ctk.CTk):
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.engine = ControlEngine(config)

        self.title("AIRstylus — Air Mouse")
        self.geometry("860x520")
        self.minsize(760, 460)

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        # Left: preview.
        self.preview = PreviewPanel(self)
        self.preview.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)

        # Right: controls.
        right = ctk.CTkFrame(self)
        right.grid(row=0, column=1, sticky="nsew", padx=(0, 12), pady=12)
        right.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            right, text="STOPPED", fg_color="#b03a3a",
            corner_radius=8, height=30, text_color="white")
        self.status_label.grid(row=0, column=0, sticky="ew", padx=12, pady=12)

        self.start_btn = ctk.CTkButton(
            right, text="Start Tracking", command=self.toggle_tracking,
            height=40, font=ctk.CTkFont(size=15, weight="bold"))
        self.start_btn.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))

        self.calibrate_btn = ctk.CTkButton(
            right, text="Calibrate", command=self.open_calibration,
            height=36)
        self.calibrate_btn.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))

        self.settings = SettingsPanel(right, config.settings,
                                      on_change=self.on_settings_change)
        self.settings.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))

        self.hint = ctk.CTkLabel(
            right, text="Gestures:\n"
                        "  Move  - open palm\n"
                        "  Click - pinch thumb+index\n"
                        "  Right - pinch thumb+middle\n"
                        "  Scroll- two fingers up/down\n"
                        "  Zoom  - both hands apart/together",
            justify="left", anchor="w")
        self.hint.grid(row=4, column=0, sticky="ew", padx=16, pady=4)

        self.engine.on_frame = self._on_frame
        self.engine.on_status = self._on_status

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._running = False

    # ------------------------------------------------------------------
    def toggle_tracking(self):
        if self._running:
            self.engine.stop()
            self._running = False
            self.start_btn.configure(text="Start Tracking")
            self.status_label.configure(text="STOPPED", fg_color="#b03a3a")
            self.preview.clear()
        else:
            if self.engine.start():
                self._running = True
                self.start_btn.configure(text="Stop Tracking")
                self.status_label.configure(text="RUNNING", fg_color="#3a8c3a")
            else:
                self.status_label.configure(text="CAMERA ERROR", fg_color="#b03a3a")

    def open_calibration(self):
        from app.ui.calibration import CalibrationWindow
        was_running = self._running
        if was_running:
            self.engine.stop()
            self._running = False
            self.start_btn.configure(text="Start Tracking")
            self.status_label.configure(text="STOPPED", fg_color="#b03a3a")

        CalibrationWindow(self, self.config).grab_set()

    def on_settings_change(self):
        save_config(self.config)
        self.engine.update_config(self.config)

    # ------------------------------------------------------------------
    def _on_frame(self, frame, result, gesture):
        self.after(0, lambda: self.preview.show_frame(frame))

    def _on_status(self, text):
        self.after(0, lambda: self.status_label.configure(
            text=f"RUNNING — {text}", fg_color="#3a8c3a"))

    def _on_close(self):
        self.engine.stop()
        save_config(self.config)
        self.destroy()