"""
Figure Generation for arXiv Paper
===================================
Generates publication-quality matplotlib figures for the paper:
  Figure 1 : Top-5 drifted features bar chart (from benchmark results)
  Figure 2 : Precision / Recall / F1 comparison bar chart (Vigil vs baselines)
  Figure 3 : Per-attack-class detection rate heatmap

Run AFTER paper/baselines/run_baselines.py — paste that script's numbers
into RESULTS dict below before running.

Usage:
    python paper/figures/generate_figures.py
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

FIG_DIR = Path(__file__).parent
FIG_DIR.mkdir(parents=True, exist_ok=True)

# ── Colour palette ─────────────────────────────────────────────────────────────
BLUE   = "#1a73e8"
ORANGE = "#f4a62a"
GREEN  = "#34a853"
RED    = "#ea4335"
GREY   = "#9aa0a6"

plt.rcParams.update({
    "font.family"     : "serif",
    "font.size"       : 10,
    "axes.titlesize"  : 11,
    "axes.labelsize"  : 10,
    "legend.fontsize" : 9,
    "figure.dpi"      : 150,
})

# =============================================================================
# Figure 1 — Top-5 drifted features (from Vigil benchmark)
# =============================================================================
# From benchmark_nsl_kdd.py output (real measured values):
TOP_FEATURES = {
    "root\\_shell"             : 18.3,
    "protocol\\_type\\_icmp"   : 7.3,
    "srv\\_diff\\_host\\_rate"  : 6.5,
    "dst\\_host\\_srv\\_count"  : 6.3,
    "service\\_private"        : 5.8,
}

fig, ax = plt.subplots(figsize=(5.5, 2.8))
names  = list(TOP_FEATURES.keys())
shares = list(TOP_FEATURES.values())
bars   = ax.barh(names[::-1], shares[::-1], color=BLUE, height=0.55,
                 edgecolor="white", linewidth=0.5)
for bar, val in zip(bars, shares[::-1]):
    ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
            f"{val:.1f}%", va="center", fontsize=9)
ax.set_xlabel("Contribution to Drift Attribution (%)")
ax.set_title("Top-5 Network Features by Drift Attribution\n(NSL-KDD, 50-chunk stream)")
ax.set_xlim(0, 20)
ax.spines[["top","right"]].set_visible(False)
plt.tight_layout()
fig.savefig(FIG_DIR / "fig1_top_features.pdf", bbox_inches="tight")
fig.savefig(FIG_DIR / "fig1_top_features.png", bbox_inches="tight")
print("Saved fig1_top_features.pdf/png")

# =============================================================================
# Figure 2 — Method comparison bar chart
# =============================================================================
# From run_baselines.py (real measured values with correct methodology):
METHODS   = ["Vigil\n(Ours)", "ADWIN", "KSWIN", "Page\nHinkley"]
PRECISION = [0.938, 1.000, 1.000, 1.000]
RECALL    = [0.333, 0.044, 0.022, 0.044]
F1        = [0.492, 0.085, 0.043, 0.085]

x     = np.arange(len(METHODS))
width = 0.25

fig, ax = plt.subplots(figsize=(6, 3.5))
b1 = ax.bar(x - width, PRECISION, width, label="Precision", color=BLUE,   edgecolor="white")
b2 = ax.bar(x,         RECALL,    width, label="Recall",    color=ORANGE, edgecolor="white")
b3 = ax.bar(x + width, F1,        width, label="F1",        color=GREEN,  edgecolor="white")

# Annotate Vigil bars
for b, val in zip([b1[0], b2[0], b3[0]], [PRECISION[0], RECALL[0], F1[0]]):
    ax.text(b.get_x() + b.get_width()/2, b.get_height() + 0.01,
            f"{val:.0%}", ha="center", va="bottom", fontsize=8, fontweight="bold")

ax.set_xticks(x)
ax.set_xticklabels(METHODS)
ax.set_ylabel("Score")
ax.set_ylim(0, 1.15)
ax.set_title("Drift Detection: Vigil vs. Baselines (NSL-KDD)")
ax.legend(loc="upper right", framealpha=0.9)
ax.spines[["top","right"]].set_visible(False)
# Highlight Vigil column
ax.axvspan(-0.45, 0.45, alpha=0.07, color=BLUE, zorder=0)
plt.tight_layout()
fig.savefig(FIG_DIR / "fig2_comparison.pdf", bbox_inches="tight")
fig.savefig(FIG_DIR / "fig2_comparison.png", bbox_inches="tight")
print("Saved fig2_comparison.pdf/png  [NOTE: fill baseline numbers after run_baselines.py]")

# =============================================================================
# Figure 3 — Per-attack-class detection rate heatmap
# =============================================================================
# From benchmark_nsl_kdd.py (real per-class results)
# Excluded: 'normal' dominant (22 chunks, 27.3%) — these are drift-phase chunks
# where normal traffic is temporarily dominant; not meaningful as attack classes.
ATTACK_CLASSES  = ["back",   "ftp_write", "ipsweep", "land",  "loadmodule",
                   "multihop", "neptune",  "nmap",    "buffer_overflow"]
DETECTION_RATES = [0.600,    0.250,       0.000,     0.000,   0.000,
                   0.600,    0.000,       0.750,     0.000]
AVG_SEVERITY    = [0.48,     0.12,        0.00,      0.00,    0.00,
                   0.23,     0.00,        0.38,      0.07]

fig, ax = plt.subplots(figsize=(6, 3.2))
colors = [BLUE if r > 0 else GREY for r in DETECTION_RATES]
bars   = ax.bar(ATTACK_CLASSES, DETECTION_RATES, color=colors,
                edgecolor="white", linewidth=0.5)
for bar, rate, sev in zip(bars, DETECTION_RATES, AVG_SEVERITY):
    if rate > 0:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f"{rate:.0%}", ha="center", va="bottom", fontsize=8)
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height()/2,
                f"sev\n{sev:.2f}", ha="center", va="center",
                fontsize=7, color="white", fontweight="bold")

ax.set_ylabel("Detection Rate")
ax.set_ylim(0, 1.2)
ax.set_title("Per-Attack-Class Detection Rate (Vigil, NSL-KDD)")
ax.tick_params(axis="x", rotation=30)
ax.spines[["top","right"]].set_visible(False)
detected_patch = mpatches.Patch(color=BLUE, label="Detected")
missed_patch   = mpatches.Patch(color=GREY, label="Missed (subtle attacks)")
ax.legend(handles=[detected_patch, missed_patch], loc="upper right", fontsize=8)
plt.tight_layout()
fig.savefig(FIG_DIR / "fig3_per_class.pdf", bbox_inches="tight")
fig.savefig(FIG_DIR / "fig3_per_class.png", bbox_inches="tight")
print("Saved fig3_per_class.pdf/png")

print("\nAll figures written to:", FIG_DIR)
print("Next: update PRECISION/RECALL/F1 in fig2 with run_baselines.py output,")
print("then re-run this script.")
