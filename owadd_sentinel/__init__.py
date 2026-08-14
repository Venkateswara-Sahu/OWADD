"""
OWADD Sentinel
==============
Production-ready unsupervised ML data drift detection with feature attribution.

Based on: "Open World Autoencoding Drift Detection with Novel Class Recognition
in Tabular Non-stationary Data Streams" (arXiv:2605.29834)

Quick Start
-----------
    from owadd_sentinel import OWADDSentinel
    import pandas as pd

    # Initialize
    sentinel = OWADDSentinel()

    # Train on your first batch of data (offline phase)
    sentinel.fit(initial_data_df)

    # Process incoming stream batches
    for batch in your_data_stream:
        result = sentinel.detect(batch)
        print(result.drift_detected)       # True / False
        print(result.drift_severity)       # 0.0 - 1.0
        print(result.top_drifted_features) # Which features changed most
        print(result.novelty_proportion)   # % of unknown class samples
"""

from owadd_sentinel.sentinel import OWADDSentinel
from owadd_sentinel.core.drift_detector import DriftDetector
from owadd_sentinel.core.novelty_detector import NoveltyDetector
from owadd_sentinel.core.autoencoder import Autoencoder
from owadd_sentinel.attribution import DriftAttributor

__version__ = "0.1.0"
__author__ = "Venkateswara Sahu"
__paper__ = "arXiv:2605.29834"

__all__ = [
    "OWADDSentinel",
    "DriftDetector",
    "NoveltyDetector",
    "Autoencoder",
    "DriftAttributor",
]
