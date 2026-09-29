"""Frozen research scoring; no drift detection, adaptation or thresholding."""

import json
import pickle
from copy import deepcopy
from hashlib import sha256

import numpy as np
import sklearn
import torch
from sklearn.utils.validation import check_is_fitted

MATRIX_DIMENSIONS = 2


class FrozenNoveltyScorer:
    """Snapshot an already-fitted autoencoder and KDE. Higher means more novel."""

    def __init__(
        self, autoencoder, kde, *, preprocessing_id, reference_id, batch_size=1024
    ):
        if not all(
            isinstance(value, str) and value.strip()
            for value in (preprocessing_id, reference_id)
        ):
            raise ValueError("preprocessing and reference identities are required")
        if type(batch_size) is not int or batch_size < 1:
            raise ValueError("batch_size must be a positive integer")
        check_is_fitted(kde, ["tree_", "bandwidth_", "n_features_in_"])
        if kde.n_features_in_ != 1:
            raise ValueError(
                "KDE must be fitted to one-dimensional reconstruction errors"
            )
        self._batch_size = batch_size
        self._model = deepcopy(autoencoder).cpu().eval()
        self._model.requires_grad_(False)
        self._kde = deepcopy(kde)
        weights = {}
        for name, tensor in self._model.state_dict().items():
            array = tensor.detach().cpu().numpy()
            weights[name] = {
                "shape": array.shape,
                "dtype": str(array.dtype),
                "sha256": sha256(array.tobytes()).hexdigest(),
            }
        identity = {
            "schema_version": 1,
            "score": "negative-log-kde-of-float32-reconstruction-mse",
            "architecture": repr(self._model),
            "weights": weights,
            # Hash only: no pickle files are loaded or published by this adapter.
            "kde_sha256": sha256(pickle.dumps(self._kde, protocol=5)).hexdigest(),
            "preprocessing_id": preprocessing_id,
            "reference_id": reference_id,
            "torch": torch.__version__,
            "sklearn": sklearn.__version__,
            "batch_size": batch_size,
        }
        self._model_id = sha256(
            json.dumps(identity, sort_keys=True, allow_nan=False).encode()
        ).hexdigest()

    @property
    def model_id(self):
        return self._model_id

    @classmethod
    def from_vigil(cls, sentinel, *, preprocessing_id, reference_id, batch_size=1024):
        """Snapshot fitted A_KC/KDE, never call detect() or adapt the source.

        Caller attests to training-only preprocessing and reference fitting.
        This narrow bridge intentionally contains access to Vigil internals.
        """
        if not sentinel.is_fitted:
            raise ValueError("Vigil must be fitted before taking a scoring snapshot")
        return cls(
            sentinel._autoencoder_AKC,
            sentinel._novelty_detector._kde,
            preprocessing_id=preprocessing_id,
            reference_id=reference_id,
            batch_size=batch_size,
        )

    def __call__(self, X):
        X = np.asarray(X)
        if (
            X.ndim != MATRIX_DIMENSIONS
            or not len(X)
            or X.shape[1] != self._model.n_features
        ):
            raise ValueError("features must be a nonempty aligned matrix")
        scores = np.empty(len(X), dtype=float)
        for start in range(0, len(X), self._batch_size):
            stop = start + self._batch_size
            with np.errstate(over="ignore", invalid="ignore"):
                batch = np.asarray(X[start:stop], dtype=np.float32)
            if not np.isfinite(batch).all():
                raise ValueError("features must be finite in float32")
            errors = self._model.reconstruction_errors(torch.tensor(batch))
            if not np.isfinite(errors).all():
                raise ValueError("nonfinite reconstruction errors")
            scores[start:stop] = -self._kde.score_samples(errors.reshape(-1, 1))
        if not np.isfinite(scores).all():
            raise ValueError("nonfinite KDE novelty scores")
        return scores
