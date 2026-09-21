"""Reproducible split audit; no model fitting or performance evaluation."""

from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path

import numpy as np

from experiments.config import ExperimentConfig
from experiments.datasets.base import PreparedDataset, validate_disjoint_ids
from experiments.io import ResultEnvelope, write_result_atomic
from experiments.provenance import capture_provenance


def build_audit_report(dataset: PreparedDataset) -> dict:
    splits = {
        name: getattr(dataset, name) for name in ("reference", "validation", "test")
    }
    validate_disjoint_ids({name: set(split.row_ids) for name, split in splits.items()})
    report = {}
    for name, split in splits.items():
        if split.X.ndim != 2 or split.X.shape != (
            len(split.y),
            len(dataset.feature_names),
        ):
            raise ValueError(f"invalid feature/label shape: {name}")
        if len(split.row_ids) != len(split.y) or len(set(split.row_ids)) != len(
            split.row_ids
        ):
            raise ValueError(f"invalid or repeated row identities: {name}")
        nonfinite = int((~np.isfinite(split.X)).sum())
        if nonfinite:
            raise ValueError(f"non-finite transformed values: {name}")
        labels, counts = np.unique(split.y, return_counts=True)
        report[name] = {
            "rows": len(split.y),
            "nonfinite_values": nonfinite,
            "class_counts": dict(zip(labels.tolist(), counts.tolist())),
            "row_identity_hash": sha256(
                "\n".join(sorted(split.row_ids)).encode()
            ).hexdigest(),
        }
    return {
        "checksums": dataset.checksums,
        "feature_names": dataset.feature_names,
        "feature_types": dataset.feature_types,
        "feature_groups": dataset.feature_groups,
        "splits": report,
        "preprocessing_audit": dataset.audit,
        "scope": "split and preprocessing audit only; not performance evidence",
    }


def main(argv=None) -> int:
    from experiments.datasets.nsl_kdd import prepare_nsl_kdd

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", required=True, type=Path)
    parser.add_argument("--test", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    dataset = prepare_nsl_kdd(args.train, args.test, seed=args.seed)
    report = build_audit_report(dataset)
    config = ExperimentConfig(dataset="nsl_kdd", method="dataset_audit", seed=args.seed)
    path = write_result_atomic(
        args.output,
        ResultEnvelope(
            config.canonical_dict(),
            capture_provenance([args.train, args.test]),
            report,
            metadata={"stage": "audit_only"},
        ),
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
