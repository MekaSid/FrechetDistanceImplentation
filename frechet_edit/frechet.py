"""Ordinary strong discrete Frechet distance baseline."""

from __future__ import annotations

import numpy as np

from .validation import validate_curves


def ordinary_discrete_frechet(pi, sigma) -> float:
    """Return the classical O(mn) strong discrete Frechet distance."""

    reference, candidate = validate_curves(pi, sigma)
    m, n = len(reference), len(candidate)
    dp = np.empty((m, n), dtype=float)
    for i in range(m):
        for j in range(n):
            distance = float(np.linalg.norm(reference[i] - candidate[j]))
            if i == 0 and j == 0:
                previous = 0.0
            elif i == 0:
                previous = dp[i, j - 1]
            elif j == 0:
                previous = dp[i - 1, j]
            else:
                previous = min(dp[i - 1, j], dp[i, j - 1], dp[i - 1, j - 1])
            dp[i, j] = max(distance, previous)
    return float(dp[-1, -1])

