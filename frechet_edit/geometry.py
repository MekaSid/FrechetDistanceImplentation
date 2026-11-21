"""Euclidean geometry used by the insertion algorithms."""

from __future__ import annotations

from dataclasses import dataclass
import random

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class Ball:
    center: NDArray[np.float64]
    radius: float


def euclidean_distance(a: NDArray[np.float64], b: NDArray[np.float64]) -> float:
    return float(np.linalg.norm(a - b))


def _tolerance(radius: float, point: NDArray[np.float64]) -> float:
    scale = max(1.0, abs(radius), float(np.max(np.abs(point))))
    return 1e-12 * scale


def contains(ball: Ball, point: NDArray[np.float64]) -> bool:
    return euclidean_distance(ball.center, point) <= ball.radius + _tolerance(ball.radius, point)


def _diameter_ball(a: NDArray[np.float64], b: NDArray[np.float64]) -> Ball:
    center = (a + b) / 2.0
    return Ball(center, euclidean_distance(center, a))


def _three_point_ball(
    a: NDArray[np.float64], b: NDArray[np.float64], c: NDArray[np.float64]
) -> Ball:
    """Return the minimum circle containing three points, including collinear triples."""

    candidates = [_diameter_ball(a, b), _diameter_ball(a, c), _diameter_ball(b, c)]
    covering = [ball for ball in candidates if all(contains(ball, p) for p in (a, b, c))]
    if covering:
        return min(covering, key=lambda ball: ball.radius)

    ax, ay = a
    bx, by = b
    cx, cy = c
    determinant = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(determinant) <= 1e-15:
        return max(candidates, key=lambda ball: ball.radius)
    a2 = ax * ax + ay * ay
    b2 = bx * bx + by * by
    c2 = cx * cx + cy * cy
    ux = (a2 * (by - cy) + b2 * (cy - ay) + c2 * (ay - by)) / determinant
    uy = (a2 * (cx - bx) + b2 * (ax - cx) + c2 * (bx - ax)) / determinant
    center = np.array([ux, uy], dtype=float)
    return Ball(center, euclidean_distance(center, a))


def minimum_enclosing_ball(
    points: NDArray[np.float64], *, seed: int = 0
) -> Ball:
    """Compute the exact 2D minimum enclosing ball up to floating-point precision.

    This is the randomized incremental algorithm. Its expected running time is
    linear for a fixed dimension; ``seed`` makes experiments reproducible.
    """

    pts = np.asarray(points, dtype=float)
    if pts.ndim != 2 or pts.shape[1] != 2 or pts.shape[0] == 0:
        raise ValueError("points must be a nonempty array of 2D points")
    order = list(range(len(pts)))
    random.Random(seed).shuffle(order)
    shuffled = pts[order]
    ball: Ball | None = None
    for i, p in enumerate(shuffled):
        if ball is not None and contains(ball, p):
            continue
        ball = Ball(p.copy(), 0.0)
        for j in range(i):
            q = shuffled[j]
            if contains(ball, q):
                continue
            ball = _diameter_ball(p, q)
            for k in range(j):
                r = shuffled[k]
                if not contains(ball, r):
                    ball = _three_point_ball(p, q, r)
    assert ball is not None
    return ball


def fits_in_delta(ball: Ball, delta: float) -> bool:
    return ball.radius <= delta + 1e-12 * max(1.0, ball.radius, delta)

