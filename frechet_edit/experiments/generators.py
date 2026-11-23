"""Seeded synthetic curve families used by the experimental evaluation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from .config import SCENARIOS


@dataclass(frozen=True)
class GeneratedCurves:
    pi: NDArray[np.float64]
    sigma: NDArray[np.float64]
    scenario: str
    seed: int


def _resample(curve: NDArray[np.float64], count: int) -> NDArray[np.float64]:
    """Linearly resample a polyline by normalized vertex position."""

    if len(curve) == 1:
        return np.repeat(curve, count, axis=0)
    source = np.linspace(0.0, 1.0, len(curve))
    target = np.linspace(0.0, 1.0, count)
    return np.column_stack(
        [np.interp(target, source, curve[:, dimension]) for dimension in range(2)]
    )


def _normalize_to_reference(
    pi: NDArray[np.float64], sigma: NDArray[np.float64]
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Scale by the reference bounding box so delta values are comparable."""

    lower = np.min(pi, axis=0)
    scale = float(np.max(np.ptp(pi, axis=0)))
    if scale <= 1e-12:
        scale = 1.0
    return (pi - lower) / scale, (sigma - lower) / scale


def _smooth_reference(m: int) -> NDArray[np.float64]:
    t = np.linspace(0.0, 1.0, m)
    return np.column_stack((t, 0.35 * np.sin(3.0 * np.pi * t) + 0.15 * np.sin(7.0 * np.pi * t)))


def _random_walk_reference(m: int, rng: np.random.Generator) -> NDArray[np.float64]:
    steps = rng.normal(size=(m, 2))
    steps[0] = 0.0
    return np.cumsum(steps, axis=0)


def generate_curves(
    scenario: str,
    m: int,
    n: int,
    *,
    seed: int,
    noise: float = 0.03,
    corruption_rate: float = 0.1,
    outlier_scale: float = 1.5,
) -> GeneratedCurves:
    """Generate one deterministic pair of nonempty 2D curves.

    All pairs are scaled relative to ``pi``. Consequently the same threshold
    has a comparable geometric meaning across sizes and scenario families.
    """

    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario {scenario!r}")
    if m < 1 or n < 1:
        raise ValueError("m and n must be positive")
    if noise < 0 or outlier_scale < 0 or not 0 <= corruption_rate <= 1:
        raise ValueError("invalid generator parameters")

    rng = np.random.default_rng(seed)
    if scenario == "random_walk":
        pi = _random_walk_reference(m, rng)
    else:
        pi = _smooth_reference(m)

    if scenario == "undersampled":
        # Sampling by vertex position intentionally creates long gaps when n < m.
        indices = np.rint(np.linspace(0, m - 1, n)).astype(int)
        sigma = pi[indices].copy()
    else:
        sigma = _resample(pi, n)

    pi, sigma = _normalize_to_reference(pi, sigma)
    # Noise and corruption are applied after normalization so their magnitudes
    # retain the same meaning as m changes, including for random walks.
    sigma = sigma + rng.normal(scale=noise, size=sigma.shape)

    if scenario == "outliers":
        count = max(1, int(round(corruption_rate * n))) if corruption_rate > 0 else 0
        if count:
            indices = rng.choice(n, size=min(count, n), replace=False)
            directions = rng.normal(size=(len(indices), 2))
            norms = np.linalg.norm(directions, axis=1, keepdims=True)
            directions /= np.maximum(norms, 1e-12)
            sigma[indices] += outlier_scale * directions
    elif scenario == "repeated" and n > 1:
        count = max(1, int(round(corruption_rate * n))) if corruption_rate > 0 else 0
        for index in sorted(rng.choice(np.arange(1, n), size=min(count, n - 1), replace=False)):
            sigma[index] = sigma[index - 1]

    return GeneratedCurves(pi, sigma, scenario, seed)
