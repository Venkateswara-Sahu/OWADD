"""
NSL-KDD Dataset Loader
======================
Downloads, preprocesses and returns the NSL-KDD network intrusion detection
dataset as a clean NumPy array suitable for stream simulation.

NSL-KDD is the standard benchmark for concept drift in network traffic:
- 41 features (mix of numeric and categorical)
- Labels: normal, neptune, back, smurf, teardrop, etc.
- Contains natural distribution shifts between train/test sets

Source: Canadian Institute for Cybersecurity
        https://www.unb.ca/cic/datasets/nsl.html
"""

import numpy as np
import pandas as pd
import urllib.request
from pathlib import Path

# Column names for the NSL-KDD dataset (41 features + label + difficulty)
COLUMN_NAMES = [
    "duration", "protocol_type", "service", "flag", "src_bytes",
    "dst_bytes", "land", "wrong_fragment", "urgent", "hot",
    "num_failed_logins", "logged_in", "num_compromised", "root_shell",
    "su_attempted", "num_root", "num_file_creations", "num_shells",
    "num_access_files", "num_outbound_cmds", "is_host_login",
    "is_guest_login", "count", "srv_count", "serror_rate",
    "srv_serror_rate", "rerror_rate", "srv_rerror_rate", "same_srv_rate",
    "diff_srv_rate", "srv_diff_host_rate", "dst_host_count",
    "dst_host_srv_count", "dst_host_same_srv_rate", "dst_host_diff_srv_rate",
    "dst_host_same_src_port_rate", "dst_host_srv_diff_host_rate",
    "dst_host_serror_rate", "dst_host_srv_serror_rate", "dst_host_rerror_rate",
    "dst_host_srv_rerror_rate", "label", "difficulty"
]

# Categorical columns that need encoding
CATEGORICAL_COLS = ["protocol_type", "service", "flag"]

# Feature columns (everything except label and difficulty)
FEATURE_COLS = [c for c in COLUMN_NAMES if c not in ("label", "difficulty")]

# Download URLs (raw GitHub mirror — always available)
TRAIN_URL = (
    "https://raw.githubusercontent.com/defcom17/NSL_KDD/master/KDDTrain%2B.txt"
)
TEST_URL = (
    "https://raw.githubusercontent.com/defcom17/NSL_KDD/master/KDDTest%2B.txt"
)

DATA_DIR = Path(__file__).parent / "raw"


def download_nsl_kdd(force: bool = False) -> tuple[Path, Path]:
    """
    Download NSL-KDD train and test files if not already present.

    Parameters
    ----------
    force : bool
        Re-download even if files exist.

    Returns
    -------
    train_path, test_path : Path
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    train_path = DATA_DIR / "KDDTrain+.txt"
    test_path = DATA_DIR / "KDDTest+.txt"

    if not train_path.exists() or force:
        print("[NSL-KDD] Downloading training set...")
        urllib.request.urlretrieve(TRAIN_URL, train_path)
        print(f"[NSL-KDD] Saved to {train_path}")

    if not test_path.exists() or force:
        print("[NSL-KDD] Downloading test set...")
        urllib.request.urlretrieve(TEST_URL, test_path)
        print(f"[NSL-KDD] Saved to {test_path}")

    return train_path, test_path


def load_nsl_kdd(split: str = "train", force_download: bool = False):
    """
    Load and preprocess the NSL-KDD dataset.

    Preprocessing steps:
    1. One-hot encode categorical columns (protocol_type, service, flag)
    2. Normalise numeric columns to [0, 1] range
    3. Return feature matrix X, labels y, and feature names

    Parameters
    ----------
    split : str
        'train' or 'test'
    force_download : bool

    Returns
    -------
    X : np.ndarray, shape (n_samples, n_features_encoded)
        Normalised feature matrix ready for the autoencoder.
    y : np.ndarray, shape (n_samples,)
        String labels ('normal', 'neptune', 'back', etc.)
    feature_names : list of str
        Column names after one-hot encoding (for attribution reports).
    """
    train_path, test_path = download_nsl_kdd(force=force_download)
    path = train_path if split == "train" else test_path

    print(f"[NSL-KDD] Loading {split} set from {path}...")
    df = pd.read_csv(path, header=None, names=COLUMN_NAMES)

    # Extract labels before encoding
    y = df["label"].values

    # Drop label and difficulty columns
    df = df[FEATURE_COLS].copy()

    # One-hot encode categorical columns
    df = pd.get_dummies(df, columns=CATEGORICAL_COLS, dtype=float)

    feature_names = df.columns.tolist()

    # Normalise all columns to [0, 1] — min-max scaling
    df_min = df.min()
    df_max = df.max()
    df_range = df_max - df_min
    df_range[df_range == 0] = 1  # avoid division by zero for constant columns
    df_norm = (df - df_min) / df_range

    X = df_norm.values.astype(np.float32)

    print(
        f"[NSL-KDD] Loaded {len(X)} samples, {X.shape[1]} features "
        f"({len(np.unique(y))} unique attack classes)"
    )
    return X, y, feature_names
