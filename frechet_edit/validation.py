"""Input normalization shared by all algorithms."""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np
from numpy.typing import NDArray

Curve = NDArray[np.float64]


def as_curve(points: Iterable[Iterable[float]] | NDArray[np.floating], name: str) -> Curve:
    """Return a finite, nonempty, two-dimensional floating-point array."""

    try:
        curve = np.asarray(points, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a rectangular numeric point sequence") from exc
    if curve.ndim != 2:
        raise ValueError(f"{name} must have shape (number_of_points, dimension)")
    if curve.shape[0] == 0:
        raise ValueError(f"{name} must be nonempty")
    if curve.shape[1] != 2:
        raise ValueError(f"{name} must contain 2D points; got dimension {curve.shape[1]}")
    if not np.isfinite(curve).all():
        raise ValueError(f"{name} coordinates must all be finite")
    return curve


def validate_curves(
    pi: Iterable[Iterable[float]] | NDArray[np.floating],
    sigma: Iterable[Iterable[float]] | NDArray[np.floating],
) -> tuple[Curve, Curve]:
    reference = as_curve(pi, "pi")
    editable = as_curve(sigma, "sigma")
    if reference.shape[1] != editable.shape[1]:
        raise ValueError("pi and sigma must have the same point dimension")
    return reference, editable


def validate_problem(
    pi: Iterable[Iterable[float]] | NDArray[np.floating],
    sigma: Iterable[Iterable[float]] | NDArray[np.floating],
    delta: float,
) -> tuple[Curve, Curve, float]:
    reference, editable = validate_curves(pi, sigma)
    threshold = float(delta)
    if not math.isfinite(threshold) or threshold < 0:
        raise ValueError("delta must be finite and nonnegative")
    return reference, editable, threshold

