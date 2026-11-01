"""Render the exchangeability table from the block-permutation artifact.

Every number in the table is read from ``summary.json``; nothing is
transcribed. The artifact is produced by

    uv run python -m experiments.calibrated_blocknull \
        --output artifacts/runs/calibrated-blocknull-v2 \
        --prepared artifacts/prepared/cicids2017-prepared-v1 \
        --trials 300 --block-sizes 1,10,25,50

Usage:

    uv run python paper/scripts/render_blocknull_table.py \
        --summary artifacts/runs/calibrated-blocknull-v2/summary.json \
        --out paper/sections/blocks_null.tex
"""

from __future__ import annotations

import argparse
import json  # artifact JSON -> LaTeX table
from pathlib import Path

POOL_LABELS = {
    "gaussian": "Gaussian (i.i.d.)",
    "multivariate_t3": "Multivariate $t_3$ (i.i.d.)",
    "real_tuesday": "CICIDS Tuesday, recorded",
    "real_heldout": "CICIDS Wed--Fri, recorded",
    "nsl_kdd": "NSL-KDD, random order",
}

CONDITION_LABELS = {
    "null": "nothing injected (nominal $5\\%$)",
    "mean_0.5": "one feature shifted by $+0.5\\sigma$",
}

CAPTION = (
    r"Block-permutation null on exchangeable and recorded data "
    r"(family-wise rejection rate at $\alpha = 0.05$, "
    "{n_permutations} permutations, {trials} trials per cell, "
    r"$d = {d}$, windows of {window} rows). A rate above the nominal "
    r"$5\%$ means the permuted null is too optimistic; block size $1$ is "
    r"the textbook permutation and larger blocks keep adjacent rows "
    r"together. Pooled synthetic rows are i.i.d. by construction, so a "
    r"rate that moves with block size there is Monte-Carlo noise; the "
    r"recorded streams keep their order, so those rows are the measurement."
)


def _order(pools: dict) -> list[str]:
    """Stable pool order: known labels first, then anything unexpected."""
    known = [name for name in POOL_LABELS if name in pools]
    return known + sorted(name for name in pools if name not in POOL_LABELS)


def _row(name: str, cell: dict, blocks: list[str]) -> str:
    """One table row: pool label followed by a rate per block size."""
    rates = []
    for block in blocks:
        entry = cell.get(block)
        rates.append("--" if entry is None else format(100 * entry["rate"], ".1f"))
    label = POOL_LABELS.get(name) or name.replace("_", "\\_")
    return label + " & " + " & ".join(rates) + r" \\"


def _condition_header(condition: str, n_columns: int) -> str:
    """Panel header spanning the whole table (no f-string: brace-heavy LaTeX)."""
    label = CONDITION_LABELS.get(condition) or condition
    return "\\multicolumn{" + str(n_columns) + "}{l}{\\emph{" + label + "}} \\\\"


def render(payload: dict) -> str:
    """Return a booktabs table whose entries are all artifact values."""
    pools = payload["pools"]
    blocks = [str(block) for block in payload["block_sizes"]]
    conditions = list(payload["conditions"])
    n_columns = len(blocks) + 1
    caption = CAPTION.format(
        n_permutations=payload["n_permutations"],
        trials=payload["trials"],
        d=payload["d"],
        window=payload["window"],
    )
    lines = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\caption{" + caption + "}",
        r"\label{tab:block-null}",
        r"\footnotesize",
        r"\setlength{\tabcolsep}{4pt}",
        r"\resizebox{\columnwidth}{!}{%",
        r"\begin{tabular}{l" + "r" * len(blocks) + "}",
        r"\toprule",
        r"Pool & " + " & ".join("block $" + block + "$" for block in blocks) + r" \\",
        r"\midrule",
    ]
    for index, condition in enumerate(conditions):
        lines.append(_condition_header(condition, n_columns))
        for name in _order(pools):
            cell = pools.get(name, {}).get(condition)
            if not cell:
                continue
            lines.append(_row(name, cell, blocks))
        if index != len(conditions) - 1:
            lines.append(r"\midrule")
    lines += [
        r"\bottomrule",
        r"\end{tabular}}",
        r"\end{table}",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.summary.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot read {args.summary}: {exc}") from exc
    table = render(payload)
    out = args.out or args.summary.parent / "blocks_null.tex"
    try:
        out.write_text(table, encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"cannot write {out}: {exc}") from exc
    print("wrote", out, "(", len(table.splitlines()), "lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
