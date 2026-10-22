"""Gesture classification from hand landmarks.

Single-hand mode (one hand visible):
  - Open palm / relaxed hand  -> move cursor (palm centroid).
  - Thumb+index pinch        -> left click.
  - Thumb+middle pinch       -> right click.
  - Pinch held beyond threshold -> drag.
  - Two fingers extended, vertical travel -> scroll.

Two-hand mode (both hands visible):
  - Distance between the two hands' index tips -> pinch-zoom (Ctrl+wheel).
"""
from __future__ import annotations

import math
import time
from typing import Optional

import numpy as np

from app.config import SettingsData
from app.core.smoothing import Hysteresis
from app.core.tracking import Hand, TrackingResult


def _distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))


class GestureEngine:
    def __init__(self, settings: SettingsData):
        self.settings = settings
        self.left_pinch = Hysteresis(
            settings.pinch_threshold, settings.pinch_hysteresis)
        self.right_pinch = Hysteresis(
            settings.pinch_threshold, settings.pinch_hysteresis)

        # Drag state.
        self._drag_pressed_at: Optional[float] = None
        self._dragging = False
        self._pinch_active = False
        self._right_prev = False

        # Scroll state.
        self._scroll_prev_y: Optional[float] = None
        self._scroll_accum = 0.0

        # Two-hand zoom state.
        self._zoom_prev_dist: Optional[float] = None

    def update_settings(self, settings: SettingsData) -> None:
        self.settings = settings
        self.left_pinch.threshold = settings.pinch_threshold
        self.left_pinch.margin = settings.pinch_hysteresis
        self.right_pinch.threshold = settings.pinch_threshold
        self.right_pinch.margin = settings.pinch_hysteresis

    def reset(self) -> None:
        self.left_pinch.reset()
        self.right_pinch.reset()
        self._drag_pressed_at = None
        self._dragging = False
        self._pinch_active = False
        self._right_prev = False
        self._scroll_prev_y = None
        self._scroll_accum = 0.0
        self._zoom_prev_dist = None

    def analyze(self, result: TrackingResult) -> dict:
        """Return a structured gesture snapshot for the current frame."""
        if not result.hands:
            self.reset()
            return {"moving": False, "left_click": False,
                    "right_click": False, "dragging": False,
                    "scroll": 0, "zoom": 0, "point": None}

        if len(result.hands) == 2 and self.settings.enable_two_hand:
            return self._two_hand(result)

        return self._single_hand(result.hands[0])

    # ------------------------------------------------------------------
    def _single_hand(self, hand: Hand) -> dict:
        thumb = hand.thumb_tip
        index = hand.index_tip
        middle = hand.middle_tip

        pinch = _distance(thumb, index)
        pinch_mid = _distance(thumb, middle)

        left_pressed = self.left_pinch.update(pinch)
        right_pressed = self.right_pinch.update(pinch_mid)

        # Right click only on the rising edge of the right-pinch.
        right_click = right_pressed and not self._right_prev
        self._right_prev = right_pressed

        # Drag: left pinch sustained past hold threshold.
        dragging, left_click = self._resolve_drag(left_pressed)

        # Scroll: two fingers extended (thumb+index+middle not pinched),
        # use vertical movement of index tip.
        scroll = self._resolve_scroll(hand, left_pressed, right_pressed)

        point = self._move_point(hand)
        return {
            "moving": not left_pressed and not right_pressed,
            "left_click": left_click and not dragging,
            "right_click": right_click,
            "dragging": dragging,
            "scroll": scroll,
            "zoom": 0,
            "point": point,
        }

    def _resolve_drag(self, left_pressed: bool) -> tuple[bool, bool]:
        """Returns (dragging, click_now).

        A pinch that is held longer than click_hold_seconds becomes a drag;
        a quick tap is emitted as a click only on the release transition.
        """
        now = time.monotonic()
        was_pressed = self._pinch_active
        self._pinch_active = left_pressed

        if left_pressed:
            if self._dragging:
                return True, False
            if self._drag_pressed_at is None:
                self._drag_pressed_at = now
            if (now - self._drag_pressed_at) >= self.settings.click_hold_seconds:
                self._dragging = True
                return True, False
            return False, False

        # Pinch is released this frame or idle.
        dragging = self._dragging
        self._dragging = False
        self._drag_pressed_at = None

        # Only emit a click on the falling edge of a short tap.
        if was_pressed and not dragging:
            return False, True
        return False, False

    def _resolve_scroll(self, hand: Hand, left_pressed: bool,
                        right_pressed: bool) -> int:
        """Detect two-finger scroll gesture; returns integer wheel notches."""
        # Only when the hand is open (no pinch) and thumb+index+middle are
        # held apart-ish. Use index tip vertical position delta.
        index = hand.index_tip
        y = float(index[1])

        scroll_active = (not left_pressed and not right_pressed)

        if not scroll_active:
            self._scroll_prev_y = None
            self._scroll_accum = 0.0
            return 0

        if self._scroll_prev_y is None:
            self._scroll_prev_y = y
            return 0

        dy = self._scroll_prev_y - y  # positive = move up = scroll up
        self._scroll_prev_y = y

        # Accumulate and emit notches in whole steps.
        self._scroll_accum += dy * 30.0
        notches = int(self._scroll_accum)
        self._scroll_accum -= notches
        return notches

    def _move_point(self, hand: Hand) -> tuple[float, float]:
        # Use palm center for stable cursor positioning.
        c = hand.palm_center
        return float(c[0]), float(c[1])

    # ------------------------------------------------------------------
    def _two_hand(self, result: TrackingResult) -> dict:
        h1 = result.hands[0]
        h2 = result.hands[1]

        dist = _distance(h1.index_tip, h2.index_tip)

        zoom = 0
        if self._zoom_prev_dist is not None:
            delta = dist - self._zoom_prev_dist
            zoom = int(delta * 60.0)  # +/- wheel notches
        self._zoom_prev_dist = dist

        # Midpoint of the two hands drives the cursor.
        mid = (h1.palm_center + h2.palm_center) / 2.0

        return {
            "moving": True,
            "left_click": False,
            "right_click": False,
            "dragging": False,
            "scroll": 0,
            "zoom": zoom,
            "point": (float(mid[0]), float(mid[1])),
        }