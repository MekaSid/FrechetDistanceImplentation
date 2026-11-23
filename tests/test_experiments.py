import csv
import json

import numpy as np
import pytest

from frechet_edit.experiments.analysis import analyze_results, summarize
from frechet_edit.experiments.config import ExperimentConfig
from frechet_edit.experiments.generators import generate_curves
from frechet_edit.experiments.runner import run_experiment


@pytest.mark.parametrize(
    "scenario", ["smooth", "random_walk", "outliers", "undersampled", "repeated"]
)
def test_generators_are_deterministic_and_well_shaped(scenario):
    first = generate_curves(scenario, 9, 6, seed=123)
    second = generate_curves(scenario, 9, 6, seed=123)
    assert first.pi.shape == (9, 2)
    assert first.sigma.shape == (6, 2)
    assert np.array_equal(first.pi, second.pi)
    assert np.array_equal(first.sigma, second.sigma)
    assert np.isfinite(first.pi).all()
    assert np.isfinite(first.sigma).all()


def test_config_rejects_unknown_fields_and_invalid_values():
    with pytest.raises(ValueError, match="unknown configuration"):
        ExperimentConfig.from_dict({"name": "bad", "surprise": True})
    with pytest.raises(ValueError, match="size pair"):
        ExperimentConfig.from_dict({"name": "bad", "size_pairs": [[0, 2]]})
    with pytest.raises(ValueError, match="unknown scenarios"):
        ExperimentConfig.from_dict({"name": "bad", "scenarios": ["mystery"]})


def test_runner_writes_reproducible_schema_and_reference_checks(tmp_path):
    config = ExperimentConfig.from_dict(
        {
            "name": "pytest-smoke",
            "seed": 77,
            "size_pairs": [[4, 4]],
            "scenarios": ["smooth"],
            "deltas": [0.1],
            "repetitions": 1,
            "warmups": 0,
            "algorithms": [
                "ordinary_discrete_frechet",
                "deletions_only",
                "insertions_only",
                "insertions_and_deletions",
            ],
            "include_references": True,
            "reference_max_m": 8,
            "reference_max_cells": 64,
            "include_mu_benchmarks": True,
            "mu_reference_max_m": 8,
            "measure_memory": False,
        }
    )
    raw_path = run_experiment(config, tmp_path / "raw.csv")
    with raw_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    algorithms = {row["algorithm"] for row in rows}
    assert algorithms == {
        "ordinary_discrete_frechet",
        "deletions_only",
        "insertions_only",
        "insertions_and_deletions",
        "insertions_only_reference",
        "insertions_and_deletions_reference",
        "compute_mu",
        "compute_mu_reference",
    }
    assert all(float(row["elapsed_ns"]) > 0 for row in rows)
    assert all(float(row["work_units"]) > 0 for row in rows)
    metadata = json.loads((tmp_path / "raw.metadata.json").read_text(encoding="utf-8"))
    assert metadata["config"]["name"] == "pytest-smoke"
    assert metadata["row_count"] == len(rows)


def test_analysis_outputs_tables_and_markdown(tmp_path):
    raw = tmp_path / "raw.csv"
    raw.write_text(
        "experiment,run_timestamp_utc,case_id,scenario,m,n,regime,delta,seed,repetition,"
        "algorithm,variant,theoretical_model,work_units,elapsed_ns,elapsed_ms,"
        "normalized_ns_per_work,peak_python_bytes,min_edits,feasible,ordinary_distance\n"
        "x,t,c,smooth,4,4,balanced,0.1,1,0,deletions_only,optimized,m*n,16,1000000,1,"
        "62500,1024,1,true,0.2\n"
        "x,t,c,smooth,4,4,balanced,0.1,1,1,deletions_only,optimized,m*n,16,2000000,2,"
        "125000,,1,true,0.2\n",
        encoding="utf-8",
    )
    rows = list(csv.DictReader(raw.open(encoding="utf-8", newline="")))
    summary = summarize(rows)
    assert summary[0]["median_elapsed_ms"] == pytest.approx(1.5)
    assert summary[0]["feasibility_rate"] == pytest.approx(1.0)
    artifacts = analyze_results(raw, tmp_path / "analysis", make_plots=False)
    assert artifacts["summary"].exists()
    assert artifacts["scaling"].exists()
    assert "Experimental Results Brief" in artifacts["markdown"].read_text(encoding="utf-8")
