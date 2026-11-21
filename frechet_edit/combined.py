"""Combined insertion/deletion discrete Frechet edit distance (Section 5.3)."""

from __future__ import annotations

import math
import numpy as np

from .preprocessing import SlidingMinimum, compute_mu
from .results import EditResult, build_result
from .validation import validate_problem


def insertions_and_deletions(
    pi, sigma, delta: float, *, return_witness: bool = False, return_table: bool = False
) -> EditResult:
    if return_witness:
        raise NotImplementedError(
            "verified combined-edit witness reconstruction is not implemented; "
            "the exact optimal count and DP table are available"
        )
    reference, editable, threshold = validate_problem(pi, sigma, delta)
    m, n = len(reference), len(editable)
    mu = compute_mu(reference, threshold).mu
    table = np.full((m + 1, n + 1), math.inf, dtype=float)
    choices = np.full((m + 1, n + 1), None, dtype=object)
    insert_from = np.full((m + 1, n + 1), -1, dtype=np.int64)
    table[0, 0] = 0.0
    for j in range(1, n + 1):
        table[0, j] = table[0, j - 1] + 1.0
        choices[0, j] = "delete"

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
                candidates = [
                    (table[i, j - 1] + 1.0, "delete", -1),
                    (insertion, "insert", predecessor),
                ]
            else:
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
        method="insertions-and-deletions",
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


def insertions_and_deletions_reference(pi, sigma, delta: float) -> EditResult:
    """Slow O(m^2 n) range-minimum reference DP for testing."""

    reference, editable, threshold = validate_problem(pi, sigma, delta)
    m, n = len(reference), len(editable)
    mu = compute_mu(reference, threshold).mu
    table = np.full((m + 1, n + 1), math.inf, dtype=float)
    table[0, :] = np.arange(n + 1, dtype=float)
    for j in range(n + 1):
        for i in range(1, m + 1):
            insertion = 1 + min(table[mu[i] - 1 : i, j])
            if j == 0:
                table[i, j] = insertion
            elif np.linalg.norm(reference[i - 1] - editable[j - 1]) > threshold:
                table[i, j] = min(table[i, j - 1] + 1, insertion)
            else:
                table[i, j] = min(
                    table[i, j - 1], table[i - 1, j], table[i - 1, j - 1], insertion
                )
    value = int(table[m, n])
    return EditResult(value, True, "insertions-and-deletions-reference")

