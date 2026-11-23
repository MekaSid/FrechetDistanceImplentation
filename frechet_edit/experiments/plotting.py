"""Matplotlib figures designed for direct use in the report and slides."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Iterable


DISPLAY_NAMES = {
    "ordinary_discrete_frechet": "Ordinary Fréchet",
    "deletions_only": "Deletions",
    "insertions_only": "Insertions",
    "insertions_and_deletions": "Insertions + deletions",
    "insertions_only_reference": "Insertions reference",
    "insertions_and_deletions_reference": "Combined reference",
    "compute_mu": "Optimized μ",
    "compute_mu_reference": "Reference μ",
}


def _matplotlib():
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError(
            "plotting requires matplotlib; install the experiment dependencies with "
            "python -m pip install -e '.[experiments]'"
        ) from exc
    plt.rcParams.update(
        {
            "figure.dpi": 140,
            "savefig.dpi": 220,
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "legend.fontsize": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "lines.linewidth": 1.8,
            "lines.markersize": 5,
        }
    )
    return plt


def _save(plt, figure, directory: Path, name: str) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    png = directory / f"{name}.png"
    pdf = directory / f"{name}.pdf"
    figure.savefig(png, bbox_inches="tight")
    figure.savefig(pdf, bbox_inches="tight")
    plt.close(figure)
    return png, pdf


def _float(row: dict[str, object], key: str) -> float | None:
    value = row.get(key, "")
    return None if value == "" else float(value)


def _optimized_algorithms(rows: Iterable[dict[str, object]]) -> list[str]:
    allowed = {
        "ordinary_discrete_frechet",
        "deletions_only",
        "insertions_only",
        "insertions_and_deletions",
    }
    return sorted(
        {str(row["algorithm"]) for row in rows if row["variant"] == "optimized" and row["algorithm"] in allowed}
    )


def _compact_tick(value: float) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:g}M"
    if value >= 1_000:
        return f"{value / 1_000:g}k"
    return f"{value:g}"


def plot_runtime_by_regime(rows: list[dict[str, object]], directory: Path) -> tuple[Path, Path]:
    plt = _matplotlib()
    regimes = [regime for regime in ("balanced", "m-dominant", "n-dominant") if any(row["regime"] == regime for row in rows)]
    figure, axes = plt.subplots(1, len(regimes), figsize=(4.2 * len(regimes), 3.7), squeeze=False)
    algorithms = _optimized_algorithms(rows)
    markers = ["o", "s", "^", "D"]
    for axis, regime in zip(axes[0], regimes):
        work_values: set[int] = set()
        for marker, algorithm in zip(markers, algorithms):
            grouped: dict[int, list[float]] = defaultdict(list)
            for row in rows:
                if row["regime"] != regime or row["algorithm"] != algorithm or row["variant"] != "optimized":
                    continue
                m, n = int(row["m"]), int(row["n"])
                if algorithm in {"ordinary_discrete_frechet", "deletions_only"}:
                    work = m * n
                else:
                    work = m * m + m * n
                grouped[work].append(float(row["median_elapsed_ms"]))
                work_values.add(work)
            if grouped:
                x = sorted(grouped)
                y = [median(grouped[value]) for value in x]
                axis.plot(x, y, marker=marker, label=DISPLAY_NAMES[algorithm])
        axis.set_xscale("log")
        axis.set_yscale("log")
        ordered_work = sorted(work_values)
        if ordered_work:
            count = min(3, len(ordered_work))
            indices = sorted(
                {round(index * (len(ordered_work) - 1) / max(1, count - 1)) for index in range(count)}
            )
            ticks = [ordered_work[index] for index in indices]
            axis.set_xticks(ticks, [_compact_tick(value) for value in ticks])
            axis.tick_params(axis="x", which="minor", labelbottom=False)
        axis.set_title(regime.replace("-", " ").title())
        axis.set_xlabel("Theoretical work units")
        axis.set_ylabel("Median runtime (ms)")
    handles, labels = axes[0][0].get_legend_handles_labels()
    if handles:
        figure.legend(
            handles,
            labels,
            loc="lower center",
            bbox_to_anchor=(0.5, -0.04),
            ncol=min(4, len(labels)),
            frameon=False,
        )
        figure.subplots_adjust(bottom=0.23, top=0.84, wspace=0.34)
    figure.suptitle("Runtime growth by input-size regime", y=0.98)
    return _save(plt, figure, directory, "runtime-by-regime")


def plot_reference_speedup(rows: list[dict[str, object]], directory: Path) -> tuple[Path, Path]:
    plt = _matplotlib()
    lookup: dict[tuple[str, str, str, str], float] = {}
    for row in rows:
        key = (str(row["scenario"]), str(row["m"]), str(row["n"]), str(row["delta"]))
        lookup[(str(row["algorithm"]), *key)] = float(row["median_elapsed_ms"])
    pairs = (
        ("insertions_only", "insertions_only_reference"),
        ("insertions_and_deletions", "insertions_and_deletions_reference"),
        ("compute_mu", "compute_mu_reference"),
    )
    figure, axis = plt.subplots(figsize=(6.8, 4.0))
    markers = ["o", "s", "^"]
    for marker, (optimized, reference) in zip(markers, pairs):
        grouped: dict[int, list[float]] = defaultdict(list)
        for row in rows:
            if row["algorithm"] != optimized:
                continue
            key = (str(row["scenario"]), str(row["m"]), str(row["n"]), str(row["delta"]))
            reference_time = lookup.get((reference, *key))
            if reference_time is None:
                continue
            optimized_time = float(row["median_elapsed_ms"])
            grouped[int(row["m"])].append(reference_time / optimized_time)
        if grouped:
            x = sorted(grouped)
            y = [median(grouped[value]) for value in x]
            axis.plot(x, y, marker=marker, label=f"{DISPLAY_NAMES[optimized]} vs reference")
    axis.axhline(1.0, color="0.45", linewidth=1.0, linestyle="--")
    axis.set_xscale("log", base=2)
    axis.set_yscale("log")
    axis.set_xlabel("Reference curve length m")
    axis.set_ylabel("Reference / optimized runtime")
    axis.set_title("Speedup from optimized data structures")
    axis.legend(frameon=False)
    return _save(plt, figure, directory, "reference-speedup")


def plot_memory(rows: list[dict[str, object]], directory: Path) -> tuple[Path, Path]:
    plt = _matplotlib()
    figure, axis = plt.subplots(figsize=(6.8, 4.0))
    algorithms = _optimized_algorithms(rows)
    markers = ["o", "s", "^", "D"]
    for marker, algorithm in zip(markers, algorithms):
        grouped: dict[int, list[float]] = defaultdict(list)
        for row in rows:
            memory = _float(row, "median_peak_python_mib")
            if row["algorithm"] == algorithm and memory is not None:
                grouped[int(row["m"]) * int(row["n"])].append(memory)
        if grouped:
            x = sorted(grouped)
            y = [median(grouped[value]) for value in x]
            axis.plot(x, y, marker=marker, label=DISPLAY_NAMES[algorithm])
    axis.set_xscale("log")
    axis.set_yscale("log")
    axis.set_xlabel("Input grid cells m·n")
    axis.set_ylabel("Peak traced allocation (MiB)")
    axis.set_title("Memory growth")
    axis.legend(frameon=False)
    return _save(plt, figure, directory, "memory-growth")


def plot_edit_outcomes(rows: list[dict[str, object]], directory: Path) -> tuple[Path, Path]:
    plt = _matplotlib()
    algorithms = [
        algorithm
        for algorithm in _optimized_algorithms(rows)
        if algorithm != "ordinary_discrete_frechet"
    ]
    figure, axes = plt.subplots(1, 2, figsize=(10.0, 3.9))
    markers = ["o", "s", "^"]
    for marker, algorithm in zip(markers, algorithms):
        feasibility: dict[float, list[float]] = defaultdict(list)
        edits: dict[float, list[float]] = defaultdict(list)
        for row in rows:
            if row["algorithm"] != algorithm or row["variant"] != "optimized":
                continue
            delta = float(row["delta"])
            feasible = _float(row, "feasibility_rate")
            edit_count = _float(row, "median_min_edits")
            if feasible is not None:
                feasibility[delta].append(feasible)
            if edit_count is not None:
                edits[delta].append(edit_count)
        if feasibility:
            x = sorted(feasibility)
            axes[0].plot(x, [sum(feasibility[value]) / len(feasibility[value]) for value in x], marker=marker, label=DISPLAY_NAMES[algorithm])
        if edits:
            x = sorted(edits)
            axes[1].plot(x, [median(edits[value]) for value in x], marker=marker, label=DISPLAY_NAMES[algorithm])
    axes[0].set_xlabel("Threshold δ")
    axes[0].set_ylabel("Mean feasibility rate")
    axes[0].set_ylim(-0.03, 1.03)
    axes[0].set_title("Feasibility by edit model")
    axes[1].set_xlabel("Threshold δ")
    axes[1].set_ylabel("Median finite edit count")
    axes[1].set_title("Edit cost by edit model")
    handles, labels = axes[0].get_legend_handles_labels()
    if handles:
        figure.legend(handles, labels, loc="upper center", ncol=3, frameon=False)
        figure.subplots_adjust(top=0.82)
    return _save(plt, figure, directory, "edit-outcomes")


def create_all_plots(
    summary_rows: list[dict[str, object]], output_directory: str | Path
) -> dict[str, Path]:
    directory = Path(output_directory)
    plots = {
        "runtime": plot_runtime_by_regime(summary_rows, directory),
        "speedup": plot_reference_speedup(summary_rows, directory),
        "memory": plot_memory(summary_rows, directory),
        "outcomes": plot_edit_outcomes(summary_rows, directory),
    }
    return {
        f"{name}_{suffix}": path
        for name, pair in plots.items()
        for suffix, path in zip(("png", "pdf"), pair)
    }
