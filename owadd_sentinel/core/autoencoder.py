"""
Autoencoder Module
==================
Implements the dual mirrored fully-connected autoencoder architecture
described in arXiv:2605.29834.

Two autoencoders are used:
  - A      : Primary autoencoder for drift detection. Its weights are
             incrementally updated after each detected drift so it
             continuously adapts to the new reference distribution.
  - A_KC   : Mirror of A, frozen after initial training. Used exclusively
             for novelty (unknown-class) recognition via KDE on its
             reconstruction errors. Only updated when a novel class is
             confirmed and the known-class distribution changes.

Architecture (paper defaults):
  Input(n_features) → Linear(10) → ReLU → Linear(10) → ReLU → Linear(10)
  → ReLU → Linear(n_features)   [encoder + decoder as one Sequential]
"""


import numpy as np
import torch
from torch import nn


class Autoencoder(nn.Module):
    """
    Fully-connected autoencoder for tabular data.

    The architecture uses three hidden layers of 10 neurons each,
    matching the configuration optimised in arXiv:2605.29834.

    Parameters
    ----------
    n_features : int
        Number of input features (columns) in the tabular data.
    hidden_dim : int, optional
        Number of neurons in each hidden layer. Default: 10 (paper default).
    """

    def __init__(self, n_features: int, hidden_dim: int = 10):
        super().__init__()
        self.n_features = n_features
        self.hidden_dim = hidden_dim

        # Encoder: compresses input to latent representation
        self.encoder = nn.Sequential(
            nn.Linear(n_features, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )

        # Decoder: reconstructs input from latent representation
        self.decoder = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, n_features),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass: encode then decode."""
        latent = self.encoder(x)
        reconstructed = self.decoder(latent)
        return reconstructed

    def reconstruction_errors(self, x: torch.Tensor) -> np.ndarray:
        """
        Compute per-sample MSE reconstruction error.

        This is the core 1-D proxy used by both the drift detector (T-test)
        and the novelty detector (KDE). Using a 1-D proxy instead of the full
        feature vector significantly reduces memory complexity.

        Parameters
        ----------
        x : torch.Tensor, shape (n_samples, n_features)

        Returns
        -------
        errors : np.ndarray, shape (n_samples,)
            Mean squared reconstruction error per sample.
        """
        self.eval()
        with torch.no_grad():
            reconstructed = self.forward(x)
            # Per-sample MSE: mean over feature dimension
            errors = torch.mean((x - reconstructed) ** 2, dim=1)
        return errors.cpu().numpy()


def create_autoencoder_pair(n_features: int, hidden_dim: int = 10):
    """
    Create the dual mirrored autoencoder pair (A and A_KC).

    A_KC starts as an exact copy of A (same initial weights).
    They diverge over time because A is updated on drift, while A_KC
    is only updated when novel class emergence is confirmed.

    Parameters
    ----------
    n_features : int
    hidden_dim : int

    Returns
    -------
    autoencoder_A : Autoencoder   — drift detection model
    autoencoder_AKC : Autoencoder — novelty recognition model (mirror of A)
    """
    autoencoder_A = Autoencoder(n_features=n_features, hidden_dim=hidden_dim)
    autoencoder_AKC = Autoencoder(n_features=n_features, hidden_dim=hidden_dim)

    # Mirror: copy exact weights from A into A_KC
    autoencoder_AKC.load_state_dict(autoencoder_A.state_dict())

    return autoencoder_A, autoencoder_AKC


def train_autoencoder(
    model: Autoencoder,
    data: np.ndarray,
    epochs: int = 400,
    lr: float = 1e-3,
    batch_size: int = 32,
    verbose: bool = False,
) -> list:
    """
    Train an autoencoder on a numpy array of tabular data.

    Uses Adam optimiser and MSE reconstruction loss.
    Paper uses 400 epochs for the offline (initial) training phase.

    Parameters
    ----------
    model : Autoencoder
    data : np.ndarray, shape (n_samples, n_features)
    epochs : int
        Number of training epochs. Use 400 for initial training (paper default),
        fewer (e.g., 50) for incremental updates after drift.
    lr : float
        Learning rate for Adam optimiser.
    batch_size : int
    verbose : bool
        If True, print loss every 50 epochs.

    Returns
    -------
    loss_history : list of float
        MSE loss per epoch.
    """
    model.train()
    optimiser = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()

    # Convert numpy array to tensor
    X = torch.tensor(data, dtype=torch.float32)
    dataset = torch.utils.data.TensorDataset(X)
    loader = torch.utils.data.DataLoader(
        dataset, batch_size=batch_size, shuffle=True
    )

    loss_history = []
    for epoch in range(epochs):
        epoch_loss = 0.0
        for (batch,) in loader:
            optimiser.zero_grad()
            output = model(batch)
            loss = criterion(output, batch)
            loss.backward()
            optimiser.step()
            epoch_loss += loss.item()

        avg_loss = epoch_loss / len(loader)
        loss_history.append(avg_loss)

        if verbose and (epoch + 1) % 50 == 0:
            print(f"  Epoch [{epoch+1}/{epochs}]  Loss: {avg_loss:.6f}")

    model.eval()
    return loss_history
