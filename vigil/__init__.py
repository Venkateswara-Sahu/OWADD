"""
Vigil
=====
Production-ready unsupervised drift detection for network traffic streams.
Feature-level attribution tells you exactly which signals changed.

Based on: "Open World Autoencoding Drift Detection with Novel Class Recognition
in Tabular Non-stationary Data Streams" (arXiv:2605.29834)

Quick Start
-----------
    from vigil import Vigil

    v = Vigil(feature_names=your_columns)
    v.fit(baseline_traffic)        # offline phase

    for batch in live_stream:
        result = v.detect(batch)
        print(result.drift_detected)      # True / False
        print(result.drift_severity)      # 0.0 – 1.0
        print(result.novelty_proportion)  # % unknown class samples

        for feat in result.attribution.top_features:
            print(feat['feature_name'], feat['contribution'])
"""

from vigil.attribution import DriftAttributor
from vigil.core.autoencoder import Autoencoder
from vigil.core.drift_detector import DriftDetector
from vigil.core.novelty_detector import NoveltyDetector
from vigil.sentinel import Vigil

# Keep Vigil as an alias so nothing breaks during transition
Vigil = Vigil

__version__ = "0.1.0"
__author__  = "Venkateswara Sahu"
__paper__   = "arXiv:2605.29834"

__all__ = [
    "Vigil",
    "Vigil",   # backwards-compat alias
    "Autoencoder",
    "DriftAttributor",
    "DriftDetector",
    "NoveltyDetector",
]
