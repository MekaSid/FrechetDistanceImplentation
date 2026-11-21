"""Minimum-enclosing-ball preprocessing for insertion transitions."""

from __future__ import annotations

from dataclasses import dataclass
from collections import deque
import math

import numpy as np
from numpy.typing import NDArray

from .geometry import Ball, fits_in_delta, minimum_enclosing_ball


@dataclass(frozen=True)
class MuPreprocessing:
    """One-indexed ``mu`` values; element zero is unused."""

    mu: tuple[int, ...]


def compute_mu(pi: NDArray[np.float64], delta: float) -> MuPreprocessing:
    """Compute all mu values in O(m^2) expected time.

    The left boundary moves only forward. There are O(m) MEB calls in total,
    each costing expected O(m) time in 2D.
    """

    m = len(pi)
    values = [0] * (m + 1)
    left = 1
    for i in range(1, m + 1):
        while True:
            ball = minimum_enclosing_ball(pi[left - 1 : i], seed=31 * i + left)
            if fits_in_delta(ball, delta):
                values[i] = left
                break
            left += 1
    return MuPreprocessing(tuple(values))


def compute_mu_reference(pi: NDArray[np.float64], delta: float) -> MuPreprocessing:
    """Clear O(m^3)-worst-case reference implementation used by tests."""

    m = len(pi)
    values = [0] * (m + 1)
    for i in range(1, m + 1):
        for left in range(1, i + 1):
            if fits_in_delta(minimum_enclosing_ball(pi[left - 1 : i]), delta):
                values[i] = left
                break
    return MuPreprocessing(tuple(values))


def insertion_ball(pi: NDArray[np.float64], start: int, end: int) -> Ball:
    """Ball for zero-indexed half-open reference block ``pi[start:end]``."""

    return minimum_enclosing_ball(pi[start:end], seed=97 * end + start)


class SlidingMinimum:
    """Monotonic queue over already computed rows of one DP column."""

    def __init__(self) -> None:
        self._items: deque[tuple[int, float]] = deque()

    def add(self, index: int, value: float) -> None:
        while self._items and self._items[-1][1] >= value:
            self._items.pop()
        self._items.append((index, value))

    def discard_before(self, index: int) -> None:
        while self._items and self._items[0][0] < index:
            self._items.popleft()

    @property
    def minimum(self) -> tuple[int, float]:
        return self._items[0] if self._items else (-1, math.inf)

