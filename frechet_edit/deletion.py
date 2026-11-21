"""Deletion-only discrete Frechet edit distance (paper Section 5.1)."""

from __future__ import annotations

import math
import numpy as np

from .results import EditResult, build_result
from .validation import validate_problem


def deletions_only(
    pi, sigma, delta: float, *, return_witness: bool = False, return_table: bool = False
) -> EditResult:
    reference, editable, threshold = validate_problem(pi, sigma, delta)
    m, n = len(reference), len(editable)
    table = np.full((m + 1, n + 1), math.inf, dtype=float)
    choices = np.full((m + 1, n + 1), None, dtype=object)
    table[0, 0] = 0.0
    for j in range(1, n + 1):
        table[0, j] = table[0, j - 1] + 1.0
        choices[0, j] = "delete"
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            near = np.linalg.norm(reference[i - 1] - editable[j - 1]) <= threshold
            if not near:
                table[i, j] = table[i, j - 1] + 1.0
                choices[i, j] = "delete"
                continue
            candidates = [
                (table[i - 1, j - 1], "keep-diagonal"),
                (table[i - 1, j], "keep-vertical"),
                (table[i, j - 1], "keep-horizontal"),
            ]
            table[i, j], choices[i, j] = min(candidates, key=lambda item: item[0])
    return build_result(
        method="deletions-only",
        pi=reference,
        sigma=editable,
        delta=threshold,
        table=table,
        choices=choices,
        return_witness=return_witness,
        return_table=return_table,
    )

