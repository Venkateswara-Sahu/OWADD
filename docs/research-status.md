# Vigil research status

Vigil is an engineering prototype with a reproducible evaluation record, not a
proven novel or generally superior attribution method. No Vigil publication is
claimed. The original public default is retained; named research variants are
experimental.

## Evidence and decision

The [final decision report](superpowers/final-mechanism-decision-2026-09-28.md)
records the 20-seed comparison of trained and untrained reconstruction attribution,
squared-input change, KS and correlation baselines. It includes selected per-case
results, paired uncertainty intervals, provenance hashes and limitations.

Training helped in some dependency conditions but hurt small-mean localization.
The declared continuation criterion was not met. We stopped the general-superiority
investigation rather than relabeling those mixed results as a successful method.

The real-data experiments use controlled injections into CICIDS2017 development
flow features. They are semi-synthetic, not held-out attack detection, causal
identification or live deployment validation. Recall@3 measures recovery of
injected feature indices, not attack recall.

## Reproduction and provenance

Install the source with `pip install -e ".[dev,research]"` and run
`python -m pytest tests/`. The experiment interface is `vigil-bench --help`.
Follow the [frozen mechanism protocol](superpowers/final-mechanism-protocol.md)
for the declared design and the final report for its exact execution checkpoint.

Raw datasets, prepared caches and per-run outputs are intentionally not distributed.
Dataset acquisition and preparation are separate prerequisites; a source checkout
alone does not reproduce the real-data results. Historical output paths in reports
identify local provenance records, not downloadable artifacts. The reports retain
compact results and hashes; do not claim that raw outputs are publicly available.

## Public claims

- Keep Vigil in the CV projects section as a package and evaluation project.
- Describe API, Kafka, Airflow, MLflow and dashboard code as example integrations.
- Do not reuse old demo precision or novel-class recall as validated performance.
- Do not call feature scores causal explanations or percentages of input change.
- Do not list the historical manuscript as an accepted or submitted publication.

The manuscript in `paper/` and earlier research plans remain historical material;
this status and the final decision supersede their optimistic claims.
