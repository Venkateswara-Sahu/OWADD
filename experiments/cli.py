from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from experiments.aggregate import aggregate_results
from experiments.config import ExperimentConfig
from experiments.runner import run_experiment


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vigil-bench")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--config", type=Path, required=True)
    prepare.add_argument("--archive", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    run = commands.add_parser("run")
    run.add_argument("--config", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--mode", choices=("smoke", "tune", "test"), default="smoke")
    run.add_argument("--train", type=Path)
    run.add_argument("--test", type=Path)
    run.add_argument(
        "--frozen", type=Path, default=Path("artifacts/manifests/nsl_kdd_frozen.json")
    )

    aggregate = commands.add_parser("aggregate")
    aggregate.add_argument("--input", type=Path, required=True)
    aggregate.add_argument("--output", type=Path, required=True)

    paper = commands.add_parser("paper")
    paper.add_argument("--input", type=Path, required=True)
    paper.add_argument("--output", type=Path, required=True)
    return parser


def _discover_expected(root: Path) -> tuple[set[str], set[int]]:
    methods: set[str] = set()
    seeds: set[int] = set()
    for path in root.rglob("*.json"):
        if path.name == "failure.json":
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "config" in payload:
            methods.add(str(payload["config"]["method"]))
            seeds.add(int(payload["config"]["seed"]))
    return methods, seeds


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "prepare":
            import yaml
            from experiments.datasets.cicids2017_improved import prepare_archive

            settings = yaml.safe_load(args.config.read_text(encoding="utf-8"))
            if not isinstance(settings, dict) or set(settings) != {
                "dataset",
                "read_chunk_rows",
                "attempted_policy",
            }:
                raise ValueError(
                    "preparation requires exactly dataset, read_chunk_rows, attempted_policy"
                )
            if (
                settings["dataset"] != "cicids2017_improved_cns2022"
                or settings["attempted_policy"] != "benign"
            ):
                raise ValueError("unsupported preparation protocol")
            if type(settings["read_chunk_rows"]) is not int:
                raise ValueError("read_chunk_rows must be an integer")
            prepare_archive(
                args.archive, args.output, read_chunk_rows=settings["read_chunk_rows"]
            )
            print(args.output / "manifest.json")
            return 0
        if args.command == "run":
            config = ExperimentConfig.from_yaml(args.config)
            if config.dataset == "nsl_kdd":
                from experiments.network import run_nsl_kdd_mode

                if args.train is None or args.test is None:
                    raise ValueError("NSL-KDD requires --train and --test file paths")
                results = run_nsl_kdd_mode(
                    config,
                    args.output,
                    train_path=args.train,
                    test_path=args.test,
                    mode=args.mode,
                    frozen_path=args.frozen,
                )
                for result in results:
                    print(result.result_id)
                return 0
            if args.mode != "smoke":
                raise ValueError("synthetic runner currently supports smoke mode only")
            result = run_experiment(config, args.output)
            print(result.result_id)
            return 0
        if args.command == "aggregate":
            methods, seeds = _discover_expected(args.input)
            summary = aggregate_results(args.input, methods, seeds)
            args.output.mkdir(parents=True, exist_ok=True)
            summary.to_csv(args.output / "summary.csv", index=False)
            return 0
        if args.command == "paper":
            from experiments.paper_outputs import generate_paper_outputs

            generate_paper_outputs(args.input, args.output)
            return 0
    except Exception as error:
        print(f"vigil-bench: {error}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
