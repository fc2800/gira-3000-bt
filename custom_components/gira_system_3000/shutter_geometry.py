"""Ideal roller geometry; all lengths in cm, HA positions are 100 = open.

The device's position is assumed proportional to shaft rotation. The extended
curtain length includes slat gaps; after the bottom rail reaches the sill,
further unwinding closes those gaps. This is an approximation, not a sensor.
"""
from math import isfinite, pi, sqrt

CONF_WINDOW_HEIGHT = "window_height_cm"
CONF_CORE_RADIUS = "closed_radius_cm"
CONF_LAYER_THICKNESS = "layer_thickness_cm"
CONF_SLAT_HEIGHT = "slat_height_cm"
CONF_SLAT_GAP = "slat_gap_cm"
CORE_RADIUS = 5.0  # 8 cm shaft diameter plus one remaining 1 cm layer
LAYER_THICKNESS = 1.0
SLAT_HEIGHT = 5.0
SLAT_GAP = 0.5


# option: (default, minimum, maximum); 0 height disables correction.
GEOMETRY_OPTIONS = {
    CONF_WINDOW_HEIGHT: (0.0, 0.0, 1000.0),
    CONF_CORE_RADIUS: (CORE_RADIUS, 0.1, 100.0),
    CONF_LAYER_THICKNESS: (LAYER_THICKNESS, 0.01, 10.0),
    CONF_SLAT_HEIGHT: (SLAT_HEIGHT, 0.1, 100.0),
    CONF_SLAT_GAP: (SLAT_GAP, 0.0, 10.0),
}


class ShutterGeometry:
    """Continuous effective-layer model with reversible positive openings."""

    def __init__(
        self, height: float, core_radius: float = CORE_RADIUS,
        layer_thickness: float = LAYER_THICKNESS,
        slat_height: float = SLAT_HEIGHT, slat_gap: float = SLAT_GAP,
    ) -> None:
        self.height = float(height)
        if not isfinite(self.height) or self.height <= 0:
            raise ValueError("Window height must be finite and positive")
        self.core_radius = float(core_radius)
        self.layer_thickness = float(layer_thickness)
        self.slat_height = float(slat_height)
        self.slat_gap = float(slat_gap)
        for value in (self.core_radius, self.layer_thickness, self.slat_height):
            if not isfinite(value) or value <= 0:
                raise ValueError("Geometry dimensions must be finite and positive")
        if not isfinite(self.slat_gap) or self.slat_gap < 0:
            raise ValueError("Slat gap must be finite and nonnegative")
        self.length = self.height * (1.0 + self.slat_gap / self.slat_height)
        self.radius = sqrt(self.core_radius**2 + self.layer_thickness * self.length / pi)
        self.delta = self.radius - self.core_radius

    def to_opening(self, device_position: float) -> float:
        """Convert device percentage to free window opening percentage."""
        u = 1.0 - min(100.0, max(0.0, device_position)) / 100.0
        unwound = self.length * (
            2.0 * self.radius * u - self.delta * u * u
        ) / (self.radius + self.core_radius)
        return min(100.0, max(0.0, 100.0 * (1.0 - unwound / self.height)))

    def to_device(self, opening: float) -> float:
        """Inverse; zero explicitly means fully closed including all gaps."""
        if opening <= 0:
            return 0.0
        if opening >= 100:
            return 100.0
        length_fraction = self.height * (1.0 - opening / 100.0) / self.length
        # Rationalized quadratic root avoids cancellation near fully open.
        term = length_fraction * (self.radius + self.core_radius)
        u = term / (self.radius + sqrt(self.radius**2 - self.delta * term))
        return 100.0 * (1.0 - u)
