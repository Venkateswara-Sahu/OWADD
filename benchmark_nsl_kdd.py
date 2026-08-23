"""
NSL-KDD Benchmark for Vigil
============================
Runs Vigil on the NSL-KDD network intrusion detection dataset across a
3-phase non-stationary stream and reports precision, recall, F1, detection
delay, novelty detection rate, and top drifted features per attack type.

Usage:
    python benchmark_nsl_kdd.py
"""

import sys
import time
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data.nsl_kdd_loader import load_nsl_kdd
from data.stream_simulator import StreamSimulator
from vigil import Vigil

# ── Config ─────────────────────────────────────────────────────────────────────
CHUNK_SIZE         = 200
N_CHUNKS           = 50
DRIFT_AFTER_CHUNK  = 5
NOVELTY_AFTER      = 20
NOVELTY_PROPORTION = 0.25
BUFFER_SIZE        = 600    # smaller buffer = more sensitive to change
DRIFT_THRESHOLD    = 0.10   # 10% of T-tests must reject H0 (paper: 0.1-0.3)
TOP_K              = 5
NOVELTY_THRESHOLD  = 0.05   # flag novelty if >5% samples are novel-class
SEED               = 42

def divider(char="-", width=72):
    print(char * width)

def section(title):
    divider("=")
    print(f"  {title}")
    divider("=")

# ── Load ────────────────────────────────────────────────────────────────────────
section("Loading NSL-KDD")
X_train, y_train, feature_names = load_nsl_kdd("train")
print(f"  Training samples  : {len(X_train):,}")
print(f"  Features (encoded): {len(feature_names)}")
print(f"  Unique classes    : {len(set(y_train))}  "
      f"({len(set(y_train)-{'normal'})} attack types)")

# ── Train on Normal-Only Baseline ───────────────────────────────────────────────
section("Training Vigil — Offline Phase (normal traffic only)")
normal_idx = np.where(y_train == "normal")[0]
rng = np.random.default_rng(SEED)
baseline_idx = rng.choice(normal_idx, size=1000, replace=False)
baseline_X = X_train[baseline_idx]

vigil = Vigil(
    feature_names=feature_names,
    top_k_features=TOP_K,
    buffer_size=BUFFER_SIZE,
    drift_threshold=DRIFT_THRESHOLD,
    initial_epochs=400,
    update_epochs=50,
)

t0 = time.time()
vigil.fit(baseline_X, verbose=True)
fit_time = time.time() - t0
print(f"\n  Fit time : {fit_time:.1f}s | {len(baseline_X)} samples | "
      f"{len(feature_names)} features")

# ── Stream Simulation ───────────────────────────────────────────────────────────
section(f"Streaming {N_CHUNKS} Chunks  (chunk_size={CHUNK_SIZE})")
sim = StreamSimulator(
    X_train, y_train,
    chunk_size=CHUNK_SIZE,
    drift_after_chunk=DRIFT_AFTER_CHUNK,
    novelty_after_chunk=NOVELTY_AFTER,
    novelty_proportion=NOVELTY_PROPORTION,
    seed=SEED,
)

results = []
feature_drift_totals = {}
attack_stats = {}

print(f"\n  {'Chunk':>5}  {'Phase':<8}  {'Dominant':<16}  "
      f"{'GT':>5}  {'Detected':<14}  {'Severity':>8}  {'Novelty%':>8}")
divider()

for chunk in sim.stream(n_chunks=N_CHUNKS):
    cid      = chunk.chunk_id
    phase    = ("NORMAL " if cid <= DRIFT_AFTER_CHUNK
                else "NOVELTY" if cid > NOVELTY_AFTER
                else "ATTACK ")
    gt_drift = cid > DRIFT_AFTER_CHUNK
    gt_label = "YES" if gt_drift else "NO "

    result   = vigil.detect(chunk.X)
    detected = result.drift_detected
    severity = result.drift_severity
    novelty  = result.novelty_proportion
    det_str  = "!! DRIFT  " if detected else "   STABLE "

    results.append({
        "chunk_id"  : cid,
        "phase"     : phase,
        "dominant"  : chunk.dominant_class,
        "gt_drift"  : gt_drift,
        "gt_novelty": cid > NOVELTY_AFTER,
        "detected"  : detected,
        "severity"  : severity,
        "novelty_p" : novelty,
    })

    if detected and result.attribution:
        for f in result.attribution.top_features:
            fn = f["feature_name"]
            feature_drift_totals[fn] = feature_drift_totals.get(fn, 0.0) + f["contribution"]

    cls = chunk.dominant_class
    if cls not in attack_stats:
        attack_stats[cls] = {"n": 0, "det": 0, "sev": []}
    attack_stats[cls]["n"]   += 1
    attack_stats[cls]["det"] += int(detected)
    attack_stats[cls]["sev"].append(severity)

    print(f"  {cid:>5}  {phase:<8}  {chunk.dominant_class:<16}  "
          f"{gt_label:>5}  {det_str:<14}  {severity:>8.2f}  {novelty:>8.1%}")

# ── Drift Metrics ───────────────────────────────────────────────────────────────
section("Drift Detection Metrics")

tp = sum(1 for r in results if r["gt_drift"]  and r["detected"])
fp = sum(1 for r in results if not r["gt_drift"] and r["detected"])
fn = sum(1 for r in results if r["gt_drift"]  and not r["detected"])
tn = sum(1 for r in results if not r["gt_drift"] and not r["detected"])

precision = tp / (tp + fp) if (tp + fp) else 0.0
recall    = tp / (tp + fn) if (tp + fn) else 0.0
f1        = 2*precision*recall / (precision+recall) if (precision+recall) else 0.0
accuracy  = (tp + tn) / len(results)

drift_cids       = [r["chunk_id"] for r in results if r["gt_drift"] and r["detected"]]
detect_delay     = (drift_cids[0] - DRIFT_AFTER_CHUNK) if drift_cids else None
avg_severity_tp  = np.mean([r["severity"] for r in results if r["gt_drift"] and r["detected"]]) if tp else 0.0

print(f"\n  TP (drift caught)    : {tp}")
print(f"  FP (false alarms)    : {fp}")
print(f"  FN (missed)          : {fn}")
print(f"  TN (correct stable)  : {tn}")
print()
print(f"  Precision            : {precision:.1%}")
print(f"  Recall               : {recall:.1%}")
print(f"  F1 Score             : {f1:.1%}")
print(f"  Accuracy             : {accuracy:.1%}")
if detect_delay:
    print(f"  Detection delay      : {detect_delay} chunk(s)  "
          f"[{detect_delay * CHUNK_SIZE} samples] after drift injection")
print(f"  Avg severity (TP)    : {avg_severity_tp:.2f}")

# ── Novelty Metrics ─────────────────────────────────────────────────────────────
section("Novelty Detection Metrics")
novel_r    = [r for r in results if r["gt_novelty"]]
n_nov      = len(novel_r)
n_nov_det  = sum(1 for r in novel_r if r["novelty_p"] >= NOVELTY_THRESHOLD)
nov_recall = n_nov_det / n_nov if n_nov else 0.0
avg_nov    = np.mean([r["novelty_p"] for r in novel_r]) if novel_r else 0.0

print(f"\n  Novel-class chunks in stream     : {n_nov}")
print(f"  Detected (>{NOVELTY_THRESHOLD:.0%} threshold)       : {n_nov_det}")
print(f"  Novelty Recall                   : {nov_recall:.1%}")
print(f"  Avg reported novelty proportion  : {avg_nov:.1%}")

# ── Per-Attack Class ────────────────────────────────────────────────────────────
section("Per-Attack-Class Detection Rate")
print(f"\n  {'Class':<22}  {'Chunks':>6}  {'Detected':>8}  "
      f"{'Det Rate':>9}  {'Avg Severity':>12}")
divider()
for cls in sorted(attack_stats):
    s = attack_stats[cls]
    rate = s["det"] / s["n"]
    avg  = np.mean(s["sev"])
    bar  = "#" * int(rate * 20)
    print(f"  {cls:<22}  {s['n']:>6}  {s['det']:>8}  "
          f"{rate:>9.1%}  {avg:>12.2f}  {bar}")

# ── Top Drifted Features ────────────────────────────────────────────────────────
section(f"Top {TOP_K} Features by Total Drift Contribution")
sorted_feats = sorted(feature_drift_totals.items(), key=lambda x: x[1], reverse=True)
total = sum(v for _, v in sorted_feats) or 1.0
print(f"\n  {'Feature':<40}  {'Contribution':>12}  {'Share':>6}")
divider()
for fname, score in sorted_feats[:TOP_K]:
    print(f"  {fname:<40}  {score:>12.4f}  {score/total:>6.1%}")

# ── README Summary ───────────────────────────────────────────────────────────────
section("README / Portfolio Summary")
delay_str = f"{detect_delay} chunk ({detect_delay*CHUNK_SIZE} samples)" if detect_delay else "N/A"
top5 = ", ".join(f[0] for f in sorted_feats[:5])

print(f"""
  Dataset  : NSL-KDD (Canadian Institute for Cybersecurity)
             125,973 samples | 122 features | 22 attack classes

  | Metric                          | Result                |
  |---------------------------------|-----------------------|
  | Training samples (normal only)  | 1,000                 |
  | Stream chunks evaluated         | {N_CHUNKS} (10,000 samples)   |
  | Drift detection Precision       | {precision:.1%}                |
  | Drift detection Recall          | {recall:.1%}                |
  | Drift detection F1              | {f1:.1%}                |
  | Accuracy                        | {accuracy:.1%}                |
  | Detection delay                 | {delay_str}    |
  | Novelty detection Recall        | {nov_recall:.1%}                |

  Top drifted network features:
    {top5}
""")

print("Done.")
