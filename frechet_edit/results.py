"""Results and independently checked witness reconstruction."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Literal

import numpy as np
from numpy.typing import NDArray

from .frechet import ordinary_discrete_frechet
from .preprocessing import insertion_ball


@dataclass(frozen=True)
class EditOperation:
    kind: Literal["insert", "delete"]
    position: int | None = None
    original_index: int | None = None
    point: tuple[float, float] | None = None
    reference_range: tuple[int, int] | None = None


@dataclass
class EditResult:
    min_edits: int | float
    feasible: bool
    method: str
    edited_sigma: NDArray[np.float64] | None = None
    operations: tuple[EditOperation, ...] = ()
    dp_table: NDArray[np.float64] | None = field(default=None, repr=False)
    mu: tuple[int, ...] | None = None

    def as_dict(self) -> dict:
        return {
            "method": self.method,
            "min_edits": "Infinity" if math.isinf(self.min_edits) else self.min_edits,
            "feasible": self.feasible,
            "edited_sigma": None if self.edited_sigma is None else self.edited_sigma.tolist(),
            "operations": [operation.__dict__ for operation in self.operations],
            "mu": self.mu,
        }


def build_result(
    *,
    method: str,
    pi: NDArray[np.float64],
    sigma: NDArray[np.float64],
    delta: float,
    table: NDArray[np.float64],
    choices: NDArray[np.object_],
    insert_from: NDArray[np.int64] | None = None,
    mu: tuple[int, ...] | None = None,
    return_witness: bool = False,
    return_table: bool = False,
) -> EditResult:
    value = float(table[-1, -1])
    if math.isinf(value):
        return EditResult(math.inf, False, method, dp_table=table if return_table else None, mu=mu)
    minimum = int(value)
    result = EditResult(minimum, True, method, dp_table=table if return_table else None, mu=mu)
    if not return_witness:
        return result

    i, j = len(pi), len(sigma)
    reverse_provenance: list[tuple[str, object]] = []
    deleted: list[int] = []
    while i > 0 or j > 0:
        action = choices[i, j]
        if action == "delete":
            deleted.append(j - 1)
            j -= 1
        elif action == "keep-diagonal":
            reverse_provenance.append(("original", j - 1))
            i -= 1
            j -= 1
        elif action == "keep-horizontal":
            reverse_provenance.append(("original", j - 1))
            j -= 1
        elif action == "keep-vertical":
            i -= 1
        elif action == "insert":
            if insert_from is None:
                raise RuntimeError("missing insertion predecessor table")
            start = int(insert_from[i, j])
            ball = insertion_ball(pi, start, i)
            reverse_provenance.append(("insert", (ball.center.copy(), start, i)))
            i = start
        else:
            raise RuntimeError(f"cannot backtrack {method} at ({i}, {j}); action={action!r}")

    provenance = list(reversed(reverse_provenance))
    points: list[NDArray[np.float64]] = []
    operations: list[EditOperation] = [
        EditOperation("delete", original_index=index) for index in sorted(deleted)
    ]
    for position, (kind, payload) in enumerate(provenance):
        if kind == "original":
            points.append(sigma[int(payload)].copy())
        else:
            point, start, end = payload
            points.append(point)
            operations.append(
                EditOperation(
                    "insert",
                    position=position,
                    point=(float(point[0]), float(point[1])),
                    reference_range=(int(start), int(end)),
                )
            )
    edited = np.asarray(points, dtype=float)
    if edited.ndim != 2 or len(edited) == 0:
        raise RuntimeError("backtracking produced an invalid empty curve")
    if len(operations) != minimum:
        raise RuntimeError("witness edit count does not match the dynamic program")
    witness_distance = ordinary_discrete_frechet(pi, edited)
    tolerance = 1e-9 * max(1.0, delta)
    if witness_distance > delta + tolerance:
        raise RuntimeError(
            f"witness failed verification: distance {witness_distance} exceeds delta {delta}"
        )
    result.edited_sigma = edited
    result.operations = tuple(operations)
    return result

