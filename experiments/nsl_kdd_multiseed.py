"""Multi-seed NSL-KDD streaming benchmark comparing Vigil against river baselines."""

import json
from pathlib import Path

import numpy as np
import torch
from river import drift as river_drift
from sklearn.neighbors import NearestNeighbors

from data.nsl_kdd_loader import get_nsl_kdd_feature_groups, load_nsl_kdd
from data.stream_simulator import StreamSimulator
from vigil import Vigil

SEEDS = (42, 43, 44, 45, 46)
CHUNK_SIZE = 200
N_CHUNKS = 50
DRIFT_AFTER_CHUNK = 5
NOVELTY_AFTER = 20
NOVELTY_PROPORTION = 0.25
BUFFER_SIZE = 600
DRIFT_THRESHOLD = 0.30
NOVELTY_THRESHOLD = 0.05


def _chunk_metrics(gt_flags: list[bool], det_flags: list[bool]) -> dict[str, float]:
    tp = sum(1 for g, d in zip(gt_flags, det_flags) if g and d)
    fp = sum(1 for g, d in zip(gt_flags, det_flags) if not g and d)
    fn = sum(1 for g, d in zip(gt_flags, det_flags) if g and not d)
    tn = sum(1 for g, d in zip(gt_flags, det_flags) if not g and not d)
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    acc = (tp + tn) / len(gt_flags) if gt_flags else 0.0
    drift_cids = [
        idx + 1 for idx, (g, d) in enumerate(zip(gt_flags, det_flags)) if g and d
    ]
    delay = float(drift_cids[0] - DRIFT_AFTER_CHUNK) if drift_cids else float("nan")
    return {
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "accuracy": acc,
        "delay": delay,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


def run_single_seed(
    X_train: np.ndarray,
    y_train: np.ndarray,
    feature_names: list[str],
    feature_groups: dict[str, list[int]],
    seed: int,
) -> dict[str, dict[str, float]]:
    normal_idx = np.where(y_train == "normal")[0]
    rng = np.random.default_rng(seed)
    baseline_idx = rng.choice(normal_idx, size=1000, replace=False)
    baseline_X = X_train[baseline_idx]

    # 1. Fit 1-NN anomaly threshold on baseline normal traffic (95th pct distance)
    nn = NearestNeighbors(n_neighbors=2).fit(baseline_X)
    base_dists, _ = nn.kneighbors(baseline_X)
    nn_thresh = float(np.percentile(base_dists[:, 1], 95.0))

    # 2. Fit Vigil (auto adaptation mode) and Vigil (verified_only mode)
    vigil_auto = Vigil(
        feature_names=feature_names,
        top_k_features=5,
        buffer_size=BUFFER_SIZE,
        drift_threshold=DRIFT_THRESHOLD,
        initial_epochs=400,
        update_epochs=50,
        attribution_mode="decomposed",
        adaptation_mode="auto",
        feature_groups=feature_groups,
        seed=seed,
    )
    vigil_auto.fit(baseline_X, verbose=False)

    vigil_verified = Vigil(
        feature_names=feature_names,
        top_k_features=5,
        buffer_size=BUFFER_SIZE,
        drift_threshold=DRIFT_THRESHOLD,
        initial_epochs=400,
        update_epochs=50,
        attribution_mode="decomposed",
        adaptation_mode="verified_only",
        feature_groups=feature_groups,
        seed=seed,
    )
    vigil_verified.fit(baseline_X, verbose=False)

    # 3. Initialize river detectors for supervised labels and unsupervised AE errors
    sup_detectors = {
        "adwin_supervised": river_drift.ADWIN(),
        "kswin_supervised": river_drift.KSWIN(seed=seed),
        "ph_supervised": river_drift.PageHinkley(),
    }
    unsup_detectors = {
        "adwin_ae_error": river_drift.ADWIN(),
        "kswin_ae_error": river_drift.KSWIN(seed=seed),
        "ph_ae_error": river_drift.PageHinkley(),
    }
    # Warm up unsupervised river detectors on baseline reconstruction errors
    base_ae_errors = vigil_verified._autoencoder_A.reconstruction_errors(
        torch.as_tensor(baseline_X, dtype=torch.float32)
    )
    for err in base_ae_errors:
        for det in unsup_detectors.values():
            det.update(float(err))

    sim = StreamSimulator(
        X_train,
        y_train,
        chunk_size=CHUNK_SIZE,
        drift_after_chunk=DRIFT_AFTER_CHUNK,
        novelty_after_chunk=NOVELTY_AFTER,
        novelty_proportion=NOVELTY_PROPORTION,
        seed=seed,
    )

    gt_drift_flags: list[bool] = []
    gt_novelty_flags: list[bool] = []
    det_tracks: dict[str, list[bool]] = {
        "vigil_auto": [],
        "vigil_verified_only": [],
        **{k: [] for k in sup_detectors},
        **{k: [] for k in unsup_detectors},
    }
    novelty_hits = 0

    for chunk in sim.stream(n_chunks=N_CHUNKS):
        cid = chunk.chunk_id
        gt_drift = cid > DRIFT_AFTER_CHUNK
        gt_nov = cid > NOVELTY_AFTER
        gt_drift_flags.append(gt_drift)
        gt_novelty_flags.append(gt_nov)

        res_auto = vigil_auto.detect(chunk.X)
        res_ver = vigil_verified.detect(chunk.X)
        det_tracks["vigil_auto"].append(res_auto.drift_detected)
        det_tracks["vigil_verified_only"].append(res_ver.drift_detected)

        if gt_nov and res_auto.novelty_proportion >= NOVELTY_THRESHOLD:
            novelty_hits += 1

        # Supervised 1-NN error stream (requires ground-truth attack/normal labels)
        dists, _ = nn.kneighbors(chunk.X, n_neighbors=1)
        pred_attack = dists[:, 0] > nn_thresh
        true_attack = chunk.labels != "normal"
        sup_errors = (pred_attack != true_attack).astype(float)


        for name, det in sup_detectors.items():
            fired = False
            for val in sup_errors:
                det.update(float(val))
                if det.drift_detected:
                    fired = True
            det_tracks[name].append(fired)

        # Unsupervised AE reconstruction error stream
        ae_errors = vigil_verified._autoencoder_A.reconstruction_errors(
            torch.as_tensor(chunk.X, dtype=torch.float32)
        )
        for name, det in unsup_detectors.items():
            fired = False
            for val in ae_errors:
                det.update(float(val))
                if det.drift_detected:
                    fired = True
            det_tracks[name].append(fired)


    out = {
        method: _chunk_metrics(gt_drift_flags, flags)
        for method, flags in det_tracks.items()
    }
    n_nov_chunks = sum(gt_novelty_flags)
    out["vigil_auto"]["novelty_recall"] = (
        novelty_hits / n_nov_chunks if n_nov_chunks else 0.0
    )
    return out


def main():
    X_train, y_train, feature_names = load_nsl_kdd("train", fit_normal_only=True)
    feature_groups = get_nsl_kdd_feature_groups(feature_names)
    per_seed = {}
    for seed in SEEDS:
        print(f"[NSL-KDD Multi-Seed] Running seed {seed}...", flush=True)
        per_seed[seed] = run_single_seed(
            X_train, y_train, feature_names, feature_groups, seed
        )

    methods = list(per_seed[SEEDS[0]].keys())
    summary = {}
    print("\n=== NSL-KDD 5-SEED SUMMARY (Mean ± SD) ===")
    print(
        f"{'Method':<24} | {'Precision (%)':<15} | {'Recall (%)':<15} | "
        f"{'F1 (%)':<15} | {'Delay (chunks)':<14}"
    )
    print("-" * 92)
    for m in methods:
        precs = [per_seed[s][m]["precision"] * 100 for s in SEEDS]
        recs = [per_seed[s][m]["recall"] * 100 for s in SEEDS]
        f1s = [per_seed[s][m]["f1"] * 100 for s in SEEDS]
        delays = [
            per_seed[s][m]["delay"]
            for s in SEEDS
            if not np.isnan(per_seed[s][m]["delay"])
        ]
        summary[m] = {
            "precision_mean": float(np.mean(precs)),
            "precision_std": float(np.std(precs)),
            "recall_mean": float(np.mean(recs)),
            "recall_std": float(np.std(recs)),
            "f1_mean": float(np.mean(f1s)),
            "f1_std": float(np.std(f1s)),
            "delay_mean": float(np.mean(delays)) if delays else None,
        }
        if m == "vigil_auto":
            novs = [per_seed[s][m]["novelty_recall"] * 100 for s in SEEDS]
            summary[m]["novelty_recall_mean"] = float(np.mean(novs))
            summary[m]["novelty_recall_std"] = float(np.std(novs))

        d_str = f"{np.mean(delays):.1f}" if delays else "N/A"
        print(
            f"{m:<24} | {np.mean(precs):6.1f} ± {np.std(precs):4.1f} | "
            f"{np.mean(recs):6.1f} ± {np.std(recs):4.1f} | "
            f"{np.mean(f1s):6.1f} ± {np.std(f1s):4.1f} | {d_str:>14}"
        )

    out_path = Path("artifacts/runs/nsl_kdd_multiseed_summary.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {"seeds": list(SEEDS), "summary": summary, "per_seed": per_seed},
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nSaved summary to {out_path}")


if __name__ == "__main__":
    main()
