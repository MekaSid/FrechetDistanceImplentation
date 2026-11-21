"""Exact strong discrete Frechet edit-distance algorithms."""

from .combined import insertions_and_deletions
from .deletion import deletions_only
from .frechet import ordinary_discrete_frechet
from .insertion import insertions_only
from .results import EditOperation, EditResult

__all__ = [
    "EditOperation",
    "EditResult",
    "ordinary_discrete_frechet",
    "deletions_only",
    "insertions_only",
    "insertions_and_deletions",
]

