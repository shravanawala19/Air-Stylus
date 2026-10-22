"""Hand landmark extraction via MediaPipe Tasks (HandLandmarker).

Consumes RGB frames from the Camera and returns normalized 21-landmark data
for up to two hands. Landmarks are indexed per the MediaPipe Hands spec.

Uses the modern `mp.tasks` API (legacy `mp.solutions` is not bundled with
mediapipe >= 0.10.30). Requires the `hand_landmarker.task` model file, which
is bundled under `models/`.
"""
from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

# MediaPipe Hands landmark indices.
WRIST = 0
THUMB_CMC = 1
THUMB_TIP = 4
INDEX_MCP = 5
INDEX_TIP = 8
MIDDLE_TIP = 12
RING_TIP = 16
PINKY_TIP = 20

# Default location of the model, relative to this file.
def _default_model_path() -> str:
    # When frozen with PyInstaller, bundled data lives in sys._MEIPASS.
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, "models", "hand_landmarker.task")
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "models", "hand_landmarker.task",
    )


_MODEL_PATH = _default_model_path()


@dataclass
class Hand:
    """A single detected hand with its 21 landmarks (normalized 0..1)."""
    handedness: str                       # "Left" or "Right"
    confidence: float
    landmarks: np.ndarray                 # shape (21, 2), x, y normalized

    def tip(self, idx: int) -> np.ndarray:
        return self.landmarks[idx]

    @property
    def index_tip(self) -> np.ndarray:
        return self.landmarks[INDEX_TIP]

    @property
    def thumb_tip(self) -> np.ndarray:
        return self.landmarks[THUMB_TIP]

    @property
    def middle_tip(self) -> np.ndarray:
        return self.landmarks[MIDDLE_TIP]

    @property
    def palm_center(self) -> np.ndarray:
        return self.landmarks[[0, 5, 9, 13, 17]].mean(axis=0)


@dataclass
class TrackingResult:
    hands: List[Hand] = field(default_factory=list)

    def handed(self, handedness: str) -> Optional[Hand]:
        for h in self.hands:
            if h.handedness == handedness:
                return h
        return None


class HandTracker:
    def __init__(self, max_hands: int = 2, detection_conf: float = 0.5,
                 tracking_conf: float = 0.5, model_path: Optional[str] = None):
        self.max_hands = max_hands
        self.model_path = model_path or _MODEL_PATH

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Hand landmarker model not found: {self.model_path}")

        base_options = mp_python.BaseOptions(model_asset_path=self.model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=max_hands,
            min_hand_detection_confidence=detection_conf,
            min_hand_presence_confidence=detection_conf,
            min_tracking_confidence=tracking_conf,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)

    def process(self, frame: np.ndarray) -> TrackingResult:
        """Run detection on an RGB frame and return normalized landmarks."""
        result = TrackingResult()

        if frame.dtype != np.uint8:
            frame = frame.astype(np.uint8)
        if frame.ndim != 3 or frame.shape[-1] != 3:
            return result

        frame.flags.writeable = False
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB, data=frame)
        # MediaPipe's VIDEO mode needs real monotonic timestamps (ms) for
        # stable temporal tracking. A manual counter desyncs with variable
        # inference latency and degrades accuracy over time.
        timestamp_ms = int(time.monotonic() * 1000)
        mp_result = self._landmarker.detect_for_video(
            mp_image, timestamp_ms)
        frame.flags.writeable = True

        if not mp_result.hand_landmarks:
            return result

        for lm_list, handedness in zip(
                mp_result.hand_landmarks, mp_result.handedness):
            pts = np.array(
                [[lm.x, lm.y] for lm in lm_list], dtype=np.float32)
            label = handedness[0].category_name or "Right"
            if label not in ("Left", "Right"):
                label = "Right"
            confidence = float(handedness[0].score) if handedness[0].score else 0.0
            result.hands.append(Hand(label, confidence, pts))

        return result

    def close(self) -> None:
        try:
            self._landmarker.close()
        except Exception:
            pass