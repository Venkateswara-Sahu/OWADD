"""Final bounded mechanism screen; no automatic method promotion."""

import argparse
from hashlib import sha256
from pathlib import Path

import numpy as np
import torch
from scipy.stats import spearmanr
from threadpoolctl import threadpool_limits

from experiments.config import ExperimentConfig
from experiments.io import ResultEnvelope, load_completed_result, write_result_atomic
from experiments.mechanism import fit_pair, score_windows
from experiments.mechanism_data import load_real_pools, real_cases, synthetic_cases
from experiments.metrics.attribution import evaluate_ranking
from experiments.metrics.stats import bootstrap_mean_ci
from experiments.provenance import capture_provenance

SEEDS = tuple(range(50, 70))
EPOCHS = 20
MIN_SEEDS = 2
METHODS = (
    *(
        f"{state}_{rule}"
        for state in ("trained", "untrained")
        for rule in ("positive", "absolute", "standardized")
    ),
    "squared_input_change",
    "kolmogorov_smirnov",
    "max_correlation_change",
)
PAIRS = [
    (f"trained_{rule}", f"untrained_{rule}")
    for rule in ("positive", "absolute", "standardized")
]
PAIRS.append(("trained_absolute", "squared_input_change"))


def _hash(array):
    return sha256(array.tobytes()).hexdigest()


def _summary(values):
    defined = [value for value in values if value is not None]
    return {
        "mean": float(np.mean(defined)) if defined else None,
        "ci95": list(bootstrap_mean_ci(defined)) if defined else None,
        "n_defined": len(defined),
    }


def aggregate(runs, case_names):
    expected = {(case, method) for case in case_names for method in METHODS}
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
        for candidate, baseline in PAIRS:
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
    models, model_metadata, case_metadata, records = {}, {}, {}, []
    for case in cases:
        key = _hash(case["train"])
        if key not in models:
            original, trained, metadata = fit_pair(case["train"], seed, epochs)
            models[key] = original, trained
            model_metadata[key] = metadata
        scores, details = score_windows(
            *models[key], case["reference"], case["current"]
        )
        a, b = scores["trained_absolute"], scores["squared_input_change"]
        agreement = (
            float(spearmanr(a, b).statistic)
            if np.ptp(a) > 0 and np.ptp(b) > 0
            else None
        )
        case_metadata[case["case"]] = {
            "train_sha256": key,
            "reference_sha256": _hash(case["reference"]),
            "current_sha256": _hash(case["current"]),
            "truth": list(case["truth"]),
            "tie_order": case["tie_order"].tolist(),
            "details": details,
            "trained_input_spearman": agreement,
            "reference_ids": case.get("reference_ids", []),
            "current_ids": case.get("current_ids", []),
        }
        truth = tuple(
            i for i, col in enumerate(case["tie_order"]) if col in case["truth"]
        )
        for method, values in scores.items():
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
    return records, {"models": model_metadata, "cases": case_metadata}


def run_screen(output, *, seeds=SEEDS, epochs=EPOCHS, prepared=None):
    if (
        len(seeds) < MIN_SEEDS
        or len(set(seeds)) != len(seeds)
        or any(type(s) is not int or s < 0 for s in seeds)
        or type(epochs) is not int
        or epochs < 1
    ):
        raise ValueError("distinct nonnegative seeds and positive epochs required")
    output = Path(output)
    pools = load_real_pools(prepared) if prepared is not None else None
    provenance = capture_provenance(
        [Path(prepared) / "manifest.json"] if prepared is not None else []
    )
    params = {"epochs": epochs, "protocol_version": 1, "real_data": pools is not None}
    runs, diagnostic = {}, {}
    threads = torch.get_num_threads()
    try:
        torch.set_num_threads(1)
        with threadpool_limits(limits=1):
            for seed in seeds:
                print(f"Mechanism screen seed {seed}", flush=True)
                config = ExperimentConfig(
                    dataset="final_mechanism",
                    method="paired_mechanism",
                    seed=seed,
                    split="validation",
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
                diagnostic[seed] = result.metadata["cases"]
    finally:
        torch.set_num_threads(threads)
    cases = {c["case"] for c in synthetic_cases(0)}
    if pools is not None:
        cases.update(c["case"] for c in real_cases(pools, 50))
    metrics = aggregate(runs, cases)
    metrics["score_agreement"] = {
        case: _summary(
            [diagnostic[s][case]["trained_input_spearman"] for s in sorted(runs)]
        )
        for case in sorted(cases)
    }
    config = ExperimentConfig(
        dataset="final_mechanism",
        method="mechanism_summary",
        seed=0,
        split="validation",
        params={**params, "seeds": list(seeds)},
    )
    root = output / "summary"
    completed = load_completed_result(root, config, provenance)
    if completed is not None:
        if completed.metrics != metrics:
            raise ValueError("summary mismatch")
        return root / config.config_hash / provenance.identity_hash / "result.json"
    real_metadata = (
        {
            k: v
            for k, v in pools.items()
            if k not in ("train", "validation", "validation_ids")
        }
        if pools
        else None
    )
    return write_result_atomic(
        root,
        ResultEnvelope(
            config.canonical_dict(),
            provenance,
            metrics,
            metadata={
                "protocol_complete": set(seeds) == set(SEEDS)
                and epochs == EPOCHS
                and pools is not None,
                "not_full_study": True,
                "stage": "final_mechanism_development",
                "real_data": real_metadata,
            },
        ),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prepared", type=Path, required=True)
    args = parser.parse_args()
    print(run_screen(args.output, prepared=args.prepared), flush=True)
