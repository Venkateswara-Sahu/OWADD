"""Tests for the Autoencoder module."""
import numpy as np
import torch
import pytest
from owadd_sentinel.core.autoencoder import (
    Autoencoder,
    create_autoencoder_pair,
    train_autoencoder,
)


def test_autoencoder_forward_shape():
    """Output shape must match input shape."""
    model = Autoencoder(n_features=50)
    x = torch.randn(200, 50)
    output = model(x)
    assert output.shape == x.shape, "Autoencoder output shape mismatch"


def test_reconstruction_errors_shape():
    """reconstruction_errors() must return 1-D array of length n_samples."""
    model = Autoencoder(n_features=10)
    x = torch.randn(100, 10)
    errors = model.reconstruction_errors(x)
    assert errors.shape == (100,), "Errors must be 1-D with one value per sample"


def test_reconstruction_errors_non_negative():
    """MSE reconstruction errors must be non-negative."""
    model = Autoencoder(n_features=10)
    x = torch.randn(50, 10)
    errors = model.reconstruction_errors(x)
    assert np.all(errors >= 0), "MSE errors must be >= 0"


def test_mirrored_pair_identical_weights():
    """A and A_KC must start with identical weights."""
    A, AKC = create_autoencoder_pair(n_features=20)
    for p1, p2 in zip(A.parameters(), AKC.parameters()):
        assert torch.allclose(p1, p2), "Mirror autoencoders must have identical weights"


def test_training_reduces_loss():
    """Loss should decrease after training."""
    np.random.seed(42)
    data = np.random.randn(200, 10).astype(np.float32)
    model = Autoencoder(n_features=10)

    # Measure loss before training
    X = torch.tensor(data)
    with torch.no_grad():
        pre_loss = torch.mean((X - model(X)) ** 2).item()

    train_autoencoder(model, data, epochs=50, verbose=False)

    # Measure loss after training
    with torch.no_grad():
        post_loss = torch.mean((X - model(X)) ** 2).item()

    assert post_loss < pre_loss, "Training should reduce reconstruction loss"
