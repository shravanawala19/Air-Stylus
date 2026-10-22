"""Configuration loading and saving for AIRstylus.

All tunable settings live in a single JSON file next to the app so users can
back it up and it persists across launches.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict, field
from typing import Any


APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(APP_DIR, "config.json")


@dataclass
class CalibrationData:
    """Maps a hand-defined region in camera space to the full screen."""
    x_min: float = 0.15
    x_max: float = 0.85
    y_min: float = 0.15
    y_max: float = 0.85
    invert_x: bool = False
    invert_y: bool = False


@dataclass
class SettingsData:
    sensitivity: float = 1.0          # cursor speed multiplier
    smoothing: float = 0.5            # 0..1, higher = more smoothing
    edge_ease: float = 0.35           # 0..1 non-linear reach toward screen corners
    edge_pad: float = 0.08            # 0..0.5 calibrated-region auto-pad fraction
    pinch_threshold: float = 0.05     # normalized distance to register pinch
    pinch_hysteresis: float = 0.012   # debounce band on top of threshold
    click_hold_seconds: float = 0.35  # pinch hold time to start drag
    scroll_sensitivity: float = 1.0   # wheel delta multiplier
    enable_two_hand: bool = True
    camera_index: int = 0
    flip_preview: bool = False


@dataclass
class Config:
    calibration: CalibrationData = field(default_factory=CalibrationData)
    settings: SettingsData = field(default_factory=SettingsData)


def _as_dict(obj: Any) -> dict:
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _as_dict(v) for k, v in asdict(obj).items()}
    return obj


def load_config(path: str = CONFIG_PATH) -> Config:
    cfg = Config()
    if not os.path.exists(path):
        return cfg
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)

        cal = raw.get("calibration", {})
        if cal:
            for k in CalibrationData.__dataclass_fields__:
                if k in cal:
                    setattr(cfg.calibration, k, cal[k])

        st = raw.get("settings", {})
        if st:
            for k in SettingsData.__dataclass_fields__:
                if k in st:
                    setattr(cfg.settings, k, st[k])
    except (OSError, json.JSONDecodeError):
        pass
    return cfg


def save_config(cfg: Config, path: str = CONFIG_PATH) -> None:
    data = {
        "calibration": _as_dict(cfg.calibration),
        "settings": _as_dict(cfg.settings),
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)