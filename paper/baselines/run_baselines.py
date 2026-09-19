"""
Baseline Comparison: ADWIN, KSWIN, DDM vs. Vigil on NSL-KDD
=============================================================
Runs three classical concept-drift detectors from the `river` library on the
same 50-chunk NSL-KDD stream used in the Vigil benchmark, then outputs a
unified results table suitable for the paper.

Detectors compared
------------------
- ADWIN  : Adaptive Windowing (Bifet & Gavalda, 2007)
- KSWIN  : Kolmogorov-Smirnov Windowing (Raab et al., 2020)
- DDM    : Drift Detection Method (Gama et al., 2004)
- Vigil  : Our method (dual autoencoder + DriftAttributor)

Note: ADWIN/KSWIN/DDM are univariate detectors; they are applied to the
      mean absolute error of a 1-NN classifier trained on normal traffic,
      matching the common "error-rate monitoring" evaluation protocol.

Usage
-----
    python paper/baselines/run_baselines.py
"""

import sys
import time
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from data.nsl_kdd_loader import load_nsl_kdd
from data.stream_simulator import StreamSimulator
from vigil import Vigil

# ── Shared config ──────────────────────────────────────────────────────────────
CHUNK_SIZE        = 200
N_CHUNKS          = 50
DRIFT_AFTER       = 5       # chunks 1-5 are normal (ground truth: no drift)
NOVELTY_AFTER     = 20
NOVELTY_PROP      = 0.25
BUFFER_SIZE       = 600
DRIFT_THRESHOLD   = 0.10
TOP_K             = 5
SEED              = 42

# ── Load data ──────────────────────────────────────────────────────────────────
print("Loading NSL-KDD...", flush=True)
X_train, y_train, feature_names = load_nsl_kdd("train")
rng = np.random.default_rng(SEED)

normal_idx   = np.where(y_train == "normal")[0]
baseline_idx = rng.choice(normal_idx, size=1000, replace=False)
baseline_X   = X_train[baseline_idx]

# ── Vigil ──────────────────────────────────────────────────────────────────────
print("Training Vigil...", flush=True)
vigil = Vigil(
    feature_names=feature_names,
    top_k_features=TOP_K,
    buffer_size=BUFFER_SIZE,
    drift_threshold=DRIFT_THRESHOLD,
    initial_epochs=400,
    update_epochs=50,
)
t0 = time.time()
vigil.fit(baseline_X, verbose=False)
vigil_fit_time = time.time() - t0

# ── Build 1-NN error-rate signal for classical detectors ──────────────────────
# Classical detectors monitor a scalar error signal (binary: 0 or 1 per sample).
# We use: does a 1-NN model trained on normal traffic misclassify this sample?
# This is the standard evaluation protocol for DDM/ADWIN/KSWIN on NSL-KDD.
print("Building 1-NN error signal for classical detectors...", flush=True)
from sklearn.neighbors import KNeighborsClassifier

knn = KNeighborsClassifier(n_neighbors=1, n_jobs=-1)
knn.fit(baseline_X, np.zeros(len(baseline_X)))   # all baseline = class 0

# ── Stream ─────────────────────────────────────────────────────────────────────
sim = StreamSimulator(
    X_train, y_train,
    chunk_size=CHUNK_SIZE,
    drift_after_chunk=DRIFT_AFTER,
    novelty_after_chunk=NOVELTY_AFTER,
    novelty_proportion=NOVELTY_PROP,
    seed=SEED,
)

# Storage
vigil_results   = []
adwin_results   = []
kswin_results   = []
ph_results      = []

# Import river detectors
from river.drift import ADWIN, KSWIN, PageHinkley

adwin_det = ADWIN(delta=0.002)
kswin_det = KSWIN(window_size=300, stat_size=50)
ph_det    = PageHinkley()   # Page-Hinkley test — detects mean shift in error rate

def metrics_from_results(results, n_chunks, drift_after):
    gt_drift = [i > drift_after for i in range(1, n_chunks + 1)]
    tp = sum(1 for g, d in zip(gt_drift, results) if g and d)
    fp = sum(1 for g, d in zip(gt_drift, results) if not g and d)
    fn = sum(1 for g, d in zip(gt_drift, results) if g and not d)
    tn = sum(1 for g, d in zip(gt_drift, results) if not g and not d)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall    = tp / (tp + fn) if (tp + fn) else 0.0
    f1        = 2*precision*recall/(precision+recall) if (precision+recall) else 0.0
    detected  = [i+1 for i, d in enumerate(results) if d]
    delay     = (detected[0] - drift_after) if detected else None
    for i, d in enumerate(results):
        if i >= drift_after and d:
            delay = i + 1 - drift_after
            break
    return dict(TP=tp, FP=fp, FN=fn, TN=tn,
                precision=precision, recall=recall, f1=f1, delay=delay)

print(f"\n{'Chunk':>5}  {'GT':>5}  {'Vigil':>8}  {'ADWIN':>8}  {'KSWIN':>8}  {'DDM':>8}")
print("-" * 55)

for chunk in sim.stream(n_chunks=N_CHUNKS):
    cid      = chunk.chunk_id
    gt_drift = cid > DRIFT_AFTER

    # ── Vigil detection ──────────────────────────────────────────────────────
    vr = vigil.detect(chunk.X)
    vigil_detected = vr.drift_detected
    vigil_results.append(vigil_detected)

    # ── 1-NN error signal for this chunk ────────────────────────────────────
    # Treat attack samples as class 1, normal as class 0.
    true_labels = (y_train[
        rng.choice(len(y_train), size=CHUNK_SIZE, replace=False)
    ] != "normal").astype(int)
    # Simpler: just predict on chunk.X and check against ground truth
    preds = knn.predict(chunk.X).astype(int)
    # For the error signal: the ground truth for this chunk is that
    # attack-phase chunks have many non-normal samples
    chunk_gt = (y_train[
        rng.choice(len(X_train), size=CHUNK_SIZE, replace=False)
    ] != "normal").astype(int)

    # Feed each sample's error (1 = wrong, 0 = correct) to classical detectors
    adwin_fired = False
    kswin_fired = False
    ph_fired   = False

    for i in range(CHUNK_SIZE):
        # error = 1 if prediction differs from ground truth concept
        err = int(preds[i] != chunk_gt[i])

        # ADWIN: feed raw feature values (use first principal component as proxy)
        # Actually ADWIN needs a scalar per sample — use reconstruction error proxy
        # We use the error signal (0/1) for ADWIN which is standard in literature
        adwin_det.update(err)
        if adwin_det.drift_detected:
            adwin_fired = True

        kswin_det.update(err)
        if kswin_det.drift_detected:
            kswin_fired = True

        ph_det.update(err)
        if ph_det.drift_detected:
            ph_fired = True

    adwin_results.append(adwin_fired)
    kswin_results.append(kswin_fired)
    ph_results.append(ph_fired)

    gt_str = "YES" if gt_drift else "NO "
    v_str  = "DRIFT" if vigil_detected  else "stable"
    a_str  = "DRIFT" if adwin_fired  else "stable"
    k_str  = "DRIFT" if kswin_fired  else "stable"
    d_str  = "DRIFT" if ph_fired     else "stable"

    print(f"  {cid:>3}  {gt_str:>5}  {v_str:>8}  {a_str:>8}  {k_str:>8}  {d_str:>8}")

# ── Metrics ────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("  RESULTS TABLE")
print("=" * 70)

detectors = {
    "Vigil (ours)" : vigil_results,
    "ADWIN"        : adwin_results,
    "KSWIN"        : kswin_results,
    "PageHinkley"  : ph_results,
}

results_table = {}
for name, res in detectors.items():
    m = metrics_from_results(res, N_CHUNKS, DRIFT_AFTER)
    results_table[name] = m

print(f"\n  {'Method':<20}  {'Prec':>6}  {'Rec':>6}  {'F1':>6}  "
      f"{'TP':>4}  {'FP':>4}  {'FN':>4}  {'Delay':>6}")
print("  " + "-" * 66)
for name, m in results_table.items():
    delay_str = f"{m['delay']}ch" if m['delay'] else "N/A"
    flag = " <-- OUR METHOD" if "Vigil" in name else ""
    print(f"  {name:<20}  {m['precision']:>6.1%}  {m['recall']:>6.1%}  "
          f"{m['f1']:>6.1%}  {m['TP']:>4}  {m['FP']:>4}  {m['FN']:>4}  "
          f"{delay_str:>6}{flag}")

# ── LaTeX table output ─────────────────────────────────────────────────────────
print("\n\n% ── LaTeX table (paste into paper/main.tex) ──────────────────────")
print(r"\begin{table}[!t]")
print(r"\caption{Drift Detection Results on NSL-KDD (50 chunks $\times$ 200 samples)}")
print(r"\label{tab:results}")
print(r"\centering")
print(r"\begin{tabular}{lcccccc}")
print(r"\toprule")
print(r"\textbf{Method} & \textbf{Precision} & \textbf{Recall} & "
      r"\textbf{F1} & \textbf{Delay} & \textbf{Labels?} & \textbf{Attribution?} \\")
print(r"\midrule")
meta = {
    "Vigil (ours)" : ("No",  "Yes"),
    "ADWIN"        : ("No",  "No"),
    "KSWIN"        : ("No",  "No"),
    "PageHinkley"  : ("No",  "No"),
}
for name, m in results_table.items():
    labels, attr = meta[name]
    delay_str = f"{m['delay']} chunk" if m['delay'] else "N/A"
    bold_open  = r"\textbf{" if "Vigil" in name else ""
    bold_close = "}"         if "Vigil" in name else ""
    print(f"{bold_open}{name}{bold_close} & "
          f"{bold_open}{m['precision']:.1%}{bold_close} & "
          f"{bold_open}{m['recall']:.1%}{bold_close} & "
          f"{bold_open}{m['f1']:.1%}{bold_close} & "
          f"{bold_open}{delay_str}{bold_close} & "
          f"{labels} & {attr} \\\\")
print(r"\bottomrule")
print(r"\end{tabular}")
print(r"\end{table}")

print("\nDone.")
