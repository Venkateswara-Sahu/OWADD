from __future__ import annotations

from collections.abc import Sequence
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder
from experiments.datasets.base import (
    DatasetSplit,
    PreparedDataset,
    validate_disjoint_ids,
)
from experiments.provenance import sha256_file


def fit_preprocessor(
    training_frame: pd.DataFrame,
    *,
    categorical_columns: Sequence[str],
    numerical_columns: Sequence[str],
) -> ColumnTransformer:
    """Fit an encoder/scaler exclusively on a declared training frame."""

    transformer = ColumnTransformer(
        [
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                list(categorical_columns),
            ),
            ("num", MinMaxScaler(), list(numerical_columns)),
        ],
        verbose_feature_names_out=False,
    )
    return transformer.fit(training_frame)


def prepare_frames(
    train: pd.DataFrame,
    test: pd.DataFrame | None,
    *,
    seed: int = 42,
    validation_fraction: float = 0.25,
) -> PreparedDataset:
    """Prepare normal-only reference and disjoint validation/test pools.

    Identity excludes label and difficulty: relabeling an identical feature
    vector cannot bypass duplicate protection. Test overlaps are removed using
    training identities; no test value influences fitted transformations.
    """
    if not 0 < validation_fraction < 1:
        raise ValueError("validation_fraction must be between zero and one")
    columns = [c for c in train.columns if c not in {"label", "difficulty"}]
    if test is not None and set(test.columns) != set(train.columns):
        raise ValueError("training and test schemas differ")
    categorical = [c for c in columns if c in {"protocol_type", "service", "flag"}]
    numerical = [c for c in columns if c not in categorical]
    frames = []
    removed = []
    for source in (train, test if test is not None else train.iloc[:0]):
        frame = source.copy()
        if frame[columns + ["label"]].isna().any().any():
            raise ValueError("missing feature or label values")
        frame[numerical] = frame[numerical].astype(float)
        if not np.isfinite(frame[numerical].to_numpy()).all():
            raise ValueError("non-finite numerical values")
        frame["_row_id"] = [
            sha256(json.dumps(list(row), separators=(",", ":")).encode()).hexdigest()
            for row in frame[columns].itertuples(index=False, name=None)
        ]
        removed.append(int(frame.duplicated("_row_id").sum()))
        frames.append(frame.drop_duplicates("_row_id").copy())
    train_clean, test_clean = frames
    overlap = test_clean["_row_id"].isin(train_clean["_row_id"])
    test_clean = test_clean.loc[~overlap].copy()
    normal = train_clean["label"].eq("normal")
    # Stable hash assignment is independent of input file ordering.
    fractions = train_clean["_row_id"].map(
        lambda value: int(sha256(f"{seed}:{value}".encode()).hexdigest()[:16], 16)
        / 2**64
    )
    reference = train_clean.loc[normal & (fractions >= validation_fraction)]
    validation = train_clean.loc[~train_clean["_row_id"].isin(reference["_row_id"])]
    required = (
        (reference, validation, test_clean)
        if test is not None
        else (reference, validation)
    )
    if any(frame.empty for frame in required):
        raise ValueError("reference, validation and test pools must all be non-empty")
    validate_disjoint_ids(
        {
            "reference": set(reference._row_id),
            "validation": set(validation._row_id),
            "test": set(test_clean._row_id),
        }
    )
    transformer = fit_preprocessor(
        reference[columns], categorical_columns=categorical, numerical_columns=numerical
    )
    names = tuple(transformer.get_feature_names_out())
    groups = {}
    cursor = 0
    if categorical:
        for name, categories in zip(
            categorical, transformer.named_transformers_["cat"].categories_
        ):
            groups[name] = tuple(range(cursor, cursor + len(categories)))
            cursor += len(categories)
    for name in numerical:
        groups[name] = (cursor,)
        cursor += 1

    def convert(frame):
        values = (
            transformer.transform(frame[columns]).astype(np.float32)
            if len(frame)
            else np.empty((0, len(names)), dtype=np.float32)
        )
        if not np.isfinite(values).all():
            raise ValueError("non-finite transformed features")
        return DatasetSplit(
            values, frame.label.to_numpy(copy=True), tuple(frame._row_id)
        )

    audit = {
        "test_loaded": test is not None,
        "train_duplicates_removed": removed[0],
        "test_duplicates_removed": removed[1],
        "test_overlap_removed": int(overlap.sum()),
        "seed": seed,
        "validation_fraction": validation_fraction,
        "identity_columns": columns,
        "split_counts": {
            name: len(frame)
            for name, frame in (
                ("reference", reference),
                ("validation", validation),
                ("test", test_clean),
            )
        },
        "class_counts": {
            name: frame.label.value_counts().to_dict()
            for name, frame in (
                ("reference", reference),
                ("validation", validation),
                ("test", test_clean),
            )
        },
    }
    return PreparedDataset(
        convert(reference),
        convert(validation),
        convert(test_clean),
        names,
        tuple("numerical" for _ in names),
        groups,
        {},
        audit,
    )


def prepare_nsl_kdd(
    train_path: Path, test_path: Path, *, seed: int = 42, include_test: bool = True
) -> PreparedDataset:
    from dataclasses import replace
    from data.nsl_kdd_loader import COLUMN_NAMES

    dataset = prepare_frames(
        pd.read_csv(train_path, header=None, names=COLUMN_NAMES),
        (
            pd.read_csv(test_path, header=None, names=COLUMN_NAMES)
            if include_test
            else None
        ),
        seed=seed,
    )
    return replace(
        dataset,
        checksums={"train": sha256_file(train_path), "test": sha256_file(test_path)},
    )


def build_network_stream(
    split: DatasetSplit,
    *,
    attack_classes: tuple[str, ...],
    chunk_size: int = 200,
    interval_chunks: int = 5,
    seed: int = 42,
):
    """Alternate normal and 50%-attack regimes without reusing records.

    Real attack transitions have no feature localization ground truth, so event
    feature sets are empty. Insufficient pools fail instead of duplicating rows.
    """
    from experiments.streams.types import ChangeEvent, StreamChunk, StreamManifest

    if chunk_size < 2 or interval_chunks < 1 or not attack_classes:
        raise ValueError(
            "positive intervals, chunk_size >= 2 and attack classes required"
        )
    if len(set(attack_classes)) != len(attack_classes) or "normal" in attack_classes:
        raise ValueError("attack classes must be unique and exclude normal")
    rng = np.random.default_rng(seed)
    pools = {
        name: list(rng.permutation(np.flatnonzero(split.y == name)))
        for name in ("normal", *attack_classes)
    }
    attack_count = chunk_size // 2
    required_normal = (len(attack_classes) + 1) * interval_chunks * chunk_size + len(
        attack_classes
    ) * interval_chunks * (chunk_size - attack_count)
    if len(pools["normal"]) < required_normal or any(
        len(pools[name]) < interval_chunks * attack_count for name in attack_classes
    ):
        raise ValueError("insufficient distinct rows for the requested stream")
    chunks, events, used_ids = [], [], []

    def append_interval(attack=None):
        for _ in range(interval_chunks):
            n_attack = attack_count if attack else 0
            indices = [pools["normal"].pop() for _ in range(chunk_size - n_attack)]
            if attack:
                indices.extend(pools[attack].pop() for _ in range(n_attack))
            rng.shuffle(indices)
            used_ids.extend(split.row_ids[i] for i in indices)
            chunks.append(
                StreamChunk(
                    len(chunks) + 1, split.X[indices].copy(), split.y[indices].copy()
                )
            )

    append_interval()
    for attack in attack_classes:
        start = len(chunks) + 1
        events.append(
            ChangeEvent(f"{attack}-onset", start, start, "attack_mixture", (), 0.5)
        )
        append_interval(attack)
        start = len(chunks) + 1
        events.append(ChangeEvent(f"{attack}-return", start, start, "return", (), -0.5))
        append_interval()
    return (
        chunks,
        StreamManifest(seed, split.X.shape[1], chunk_size, tuple(events)),
        tuple(used_ids),
    )
