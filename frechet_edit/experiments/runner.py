"""Benchmark runner that writes one tidy CSV row per measured trial."""

from __future__ import annotations

from dataclasses import asdict
import csv
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import tracemalloc
from typing import Callable

import numpy as np

from frechet_edit import (
    deletions_only,
    insertions_and_deletions,
    insertions_only,
    ordinary_discrete_frechet,
)
from frechet_edit.combined import insertions_and_deletions_reference
from frechet_edit.insertion import insertions_only_reference
from frechet_edit.preprocessing import compute_mu, compute_mu_reference
from frechet_edit.results import EditResult

from .config import ExperimentConfig
from .generators import GeneratedCurves, generate_curves


CSV_FIELDS = (
    "experiment",
    "run_timestamp_utc",
    "case_id",
    "scenario",
    "m",
    "n",
    "regime",
    "delta",
    "seed",
    "repetition",
    "algorithm",
    "variant",
    "theoretical_model",
    "work_units",
    "elapsed_ns",
    "elapsed_ms",
    "normalized_ns_per_work",
    "peak_python_bytes",
    "min_edits",
    "feasible",
    "ordinary_distance",
)


def _stable_seed(base: int, *parts: object) -> int:
    payload = "|".join([str(base), *(str(part) for part in parts)]).encode("utf-8")
    return int.from_bytes(hashlib.blake2b(payload, digest_size=8).digest(), "big") % (2**32)


def _regime(m: int, n: int) -> str:
    if m >= 2 * n:
        return "m-dominant"
    if n >= 2 * m:
        return "n-dominant"
    return "balanced"


def _git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


def _git_dirty() -> bool | None:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return bool(result.stdout.strip())


def _memory_peak(function: Callable[[], object]) -> int:
    """Measure peak traced Python/NumPy allocation in a separate invocation."""

    gc.collect()
    tracemalloc.start()
    try:
        function()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return int(peak)


def _timed(function: Callable[[], object]) -> tuple[object, int]:
    gc.collect()
    start = time.perf_counter_ns()
    result = function()
    return result, time.perf_counter_ns() - start


def _work_model(algorithm: str, m: int, n: int) -> tuple[str, int]:
    if algorithm in {"ordinary_discrete_frechet", "deletions_only"}:
        return "m*n", m * n
    if algorithm in {"insertions_only", "insertions_and_deletions"}:
        return "m^2 + m*n", m * m + m * n
    if algorithm in {"insertions_only_reference", "insertions_and_deletions_reference"}:
        return "m^2*n + m^2", m * m * n + m * m
    if algorithm == "compute_mu":
        return "m^2 expected", m * m
    if algorithm == "compute_mu_reference":
        return "m^3 worst-case", m * m * m
    raise KeyError(algorithm)


def _algorithm_functions(curves: GeneratedCurves, delta: float) -> dict[str, Callable[[], object]]:
    pi, sigma = curves.pi, curves.sigma
    return {
        "ordinary_discrete_frechet": lambda: ordinary_discrete_frechet(pi, sigma),
        "deletions_only": lambda: deletions_only(pi, sigma, delta),
        "insertions_only": lambda: insertions_only(pi, sigma, delta),
        "insertions_and_deletions": lambda: insertions_and_deletions(pi, sigma, delta),
        "insertions_only_reference": lambda: insertions_only_reference(pi, sigma, delta),
        "insertions_and_deletions_reference": lambda: insertions_and_deletions_reference(
            pi, sigma, delta
        ),
        "compute_mu": lambda: compute_mu(pi, delta),
        "compute_mu_reference": lambda: compute_mu_reference(pi, delta),
    }


def _outcome(result: object) -> tuple[str, str]:
    if isinstance(result, EditResult):
        edits = "Infinity" if math.isinf(result.min_edits) else str(int(result.min_edits))
        return edits, str(result.feasible).lower()
    return "", ""


def _make_row(
    *,
    config: ExperimentConfig,
    timestamp: str,
    case_id: str,
    curves: GeneratedCurves,
    m: int,
    n: int,
    delta: float,
    repetition: int,
    algorithm: str,
    variant: str,
    elapsed_ns: int,
    peak_bytes: int | None,
    result: object,
    ordinary_distance: float,
) -> dict[str, object]:
    model, work = _work_model(algorithm, m, n)
    edits, feasible = _outcome(result)
    return {
        "experiment": config.name,
        "run_timestamp_utc": timestamp,
        "case_id": case_id,
        "scenario": curves.scenario,
        "m": m,
        "n": n,
        "regime": _regime(m, n),
        "delta": delta,
        "seed": curves.seed,
        "repetition": repetition,
        "algorithm": algorithm,
        "variant": variant,
        "theoretical_model": model,
        "work_units": work,
        "elapsed_ns": elapsed_ns,
        "elapsed_ms": elapsed_ns / 1_000_000.0,
        "normalized_ns_per_work": elapsed_ns / work,
        "peak_python_bytes": "" if peak_bytes is None else peak_bytes,
        "min_edits": edits,
        "feasible": feasible,
        "ordinary_distance": ordinary_distance,
    }


def _assert_reference_matches(
    optimized: object, reference: object, optimized_name: str, case_id: str
) -> None:
    if not isinstance(optimized, EditResult) or not isinstance(reference, EditResult):
        return
    if optimized.min_edits != reference.min_edits:
        raise AssertionError(
            f"{optimized_name} disagrees with its reference on {case_id}: "
            f"{optimized.min_edits!r} != {reference.min_edits!r}"
        )


def run_experiment(
    config: ExperimentConfig,
    output_path: str | Path,
    *,
    progress: Callable[[str], None] | None = None,
) -> Path:
    """Execute a configuration and atomically write its raw tidy CSV data."""

    config.validate()
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rows: list[dict[str, object]] = []

    total_cases = len(config.scenarios) * len(config.size_pairs) * len(config.deltas)
    case_number = 0
    for scenario in config.scenarios:
        for m, n in config.size_pairs:
            case_seed = _stable_seed(config.seed, scenario, m, n)
            curves = generate_curves(
                scenario,
                m,
                n,
                seed=case_seed,
                noise=config.noise,
                corruption_rate=config.corruption_rate,
                outlier_scale=config.outlier_scale,
            )
            ordinary_distance = ordinary_discrete_frechet(curves.pi, curves.sigma)
            for delta in config.deltas:
                case_number += 1
                case_id = f"{scenario}-m{m}-n{n}-d{delta:g}-s{case_seed}"
                if progress is not None:
                    progress(
                        f"[{case_number}/{total_cases}] {scenario}: m={m}, n={n}, delta={delta:g}"
                    )
                functions = _algorithm_functions(curves, delta)
                optimized_results: dict[str, object] = {}
                algorithms = list(config.algorithms)
                if config.include_references and m <= config.reference_max_m and m * n <= config.reference_max_cells:
                    if "insertions_only" in config.algorithms:
                        algorithms.append("insertions_only_reference")
                    if "insertions_and_deletions" in config.algorithms:
                        algorithms.append("insertions_and_deletions_reference")

                for algorithm in algorithms:
                    function = functions[algorithm]
                    for _ in range(config.warmups):
                        function()
                    peak = _memory_peak(function) if config.measure_memory else None
                    first_result: object | None = None
                    for repetition in range(config.repetitions):
                        result, elapsed_ns = _timed(function)
                        if first_result is None:
                            first_result = result
                        rows.append(
                            _make_row(
                                config=config,
                                timestamp=timestamp,
                                case_id=case_id,
                                curves=curves,
                                m=m,
                                n=n,
                                delta=delta,
                                repetition=repetition,
                                algorithm=algorithm,
                                variant="reference" if algorithm.endswith("_reference") else "optimized",
                                elapsed_ns=elapsed_ns,
                                peak_bytes=peak if repetition == 0 else None,
                                result=result,
                                ordinary_distance=ordinary_distance,
                            )
                        )
                    assert first_result is not None
                    optimized_results[algorithm] = first_result

                for reference_name, optimized_name in (
                    ("insertions_only_reference", "insertions_only"),
                    ("insertions_and_deletions_reference", "insertions_and_deletions"),
                ):
                    if reference_name in optimized_results:
                        _assert_reference_matches(
                            optimized_results[optimized_name],
                            optimized_results[reference_name],
                            optimized_name,
                            case_id,
                        )

                if config.include_mu_benchmarks:
                    mu_algorithms = ["compute_mu"]
                    if m <= config.mu_reference_max_m:
                        mu_algorithms.append("compute_mu_reference")
                    mu_results: dict[str, object] = {}
                    for algorithm in mu_algorithms:
                        function = functions[algorithm]
                        for _ in range(config.warmups):
                            function()
                        peak = _memory_peak(function) if config.measure_memory else None
                        first_result = None
                        for repetition in range(config.repetitions):
                            result, elapsed_ns = _timed(function)
                            first_result = result if first_result is None else first_result
                            rows.append(
                                _make_row(
                                    config=config,
                                    timestamp=timestamp,
                                    case_id=case_id,
                                    curves=curves,
                                    m=m,
                                    n=n,
                                    delta=delta,
                                    repetition=repetition,
                                    algorithm=algorithm,
                                    variant="reference" if algorithm.endswith("_reference") else "optimized",
                                    elapsed_ns=elapsed_ns,
                                    peak_bytes=peak if repetition == 0 else None,
                                    result=result,
                                    ordinary_distance=ordinary_distance,
                                )
                            )
                        mu_results[algorithm] = first_result
                    if "compute_mu_reference" in mu_results:
                        if mu_results["compute_mu"].mu != mu_results["compute_mu_reference"].mu:
                            raise AssertionError(f"mu preprocessing mismatch on {case_id}")

    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, output)

    metadata = {
        "config": asdict(config),
        "environment": {
            "python": sys.version,
            "numpy": np.__version__,
            "platform": platform.platform(),
            "processor": platform.processor(),
            "git_commit": _git_commit(),
            "git_dirty": _git_dirty(),
        },
        "measurement_notes": {
            "clock": "time.perf_counter_ns",
            "memory": "separate invocation using tracemalloc; blank except repetition 0",
            "normalization": "elapsed_ns divided by the algorithm's theoretical work expression",
        },
        "row_count": len(rows),
    }
    metadata_path = output.with_suffix(".metadata.json")
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return output
