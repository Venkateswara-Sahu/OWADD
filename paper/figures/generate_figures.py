"""
Figure Generation for arXiv / IEEEtran Paper
=============================================
Generates publication-quality vector PDF and PNG figures for paper/main.tex:
  Figure 1 (fig1_top_features.pdf): Synthetic Attribution Benchmark (mean Recall@3,
    20 seeds)
  Figure 2 (fig2_comparison.pdf):   Real-Data CICIDS2017 Validation & Held-Out Test
    Attribution Benchmark
  Figure 3 (fig3_per_class.pdf):    Decomposed Pathway Ablation (Marginal vs
    Relational vs Combined)
  Figure 4 (fig4_calibration_power.pdf): Permutation-calibrated pathway -- null
    calibration and detection power

Usage:
    python paper/figures/generate_figures.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

FIG_DIR = Path(__file__).parent
POWER_JSON = (
    Path(__file__).parents[2]
    / "artifacts"
    / "runs"
    / "calibrated-power-v1"
    / "power.json"
)
FIG_DIR.mkdir(parents=True, exist_ok=True)

BLUE = "#1a73e8"
RED = "#d93025"
GREEN = "#1e8e3e"
ORANGE = "#f29900"

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.size": 8.0,
        "axes.titlesize": 9.0,
        "axes.labelsize": 8.0,
        "xtick.labelsize": 7.0,
        "ytick.labelsize": 7.5,
        "legend.fontsize": 7.0,
        "figure.dpi": 300,
    }
)


def make_fig1() -> None:
    labels = [
        "Mean\n+0.5\n(Marg.)",
        "Scale\nx0.5\n(Marg.)",
        "Corr\n0.8\n(Indep.)",
        "Dep\n+0.6\n(n=200)",
        "Dep\n+0.6\n(n=800)",
    ]
    dda = [100.0, 100.0, 100.0, 100.0, 100.0]
    ae_abs = [32.5, 92.5, 20.0, 75.0, 97.5]
    ks = [100.0, 100.0, 20.0, 2.5, 15.0]
    corr = [7.5, 10.0, 100.0, 100.0, 100.0]

    x = np.arange(len(labels)) * 1.15
    w = 0.20

    fig, ax = plt.subplots(figsize=(3.5, 2.4))
    ax.bar(
        x - 1.5 * w,
        dda,
        w,
        label="Decomposed Copula-KS (Ours)",
        color=BLUE,
        edgecolor="white",
        linewidth=0.4,
    )
    ax.bar(
        x - 0.5 * w,
        ae_abs,
        w,
        label="Trained AE (|Delta MSE|)",
        color=RED,
        edgecolor="white",
        linewidth=0.4,
    )
    ax.bar(
        x + 0.5 * w,
        ks,
        w,
        label="Univariate KS",
        color=GREEN,
        edgecolor="white",
        linewidth=0.4,
    )
    ax.bar(
        x + 1.5 * w,
        corr,
        w,
        label="Pearson Corr Shift",
        color=ORANGE,
        edgecolor="white",
        linewidth=0.4,
    )

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Mean Recall@3 (%) [20 Seeds]")
    ax.set_ylim(0, 108)
    ax.grid(axis="y", linestyle=":", alpha=0.5, zorder=0)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.03),
        ncol=2,
        frameon=False,
        columnspacing=0.8,
        handletextpad=0.4,
    )
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig1_top_features.pdf", bbox_inches="tight", pad_inches=0.03)
    fig.savefig(FIG_DIR / "fig1_top_features.png", bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)


def make_fig2() -> None:
    labels = [
        "Mean\n+0.5\n(Test)",
        "Mean\n+2.0\n(Test)",
        "Scale\nx0.5\n(Test)",
        "Perm.\n(Val)",
        "Perm.\n(Test)",
    ]
    dda = [100.0, 100.0, 100.0, 65.0, 55.0]
    ae_abs = [7.5, 15.0, 5.0, 27.5, 17.5]
    ks = [100.0, 100.0, 100.0, 15.0, 17.5]
    corr = [17.5, 17.5, 17.5, 65.0, 67.5]

    x = np.arange(len(labels)) * 1.15
    w = 0.20

    fig, ax = plt.subplots(figsize=(3.5, 2.4))
    ax.bar(
        x - 1.5 * w,
        dda,
        w,
        label="Decomposed Copula-KS (Ours)",
        color=BLUE,
        edgecolor="white",
        linewidth=0.4,
    )
    ax.bar(
        x - 0.5 * w,
        ae_abs,
        w,
        label="Trained AE (|Delta MSE|)",
        color=RED,
        edgecolor="white",
        linewidth=0.4,
    )
    ax.bar(
        x + 0.5 * w,
        ks,
        w,
        label="Univariate KS",
        color=GREEN,
        edgecolor="white",
        linewidth=0.4,
    )
    ax.bar(
        x + 1.5 * w,
        corr,
        w,
        label="Pearson Corr Shift",
        color=ORANGE,
        edgecolor="white",
        linewidth=0.4,
    )

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Mean Recall@3 (%) [CICIDS2017]")
    ax.set_ylim(0, 108)
    ax.grid(axis="y", linestyle=":", alpha=0.5, zorder=0)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.03),
        ncol=2,
        frameon=False,
        columnspacing=0.8,
        handletextpad=0.4,
    )
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig2_comparison.pdf", bbox_inches="tight", pad_inches=0.03)
    fig.savefig(FIG_DIR / "fig2_comparison.png", bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)


def make_fig3() -> None:
    labels = [
        "Syn\nMean\n+0.5",
        "Syn\nCorr\n0.8",
        "CICIDS\nMean\n+0.5",
        "CICIDS\nScale\nx0.5",
        "CICIDS\nPerm.\n(Val)",
    ]
    marg_only = [100.0, 17.5, 100.0, 100.0, 17.5]
    rel_only = [7.5, 100.0, 12.5, 12.5, 65.0]
    combined = [100.0, 100.0, 100.0, 100.0, 65.0]

    x = np.arange(len(labels)) * 1.15
    w = 0.25

    fig, ax = plt.subplots(figsize=(3.5, 2.4))
    ax.bar(
        x - w,
        marg_only,
        w,
        label="Marginal Only (-log10 p_KS)",
        color=GREEN,
        edgecolor="white",
        linewidth=0.4,
    )
    ax.bar(
        x,
        rel_only,
        w,
        label="Relational Only (-log10 p_Copula)",
        color=ORANGE,
        edgecolor="white",
        linewidth=0.4,
    )
    ax.bar(
        x + w,
        combined,
        w,
        label="Decomposed Copula-KS (Combined)",
        color=BLUE,
        edgecolor="white",
        linewidth=0.4,
    )

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Mean Recall@3 (%) [20 Seeds]")
    ax.set_ylim(0, 108)
    ax.grid(axis="y", linestyle=":", alpha=0.5, zorder=0)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.03),
        ncol=1,
        frameon=False,
        handletextpad=0.4,
    )
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig3_per_class.pdf", bbox_inches="tight", pad_inches=0.03)
    fig.savefig(FIG_DIR / "fig3_per_class.png", bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)


def make_fig4(power_json: Path | None = None) -> None:
    """Dose-response detection curve from artifacts/runs/calibrated-power-v1."""
    source = power_json or POWER_JSON
    if not source.exists():
        print(f"skip fig4: {source} not found (run experiments.calibrated_power)")
        return
    payload = json.loads(source.read_text(encoding="utf-8"))
    cells = payload["cells"].values()
    by_cell = {(cell["fraction_rows"], cell["delta"]): cell for cell in cells}
    fractions = sorted({key[0] for key in by_cell})
    deltas = sorted({key[1] for key in by_cell})

    fig, ax = plt.subplots(figsize=(3.5, 2.4))
    styles = [(BLUE, "o"), (RED, "s")]
    for delta, (color, marker) in zip(deltas, styles, strict=False):
        rates = [
            by_cell[(fraction, delta)]["detection"]["declared"] * 100.0
            for fraction in fractions
        ]
        ax.plot(
            [fraction * 100.0 for fraction in fractions],
            rates,
            marker=marker,
            color=color,
            linewidth=1.2,
            markersize=4,
            label=f"mean +{delta:.1f} SD, 2 of 20 features",
        )
    ax.axhline(5.0, color="#5f6368", linestyle=":", linewidth=0.9)
    ax.annotate(
        "nominal false-alarm rate (5%)",
        xy=(fractions[0] * 100.0, 9.0),
        fontsize=6,
        color="#5f6368",
    )
    ax.set_xscale("log")
    ax.set_xticks([fraction * 100.0 for fraction in fractions])
    ax.set_xticklabels([f"{fraction * 100:.0f}%" for fraction in fractions])
    ax.set_xlabel("Share of rows shifted")
    ax.set_ylabel("Detection rate (%)")
    ax.set_ylim(0, 105)
    ax.grid(axis="y", linestyle=":", alpha=0.5, zorder=0)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.03), frameon=False, fontsize=6)
    plt.tight_layout()
    fig.savefig(
        FIG_DIR / "fig4_calibration_power.pdf", bbox_inches="tight", pad_inches=0.03
    )
    fig.savefig(
        FIG_DIR / "fig4_calibration_power.png", bbox_inches="tight", pad_inches=0.03
    )
    plt.close(fig)


def main() -> None:
    make_fig1()
    make_fig2()
    make_fig3()
    make_fig4()
    print("Generated clean, non-overlapping figures in", FIG_DIR)


if __name__ == "__main__":
    main()
