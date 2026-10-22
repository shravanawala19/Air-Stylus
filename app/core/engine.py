"""AIRstylus control engine.

Orchestrates the pipeline: camera frame -> hand tracking -> gesture
classification -> smoothing -> mapping -> mouse input. Runs in a background
thread so the UI stays responsive.
"""
from __future__ import annotations

import threading
import time
from typing import Optional

from app.config import Config
from app.core.camera import Camera
from app.core.gestures import GestureEngine
from app.core.mapper import Mapper
from app.core.mouse import (
    button_down, button_up, move_absolute, scroll as mouse_scroll,
)
from app.core.smoothing import PointSmoother
from app.core.tracking import HandTracker


class ControlEngine:
    def __init__(self, config: Config):
        self.config = config
        self.camera: Optional[Camera] = None
        self.tracker: Optional[HandTracker] = None
        self.gestures = GestureEngine(config.settings)
        self.mapper = Mapper(config.calibration, config.settings)
        self.smoother = PointSmoother(
            min_cutoff=self._min_cutoff(),
            beta=self._beta(),
        )

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_frame = None

        # Dragging: button state tracking.
        self._left_down = False

        # Callbacks for the UI.
        self.on_frame = None
        self.on_status = None

    # ------------------------------------------------------------------
    def start(self) -> bool:
        if self._running:
            return True

        self.camera = Camera(self.config.settings.camera_index)
        if not self.camera.start():
            if self.on_status:
                self.on_status(f"Camera error: {self.camera.error}")
            return False

        self.tracker = HandTracker()
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.5)
            self._thread = None
        if self.camera is not None:
            self.camera.stop()
            self.camera = None
        if self.tracker is not None:
            self.tracker.close()
            self.tracker = None
        self.gestures.reset()
        self.smoother.reset()
        self._release_buttons()

    def _release_buttons(self) -> None:
        if self._left_down:
            button_up("left")
            self._left_down = False

    def update_config(self, config: Config) -> None:
        """Apply new settings/calibration without restarting camera.

        Preserves smoother filter state to avoid a positional jump on a
        slider tick; only the parameters are re-tuned.
        """
        self.config = config
        self.gestures.update_settings(config.settings)
        self.mapper = Mapper(config.calibration, config.settings)
        self.smoother.retune(
            min_cutoff=self._min_cutoff(),
            beta=self._beta(),
        )

    def _min_cutoff(self) -> float:
        # Lower smoothing (and lower absolute cutoff) than before to keep
        # group delay small; still higher smoothing -> more filtering.
        return 0.6 + self.config.settings.smoothing * 2.0

    def _beta(self) -> float:
        return 0.02 + self.config.settings.smoothing * 0.06

    def _loop(self) -> None:
        while self._running and self.camera is not None:
            frame = self.camera.read()
            if frame is None:
                time.sleep(0.005)
                continue

            result = self.tracker.process(frame)
            gesture = self.gestures.analyze(result)

            self._apply_gesture(gesture)

            if self.on_frame is not None:
                self.on_frame(frame, result, gesture)
            if self.on_status is not None and result.hands:
                self.on_status(f"Hands: {len(result.hands)}")

            # Small sleep to yield; camera read() already returns the latest
            # frame so we never build a queue of stale frames.
            time.sleep(0.002)

    def _apply_gesture(self, gesture: dict) -> None:
        point = gesture.get("point")

        # Cursor movement.
        if gesture.get("moving") and point is not None:
            now = time.perf_counter()
            sx, sy = self.smoother.update(point[0], point[1], now)
            px, py = self.mapper.to_screen(sx, sy)
            move_absolute(px, py)

        # Left click (short pinch tap).
        if gesture.get("left_click"):
            self._left_down = False
            button_down("left")
            button_up("left")

        # Right click.
        if gesture.get("right_click"):
            button_down("right")
            button_up("right")

        # Drag: hold left button while moving.
        if gesture.get("dragging"):
            if not self._left_down:
                button_down("left")
                self._left_down = True
        else:
            if self._left_down:
                button_up("left")
                self._left_down = False

        # Scroll.
        if gesture.get("scroll"):
            mouse_scroll(int(gesture["scroll"]) * self.config.settings.scroll_sensitivity)

        # Two-hand zoom.
        if gesture.get("zoom"):
            mouse_scroll(int(gesture["zoom"]) * self.config.settings.scroll_sensitivity)