"""Audited development-only data selection for the final mechanism check."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.attribution_screen import make_cases
from experiments.dependency_data import make_dependency_cases
from experiments.provenance import sha256_file

N_FEATURES = 20
TRAIN_START, TRAIN_STOP = 2000, 4000
VALIDATION_START, VALIDATION_STOP = 600, 32600
BLOCK_SIZE = 1600
WINDOW_SIZE = 800
MIN_TRAINING_SD = 1e-8


def load_real_pools(root):
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text())
    if (
        manifest.get("complete") is not True
        or manifest.get("dataset") != "cicids2017_improved_cns2022"
        or manifest["split_days"]["reference"] != ["monday"]
        or manifest["split_days"]["validation"] != ["tuesday"]
    ):
        raise ValueError("incompatible development manifest")
    hashes = {"manifest.json": sha256_file(root / "manifest.json")}
    for day in ("monday", "tuesday"):
        for suffix in ("X.npy", "metadata.csv"):
            name = f"{day}.{suffix}"
            hashes[name] = sha256_file(root / name)
            if hashes[name] != manifest["artifacts"][name]:
                raise ValueError("cache checksum mismatch")
    train = np.asarray(
        np.load(root / "monday.X.npy", mmap_mode="r")[TRAIN_START:TRAIN_STOP],
        dtype=float,
    )
    validation = np.asarray(
        np.load(root / "tuesday.X.npy", mmap_mode="r")[
            VALIDATION_START:VALIDATION_STOP
        ],
        dtype=float,
    )
    if (
        len(train) != TRAIN_STOP - TRAIN_START
        or len(validation) != VALIDATION_STOP - VALIDATION_START
    ):
        raise ValueError("insufficient unused development rows")
    if not np.isfinite(train).all() or not np.isfinite(validation).all():
        raise ValueError("nonfinite selected development data")
    training_ids = (
        pd.read_csv(
            root / "monday.metadata.csv", nrows=TRAIN_STOP, dtype={"row_id": str}
        )["row_id"]
        .iloc[TRAIN_START:]
        .tolist()
    )
    validation_ids = (
        pd.read_csv(
            root / "tuesday.metadata.csv", nrows=VALIDATION_STOP, dtype={"row_id": str}
        )["row_id"]
        .iloc[VALIDATION_START:]
        .tolist()
    )
    all_ids = training_ids + validation_ids
    if len(all_ids) != len(train) + len(validation) or len(set(all_ids)) != len(
        all_ids
    ):
        raise ValueError("missing or overlapping row identities")
    sd = train.std(0, ddof=1)
    columns = [
        i
        for i, name in enumerate(manifest["feature_names"])
        if name not in ("Dst Port", "Protocol") and sd[i] > MIN_TRAINING_SD
    ][:N_FEATURES]
    if len(columns) != N_FEATURES:
        raise ValueError("insufficient training-variable features")
    mean, scale = train[:, columns].mean(0), sd[columns]
    return {
        "train": (train[:, columns] - mean) / scale,
        "validation": (validation[:, columns] - mean) / scale,
        "training_ids": training_ids,
        "validation_ids": validation_ids,
        "feature_names": [manifest["feature_names"][i] for i in columns],
        "mean": mean.tolist(),
        "scale": scale.tolist(),
        "hashes": hashes,
        "selected_nonfinite_count": 0,
    }


def real_cases(pools, seed):
    streams = [
        np.random.default_rng(s) for s in np.random.SeedSequence([seed, 411]).spawn(4)
    ]
    start = ((seed - 50) % 20) * BLOCK_SIZE
    rows = streams[0].permutation(BLOCK_SIZE) + start
    ref_rows, current_rows = rows[:WINDOW_SIZE], rows[WINDOW_SIZE:]
    reference, base = pools["validation"][ref_rows], pools["validation"][current_rows]
    truth = tuple(int(i) for i in streams[1].choice(N_FEATURES, 2, replace=False))
    order = streams[2].permutation(N_FEATURES)
    variants = [("no_injection", (), base.copy())]
    for magnitude in (0.5, 2):
        current = base.copy()
        current[:, truth] += magnitude
        variants.append((f"mean_{magnitude}", truth, current))
    for multiplier in (0.5, 2):
        current = base.copy()
        current[:, truth] *= multiplier
        variants.append((f"std_{multiplier}", truth, current))
    current = base.copy()
    for col in truth:
        current[:, col] = streams[3].permutation(current[:, col])
    variants.append(("permutation", truth, current))
    return [
        {
            "case": "real/" + name,
            "train": pools["train"],
            "reference": reference,
            "current": current,
            "truth": target,
            "tie_order": order,
            "reference_ids": [pools["validation_ids"][i] for i in ref_rows],
            "current_ids": [pools["validation_ids"][i] for i in current_rows],
        }
        for name, target, current in variants
    ]


def synthetic_cases(seed):
    train, reference, cases, order = make_cases(seed)
    result = [
        {
            "case": "independent/" + name,
            "train": train,
            "reference": reference,
            "current": current,
            "truth": truth,
            "tie_order": order,
        }
        for name, truth, current in cases
    ]
    for case in make_dependency_cases(seed):
        result.append({**case, "case": "dependency/" + case["case"]})
    return result
