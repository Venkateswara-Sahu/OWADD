# Pre-submission audit: calibrated attribution paper

Date: 2026-10-25. Scope: `paper/main.tex` + `paper/sections/*.tex` against
`artifacts/runs/calibrated-study-v3/summary.json`, `artifacts/runs/real-null-v1`,
`artifacts/runs/calibrated-power-v1` and `artifacts/benchmarks/*.json`.

A read-only reviewer pass (report kept at `artifacts/reviews/paper-artifact-audit.md`)
raised nine blockers. Each was re-checked against the artefacts; six were real defects in
the prose and were fixed, three did not reproduce and are recorded here so they are not
"fixed" back into an error.

## Fixed

| # | Claim before | Artefact | Correction |
| --- | --- | --- | --- |
| 1 | KS-only "stays within Monte-Carlo noise of nominal … including tied and heavy-tailed pools" | `ks_asymptotic` FWER: gaussian 3.8%, t3 2.6%, `zero_inflated_tied` **0.2%**, real 1.2–2.0% | "at or below nominal, markedly conservative where rows are tied or columns near-duplicated"; Pearson-vs-copula contrast (98.4–100% vs 9.6–82.2%) carries the mechanism |
| 2 | "peeling … closes that gap"; "every method at or near ceiling" | `zero_inflated_tied:permute_k2` peeling 32.5% / decomposed 40.0% / chance 15.0%, detection 5% vs 25%; `multivariate_t3:mean_0.5_k2_sparse5` 7.5% vs 15.0%, detection 5% vs 50% | restricted to the pools where the calibrated test still fires; tied and sparse-heavy-tail cells stated as a power limit |
| 3 | "Splitting α without replacing the null leaves (a residual) 8.6%" | 8.6% is `peeling_separate`, which peels at **full** α; asymptotic + Bonferroni leaves 80.4–82.6% | re-attributed: no-split peeling leaves 8.6%, asymptotic stays 80.4–82.6% |
| 4 | "block-clustered intervals … are tighter and agree" | block CI **wider** for 5 of 10 methods (79.0–85.7 → 76.5–88.4; 2.1–5.4 → 2.0–4.9) | "wider for the five high-rate methods, marginally narrower for the low-rate ones, every pair overlaps" |
| 5 | tex caption: "brackets are 95% Wilson intervals over trials" | tex body printed point estimates only; brackets existed in the markdown renderer | caption states point estimates and where the intervals live; `paper/sections/calibrated.tex` regenerated |
| 6 | no power statement; `tab:paired-tests` orphaned | mean `detection_rate` over 70 cells: peeling 68.8% vs decomposed 79.1% (dense 79.7/86.0, dense mean-scale 92.5/95.3, sparse 41.5/61.7) | new paragraph: recall is conditioned on alerting, so the false-alarm gain is paid in sensitivity; paired table now referenced |

Two further items from the same pass:

- `paper/sections/calibrated_method.tex:30-35` claimed validity "for any dependence
  structure" with no caveat; now states exchangeability of rows within a window and that
  autocorrelated streams would need block permutations (not implemented).
- Figure 4 (`fig:calibration-power`) described a sub-population shift without naming the
  population, contradicting `tab:localization` where the same 20%-of-rows shift is
  detected 95% of the time. The DGP was re-derived directly
  (`experiments/calibrated_power.py:89-97`): a 20%-of-rows, 0.5σ Gaussian shift gives
  `D = 0.0500, p = 0.700` against a critical value of `0.0962`, so the floor is real. The
  caption now names the Gaussian pool, quotes 30.0%/100.0% at 50%/100% coverage, and
  explains that recorded traffic moves shifted rows off a mass point rather than into a
  Gaussian tail.

## Did not reproduce

- "`paper/sections/calibrated.tex` does not exist, the paper cannot build": the file exists
  (64 642 bytes, regenerated from v3 at 20:44) but is **untracked**, which is a real
  submission risk rather than a prose error. See "Left for the author" below.
- "abstract reports 57.6% and 4.8%, in no artefact": `57.6` appears nowhere in the tree or
  in `HEAD`; the text quotes the artefact extremes 8.6% (Gaussian) and 59.0% (Tuesday).
- "results cite `calibrated-study-v1`": the tree cites
  `artifacts/runs/calibrated-study-v3/summary.json` (`paper/main.tex` calibration-check
  paragraph).

## Verification of the final tree

- `uv run python -m pytest tests/ -q -p no:randomly` → `252 passed, 13 warnings in 604.04s
  (0:10:04)`, exit 0 (2026-10-25, final edit state). The targetless/random-order failure seen once
  earlier is not reproducible: two concurrent full runs in the same checkout are what produce spurious
  teardown failures, not the code.
- `ruff check` clean on `vigil/`, `experiments/`, `tests/`, `paper/scripts/`.
- `paper/main.tex` and `paper/sections/{calibrated,calibrated_method}.tex`: braces balanced, no dangling
  `\ref`, no unused `\cite`, labels unique.
- Artifacts backing this document: `artifacts/runs/calibrated-study-v3/summary.json` (580 KB, 500-trial
  nulls + 20 seeds x 14 conditions x 5 populations), `artifacts/runs/real-null-v1`,
  `artifacts/runs/calibrated-power-v1`, `artifacts/runs/calibrated-diagnostics-v1`,
  `artifacts/benchmarks/calibrated_cost{,_d78}.json`, `artifacts/reviews/paper-artifact-audit.md`.

## Left for the author

- `paper/sections/` and several `docs/` files are untracked, so a clean checkout cannot
  build the paper. Staging them is a commit action and out of scope here.
- No LaTeX toolchain on this machine: brace balance, `\ref`/`\cite` resolution and label
  uniqueness are checked programmatically (`paper/main.tex` and the three section files
  report `unbalanced=none braces=0`, no unused cites, no dangling refs), but the PDF has
  never been compiled.
- Every number in the calibrated section is rendered by
  `paper/scripts/render_calibrated_tables.py`; the NSL-KDD null table is hand-written from
  `artifacts/runs/real-null-v1` and the power figure from
  `artifacts/runs/calibrated-power-v1`.
