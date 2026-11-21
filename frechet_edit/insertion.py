"""Insertion-only discrete Frechet edit distance (paper Section 5.2)."""

from __future__ import annotations

import math
import numpy as np

from .preprocessing import SlidingMinimum, compute_mu
from .results import EditResult, build_result
from .validation import validate_problem


def insertions_only(
    pi, sigma, delta: float, *, return_witness: bool = False, return_table: bool = False
) -> EditResult:
    if return_witness:
        raise NotImplementedError(
            "verified insertion witness reconstruction is not implemented; "
            "the exact optimal count and DP table are available"
        )
    reference, editable, threshold = validate_problem(pi, sigma, delta)
    m, n = len(reference), len(editable)
    mu = compute_mu(reference, threshold).mu
    table = np.full((m + 1, n + 1), math.inf, dtype=float)
    choices = np.full((m + 1, n + 1), None, dtype=object)
    insert_from = np.full((m + 1, n + 1), -1, dtype=np.int64)
    table[0, 0] = 0.0

    for j in range(n + 1):
        window = SlidingMinimum()
        for i in range(1, m + 1):
            window.add(i - 1, float(table[i - 1, j]))
            window.discard_before(mu[i] - 1)
            predecessor, minimum = window.minimum
            insertion = 1.0 + minimum
            if j == 0:
                table[i, j] = insertion
                choices[i, j] = "insert"
                insert_from[i, j] = predecessor
                continue
            near = np.linalg.norm(reference[i - 1] - editable[j - 1]) <= threshold
            if not near:
                table[i, j] = insertion
                choices[i, j] = "insert"
                insert_from[i, j] = predecessor
                continue
            candidates = [
                (table[i - 1, j - 1], "keep-diagonal", -1),
                (table[i - 1, j], "keep-vertical", -1),
                (table[i, j - 1], "keep-horizontal", -1),
                (insertion, "insert", predecessor),
            ]
            value, action, source = min(candidates, key=lambda item: item[0])
            table[i, j] = value
            choices[i, j] = action
            insert_from[i, j] = source
    return build_result(
        method="insertions-only",
        pi=reference,
        sigma=editable,
        delta=threshold,
        table=table,
        choices=choices,
        insert_from=insert_from,
        mu=mu,
        return_witness=return_witness,
        return_table=return_table,
    )


def insertions_only_reference(pi, sigma, delta: float) -> EditResult:
    """Slow O(m^2 n) range-minimum reference DP for testing."""

    reference, editable, threshold = validate_problem(pi, sigma, delta)
    m, n = len(reference), len(editable)
    mu = compute_mu(reference, threshold).mu
    table = np.full((m + 1, n + 1), math.inf, dtype=float)
    table[0, 0] = 0.0
    for j in range(n + 1):
        for i in range(1, m + 1):
            insertion = 1 + min(table[mu[i] - 1 : i, j])
            if j == 0 or np.linalg.norm(reference[i - 1] - editable[j - 1]) > threshold:
                table[i, j] = insertion
            else:
                table[i, j] = min(
                    table[i, j - 1], table[i - 1, j], table[i - 1, j - 1], insertion
                )
    value = float(table[m, n])
    return EditResult(math.inf if math.isinf(value) else int(value), not math.isinf(value), "insertions-only-reference")

