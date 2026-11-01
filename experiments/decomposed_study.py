"""Decomposed Copula-KS attribution evaluation against frozen mechanism baselines."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from threadpoolctl import threadpool_limits

from experiments.config import ExperimentConfig
from experiments.io import ResultEnvelope, load_completed_result, write_result_atomic
from experiments.mechanism import fit_pair, score_windows
from experiments.mechanism_data import (
    BLOCK_SIZE,
    MIN_TRAINING_SD,
    N_FEATURES,
    TRAIN_START,
    TRAIN_STOP,
     load_real_pools,
    real_cases,
    synthetic_cases,
)
from experiments.metrics.attribution import evaluate_ranking
from experiments.metrics.stats import bootstrap_mean_ci
from experiments.provenance import capture_provenance, sha256_file
from vigil.attribution import compute_decomposed_scores

SEEDS = tuple(range(50, 70))
TEST_SEEDS = tuple(range(70, 90))
EPOCHS = 20
MIN_SEEDS = 2
DECOMPOSED_METHODS = (
    "decomposed_copula_ks",
    "marginal_ks_fwe",
    "relational_copula_fwe",
)
ALL_METHODS = (
    *(
        f"{state}_{rule}"
        for state in ("trained", "untrained")
        for rule in ("positive", "absolute", "standardized")
    ),
    "squared_input_change",
    "kolmogorov_smirnov",
    "max_correlation_change",
    *DECOMPOSED_METHODS,
)
COMPARISONS = (
    ("decomposed_copula_ks", "trained_positive"),
    ("decomposed_copula_ks", "trained_absolute"),
    ("decomposed_copula_ks", "kolmogorov_smirnov"),
    ("decomposed_copula_ks", "max_correlation_change"),
    ("decomposed_copula_ks", "squared_input_change"),
)


def load_heldout_pools(root):
    """Load and checksum-verify held-out test pools (Wednesday, Thursday, Friday)."""
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if (
        manifest.get("complete") is not True
        or manifest.get("dataset") != "cicids2017_improved_cns2022"
        or manifest["split_days"]["reference"] != ["monday"]
        or manifest["split_days"]["test"] != ["wednesday", "thursday", "friday"]
    ):
        raise ValueError("incompatible held-out test manifest")

    hashes = {"manifest.json": sha256_file(root / "manifest.json")}
    for day in ("monday", "wednesday", "thursday", "friday"):
        for suffix in ("X.npy", "metadata.csv"):
            name = f"{day}.{suffix}"
            hashes[name] = sha256_file(root / name)
            if hashes[name] != manifest["artifacts"][name]:
                raise ValueError(f"cache checksum mismatch on {name}")

    train = np.asarray(
        np.load(root / "monday.X.npy", mmap_mode="r")[TRAIN_START:TRAIN_STOP],
        dtype=float,
    )
    training_ids = (
        pd.read_csv(
            root / "monday.metadata.csv", nrows=TRAIN_STOP, dtype={"row_id": str}
        )["row_id"]
        .iloc[TRAIN_START:]
        .tolist()
    )

    # Draw 7 blocks from Wed, 7 from Thu, 6 from Fri = 20 blocks (32,000 rows)
    day_specs = (("wednesday", 7), ("thursday", 7), ("friday", 6))
    test_chunks = []
    test_ids = []
    for day, n_blocks in day_specs:
        n_rows = n_blocks * BLOCK_SIZE
        arr = np.asarray(
            np.load(root / f"{day}.X.npy", mmap_mode="r")[:n_rows],
            dtype=float,
        )
        ids = (
            pd.read_csv(
                root / f"{day}.metadata.csv", nrows=n_rows, dtype={"row_id": str}
            )["row_id"]
            .tolist()
        )
        if len(arr) != n_rows or len(ids) != n_rows:
            raise ValueError(f"insufficient rows in {day}")
        test_chunks.append(arr)
        test_ids.extend(ids)

    heldout = np.vstack(test_chunks)
    if not np.isfinite(train).all() or not np.isfinite(heldout).all():
        raise ValueError("nonfinite held-out data")
    all_ids = training_ids + test_ids
    if len(set(all_ids)) != len(all_ids):
        raise ValueError("overlapping row identities between Monday and held-out days")

    sd = train.std(0, ddof=1)
    columns = [
        i
        for i, name in enumerate(manifest["feature_names"])
        if name not in ("Dst Port", "Protocol") and sd[i] > MIN_TRAINING_SD
    ][:N_FEATURES]
    mean, scale = train[:, columns].mean(0), sd[columns]
    return {
        "train": (train[:, columns] - mean) / scale,
        "validation": (heldout[:, columns] - mean) / scale,
        "training_ids": training_ids,
        "validation_ids": test_ids,
        "feature_names": [manifest["feature_names"][i] for i in columns],
        "mean": mean.tolist(),
        "scale": scale.tolist(),
        "hashes": hashes,
        "split_days": ["wednesday", "thursday", "friday"],
    }


def _summary(values):
    defined = [value for value in values if value is not None]
    return {
        "mean": float(np.mean(defined)) if defined else None,
        "ci95": list(bootstrap_mean_ci(defined)) if defined else None,
        "n_defined": len(defined),
    }


def score_decomposed_variants(reference, current):
    """Return decomposed Copula-KS and its marginal/relational ablation scores."""
    marg_ev, rel_ev, combined = compute_decomposed_scores(reference, current)
    drift_types = [
        "relational" if rel_ev[j] > marg_ev[j] else "marginal"
        for j in range(len(combined))
    ]
    return {
        "decomposed_copula_ks": combined,
        "marginal_ks_fwe": marg_ev,
        "relational_copula_fwe": rel_ev,
    }, {
        "drift_types": drift_types,
        "marginal_evidence": marg_ev.tolist(),
        "relational_evidence": rel_ev.tolist(),
    }


def aggregate_study(runs, case_names):
    expected = {(case, method) for case in case_names for method in ALL_METHODS}
    index = {}
    for seed, records in runs.items():
        rows = {(r["case"], r["method"]): r for r in records}
        if set(rows) != expected or len(records) != len(expected):
            raise ValueError("incomplete or duplicate case/method grid")
        index[seed] = rows
    groups, paired = [], []
    for case, method in sorted(expected):
        rows = [index[s][case, method] for s in sorted(index)]
        groups.append(
            {
                "case": case,
                "method": method,
                "n_seeds": len(index),
                "metrics": {
                    k: _summary([r["metrics"][k] for r in rows])
                    for k in rows[0]["metrics"]
                },
            }
        )
    for case in sorted(case_names):
        for candidate, baseline in COMPARISONS:
            rows = [
                (index[s][case, candidate], index[s][case, baseline])
                for s in sorted(index)
            ]
            paired.append(
                {
                    "case": case,
                    "candidate": candidate,
                    "baseline": baseline,
                    "n_seeds": len(index),
                    "metrics": {
                        k: _summary(
                            [
                                (
                                    None
                                    if a["metrics"][k] is None
                                    or b["metrics"][k] is None
                                    else a["metrics"][k] - b["metrics"][k]
                                )
                                for a, b in rows
                            ]
                        )
                        for k in rows[0][0]["metrics"]
                    },
                }
            )
    return {"groups": groups, "paired_differences": paired}


def _run_seed(seed, epochs, pools):
    cases = synthetic_cases(seed) + (
        real_cases(pools, seed) if pools is not None else []
    )
    models = {}
    records = []
    case_diagnostics = {}
    for case in cases:
        key = case["train"].tobytes()
        if key not in models:
            original, trained, _ = fit_pair(case["train"], seed, epochs)
            models[key] = (original, trained)
        base_scores, details = score_windows(
            *models[key], case["reference"], case["current"]
        )
        decomp_scores, decomp_details = score_decomposed_variants(
            case["reference"], case["current"]
        )
        all_scores = {**base_scores, **decomp_scores}
        case_diagnostics[case["case"]] = decomp_details
        truth = tuple(
            i for i, col in enumerate(case["tie_order"]) if col in case["truth"]
        )
        for method, values in all_scores.items():
            metrics = evaluate_ranking(values[case["tie_order"]], truth)
            if case["case"] == "real/no_injection":
                metrics = dict.fromkeys(metrics, None)
            if (
                method == "max_correlation_change"
                and not details["correlation_supported"]
            ):
                metrics = dict.fromkeys(metrics, None)
            records.append(
                {
                    "case": case["case"],
                    "method": method,
                    "scores": values.tolist(),
                    "metrics": metrics,
                }
            )
    return records, {"cases": case_diagnostics}


def run_decomposed_study(
    output,
    *,
    seeds=None,
    epochs=EPOCHS,
    prepared=None,
    split="validation",
):
    if split not in ("validation", "test"):
        raise ValueError("split must be 'validation' or 'test'")
    if seeds is None:
        seeds = SEEDS if split == "validation" else TEST_SEEDS
    if (
        len(seeds) < MIN_SEEDS
        or len(set(seeds)) != len(seeds)
        or any(type(s) is not int or s < 0 for s in seeds)
        or type(epochs) is not int
        or epochs < 1
    ):
        raise ValueError("distinct nonnegative seeds and positive epochs required")
    output = Path(output)
    if prepared is None:
        pools = None
    elif split == "validation":
        pools = load_real_pools(prepared)
    else:
        pools = load_heldout_pools(prepared)
    provenance = capture_provenance(
        [Path(prepared) / "manifest.json"] if prepared is not None else []
    )
    params = {
        "epochs": epochs,
        "protocol_version": 1,
        "real_data": pools is not None,
        "split": split,
    }
    runs = {}
    threads = torch.get_num_threads()
    try:
        torch.set_num_threads(1)
        with threadpool_limits(limits=1):
            for seed in seeds:
                print(f"Decomposed study ({split}) seed {seed}", flush=True)
                config = ExperimentConfig(
                    dataset="decomposed_study",
                    method="decomposed_vs_baselines",
                    seed=seed,
                    split=split,
                    params=params,
                )
                result = load_completed_result(output, config, provenance)
                if result is None:
                    records, metadata = _run_seed(seed, epochs, pools)
                    result = ResultEnvelope(
                        config.canonical_dict(),
                        provenance,
                        {"records": records},
                        metadata=metadata,
                    )
                    write_result_atomic(output, result)
                runs[seed] = result.metrics["records"]
    finally:
        torch.set_num_threads(threads)

    cases = {c["case"] for c in synthetic_cases(0)}
    if pools is not None:
        cases.update(c["case"] for c in real_cases(pools, seeds[0]))
    metrics = aggregate_study(runs, cases)
    config = ExperimentConfig(
        dataset="decomposed_study",
        method="decomposed_summary",
        seed=0,
        split=split,
        params={**params, "seeds": list(seeds)},
    )
    root = output / "summary"
    completed = load_completed_result(root, config, provenance)
    if completed is not None:
        if completed.metrics != metrics:
            raise ValueError("summary mismatch")
        return root / config.config_hash / provenance.identity_hash / "result.json"
    return write_result_atomic(
        root,
        ResultEnvelope(
            config.canonical_dict(),
            provenance,
            metrics,
            metadata={
                "protocol_complete": len(seeds) == len(SEEDS)
                and epochs == EPOCHS
                and pools is not None,
                "stage": f"decomposed_attribution_{split}",
            },
        ),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prepared", type=Path, required=False, default=None)
    parser.add_argument(
        "--split",
        choices=("validation", "test"),
        default="validation",
    )
    args = parser.parse_args()
    print(
        run_decomposed_study(
            args.output, prepared=args.prepared, split=args.split
        ),
        flush=True,
    )

