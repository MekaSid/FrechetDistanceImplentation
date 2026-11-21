import itertools
import math

import numpy as np
import pytest

from frechet_edit import (
    deletions_only,
    insertions_and_deletions,
    insertions_only,
    ordinary_discrete_frechet,
)
from frechet_edit.combined import insertions_and_deletions_reference
from frechet_edit.insertion import insertions_only_reference
from frechet_edit.preprocessing import compute_mu, compute_mu_reference


def brute_force_deletions(pi, sigma, delta):
    best = math.inf
    for length in range(1, len(sigma) + 1):
        for indices in itertools.combinations(range(len(sigma)), length):
            candidate = sigma[list(indices)]
            if ordinary_discrete_frechet(pi, candidate) <= delta + 1e-12:
                best = min(best, len(sigma) - length)
    return best


def test_optimized_mu_matches_reference():
    rng = np.random.default_rng(2024)
    for m in range(1, 9):
        for _ in range(20):
            pi = rng.normal(size=(m, 2))
            delta = float(rng.uniform(0, 2))
            assert compute_mu(pi, delta).mu == compute_mu_reference(pi, delta).mu


def test_optimized_dps_match_slow_range_minimum_versions():
    rng = np.random.default_rng(58)
    for m in range(1, 7):
        for n in range(1, 6):
            for _ in range(15):
                pi = rng.integers(-2, 3, size=(m, 2)).astype(float)
                sigma = rng.integers(-2, 3, size=(n, 2)).astype(float)
                delta = float(rng.choice([0, 0.5, 1, 2]))
                assert insertions_only(pi, sigma, delta).min_edits == insertions_only_reference(
                    pi, sigma, delta
                ).min_edits
                assert insertions_and_deletions(
                    pi, sigma, delta
                ).min_edits == insertions_and_deletions_reference(pi, sigma, delta).min_edits


def test_deletion_dp_matches_subsequence_oracle():
    rng = np.random.default_rng(9)
    for m in range(1, 5):
        for n in range(1, 7):
            for _ in range(12):
                pi = rng.integers(-1, 3, size=(m, 2)).astype(float)
                sigma = rng.integers(-1, 3, size=(n, 2)).astype(float)
                delta = float(rng.choice([0, 1, 2]))
                assert deletions_only(pi, sigma, delta).min_edits == brute_force_deletions(
                    pi, sigma, delta
                )


def test_global_invariants_and_monotonicity():
    rng = np.random.default_rng(101)
    for _ in range(80):
        m, n = rng.integers(1, 7, size=2)
        pi = rng.integers(-2, 3, size=(m, 2)).astype(float)
        sigma = rng.integers(-2, 3, size=(n, 2)).astype(float)
        previous = [math.inf, math.inf, math.inf]
        for delta in (0.0, 0.5, 1.0, 2.0, 5.0):
            results = [
                deletions_only(pi, sigma, delta).min_edits,
                insertions_only(pi, sigma, delta).min_edits,
                insertions_and_deletions(pi, sigma, delta).min_edits,
            ]
            assert all(current <= old for current, old in zip(results, previous))
            if math.isfinite(results[0]):
                assert results[2] <= results[0]
            if math.isfinite(results[1]):
                assert results[2] <= results[1]
            assert results[2] <= m + n
            zero_expected = ordinary_discrete_frechet(pi, sigma) <= delta + 1e-12
            assert all((value == 0) == zero_expected for value in results)
            previous = results


def test_random_deletion_witnesses_validate():
    rng = np.random.default_rng(17)
    for _ in range(80):
        m, n = rng.integers(1, 7, size=2)
        pi = rng.normal(size=(m, 2))
        sigma = rng.normal(size=(n, 2))
        delta = float(rng.uniform(0, 1.5))
        result = deletions_only(pi, sigma, delta, return_witness=True)
        if result.feasible:
            assert len(result.operations) == result.min_edits
            assert ordinary_discrete_frechet(pi, result.edited_sigma) <= delta + 1e-9

