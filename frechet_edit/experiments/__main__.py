"""Command line interface for running and analyzing experiments."""

from __future__ import annotations

import argparse
from pathlib import Path

from .analysis import analyze_results
from .config import load_config
from .runner import run_experiment


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run reproducible Fréchet edit-distance experiments"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="run a JSON experiment configuration")
    run.add_argument("--config", required=True, type=Path)
    run.add_argument("--output", required=True, type=Path, help="raw CSV destination")

    analyze = subparsers.add_parser("analyze", help="summarize an existing raw CSV")
    analyze.add_argument("--input", required=True, type=Path)
    analyze.add_argument("--output-dir", required=True, type=Path)
    analyze.add_argument("--no-plots", action="store_true")

    all_steps = subparsers.add_parser("all", help="run, summarize, and plot")
    all_steps.add_argument("--config", required=True, type=Path)
    all_steps.add_argument("--output-dir", required=True, type=Path)
    all_steps.add_argument("--no-plots", action="store_true")
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "run":
        path = run_experiment(load_config(args.config), args.output, progress=print)
        print(f"raw results: {path}")
        return
    if args.command == "analyze":
        artifacts = analyze_results(args.input, args.output_dir, make_plots=not args.no_plots)
        for name, path in artifacts.items():
            print(f"{name}: {path}")
        return

    output_dir: Path = args.output_dir
    raw_path = output_dir / "raw.csv"
    run_experiment(load_config(args.config), raw_path, progress=print)
    artifacts = analyze_results(raw_path, output_dir, make_plots=not args.no_plots)
    print(f"raw: {raw_path}")
    for name, path in artifacts.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
