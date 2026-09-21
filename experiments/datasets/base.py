from __future__ import annotations

from collections.abc import Mapping, Set
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class DatasetSplit:
    X: np.ndarray
    y: np.ndarray
    row_ids: tuple[str, ...]


@dataclass(frozen=True)
class PreparedDataset:
    reference: DatasetSplit
    validation: DatasetSplit
    test: DatasetSplit
    feature_names: tuple[str, ...]
    feature_types: tuple[str, ...]
    feature_groups: dict[str, tuple[int, ...]]
    checksums: dict[str, str]
    audit: dict[str, object]


class DataLeakageError(ValueError):
    """Raised when dataset partitions share source rows."""


def validate_disjoint_ids(split_ids: Mapping[str, Set[str]]) -> None:
    names = list(split_ids)
    for index, left_name in enumerate(names):
        for right_name in names[index + 1 :]:
            overlap = set(split_ids[left_name]) & set(split_ids[right_name])
            if overlap:
                raise DataLeakageError(
                    f"row-id overlap between {left_name} and {right_name}: "
                    f"{sorted(overlap)[:5]}"
                )
