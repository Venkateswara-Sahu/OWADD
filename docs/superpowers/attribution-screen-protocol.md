# Independent-sample attribution screen

Declared before results. This is a numerical window-localization development screen, not the full controlled study or an event-detection benchmark. Preserve the existing model and prior evidence.

- Seeds 0–9; 20 numerical features. Independently draw 2,000 training, 200 comparison-reference and 200 current rows from N(0,I). Separate seeded RNG streams generate each pool and the shifted-feature pair. No resampling of training rows into evaluation.
- Randomly choose two feature positions per seed. Compare a stable null, additive mean shifts +0.5/+2.0, standard-deviation multipliers 0.5/2.0, and a joint correlation shift rho=0.8 preserving population N(0,1) marginals. The correlation case symmetrically mixes the selected pair; both coordinates belong to the changed dependency. Reuse the same independent base current window across scenarios for paired comparisons.
- Train the unchanged Vigil autoencoder architecture (hidden width10) for20 epochs on training rows only. No tuning, scaling, drift-trigger gating or adaptation; all methods receive identical comparison windows. Model fitting gets the larger training pool; statistical methods require no fitting and see only the comparison windows. This resource asymmetry is explicit.
- Compare public positive reconstruction-error contributions with random ranking, absolute mean difference, standardized mean difference, KS, Wasserstein, and the existing held-out logistic/permutation baseline (five repeats). Numerical data only; categorical Jensen-Shannon is not applicable here. Linear logistic discrimination is not a strong general nonlinear/dependency baseline; this screen cannot establish H2.
- Rank ties using a shared, seeded random feature order independent of the chosen shift pair; do not place every shift at feature zero. Record the order, raw scores and ground truth.
- Report Precision/Recall/NDCG at1/3/5/10, MRR, mean shifted rank and top1. Stable null has empty ground truth, hence localization recall/NDCG/MRR/top1 are undefined, not successes or misses. Ranking output alone is not a false-alarm decision.
- Save every seed/scenario/method score vector, input hashes, model-state hash, rankings' metric inputs and configuration/provenance in completion-checked results. Aggregate only the complete10-seed grid. Bootstrap intervals are across independent seeded simulations; ten seeds are a limited development sample, not broad generalization proof.
- Primary checks: does Vigil exceed random and how does it compare with simple baselines separately by shift family? Retain negative results. No single aggregate across easy mean shifts and hard correlation/variance-decrease shifts will serve as a headline.

Reduced configurations are allowed for software smoke tests only; their summary explicitly sets `protocol_complete=false`. Only the declared seeds and epochs produce a protocol-complete summary.

The older synthetic smoke runner remains unchanged and is not eligible as primary study evidence. Categorical, noise, larger-dimensional, gradual/recurring stream, network-data, systems and stronger nonlinear-baseline experiments remain pending.
