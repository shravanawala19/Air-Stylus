"""Calibration wizard.

Maps a hand-defined region in camera space to the full screen by having the
user sweep their hand across the field of view. The recorded bounds are saved
to config and used by the Mapper.
"""
from __future__ import annotations

import threading
import time

import customtkinter as ctk
import numpy as np
from PIL import Image, ImageTk

from app.config import Config, save_config
from app.core.camera import Camera
from app.core.tracking import HandTracker


class CalibrationWindow(ctk.CTkToplevel):
    def __init__(self, master, config: Config):
        super().__init__(master)
        self.config = config
        self.title("Calibration")
        self.geometry("720x560")

        self.camera = Camera(config.settings.camera_index)
        self.tracker = HandTracker()

        self._running = False
        self._thread = None
        self._photo = None

        self._x_min, self._x_max = 1.0, 0.0
        self._y_min, self._y_max = 1.0, 0.0
        self._samples = 0
        self._capturing = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.preview = ctk.CTkLabel(self, text="Starting camera...", width=640, height=400)
        self.preview.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")

        ctrl = ctk.CTkFrame(self)
        ctrl.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))
        ctrl.grid_columnconfigure(0, weight=1)

        self.instruction = ctk.CTkLabel(
            ctrl, text="Wave your hand across the full area you want to use\n"
                       "as the mouse surface. Reach all four corners.",
            font=ctk.CTkFont(size=14))
        self.instruction.grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=8)

        self.progress = ctk.CTkProgressBar(ctrl)
        self.progress.set(0)
        self.progress.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=4)

        self.capture_btn = ctk.CTkButton(ctrl, text="Start Capturing",
                                         command=self.toggle_capture, height=32)
        self.capture_btn.grid(row=2, column=0, sticky="ew", padx=12, pady=8)

        self.save_btn = ctk.CTkButton(ctrl, text="Save and Apply",
                                      command=self._save, height=32)
        self.save_btn.grid(row=2, column=1, sticky="ew", padx=12, pady=8)
        self.save_btn.configure(state="disabled")

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._start_camera()

    def _start_camera(self):
        if not self.camera.start():
            self.preview.configure(text=f"Camera error: {self.camera.error}")
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while self._running and self.camera.is_running:
            frame = self.camera.read()
            if frame is None:
                time.sleep(0.005)
                continue

            result = self.tracker.process(frame)

            if self._capturing and result.hands:
                for hand in result.hands:
                    c = hand.palm_center
                    self._x_min = min(self._x_min, float(c[0]))
                    self._x_max = max(self._x_max, float(c[0]))
                    self._y_min = min(self._y_min, float(c[1]))
                    self._y_max = max(self._y_max, float(c[1]))
                    self._samples += 1

            self._render(frame)
            time.sleep(0.005)

        self._rendered_after(lambda: self.preview.configure(text="Camera stopped"))

    def _render(self, frame: np.ndarray):
        img = Image.fromarray(frame)
        img.thumbnail((640, 400), Image.LANCZOS)
        data = ImageTk.PhotoImage(img)
        self._rendered_after(lambda d=data: self._update_preview(d))

    def _update_preview(self, photo):
        self._photo = photo
        self.preview.configure(image=photo, text="")
        if self._capturing:
            frac = min(1.0, self._samples / 40.0)
            self.progress.set(frac)
            if self._samples >= 40 and str(self.save_btn.cget("state")) == "disabled":
                self.save_btn.configure(state="normal")

    def _rendered_after(self, fn):
        try:
            self.after(0, fn)
        except Exception:
            pass

    def toggle_capture(self):
        if self._capturing:
            self._capturing = False
            self.capture_btn.configure(text="Resume Capturing")
        else:
            self._capturing = True
            self.capture_btn.configure(text="Stop Capturing")

    def _save(self):
        if self._x_max <= self._x_min or self._y_max <= self._y_min:
            return

        margin = 0.02
        cal = self.config.calibration
        cal.x_min = max(0.0, self._x_min - margin)
        cal.x_max = min(1.0, self._x_max + margin)
        cal.y_min = max(0.0, self._y_min - margin)
        cal.y_max = min(1.0, self._y_max + margin)

        save_config(self.config)
        self._stop()
        self.destroy()

    def _on_close(self):
        self._stop()
        self.destroy()

    def _stop(self):
        self._running = False
        self.tracker.close()
        self.camera.stop()