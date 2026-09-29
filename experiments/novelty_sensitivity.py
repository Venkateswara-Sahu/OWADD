"""Post-pilot sensitivity using saved scores only; never fits a model."""

import argparse
import json
from collections import defaultdict
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

import numpy as np

from experiments.config import ExperimentConfig
from experiments.io import ResultEnvelope, load_completed_result, write_result_atomic
from experiments.metrics.novelty import evaluate_novelty
from experiments.metrics.stats import bootstrap_mean_ci
from experiments.novelty_development import METHODS
from experiments.novelty_protocol import prevalence_indices
from experiments.novelty_scores import load_scores
from experiments.provenance import Provenance, capture_provenance, sha256_file


def calibration_threshold(labels, scores, *, target=0.01):
    """Conservative empirical known-FPR constraint, not a population guarantee."""
    evaluate_novelty(labels, scores, 0.0)
    if not np.isfinite(target) or not 0 <= target < 1:
        raise ValueError("target FPR must be in [0, 1)")
    known = np.sort(np.asarray(scores)[np.asarray(labels) == 0])
    if not len(known):
        raise ValueError("known calibration samples required")
    allowed = int(np.floor(target * len(known)))
    threshold = float(np.nextafter(known[len(known) - allowed - 1], np.inf))
    if not np.isfinite(threshold):
        raise ValueError("no finite conservative threshold")
    return threshold


def _read_source(path, source):
    if path.with_suffix(".complete").read_text().strip() != sha256_file(path):
        raise ValueError("source result checksum mismatch")
    result = json.loads(path.read_text())
    evidence = (source / result["metadata"]["evidence_dir"]).resolve()
    if not evidence.is_relative_to(source.resolve()):
        raise ValueError("invalid evidence path")
    freeze_path = evidence / "freeze.json"
    frozen = json.loads(freeze_path.read_text())
    checksum = frozen.pop("integrity_sha256")
    encoded = json.dumps(frozen, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if sha256(encoded.encode()).hexdigest() != checksum:
        raise ValueError("freeze integrity mismatch")
    if (
        frozen["model_id"] != result["metadata"]["model_id"]
        or frozen["protocol_id"] != result["config"]["params"]["protocol_id"]
        or result["metadata"]["evaluation_scope"] != "development_holdout"
        or result["metadata"]["official_test_loaded"] is not False
        or result["config"]["split"] != "validation"
    ):
        raise ValueError("source protocol or model identity mismatch")
    name = frozen["validation_scores"]["file"]
    if Path(name).name != name:
        raise ValueError("invalid calibration sidecar path")
    calibration_path, development_path = evidence / name, evidence / "development.npz"
    cal_y, cal_s = load_scores(calibration_path, frozen["validation_scores"])
    dev_y, dev_s = load_scores(
        development_path, result["metadata"]["development_scores"]
    )
    if asdict(evaluate_novelty(dev_y, dev_s, frozen["threshold"])) != result["metrics"]:
        raise ValueError("source metrics mismatch")
    return (
        result,
        frozen,
        cal_y,
        cal_s,
        dev_y,
        dev_s,
        [path, freeze_path, calibration_path, development_path],
    )


def analyze(
    source,
    output,
    *,
    expected_seeds=tuple(range(10)),
    n_samples=8000,
    prevalences=(0.01, 0.05, 0.10, 0.25, 0.50),
):
    """Re-evaluate immutable evidence; the 1% FPR alternative is exploratory."""
    if any(
        not isinstance(value, (int, float))
        or not np.isfinite(value)
        or not 0 < value < 1
        for value in prevalences
    ) or len(set(prevalences)) != len(prevalences):
        raise ValueError(
            "prevalences must be unique finite values strictly between 0 and 1"
        )
    source, output = Path(source), Path(output)
    loaded = [
        _read_source(path, source) for path in sorted(source.glob("*/*/result.json"))
    ]
    actual = [(r[0]["config"]["seed"], r[0]["config"]["method"]) for r in loaded]
    expected = {(seed, method) for seed in expected_seeds for method in METHODS}
    if not expected or set(actual) != expected or len(actual) != len(expected):
        raise ValueError("complete unique seed/method grid required")
    if len({Provenance(**r[0]["provenance"]).identity_hash for r in loaded}) != 1:
        raise ValueError("mixed source provenance")
    if any(
        r[0]["config"]["params"] != loaded[0][0]["config"]["params"] for r in loaded
    ):
        raise ValueError("mixed source configuration")
    records, inputs = [], []
    groups = defaultdict(list)
    for result, frozen, cal_y, cal_s, dev_y, dev_s, paths in loaded:
        if not np.array_equal(dev_y, loaded[0][4]) or not np.array_equal(
            cal_y, loaded[0][2]
        ):
            raise ValueError("unpaired source labels")
        inputs.extend(paths)
        thresholds = {
            "original_f1": frozen["threshold"],
            "calibration_fpr_1pct": calibration_threshold(cal_y, cal_s),
        }
        for operating_point, threshold in thresholds.items():
            calibration = evaluate_novelty(cal_y, cal_s, threshold)
            for prevalence in (None, *prevalences):
                indices = (
                    np.arange(len(dev_y))
                    if prevalence is None
                    else prevalence_indices(dev_y, prevalence, n_samples, seed=42)
                )
                metrics = asdict(
                    evaluate_novelty(dev_y[indices], dev_s[indices], threshold)
                )
                row = {
                    "seed": result["config"]["seed"],
                    "method": result["config"]["method"],
                    "operating_point": operating_point,
                    "prevalence": prevalence,
                    "threshold": threshold,
                    "calibration_fpr": calibration.false_positive_rate,
                    "indices_sha256": sha256(
                        indices.astype("<i8").tobytes()
                    ).hexdigest(),
                    "metrics": metrics,
                }
                records.append(row)
                groups[(row["method"], operating_point, prevalence)].append(metrics)

    def statistics(values):
        defined = np.array(
            [value for value in values if value is not None], dtype=float
        )
        return {
            "n": len(values),
            "n_defined": len(defined),
            "mean": float(defined.mean()) if len(defined) else None,
            "ci95": list(bootstrap_mean_ci(defined)) if len(defined) else None,
        }

    report = []
    for (method, operating_point, prevalence), rows in groups.items():
        report.append(
            {
                "method": method,
                "operating_point": operating_point,
                "prevalence": prevalence,
                "metrics": {
                    name: statistics([row[name] for row in rows])
                    for name in rows[0]
                    if name != "undefined_reasons"
                },
            }
        )
    provenance = capture_provenance(inputs)
    config = ExperimentConfig(
        dataset="nsl_kdd_novelty_development",
        method="prevalence_sensitivity",
        seed=42,
        split="validation",
        params={
            "seeds": list(expected_seeds),
            "n_samples": n_samples,
            "prevalences": list(prevalences),
            "target_fpr": 0.01,
        },
    )
    envelope = ResultEnvelope(
        config=config.canonical_dict(),
        provenance=provenance,
        metrics={"groups": report},
        metadata={
            "records": records,
            "source_provenance": loaded[0][0]["provenance"],
            "exploratory": True,
            "official_test_loaded": False,
            "uncertainty": "model seeds conditional on fixed split and subsets",
        },
    )
    existing = load_completed_result(output, config, provenance)
    if existing is not None:
        if (
            existing.metrics != envelope.metrics
            or existing.metadata != envelope.metadata
        ):
            raise ValueError("sensitivity summary mismatch")
        return output / config.config_hash / provenance.identity_hash / "result.json"
    return write_result_atomic(output, envelope)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(analyze(args.source, args.output), flush=True)
