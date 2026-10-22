"""Signal smoothing for jitter-free air-mouse cursor control.

Implements:
  - Exponential moving average (EMA) positional smoothing.
  - A One-Euro style adaptive low-pass filter that is stable at slow speeds
    but responsive during fast hand swipes, with FPS-aware tuning.
  - Hysteresis helper for de-bouncing pinch/click thresholds.

The One-Euro filter computes dt from real monotonic time rather than assuming
a fixed frame rate, which keeps group delay low and consistent even when the
tracking FPS varies.
"""
from __future__ import annotations

import math
import time


class EMA:
    """Single-axis exponential moving average."""
    def __init__(self, alpha: float = 0.5):
        self.alpha = alpha
        self.value: float | None = None

    def update(self, x: float) -> float:
        if self.value is None:
            self.value = x
        else:
            self.value = self.alpha * x + (1.0 - self.alpha) * self.value
        return self.value

    def reset(self) -> None:
        self.value = None


class OneEuroFilter:
    """One Euro filter: low-pass with adaptive cutoff based on derivative."""
    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.0,
                 d_cutoff: float = 1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.x_prev: float | None = None
        self.dx_prev: float = 0.0
        self.t_prev: float | None = None

    def _alpha(self, cutoff: float, dt: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def update(self, x: float, t: float | None = None) -> float:
        if t is None:
            t = time.perf_counter()

        if self.x_prev is None:
            self.x_prev = x
            self.t_prev = t
            return x

        dt = t - self.t_prev
        if dt <= 0.0:
            return self.x_prev
        dt = min(dt, 0.1)

        dx = (x - self.x_prev) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        self.dx_prev = a_d * dx + (1.0 - a_d) * self.dx_prev

        cutoff = self.min_cutoff + self.beta * abs(self.dx_prev)
        a = self._alpha(cutoff, dt)

        self.x_prev = a * x + (1.0 - a) * self.x_prev
        self.t_prev = t
        return self.x_prev

    def reset(self) -> None:
        self.x_prev = None
        self.dx_prev = 0.0
        self.t_prev = None


class PointSmoother:
    """Smooths 2D points using a pair of One-Euro filters.

    Supports re-tuning parameters without resetting filter state, so a
    settings change mid-session does not cause a positional jump.
    """
    def __init__(self, min_cutoff: float = 1.5, beta: float = 0.05,
                 d_cutoff: float = 1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.fx = OneEuroFilter(min_cutoff, beta, d_cutoff)
        self.fy = OneEuroFilter(min_cutoff, beta, d_cutoff)

    def retune(self, min_cutoff: float | None = None,
               beta: float | None = None,
               d_cutoff: float | None = None) -> None:
        """Update parameters in place, preserving current filter state."""
        if min_cutoff is not None:
            self.min_cutoff = min_cutoff
        if beta is not None:
            self.beta = beta
        if d_cutoff is not None:
            self.d_cutoff = d_cutoff
        for f in (self.fx, self.fy):
            f.min_cutoff = self.min_cutoff
            f.beta = self.beta
            f.d_cutoff = self.d_cutoff

    def update(self, x: float, y: float, t: float | None = None) -> tuple[float, float]:
        if t is None:
            t = time.perf_counter()
        return self.fx.update(x, t), self.fy.update(y, t)

    def reset(self) -> None:
        self.fx.reset()
        self.fy.reset()


class Hysteresis:
    """De-bounces a boolean signal around a threshold."""
    def __init__(self, threshold: float, margin: float = 0.0):
        self.threshold = threshold
        self.margin = margin
        self.state: bool = False

    def update(self, value: float) -> bool:
        if not self.state:
            self.state = value < self.threshold
        else:
            self.state = value < (self.threshold + self.margin)
        return self.state

    def reset(self) -> None:
        self.state = False