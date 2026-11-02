"""Kafka Consumer — Vigil.

Reads network traffic chunks from a Kafka topic and evaluates each batch
with Vigil drift, novelty, and Copula-KS feature attribution.

Usage:
    python kafka_pipeline/consumer.py
    python kafka_pipeline/consumer.py --attribution-mode calibrated --n-permutations 199
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the Kafka stream consumer."""
    parser = argparse.ArgumentParser(
        description="Vigil Kafka Consumer + Drift Detector"
    )
    parser.add_argument("--broker", default="localhost:9092")
    parser.add_argument("--topic", default="network-stream")
    parser.add_argument("--group", default="vigil-consumers")
    parser.add_argument(
        "--train-chunks",
        type=int,
        default=3,
        help="Initial normal chunks buffered before fitting Vigil",
    )
    parser.add_argument(
        "--attribution-mode",
        default="decomposed",
        choices=[
            "decomposed",
            "calibrated",
            "positive_delta",
            "absolute_delta",
            "standardized_delta",
        ],
    )
    parser.add_argument(
        "--adaptation-mode",
        default="verified_only",
        choices=["verified_only", "auto", "frozen"],
    )
    parser.add_argument("--n-permutations", type=int, default=199)
    parser.add_argument("--mlflow", action="store_true", help="Log to MLflow")
    return parser.parse_args()


def _init_logger(args: argparse.Namespace) -> Any:
    """Start an optional MLflow run if `--mlflow` was passed."""
    if not args.mlflow:
        return None
    from vigil.logging.mlflow_logger import MLflowLogger

    logger = MLflowLogger(experiment_name="kafka-stream")
    logger.start_run(
        params={
            "topic": args.topic,
            "train_chunks": args.train_chunks,
            "attribution_mode": args.attribution_mode,
            "adaptation_mode": args.adaptation_mode,
        }
    )
    return logger


def _print_detection(chunk_id: int, label: str, result: Any) -> None:
    """Print a compact one-line summary for a processed Kafka batch."""
    verdict = "DRIFT" if result.drift_detected else "STABLE"
    print(
        f"[Consumer] Chunk {chunk_id:02d} [{label:<10}] {verdict:<6} | "
        f"severity={result.drift_severity:.2f} | "
        f"novelty={result.novelty_proportion:.1%} | "
        f"error={result.drift_result.batch_error_mean:.4f}"
    )
    if result.drift_detected and result.attribution is not None:
        top = result.attribution.top_features[:3]
        feat_str = ", ".join(
            f"{f['feature_name']}[{f.get('drift_type', '?')}]"
            f"({f['contribution']:.1%})"
            for f in top
        )
        print(f"             Top features: {feat_str}")


def main() -> None:
    """Consume JSON batches from Kafka and run Vigil online."""
    args = parse_args()

    try:
        from kafka import KafkaConsumer
    except ImportError:
        print('Kafka client missing. Run: pip install -e ".[kafka]"')
        sys.exit(1)

    from vigil import Vigil

    print(f"[Consumer] Connecting to Kafka at {args.broker}...")
    consumer = KafkaConsumer(
        args.topic,
        bootstrap_servers=[args.broker],
        group_id=args.group,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        consumer_timeout_ms=30_000,
    )

    logger = _init_logger(args)
    sentinel: Vigil | None = None
    train_buf: list[np.ndarray] = []
    chunk_count = 0

    print(
        f"[Consumer] Listening on topic='{args.topic}' "
        f"(train_chunks={args.train_chunks}, mode={args.attribution_mode})...\n"
    )

    for msg in consumer:
        payload = msg.value
        chunk_id = int(payload["chunk_id"])
        data = np.asarray(payload["data"], dtype=np.float32)
        feat_names = payload.get(
            "feature_names", [f"f_{i}" for i in range(data.shape[1])]
        )
        label = str(payload.get("label", "unknown"))
        chunk_count += 1

        if sentinel is None:
            train_buf.append(data)
            rem = args.train_chunks - len(train_buf)
            print(f"[Consumer] Chunk {chunk_id:02d} — buffering ({rem} remaining)")
            if len(train_buf) >= args.train_chunks:
                train_data = np.vstack(train_buf)
                sentinel = Vigil(
                    feature_names=feat_names,
                    top_k_features=5,
                    attribution_mode=args.attribution_mode,
                    adaptation_mode=args.adaptation_mode,
                    n_permutations=args.n_permutations,
                    seed=42,
                )
                t0 = time.perf_counter()
                sentinel.fit(train_data, verbose=False)
                print(
                    f"[Consumer] Sentinel fitted on {len(train_data)} rows "
                    f"in {time.perf_counter() - t0:.1f}s\n"
                )
            continue

        result = sentinel.detect(data)
        _print_detection(chunk_id, label, result)
        if logger is not None:
            logger.log_chunk(result, ground_truth_label=label)

    consumer.close()
    if logger is not None:
        logger.end_run()
    print(f"\n[Consumer] Done. Processed {chunk_count} chunks total.")


if __name__ == "__main__":
    main()
