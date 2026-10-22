"""Maps normalized hand coordinates to screen pixel coordinates.

Uses the calibration region (a bounding box in normalized camera space) to
translate hand positions into absolute screen positions.

The mapping is non-linear by design:
  - The calibrated region is auto-padded outward so screen corners sit just
    inside comfortable reach.
  - A smooth "edge ease" curve expands the center (precise) and compresses
    the edges (easy to reach corners) without the unnatural stretch of a
    fully linear map.
  - Sensitivity is applied before clipping so raising it genuinely widens
    how little hand travel you need to reach the screen edge.
"""
from __future__ import annotations

from app.config import CalibrationData, SettingsData
from app.core.mouse import get_screen_size


def _ease(v: float) -> float:
    """Monotonic cubic ease: precise near center, faster near edges.
    Maps [-1..1] -> [-1..1] preserving sign and endpoints."""
    return v * v * v


class Mapper:
    def __init__(self, calibration: CalibrationData, settings: SettingsData):
        self.calibration = calibration
        self.settings = settings

    def screen_bounds(self) -> tuple[int, int]:
        return get_screen_size()

    def to_screen(self, nx: float, ny: float) -> tuple[int, int]:
        """Map normalized hand point (0..1 camera space) to screen pixels."""
        cal = self.calibration
        settings = self.settings
        width, height = self.screen_bounds()

        # Auto-pad the calibrated region outward so the screen corners sit
        # inside comfortable physical reach.
        pad = max(0.0, min(0.5, settings.edge_pad))
        x_range = (cal.x_max - cal.x_min)
        y_range = (cal.y_max - cal.y_min)
        if x_range <= 0:
            x_range = 1.0
        if y_range <= 0:
            y_range = 1.0

        x_min = max(0.0, cal.x_min - x_range * pad)
        x_max = min(1.0, cal.x_max + x_range * pad)
        y_min = max(0.0, cal.y_min - y_range * pad)
        y_max = min(1.0, cal.y_max + y_range * pad)

        x_span = (x_max - x_min) or 1.0
        y_span = (y_max - y_min) or 1.0

        # Normalize to -1..1 relative to the active region center.
        tx = ((nx - x_min) / x_span) * 2.0 - 1.0
        ty = ((ny - y_min) / y_span) * 2.0 - 1.0

        if cal.invert_x:
            tx = -tx
        if cal.invert_y:
            ty = -ty

        # Sensitivity expands/contracts around center BEFORE the ease curve,
        # so a higher sensitivity makes edges reachable sooner.
        sens = max(settings.sensitivity, 0.05)
        tx *= sens
        ty *= sens

        # Non-linear edge ease (mild) so corners are easy to hit while the
        # center stays precise.
        ease = max(0.0, min(1.0, settings.edge_ease))
        if ease > 0:
            tx = ease * _ease(tx) + (1.0 - ease) * tx
            ty = ease * _ease(ty) + (1.0 - ease) * ty

        # Clip only after the transforms, then map to pixels.
        tx = max(-1.0, min(1.0, tx))
        ty = max(-1.0, min(1.0, ty))

        sx = int((tx + 1.0) * 0.5 * width)
        sy = int((ty + 1.0) * 0.5 * height)
        return sx, sy