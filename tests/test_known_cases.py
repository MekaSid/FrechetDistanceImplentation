import math

import numpy as np
import pytest

from frechet_edit import (
    deletions_only,
    insertions_and_deletions,
    insertions_only,
    ordinary_discrete_frechet,
)


def curve(values):
    return [(value, 0.0) for value in values]


@pytest.mark.parametrize(
    "pi,sigma,expected",
    [
        ([0, 1, 2], [0, 1, 2], (0, 0, 0)),
        ([0, 2], [0, 99, 2], (1, math.inf, 1)),
        ([0, 1, 2], [0, 2], (math.inf, 1, 1)),
        ([0, 1, 2], [0, 99, 2], (math.inf, math.inf, 2)),
        ([0, 1, 2], [1], (math.inf, 2, 2)),
        ([0], [99], (math.inf, math.inf, 2)),
    ],
)
def test_paper_brief_examples(pi, sigma, expected):
    points_pi, points_sigma = curve(pi), curve(sigma)
    actual = (
        deletions_only(points_pi, points_sigma, 0).min_edits,
        insertions_only(points_pi, points_sigma, 0).min_edits,
        insertions_and_deletions(points_pi, points_sigma, 0).min_edits,
    )
    assert actual == expected


def test_deletion_witness_is_independently_validated():
    pi = curve([0, 1, 2])
    sigma = curve([0, 99, 2])
    result = deletions_only(pi, sigma, 0, return_witness=True)
    if result.feasible:
        assert ordinary_discrete_frechet(pi, result.edited_sigma) == pytest.approx(0)
        assert len(result.operations) == result.min_edits


def test_minimum_enclosing_ball_can_use_non_input_point():
    from frechet_edit.geometry import minimum_enclosing_ball

    pi = [(0, 0), (2, 0)]
    ball = minimum_enclosing_ball(np.asarray(pi, dtype=float))
    assert ball.center == pytest.approx((1, 0))
    assert ball.radius == pytest.approx(1)


@pytest.mark.parametrize("algorithm", [insertions_only, insertions_and_deletions])
def test_unimplemented_insertion_witness_is_explicit(algorithm):
    with pytest.raises(NotImplementedError, match="witness"):
        algorithm(curve([0, 1]), curve([0]), 0, return_witness=True)


def test_repeated_points_and_threshold_equality():
    pi = [(0, 0), (0, 0), (2, 0)]
    sigma = [(1, 0), (1, 0)]
    assert ordinary_discrete_frechet(pi, sigma) == pytest.approx(1)
    for algorithm in (deletions_only, insertions_only, insertions_and_deletions):
        assert algorithm(pi, sigma, 1).min_edits == 0


def test_dp_table_is_available_on_request():
    result = deletions_only(curve([0, 1]), curve([0, 9, 1]), 0, return_table=True)
    assert result.dp_table.shape == (3, 4)
    assert result.dp_table[-1, -1] == 1


@pytest.mark.parametrize(
    "pi,sigma,delta",
    [([], [(0, 0)], 0), ([(0, 0)], [], 0), ([(0, 0)], [(0, 0)], -1)],
)
def test_invalid_arguments(pi, sigma, delta):
    with pytest.raises(ValueError):
        insertions_and_deletions(pi, sigma, delta)


def test_only_2d_is_currently_supported():
    with pytest.raises(ValueError, match="2D"):
        deletions_only([(0, 0, 0)], [(0, 0, 0)], 0)

