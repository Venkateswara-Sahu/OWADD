"""
Baseline Comparison: ADWIN, KSWIN, PageHinkley vs. Vigil on NSL-KDD
=====================================================================
Runs three classical concept-drift detectors from the `river` library on the
same 50-chunk NSL-KDD stream used in the Vigil benchmark, then outputs a
unified results table for the paper.

Methodology (fair comparison)
------------------------------
Classical detectors (ADWIN, KSWIN, Page-Hinkley) are univariate — they monitor
a scalar error signal per sample.  We use the standard "error-rate monitoring"
protocol from the drift detection literature:

  1. Train a 1-NN classifier on the SAME 1,000-sample normal-only baseline
     that Vigil uses.
  2. For each incoming sample in each chunk, compute:
       error = 1  if  true_label != "normal"  and  pred == "normal"
               0  otherwise
     Because the 1-NN is trained only on normal data, it classifies everything
     as "normal", so error simplifies to:
       error = 1  if  true_label != "normal"   (i.e. any attack sample)
               0  if  true_label == "normal"
  3. Feed each binary error to the detector.

This gives classical detectors a LABELED error signal (they know when a sample
is an attack at inference time).  Vigil receives NO labels.  The "Labels?"
column in the paper table captures this key difference.

The stream protocol (3 phases, 50 chunks × 200 samples) is identical to the
Vigil benchmark so results are directly comparable.

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

# ── Shared config (must match benchmark_nsl_kdd.py exactly) ───────────────────
CHUNK_SIZE      = 200
N_CHUNKS        = 50
DRIFT_AFTER     = 5
NOVELTY_AFTER   = 20
NOVELTY_PROP    = 0.25
BUFFER_SIZE     = 600
DRIFT_THRESHOLD = 0.10
TOP_K           = 5
SEED            = 42

# ── Load data ──────────────────────────────────────────────────────────────────
print("Loading NSL-KDD...", flush=True)
X_train, y_train, feature_names = load_nsl_kdd("train")
print(f"  {len(X_train):,} samples | {len(feature_names)} features", flush=True)

rng = np.random.default_rng(SEED)
normal_idx   = np.where(y_train == "normal")[0]
baseline_idx = rng.choice(normal_idx, size=1000, replace=False)
baseline_X   = X_train[baseline_idx]

# ── Train Vigil ────────────────────────────────────────────────────────────────
print("\nTraining Vigil...", flush=True)
vigil = Vigil(
    feature_names=feature_names,
    top_k_features=TOP_K,
    buffer_size=BUFFER_SIZE,
    drift_threshold=DRIFT_THRESHOLD,
    initial_epochs=400,
    update_epochs=50,
)
vigil.fit(baseline_X, verbose=False)
print("  Vigil ready.", flush=True)

# ── Stream ─────────────────────────────────────────────────────────────────────
sim = StreamSimulator(
    X_train, y_train,
    chunk_size=CHUNK_SIZE,
    drift_after_chunk=DRIFT_AFTER,
    novelty_after_chunk=NOVELTY_AFTER,
    novelty_proportion=NOVELTY_PROP,
    seed=SEED,
)

# Initialise detectors
from river.drift import ADWIN, KSWIN, PageHinkley

adwin_det = ADWIN(delta=0.002)
kswin_det = KSWIN(window_size=300, stat_size=50)
ph_det    = PageHinkley()

vigil_results = []
adwin_results = []
kswin_results = []
ph_results    = []

print(f"\n{'Chunk':>5}  {'GT':>5}  {'Vigil':>8}  {'ADWIN':>8}  {'KSWIN':>8}  {'PH':>8}")
print("-" * 56)

for chunk in sim.stream(n_chunks=N_CHUNKS):
    cid      = chunk.chunk_id
    gt_drift = cid > DRIFT_AFTER

    # ── Vigil (fully unsupervised, no labels) ─────────────────────────────────
    vr = vigil.detect(chunk.X)
    vigil_results.append(vr.drift_detected)

    # ── Classical detectors (error-rate monitoring with TRUE labels) ──────────
    # error_i = 1 if sample is an attack (1-NN always predicts "normal" since
    # it is trained exclusively on normal data, so error = is_attack).
    # This is the standard evaluation protocol; it REQUIRES ground-truth labels.
    is_attack = (chunk.labels != "normal").astype(int)   # shape (chunk_size,)

    adwin_fired = False
    kswin_fired = False
    ph_fired    = False

    for err in is_attack:
        err_f = float(err)

        adwin_det.update(err_f)
        if adwin_det.drift_detected:
            adwin_fired = True

        kswin_det.update(err_f)
        if kswin_det.drift_detected:
            kswin_fired = True

        ph_det.update(err_f)
        if ph_det.drift_detected:
            ph_fired = True

    adwin_results.append(adwin_fired)
    kswin_results.append(kswin_fired)
    ph_results.append(ph_fired)

    gt_str = "YES" if gt_drift   else "NO "
    v_str  = "DRIFT"  if vr.drift_detected else "stable"
    a_str  = "DRIFT"  if adwin_fired else "stable"
    k_str  = "DRIFT"  if kswin_fired else "stable"
    p_str  = "DRIFT"  if ph_fired    else "stable"

    print(f"  {cid:>3}  {gt_str:>5}  {v_str:>8}  {a_str:>8}  {k_str:>8}  {p_str:>8}")

# ── Metrics helper ─────────────────────────────────────────────────────────────
def compute_metrics(results, n_chunks, drift_after):
    gt = [i > drift_after for i in range(1, n_chunks + 1)]
    tp = sum(g and d for g, d in zip(gt, results))
    fp = sum(not g and d for g, d in zip(gt, results))
    fn = sum(g and not d for g, d in zip(gt, results))
    tn = sum(not g and not d for g, d in zip(gt, results))
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec  = tp / (tp + fn) if (tp + fn) else 0.0
    f1   = 2*prec*rec / (prec+rec) if (prec+rec) else 0.0
    delay = None
    for i, d in enumerate(results):
        if i >= drift_after and d:
            delay = i + 1 - drift_after
            break
    return dict(TP=tp, FP=fp, FN=fn, TN=tn,
                precision=prec, recall=rec, f1=f1, delay=delay)

# ── Print results ──────────────────────────────────────────────────────────────
print("\n" + "=" * 72)
print("  RESULTS TABLE")
print("=" * 72)

detectors = {
    "Vigil (ours)" : (vigil_results,  "No",  "Yes"),
    "ADWIN"        : (adwin_results,  "Yes", "No"),
    "KSWIN"        : (kswin_results,  "Yes", "No"),
    "PageHinkley"  : (ph_results,     "Yes", "No"),
}

metrics = {name: compute_metrics(res, N_CHUNKS, DRIFT_AFTER)
           for name, (res, _, _) in detectors.items()}

print(f"\n  {'Method':<20}  {'Prec':>6}  {'Rec':>6}  {'F1':>6}  "
      f"{'TP':>4}  {'FP':>4}  {'FN':>4}  {'Delay':>6}  Labels?")
print("  " + "-" * 72)
for name, (_, labels, attr) in detectors.items():
    m = metrics[name]
    delay_str = f"{m['delay']}ch" if m['delay'] else "N/A"
    flag = " <-- OUR METHOD" if "Vigil" in name else ""
    print(f"  {name:<20}  {m['precision']:>6.1%}  {m['recall']:>6.1%}  "
          f"{m['f1']:>6.1%}  {m['TP']:>4}  {m['FP']:>4}  {m['FN']:>4}  "
          f"{delay_str:>6}  {labels}{flag}")

# ── LaTeX table ────────────────────────────────────────────────────────────────
print("\n\n% ── Paste into paper/main.tex (Table 1) ─────────────────────────────────")
print(r"\begin{table}[!t]")
print(r"\caption{Drift Detection Results on NSL-KDD (50 chunks $\times$ 200 samples).}")
print(r"\label{tab:results}")
print(r"\centering")
print(r"\begin{tabular}{lcccccc}")
print(r"\toprule")
print(r"\textbf{Method} & \textbf{Prec.} & \textbf{Rec.} & \textbf{F1}"
      r" & \textbf{Delay} & \textbf{Labels?} & \textbf{Attr.?} \\")
print(r"\midrule")
for name, (_, labels, attr) in detectors.items():
    m = metrics[name]
    delay_str = f"{m['delay']} chunk" if m['delay'] else "N/A"
    bo = r"\textbf{" if "Vigil" in name else ""
    bc = "}"         if "Vigil" in name else ""
    print(f"{bo}{name}{bc} & "
          f"{bo}{m['precision']:.1%}{bc} & "
          f"{bo}{m['recall']:.1%}{bc} & "
          f"{bo}{m['f1']:.1%}{bc} & "
          f"{bo}{delay_str}{bc} & "
          f"{labels} & {attr} \\\\")
print(r"\bottomrule")
print(r"\end{tabular}")
print(r"\end{table}")
print("\nDone.")
