"""Configuration loading and validation for reproducible experiments."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


SCENARIOS = ("smooth", "random_walk", "outliers", "undersampled", "repeated")
ALGORITHMS = (
    "ordinary_discrete_frechet",
    "deletions_only",
    "insertions_only",
    "insertions_and_deletions",
)


@dataclass(frozen=True)
class ExperimentConfig:
    """Validated experiment configuration.

    ``size_pairs`` is explicit instead of a Cartesian product so report runs can
    target balanced, m-dominant, and n-dominant regimes without wasting trials.
    """

    name: str
    seed: int = 2024
    size_pairs: tuple[tuple[int, int], ...] = ((16, 16), (32, 32), (64, 64))
    scenarios: tuple[str, ...] = SCENARIOS
    deltas: tuple[float, ...] = (0.05, 0.1, 0.2)
    repetitions: int = 5
    warmups: int = 1
    algorithms: tuple[str, ...] = ALGORITHMS
    noise: float = 0.03
    corruption_rate: float = 0.1
    outlier_scale: float = 1.5
    include_references: bool = True
    reference_max_m: int = 64
    reference_max_cells: int = 4096
    include_mu_benchmarks: bool = True
    mu_reference_max_m: int = 64
    measure_memory: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ExperimentConfig":
        known = {field.name for field in cls.__dataclass_fields__.values()}
        unknown = sorted(set(raw) - known)
        if unknown:
            raise ValueError(f"unknown configuration fields: {', '.join(unknown)}")
        normalized = dict(raw)
        for key in ("size_pairs", "scenarios", "deltas", "algorithms"):
            if key in normalized:
                normalized[key] = tuple(normalized[key])
        if "size_pairs" in normalized:
            normalized["size_pairs"] = tuple(tuple(pair) for pair in normalized["size_pairs"])
        config = cls(**normalized)
        config.validate()
        return config

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("experiment name must be nonempty")
        if not self.size_pairs:
            raise ValueError("size_pairs must be nonempty")
        for pair in self.size_pairs:
            if len(pair) != 2 or any(not isinstance(value, int) or value < 1 for value in pair):
                raise ValueError(f"invalid size pair {pair!r}; expected positive integers [m, n]")
        unknown_scenarios = sorted(set(self.scenarios) - set(SCENARIOS))
        if unknown_scenarios:
            raise ValueError(f"unknown scenarios: {', '.join(unknown_scenarios)}")
        unknown_algorithms = sorted(set(self.algorithms) - set(ALGORITHMS))
        if unknown_algorithms:
            raise ValueError(f"unknown algorithms: {', '.join(unknown_algorithms)}")
        if not self.scenarios or not self.algorithms or not self.deltas:
            raise ValueError("scenarios, algorithms, and deltas must be nonempty")
        if any(delta < 0 for delta in self.deltas):
            raise ValueError("deltas must be nonnegative")
        if self.repetitions < 1 or self.warmups < 0:
            raise ValueError("repetitions must be positive and warmups must be nonnegative")
        if not 0 <= self.corruption_rate <= 1:
            raise ValueError("corruption_rate must be between 0 and 1")
        if self.noise < 0 or self.outlier_scale < 0:
            raise ValueError("noise and outlier_scale must be nonnegative")
        if min(self.reference_max_m, self.reference_max_cells, self.mu_reference_max_m) < 1:
            raise ValueError("reference limits must be positive")


def load_config(path: str | Path) -> ExperimentConfig:
    config_path = Path(path)
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {config_path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("experiment configuration must be a JSON object")
    return ExperimentConfig.from_dict(raw)
