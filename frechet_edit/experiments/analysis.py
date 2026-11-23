"""Aggregate benchmark CSV data into report-ready tables and figures."""

from __future__ import annotations

from collections import defaultdict
import csv
import json
import math
from pathlib import Path
from statistics import median
from typing import Iterable

import numpy as np


SUMMARY_FIELDS = (
    "experiment",
    "scenario",
    "m",
    "n",
    "regime",
    "delta",
    "algorithm",
    "variant",
    "theoretical_model",
    "trials",
    "median_elapsed_ms",
    "q1_elapsed_ms",
    "q3_elapsed_ms",
    "min_elapsed_ms",
    "max_elapsed_ms",
    "median_normalized_ns_per_work",
    "median_peak_python_mib",
    "feasibility_rate",
    "median_min_edits",
)


def read_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _number(row: dict[str, str], key: str) -> float | None:
    value = row.get(key, "")
    if value in {"", "Infinity", "-Infinity", "nan", "NaN"}:
        return None
    return float(value)


def _quantile(values: list[float], probability: float) -> float:
    return float(np.quantile(np.asarray(values, dtype=float), probability))


def summarize(rows: Iterable[dict[str, str]]) -> list[dict[str, object]]:
    group_fields = (
        "experiment",
        "scenario",
        "m",
        "n",
        "regime",
        "delta",
        "algorithm",
        "variant",
        "theoretical_model",
    )
    groups: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[field] for field in group_fields)].append(row)

    summaries: list[dict[str, object]] = []
    for key, members in sorted(groups.items()):
        elapsed = [float(member["elapsed_ms"]) for member in members]
        normalized = [float(member["normalized_ns_per_work"]) for member in members]
        memory = [value for member in members if (value := _number(member, "peak_python_bytes")) is not None]
        feasibility = [member["feasible"] == "true" for member in members if member["feasible"]]
        edits = [value for member in members if (value := _number(member, "min_edits")) is not None]
        summary = dict(zip(group_fields, key))
        summary.update(
            {
                "trials": len(members),
                "median_elapsed_ms": median(elapsed),
                "q1_elapsed_ms": _quantile(elapsed, 0.25),
                "q3_elapsed_ms": _quantile(elapsed, 0.75),
                "min_elapsed_ms": min(elapsed),
                "max_elapsed_ms": max(elapsed),
                "median_normalized_ns_per_work": median(normalized),
                "median_peak_python_mib": "" if not memory else median(memory) / (1024**2),
                "feasibility_rate": "" if not feasibility else sum(feasibility) / len(feasibility),
                "median_min_edits": "" if not edits else median(edits),
            }
        )
        summaries.append(summary)
    return summaries


def scaling_estimates(summary_rows: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    """Fit log(time) = intercept + slope*log(theoretical work)."""

    groups: dict[tuple[str, str, str], list[tuple[float, float]]] = defaultdict(list)
    for row in summary_rows:
        algorithm = str(row["algorithm"])
        if str(row["variant"]) != "optimized":
            continue
        work_model = str(row["theoretical_model"])
        m, n = int(row["m"]), int(row["n"])
        if algorithm in {"ordinary_discrete_frechet", "deletions_only"}:
            work = m * n
        elif algorithm in {"insertions_only", "insertions_and_deletions"}:
            work = m * m + m * n
        elif algorithm == "compute_mu":
            work = m * m
        else:
            continue
        elapsed = float(row["median_elapsed_ms"])
        if work > 0 and elapsed > 0:
            groups[(algorithm, str(row["scenario"]), str(row["regime"]))].append((work, elapsed))

    estimates: list[dict[str, object]] = []
    for (algorithm, scenario, regime), points in sorted(groups.items()):
        distinct_work = sorted(set(work for work, _ in points))
        if len(distinct_work) < 3:
            continue
        # Aggregate repeated deltas at the same work size before fitting.
        by_work: dict[float, list[float]] = defaultdict(list)
        for work, elapsed in points:
            by_work[work].append(elapsed)
        x = np.log(np.asarray(sorted(by_work), dtype=float))
        y = np.log(np.asarray([median(by_work[work]) for work in sorted(by_work)], dtype=float))
        slope, intercept = np.polyfit(x, y, 1)
        predicted = intercept + slope * x
        residual = float(np.sum((y - predicted) ** 2))
        total = float(np.sum((y - np.mean(y)) ** 2))
        r_squared = 1.0 if total == 0 else 1.0 - residual / total
        estimates.append(
            {
                "algorithm": algorithm,
                "scenario": scenario,
                "regime": regime,
                "points": len(x),
                "slope_vs_theoretical_work": float(slope),
                "r_squared": r_squared,
            }
        )
    return estimates


def _write_csv(path: Path, rows: list[dict[str, object]], fields: tuple[str, ...]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _format_table(rows: list[list[str]], headers: list[str]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _write_markdown(
    output: Path,
    raw_path: Path,
    raw_rows: list[dict[str, str]],
    summaries: list[dict[str, object]],
    scaling: list[dict[str, object]],
) -> None:
    algorithms = sorted(set(row["algorithm"] for row in raw_rows))
    scenarios = sorted(set(row["scenario"] for row in raw_rows))
    aggregate: list[list[str]] = []
    for algorithm in algorithms:
        values = [float(row["elapsed_ms"]) for row in raw_rows if row["algorithm"] == algorithm]
        aggregate.append([algorithm, str(len(values)), f"{median(values):.4g}"])
    scaling_table = [
        [
            str(row["algorithm"]),
            str(row["scenario"]),
            str(row["regime"]),
            str(row["points"]),
            f"{float(row['slope_vs_theoretical_work']):.3f}",
            f"{float(row['r_squared']):.3f}",
        ]
        for row in scaling
    ]
    slope_summary: list[list[str]] = []
    for algorithm in sorted(set(str(row["algorithm"]) for row in scaling)):
        values = [
            float(row["slope_vs_theoretical_work"])
            for row in scaling
            if row["algorithm"] == algorithm
        ]
        slope_summary.append(
            [algorithm, f"{median(values):.3f}", f"{min(values):.3f}", f"{max(values):.3f}"]
        )

    summary_lookup: dict[tuple[str, str, str, str, str], float] = {}
    for row in summaries:
        key = (
            str(row["algorithm"]),
            str(row["scenario"]),
            str(row["m"]),
            str(row["n"]),
            str(row["delta"]),
        )
        summary_lookup[key] = float(row["median_elapsed_ms"])
    speedup_summary: list[list[str]] = []
    for optimized, reference in (
        ("insertions_only", "insertions_only_reference"),
        ("insertions_and_deletions", "insertions_and_deletions_reference"),
        ("compute_mu", "compute_mu_reference"),
    ):
        common: list[tuple[int, float]] = []
        for key, optimized_time in summary_lookup.items():
            algorithm, scenario, m, n, delta = key
            if algorithm != optimized:
                continue
            reference_time = summary_lookup.get((reference, scenario, m, n, delta))
            if reference_time is not None:
                common.append((int(m), reference_time / optimized_time))
        if common:
            largest_m = max(m for m, _ in common)
            ratios = [ratio for m, ratio in common if m == largest_m]
            speedup_summary.append(
                [optimized, str(largest_m), f"{median(ratios):.2f}×", str(len(ratios))]
            )

    feasibility_summary: list[list[str]] = []
    edit_algorithms = ("deletions_only", "insertions_only", "insertions_and_deletions")
    deltas = sorted({float(row["delta"]) for row in summaries})
    for delta in deltas:
        table_row = [f"{delta:g}"]
        for algorithm in edit_algorithms:
            rates = [
                float(row["feasibility_rate"])
                for row in summaries
                if row["algorithm"] == algorithm
                and row["variant"] == "optimized"
                and float(row["delta"]) == delta
                and row["feasibility_rate"] != ""
            ]
            table_row.append("—" if not rates else f"{sum(rates) / len(rates):.3f}")
        feasibility_summary.append(table_row)
    metadata_path = raw_path.with_suffix(".metadata.json")
    metadata_note = "Metadata sidecar not found."
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        environment = metadata.get("environment", {})
        dirty = environment.get("git_dirty")
        state = "dirty working tree" if dirty else "clean working tree"
        metadata_note = (
            f"Python `{environment.get('python', 'unknown').split()[0]}`, "
            f"NumPy `{environment.get('numpy', 'unknown')}`, commit "
            f"`{environment.get('git_commit') or 'uncommitted/unknown'}` ({state})."
        )

    sections = [
        "# Experimental Results Brief",
        "",
        f"Generated from `{raw_path.name}` with {len(raw_rows)} measured trials across "
        f"{len(scenarios)} scenarios. {metadata_note}",
        "",
        "## Methodology",
        "",
        "Each reported runtime uses `time.perf_counter_ns`. Repetitions operate on the same "
        "seeded input within a case. Warmups are excluded. Memory is measured in a separate "
        "invocation with `tracemalloc`, so it is not included in the timed interval. Reference "
        "implementations are limited by the configuration and checked against optimized results.",
        "",
        "## Key findings",
        "",
        "### Scaling against the theoretical work expression",
        "",
        _format_table(
            slope_summary,
            ["Algorithm", "Median slope", "Minimum", "Maximum"],
        ) if slope_summary else "Not enough distinct sizes for scaling estimates.",
        "",
        "A median slope near 1 supports proportional growth with the stated work expression; "
        "the range shows how much the estimate changes across scenarios and size regimes.",
        "",
        "### Reference/optimized runtime ratio at the largest compared m",
        "",
        _format_table(
            speedup_summary,
            ["Optimized component", "Largest m", "Median ratio", "Compared cases"],
        ) if speedup_summary else "No reference comparisons were configured.",
        "",
        "A ratio above 1 favors the optimized implementation. Ratios near 1 are a useful "
        "negative result: asymptotic improvement need not produce a large practical win at "
        "the tested sizes and language/library constants.",
        "",
        "### Mean feasibility across generated cases",
        "",
        _format_table(
            feasibility_summary,
            ["δ", "Deletions", "Insertions", "Combined"],
        ),
        "",
        "## Overall timing inventory",
        "",
        _format_table(aggregate, ["Algorithm", "Trials", "Overall median (ms)"]),
        "",
        "## Empirical scaling",
        "",
        "A slope near 1 means elapsed time grows proportionally to the algorithm's stated "
        "theoretical work expression. Treat fits with few points or low R² as descriptive only.",
        "",
        _format_table(
            scaling_table,
            ["Algorithm", "Scenario", "Regime", "Sizes", "Slope", "R²"],
        ) if scaling_table else "Not enough distinct sizes for scaling estimates.",
        "",
        "## Interpretation checklist",
        "",
        "- Explain whether optimized and reference implementations return the same edit counts.",
        "- Compare runtime trends with `m*n`, `m^2 + m*n`, and the reference work models.",
        "- Discuss crossover points where preprocessing dominates or optimization pays off.",
        "- Report feasibility and edit-count differences as edit-model behavior, not correctness errors.",
        "- State that `tracemalloc` is a traced-allocation measure rather than total process RSS.",
        "- Record unexpected or negative results; do not remove them solely because they weaken a hypothesis.",
        "",
        "## Generated artifacts",
        "",
        "- `summary.csv`: medians, quartiles, feasibility, edit counts, and memory by case.",
        "- `scaling.csv`: log-log slopes against each optimized algorithm's theoretical work.",
        "- `figures/`: report-ready PNG and PDF versions of all plots.",
        "",
    ]
    output.write_text("\n".join(sections), encoding="utf-8")


def analyze_results(
    raw_csv: str | Path,
    output_directory: str | Path,
    *,
    make_plots: bool = True,
) -> dict[str, Path]:
    raw_path = Path(raw_csv)
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    raw_rows = read_rows(raw_path)
    if not raw_rows:
        raise ValueError(f"no benchmark rows found in {raw_path}")
    summaries = summarize(raw_rows)
    scaling = scaling_estimates(summaries)
    summary_path = output / "summary.csv"
    scaling_path = output / "scaling.csv"
    markdown_path = output / "RESULTS.md"
    _write_csv(summary_path, summaries, SUMMARY_FIELDS)
    scaling_fields = (
        "algorithm",
        "scenario",
        "regime",
        "points",
        "slope_vs_theoretical_work",
        "r_squared",
    )
    _write_csv(scaling_path, scaling, scaling_fields)
    _write_markdown(markdown_path, raw_path, raw_rows, summaries, scaling)
    artifacts = {"summary": summary_path, "scaling": scaling_path, "markdown": markdown_path}
    if make_plots:
        from .plotting import create_all_plots

        artifacts.update(create_all_plots(summaries, output / "figures"))
    return artifacts
