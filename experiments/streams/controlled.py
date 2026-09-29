from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from experiments.streams.types import ChangeEvent, StreamChunk, StreamManifest


SUPPORTED_KINDS = {"mean", "variance", "categorical", "correlated", "noise"}
SUPPORTED_PATTERNS = {"abrupt", "gradual", "recurring"}


@dataclass(frozen=True)
class ShiftSpec:
    kind: str
    features: tuple[int, ...]
    magnitude: float
    event_chunk: int
    n_chunks: int
    chunk_size: int
    seed: int
    pattern: str = "abrupt"
    end_chunk: int | None = None
    category_probabilities: dict[int, dict[float, float]] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if self.kind not in SUPPORTED_KINDS:
            raise ValueError(f"unsupported shift kind: {self.kind}")
        if self.pattern not in SUPPORTED_PATTERNS:
            raise ValueError(f"unsupported shift pattern: {self.pattern}")
        if not self.features:
            raise ValueError("at least one shifted feature is required")
        if self.event_chunk < 1 or self.event_chunk > self.n_chunks:
            raise ValueError("event_chunk must be inside the stream")
        if self.n_chunks < 1 or self.chunk_size < 1:
            raise ValueError("n_chunks and chunk_size must be positive")
        if self.seed < 0:
            raise ValueError("seed must be non-negative")
        if self.kind == "variance" and self.magnitude <= 0:
            raise ValueError("variance magnitude must be positive")


class ControlledStreamBuilder:
    """Construct deterministic streams with exact feature-shift ground truth."""

    def build(
        self, reference: np.ndarray, spec: ShiftSpec
    ) -> tuple[list[StreamChunk], StreamManifest]:
        reference = np.asarray(reference)
        if reference.ndim != 2 or reference.shape[0] == 0:
            raise ValueError("reference must be a non-empty 2D array")
        invalid = [
            index
            for index in spec.features
            if index < 0 or index >= reference.shape[1]
        ]
        if invalid:
            raise ValueError(f"feature index outside reference columns: {invalid}")
        if len(set(spec.features)) != len(spec.features):
            raise ValueError("shifted feature indices must be unique")

        end_chunk = self._validate_interval(spec)
        self._validate_categories(reference, spec)
        rng = np.random.default_rng(spec.seed)
        chunks: list[StreamChunk] = []
        for chunk_id in range(1, spec.n_chunks + 1):
            indices = rng.choice(
                reference.shape[0], size=spec.chunk_size, replace=True
            )
            values = reference[indices].copy()
            strength = self._strength(spec, chunk_id, end_chunk)
            if strength > 0:
                self._apply_shift(values, reference, spec, strength, rng)
            chunks.append(StreamChunk(chunk_id=chunk_id, X=values))

        events = [
            ChangeEvent(
                event_id="shift-1",
                start_chunk=spec.event_chunk,
                end_chunk=end_chunk,
                kind=spec.kind,
                shifted_features=spec.features,
                magnitude=spec.magnitude,
            )
        ]
        if spec.pattern == "recurring":
            events.append(
                ChangeEvent(
                    event_id="return-1",
                    start_chunk=end_chunk + 1,
                    end_chunk=end_chunk + 1,
                    kind="return",
                    shifted_features=spec.features,
                    magnitude=-spec.magnitude,
                )
            )
        manifest = StreamManifest(
            seed=spec.seed,
            n_features=reference.shape[1],
            chunk_size=spec.chunk_size,
            events=tuple(events),
        )
        return chunks, manifest

    @staticmethod
    def _validate_interval(spec: ShiftSpec) -> int:
        if spec.pattern == "abrupt":
            return spec.n_chunks
        if spec.end_chunk is None:
            raise ValueError(f"end_chunk is required for {spec.pattern} drift")
        if spec.end_chunk < spec.event_chunk:
            raise ValueError("end_chunk must be at or after event_chunk")
        if spec.pattern == "recurring" and spec.end_chunk >= spec.n_chunks:
            raise ValueError("end_chunk must leave room for a return event")
        if spec.end_chunk > spec.n_chunks:
            raise ValueError("end_chunk must be inside the stream")
        return spec.end_chunk

    @staticmethod
    def _validate_categories(reference: np.ndarray, spec: ShiftSpec) -> None:
        if spec.kind != "categorical":
            return
        if set(spec.category_probabilities) != set(spec.features):
            raise ValueError(
                "categorical shifts require probabilities for every feature"
            )
        for feature, distribution in spec.category_probabilities.items():
            if not distribution:
                raise ValueError(f"category probabilities empty for feature {feature}")
            probabilities = np.asarray(list(distribution.values()), dtype=float)
            if np.any(probabilities < 0) or not np.isclose(
                probabilities.sum(), 1.0
            ):
                raise ValueError(
                    f"category probabilities for feature {feature} must sum to 1"
                )
            known = set(np.unique(reference[:, feature]).tolist())
            if not set(distribution).issubset(known):
                raise ValueError(
                    f"categorical shift contains unknown value for feature {feature}"
                )

    @staticmethod
    def _strength(spec: ShiftSpec, chunk_id: int, end_chunk: int) -> float:
        if chunk_id < spec.event_chunk:
            return 0.0
        if spec.pattern == "recurring":
            return 1.0 if chunk_id <= end_chunk else 0.0
        if spec.pattern == "gradual" and chunk_id <= end_chunk:
            duration = end_chunk - spec.event_chunk + 1
            return (chunk_id - spec.event_chunk + 1) / duration
        return 1.0

    @staticmethod
    def _apply_shift(
        values: np.ndarray,
        reference: np.ndarray,
        spec: ShiftSpec,
        strength: float,
        rng: np.random.Generator,
    ) -> None:
        features = np.asarray(spec.features, dtype=int)
        if spec.kind == "mean":
            values[:, features] += spec.magnitude * strength
        elif spec.kind == "variance":
            centers = reference[:, features].mean(axis=0)
            multiplier = 1.0 + (spec.magnitude - 1.0) * strength
            values[:, features] = centers + (
                values[:, features] - centers
            ) * multiplier
        elif spec.kind == "noise":
            noise = rng.normal(
                loc=0.0,
                scale=spec.magnitude * strength,
                size=(values.shape[0], len(features)),
            )
            values[:, features] += noise
        elif spec.kind == "categorical":
            for feature in spec.features:
                distribution = spec.category_probabilities[feature]
                categories = np.asarray(list(distribution), dtype=values.dtype)
                target = np.asarray(list(distribution.values()), dtype=float)
                observed_values, observed_counts = np.unique(
                    reference[:, feature], return_counts=True
                )
                observed = {
                    value: count / observed_counts.sum()
                    for value, count in zip(observed_values, observed_counts)
                }
                mixed = np.asarray(
                    [
                        (1.0 - strength) * observed.get(value, 0.0)
                        + strength * probability
                        for value, probability in distribution.items()
                    ]
                )
                mixed /= mixed.sum()
                values[:, feature] = rng.choice(
                    categories, size=values.shape[0], p=mixed
                )
        elif spec.kind == "correlated":
            if len(features) < 2:
                raise ValueError("correlated shifts require at least two features")
            selected = values[:, features].astype(float)
            means = selected.mean(axis=0)
            scales = selected.std(axis=0)
            scales[scales == 0] = 1.0
            standardized = (selected - means) / scales
            rho = np.tanh(spec.magnitude * strength) * 0.8
            covariance = np.full((len(features), len(features)), rho)
            np.fill_diagonal(covariance, 1.0)
            minimum = np.linalg.eigvalsh(covariance).min()
            if minimum <= 0:
                covariance += np.eye(len(features)) * (abs(minimum) + 1e-8)
            transform = np.linalg.cholesky(covariance)
            values[:, features] = standardized @ transform.T * scales + means
