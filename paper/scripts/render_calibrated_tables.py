"""Render the calibrated-attribution tables straight from a study summary.

Every number in the generated tables is read from ``summary.json``; nothing is
typed in by hand, so a table can never drift away from the artifact it cites.

Usage:
    python paper/scripts/render_calibrated_tables.py \
        --summary artifacts/runs/calibrated-study-v3/summary.json \
        --out-prefix paper/sections/calibrated

Writes ``<prefix>.md`` (human-readable) and ``<prefix>.tex`` (booktabs/LaTeX).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# Reporting order of the FWER table: published pathway, deterministic
# alternatives, then the calibrated policies.
NULL_METHODS = (
    "decomposed_asymptotic",
    "decomposed_bonferroni",
    "ks_asymptotic",
    "copula_asymptotic",
    "pearson_asymptotic",
    "maxedge_joint",
    "peeling_joint",
    "peeling_separate",
    "peeling_rank_transform",
)
NULL_LABELS = {
    "decomposed_asymptotic": "Decomposed (published)",
    "decomposed_bonferroni": "Decomposed, alpha split",
    "ks_asymptotic": "KS only",
    "copula_asymptotic": "Copula (Fisher-$z$)",
    "pearson_asymptotic": "Pearson (raw)",
    "maxedge_joint": "Calibrated, max-edge",
    "peeling_joint": "Calibrated, peeling",
    "peeling_separate": "Calibrated, peeling, alpha not split",
    "peeling_rank_transform": "Calibrated, peeling, rank copula",
}
NULL_TEX_HEADERS = {
    "decomposed_asymptotic": r"Dec.\ ",
    "decomposed_bonferroni": r"Dec.\ ($\alpha$/2)",
    "ks_asymptotic": "KS",
    "copula_asymptotic": r"Cop.\ ",
    "pearson_asymptotic": r"Pear.\ ",
    "maxedge_joint": r"Cal.\ max-edge",
    "peeling_joint": r"Cal.\ peel",
    "peeling_separate": "Peel, no split",
    "peeling_rank_transform": "Peel, rank",
}

LOC_METHODS = (
    "decomposed_asymptotic",
    "ks_asymptotic",
    "copula_asymptotic",
    "pearson_asymptotic",
    "maxedge_joint",
    "peeling_joint",
    "peeling_rank_transform",
)
LOC_LABELS = {
    "decomposed_asymptotic": "Decomposed",
    "ks_asymptotic": "KS",
    "copula_asymptotic": "Copula",
    "pearson_asymptotic": "Pearson",
    "maxedge_joint": "Max-edge",
    "peeling_joint": "Peeling",
    "peeling_rank_transform": "Peeling (rank)",
}

PAIRED_BASELINES = (
    "copula_asymptotic",
    "decomposed_asymptotic",
    "decomposed_bonferroni",
    "ks_asymptotic",
    "ks_pearson_asymptotic",
    "pearson_asymptotic",
    "maxedge_joint",
    "peeling_separate",
    "peeling_rank_transform",
)
PAIRED_TEX_HEADERS = {
    "copula_asymptotic": "Cop",
    "decomposed_asymptotic": "Dec",
    "decomposed_bonferroni": "Bonf",
    "ks_asymptotic": "KS",
    "ks_pearson_asymptotic": "KS$+$Pear",
    "pearson_asymptotic": "Pear",
    "maxedge_joint": "Max",
    "peeling_separate": r"Sep$_\alpha$",
    "peeling_rank_transform": "Rank",
}

NULL_LABELS_SHORT = {
    "gaussian": "Gaussian",
    "zero_inflated_tied": "Zero-inflated, tied",
    "multivariate_t3": "Multivariate $t_3$",
    "real_tuesday": "CICIDS2017 Tuesday (no injection)",
    "real_heldout": "CICIDS2017 held-out (no injection)",
}

RECALL_K = 3
ALPHA = 0.05

# Reporting order of the null populations: synthetic, then real traffic.
NULL_ORDER = (
    "gaussian",
    "zero_inflated_tied",
    "multivariate_t3",
    "real_tuesday",
    "real_heldout",
)


def _ordered(names) -> list[str]:
    """Known populations first, in manuscript order; extras append alphabetically."""
    known = [name for name in NULL_ORDER if name in names]
    return known + [name for name in sorted(names) if name not in NULL_ORDER]


def _pct(value: float | None) -> str:
    return "-" if value is None else f"{100.0 * float(value):.1f}"


ZERO_TOL = 1e-9


def _signed_pct(value: float | None, star: bool = False) -> str:
    if value is None:
        return "--"
    pts = 100.0 * float(value)
    mark = "$^{*}$" if star else ""
    if abs(pts) < ZERO_TOL:
        return f"0.0{mark}"
    sign = "$+$" if pts > 0 else "$-$"
    return f"{sign}{abs(pts):.1f}{mark}"


def _num(value: float | None, digits: int = 2) -> str:
    return "-" if value is None else f"{float(value):.{digits}f}"


def _null_table(summary: dict) -> tuple[list[str], list[str]]:
    null = summary["null"]
    populations = null["populations"]
    names = _ordered(populations)
    alpha = 100.0 * float(null["alpha"])

    md = [
        "| null population | "
        + " | ".join(NULL_LABELS[m] for m in NULL_METHODS)
        + " |",
        "| --- |" + " ---: |" * len(NULL_METHODS),
    ]
    for name in names:
        methods = populations[name]["methods"]
        cells = []
        for method in NULL_METHODS:
            entry = methods.get(method)
            if entry is None:
                cells.append("-")
                continue
            low, high = entry["ci95"]
            cells.append(f"{_pct(entry['fwer'])}% [{_pct(low)}-{_pct(high)}]")
        label = NULL_LABELS_SHORT.get(name, name)
        md.append(f"| {label} | " + " | ".join(cells) + " |")
    md.append("")
    if any(name.startswith("real") for name in names):
        distinct = {n: populations[n]["blocks"]["distinct"] for n in names}
        md += [
            "Real-data rows are genuine nulls: both windows are drawn from one",
            "row-disjoint 800-row block of a single split, so nothing has changed",
            "beyond sampling. Trials resample a fixed set of blocks, so the",
            "block-clustered intervals (`ci95_block` in `summary.json`) are the",
            "ones to quote: "
            + ", ".join(f"{n}={count}" for n, count in distinct.items())
            + ".",
            "",
        ]

    tex = [
        r"\begin{table*}[!tp]",
        r"\centering",
        r"\caption{Family-wise false-alarm rate with nothing injected "
        rf"(nominal {alpha:.0f}\%, {null['n_permutations']} permutations, "
        rf"{next(iter(populations.values()))['trials']} trials per cell; "
        r"column keys: \textup{\textit{Dec.}}\ = decomposed Copula--KS as published, "
        r"\textup{\textit{Dec.\ ($\alpha$/2)}} = the same with the $\alpha$ split, "
        r"\textup{\textit{KS}} and \textup{\textit{Cop.}}\ = single pathways, "
        r"\textup{\textit{Pear.}}\ = raw Pearson, \textup{\textit{Cal.\ max-edge}} "
        r"and \textup{\textit{Cal.\ peel}} = the calibrated policy with the max-edge "
        r"and greedy-peeling orders, \textup{\textit{Peel, no split}} and "
        r"\textup{\textit{Peel, rank}} = peeling with an unsplit $\alpha$ and with "
        r"the rank copula statistic; entries are point estimates; 95\% Wilson "
        r"intervals are in \textup{\texttt{summary.json}} and in the repository's "
        r"markdown rendering). Real-data rows draw both windows from one "
        r"row-disjoint block of a single split, so they are null pairs that "
        r"resample a fixed block set; the block-clustered interval in the "
        r"artifact is the one to quote there.}",
        r"\label{tab:null-calibration}",
        r"\small",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{l" + "r" * len(NULL_METHODS) + "}",
        r"\toprule",
        "Null population & "
        + " & ".join(NULL_TEX_HEADERS[m].strip() for m in NULL_METHODS)
        + r" \\",
        r"\midrule",
    ]
    for name in names:
        methods = populations[name]["methods"]
        cells = [
            _pct(methods[m]["fwer"]) if m in methods else "-" for m in NULL_METHODS
        ]
        label = NULL_LABELS_SHORT.get(name, name)
        tex.append(f"{label} & " + " & ".join(cells) + r" \\")
    tex += [r"\bottomrule", r"\end{tabular}", "}", r"\end{table*}"]
    return md, tex


def _uniform_recall(summary: dict) -> float:
    """Per-window uniform-random Recall@K, i.e. ``K / d``.

    Every localization condition injects the same number of truth features per
    window, so this single line applies to all of them, including the column
    permutation (whose truth spans two windows).
    """
    d = summary["localization"].get("d") or summary.get("n_features")
    if not d:
        raise ValueError("summary records neither localization.d nor n_features")
    return min(1.0, RECALL_K / d)


def _reported_conditions(condition_order: list[str]) -> list[str]:
    """Drop the no-injection cell: it has no truth, so it belongs to the FWER table."""
    return [condition for condition in condition_order if condition != "null"]


def _chance_and_methods(entry: dict, uniform: float, *, suffix: str) -> list[str]:
    """Chance line plus one Recall@K cell per method, in table order."""
    chance = entry.get("chance") or {}
    chance_value = chance.get(f"recall@{RECALL_K}", uniform)
    row = [_pct(chance_value) + suffix]
    for method in LOC_METHODS:
        value = entry["methods"].get(method, {}).get(f"recall@{RECALL_K}")
        row.append(_pct(value) + suffix if value is not None else "-")
    return row


def _localization_table(
    summary: dict,
    *,
    datasets: tuple[str, ...] | None = None,
    conditions: tuple[str, ...] | None = None,
) -> tuple[list[str], list[str]]:
    loc = summary["localization"]
    cells = loc["cells"]
    datasets_list = (
        list(datasets)
        if datasets
        else sorted({label.split(":", 1)[0] for label in cells})
    )
    condition_order: list[str] = list(conditions) if conditions else []
    if conditions is None:
        for label in sorted(cells):
            condition = label.split(":", 1)[1]
            if condition not in condition_order:
                condition_order.append(condition)
    uniform = _uniform_recall(summary)

    md = [
        "| dataset | condition | chance | "
        + " | ".join(f"{LOC_LABELS[m]} R@{RECALL_K}" for m in LOC_METHODS)
        + " |",
        "| --- | --- | ---: |" + " ---: |" * len(LOC_METHODS),
    ]
    for dataset in datasets_list:
        for condition in _reported_conditions(condition_order):
            entry = cells.get(f"{dataset}:{condition}")
            if entry is None:
                continue
            row = [dataset, condition]
            row += _chance_and_methods(entry, uniform, suffix="%")
            md.append("| " + " | ".join(row) + " |")
    md.append("")

    tex = [
        r"\begin{table*}[!tp]",
        r"\centering",
        r"\caption{Recall@" + str(RECALL_K) + r" (\%) per condition against the "
        r"uniform-random line $"
        + str(RECALL_K)
        + r"/d = "
        + f"{_pct(uniform)}"
        + r"$\% (every condition injects the same number "
        r"of truth features per window, including the permutation, whose truth "
        r"spans two windows). Peeling is the calibrated ranking; its decision "
        r"rule is the joint family-wise test of Table~\ref{tab:null-calibration}.}",
        r"\label{tab:localization}",
        r"\footnotesize",
        r"\renewcommand{\arraystretch}{0.90}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{llr" + "r" * len(LOC_METHODS) + "}",
        r"\toprule",
        "Dataset & Condition & Chance & "
        + " & ".join(LOC_LABELS[m] for m in LOC_METHODS)
        + r" \\",
        r"\midrule",
    ]
    previous = None
    for dataset in datasets_list:
        if previous is not None:
            tex.append(r"\midrule")
        previous = dataset
        for condition in _reported_conditions(condition_order):
            entry = cells.get(f"{dataset}:{condition}")
            if entry is None:
                continue
            row = [
                dataset.replace("_", r"\_"),
                condition.replace("_", r"\_"),
            ]
            row += _chance_and_methods(entry, uniform, suffix="")
            tex.append(" & ".join(row) + r" \\")
    tex += [r"\bottomrule", r"\end{tabular}", "}", r"\end{table*}"]
    return md, tex


def _significance_table(summary: dict) -> tuple[list[str], list[str]]:
    loc = summary["localization"]
    proposed = loc["proposed"]
    rows = sorted(
        (
            comparison
            for comparison in loc["comparisons"]
            if comparison["candidate"] == proposed
        ),
        key=lambda row: (row["dataset"], row["condition"], row["baseline"]),
    )
    alpha = float(loc.get("alpha", ALPHA))

    def _is_ns(row):
        adjusted = row.get("holm_p_value")
        reference = row["p_value"] if adjusted is None else adjusted
        return not row["rejected"] and reference > alpha

    only_ns = [row for row in rows if _is_ns(row)]
    md = [
        "| cell | baseline | peeling | baseline R@"
        + str(RECALL_K)
        + " | delta | W/L/T | raw p | Holm p | n |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        md.append(
            "| {cell} | {base} | {c} | {b} | {d} | {w}/{l}/{t} | {p} | {hp} "
            "| {n} |".format(
                cell=row["cell"],
                base=row["baseline"],
                c=_pct(row["mean_candidate"]),
                b=_pct(row["mean_baseline"]),
                d=_pct(row["delta"]),
                w=row["wins"],
                l=row["losses"],
                t=row["ties"],
                p=_num(row["p_value"], 3),
                hp=_num(row["holm_p_value"], 3),
                n=row["n"],
            )
        )
    md.append("")
    if only_ns:
        md.append(f"{len(only_ns)} of {len(rows)} paired tests are not significant.")
        md.append("")

    # Pivot by cell across baselines so the LaTeX table fits cleanly on one page.
    present_baselines = [
        b for b in PAIRED_BASELINES if any(r["baseline"] == b for r in rows)
    ]
    extras = sorted(
        {r["baseline"] for r in rows if r["baseline"] not in PAIRED_BASELINES}
    )
    cols = present_baselines + extras
    by_cell: dict[tuple[str, str], dict[str, dict]] = {}
    for row in rows:
        key = (row["dataset"], row["condition"])
        by_cell.setdefault(key, {})[row["baseline"]] = row
    n_seeds = rows[0]["n"] if rows else len(summary.get("seeds", ()))

    tex = [
        r"\begin{table*}[!tp]",
        r"\centering",
        r"\caption{Paired Recall@" + str(RECALL_K) + r" differences in percentage "
        rf"points (peeling minus baseline) on the same {n_seeds} seeds, one row "
        r"per condition--population cell; $^{*}$ marks Holm-adjusted "
        rf"$p < {alpha:.2f}$ within each cell across the {len(cols)} baselines "
        r"(Wilcoxon signed-rank, or a sign test when $n < 10$). Positive is "
        r"better for peeling. Cop = copula asymptotic, Dec = decomposed "
        r"asymptotic, Bonf = decomposed ($\alpha/2$), KS = marginal KS pathway, "
        r"KS$+$Pear = KS plus raw Pearson, Pear = raw Pearson relational, "
        r"Max = calibrated max-edge without peeling, Sep$_\alpha$ = peeling "
        r"without $\alpha$ split, Rank = peeling on rank-copula statistic. "
        r"Win/loss/tie counts and raw $p$-values are in "
        r"\textup{\texttt{summary.json}}.}",
        r"\label{tab:paired-tests}",
        r"\scriptsize",
        r"\renewcommand{\arraystretch}{0.86}",
        r"\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}l"
        + "r" * len(cols)
        + "}",
        r"\toprule",
        f"Cell & \\multicolumn{{{len(cols)}}}{{c}}"
        f"{{$\\Delta$ Recall@{RECALL_K} vs each baseline}} \\\\",
        " & "
        + " & ".join(
            PAIRED_TEX_HEADERS.get(b, b.replace("_", r"\_")) for b in cols
        )
        + r" \\",
        r"\midrule",
    ]
    previous_ds = None
    for dataset, condition in sorted(by_cell):
        if previous_ds is not None and dataset != previous_ds:
            tex.append(r"\midrule")
        previous_ds = dataset
        cell_label = (
            r"\texttt{"
            + dataset.replace("_", r"\_")
            + "}:"
            + condition.replace("_", r"\_")
        )
        entries = []
        for baseline in cols:
            comp = by_cell[(dataset, condition)].get(baseline)
            if comp is None:
                entries.append("--")
            else:
                entries.append(
                    _signed_pct(comp["delta"], star=bool(comp["rejected"]))
                )
        tex.append(cell_label + " & " + " & ".join(entries) + r" \\")
    tex += [r"\bottomrule", r"\end{tabular*}", r"\end{table*}"]
    return md, tex


def render(
    summary: dict,
    *,
    datasets: tuple[str, ...] | None = None,
    conditions: tuple[str, ...] | None = None,
) -> str:
    parts = [
        f"Study version: `{summary['study_version']}`",
        f"Permutations: {summary['n_permutations']}, alpha: {summary['alpha']}",
        f"Null trials: {summary['null_trials']}, "
        f"localization seeds: {len(summary['seeds'])}",
        f"Datasets: {summary['localization']['n_datasets']}, "
        f"conditions: {summary['localization']['n_conditions']}",
        "",
        "## Null calibration",
        "",
        *(_null_table(summary)[0]),
        "## Localization",
        "",
        *(_localization_table(summary, datasets=datasets, conditions=conditions)[0]),
        "## Paired significance tests",
        "",
        *(_significance_table(summary)[0]),
    ]
    return "\n".join(parts)


def render_tex(
    summary: dict,
    *,
    datasets: tuple[str, ...] | None = None,
    conditions: tuple[str, ...] | None = None,
) -> str:
    loc_table = _localization_table(summary, datasets=datasets, conditions=conditions)[
        1
    ]
    blocks = [*_null_table(summary)[1], "", *loc_table, ""]
    blocks += [*_significance_table(summary)[1]]
    return "\n".join(blocks)


def main(argv: list[str] | None = None) -> Path:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--out-prefix", type=Path, required=True)
    parser.add_argument(
        "--datasets",
        default="",
        help="comma-separated dataset order/filter (default: all in summary)",
    )
    parser.add_argument(
        "--conditions",
        default="",
        help="comma-separated condition order/filter (default: all in summary)",
    )
    args = parser.parse_args(argv)
    summary = json.loads(Path(args.summary).read_text(encoding="utf-8"))
    datasets = tuple(x for x in args.datasets.split(",") if x) or None
    conditions = tuple(x for x in args.conditions.split(",") if x) or None
    prefix = Path(args.out_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    prefix.with_suffix(".md").write_text(
        render(summary, datasets=datasets, conditions=conditions) + "\n",
        encoding="utf-8",
    )
    prefix.with_suffix(".tex").write_text(
        render_tex(summary, datasets=datasets, conditions=conditions) + "\n",
        encoding="utf-8",
    )
    return prefix.with_suffix(".md")


if __name__ == "__main__":
    print(main())
