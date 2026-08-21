"""
Kafka Consumer — Vigil
=================================
Reads network traffic chunks from a Kafka topic and runs Vigil
drift detection on each chunk in real time.

Usage:
    # With docker-compose running (Kafka + producer already publishing):
    python kafka/consumer.py

    # Or with custom settings:
    python kafka/consumer.py --broker localhost:9092 --topic network-stream
"""

import argparse
import json
import sys
import time

import numpy as np

sys.path.insert(0, ".")


def main():
    parser = argparse.ArgumentParser(description="OWADD Kafka Consumer + Drift Detector")
    parser.add_argument("--broker",        default="localhost:9092")
    parser.add_argument("--topic",         default="network-stream")
    parser.add_argument("--group",         default="owadd-consumers")
    parser.add_argument("--train-chunks",  type=int, default=1,  help="Chunks to use for initial training")
    parser.add_argument("--mlflow",        action="store_true",  help="Log to MLflow")
    args = parser.parse_args()

    try:
        from kafka import KafkaConsumer
    except ImportError:
        print("kafka-python not installed. Run: pip install kafka-python")
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
        consumer_timeout_ms=30_000,   # stop if no messages for 30s
    )

    sentinel   = None
    train_buf  = []
    feat_names = None

    print(f"[Consumer] Listening on topic='{args.topic}'...")
    print(f"           Will train on first {args.train_chunks} chunk(s), then detect.\n")

    if args.mlflow:
        from vigil.logging.mlflow_logger import MLflowLogger
        logger = MLflowLogger(experiment_name="kafka-stream")
        logger.start_run(params={"topic": args.topic, "train_chunks": args.train_chunks})
    else:
        logger = None

    chunk_count = 0

    for msg in consumer:
        chunk = msg.value
        chunk_id   = chunk["chunk_id"]
        data       = np.array(chunk["data"], dtype="float32")
        feat_names = chunk.get("feature_names", [f"f_{i}" for i in range(data.shape[1])])
        label      = chunk.get("label", "unknown")
        chunk_count += 1

        # ── Training phase ────────────────────────────────────────────────
        if sentinel is None:
            train_buf.append(data)
            remaining = args.train_chunks - len(train_buf)
            print(f"[Consumer] Chunk {chunk_id:02d} — TRAINING ({remaining} more chunk(s) needed)")

            if len(train_buf) >= args.train_chunks:
                train_data = np.vstack(train_buf)
                sentinel   = Vigil(feature_names=feat_names, top_k_features=5)

                print(f"[Consumer] Fitting Vigil on {len(train_data)} samples...")
                t0 = time.time()
                sentinel.fit(train_data, verbose=False)
                print(f"[Consumer] ✓ Sentinel ready in {time.time()-t0:.1f}s\n")
            continue

        # ── Detection phase ───────────────────────────────────────────────
        result = sentinel.detect(data)

        status_icon = "⚠" if result.drift_detected else "✓"
        status_text = "DRIFT" if result.drift_detected else "STABLE"

        print(
            f"[Consumer] Chunk {chunk_id:02d} [{label:<10}] "
            f"{status_icon} {status_text:<6} | "
            f"severity={result.drift_severity:.2f} | "
            f"novelty={result.novelty_proportion:.1%} | "
            f"error={result.drift_result.batch_error_mean:.4f}"
        )

        if result.drift_detected and result.attribution:
            top = result.attribution.top_features[:3]
            feat_str = ", ".join(f"{f['feature_name']}({f['contribution']:.1%})" for f in top)
            print(f"             Top features: {feat_str}")

        if logger:
            logger.log_chunk(result, ground_truth_label=label)

    consumer.close()
    if logger:
        logger.end_run()
    print(f"\n[Consumer] Done. Processed {chunk_count} chunks total.")


if __name__ == "__main__":
    main()
