"""Command-line interface for comparing all three edit variants."""

from __future__ import annotations

import argparse
import json

from . import (
    deletions_only,
    insertions_and_deletions,
    insertions_only,
    ordinary_discrete_frechet,
)
from .examples import EXAMPLES


def _curve(value: str) -> list[list[float]]:
    try:
        return [[float(coordinate) for coordinate in point.split(",")] for point in value.split(";")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("use x,y;x,y;... (for example 0,0;1,1)") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare discrete Frechet edit-distance algorithms")
    parser.add_argument("--example", choices=EXAMPLES, default="repair-both")
    parser.add_argument("--pi", type=_curve, help="reference curve as x,y;x,y;...")
    parser.add_argument("--sigma", type=_curve, help="editable curve as x,y;x,y;...")
    parser.add_argument("--delta", type=float)
    parser.add_argument(
        "--witness",
        action="store_true",
        help="include a verified deletion-only witness (insertion witnesses are a future milestone)",
    )
    args = parser.parse_args()

    example = EXAMPLES[args.example]
    pi = args.pi if args.pi is not None else example["pi"]
    sigma = args.sigma if args.sigma is not None else example["sigma"]
    delta = args.delta if args.delta is not None else example["delta"]
    results = [
        deletions_only(pi, sigma, delta, return_witness=args.witness),
        insertions_only(pi, sigma, delta),
        insertions_and_deletions(pi, sigma, delta),
    ]
    payload = {
        "pi": pi,
        "sigma": sigma,
        "delta": delta,
        "ordinary_distance": ordinary_discrete_frechet(pi, sigma),
        "results": [result.as_dict() for result in results],
    }
    print(json.dumps(payload, indent=2, allow_nan=True))


if __name__ == "__main__":
    main()
