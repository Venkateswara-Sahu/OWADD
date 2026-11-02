"""Kafka Producer — Vigil.

Simulates a real-time network traffic stream by reading NSL-KDD chunks
and publishing them to a Kafka topic for the Vigil consumer to process.

Usage:
    python kafka_pipeline/producer.py
    python kafka_pipeline/producer.py --broker localhost:9092 --topic network-stream
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the Kafka stream producer."""
    parser = argparse.ArgumentParser(description="Vigil Kafka Stream Producer")
    parser.add_argument(
        "--broker", default="localhost:9092", help="Kafka broker address"
    )
    parser.add_argument(
        "--topic", default="network-stream", help="Target Kafka topic"
    )
    parser.add_argument(
        "--chunks", type=int, default=25, help="Total number of chunks to publish"
    )
    parser.add_argument(
        "--delay", type=float, default=1.0, help="Seconds between chunks"
    )
    parser.add_argument(
        "--drift-at", type=int, default=10, help="Inject drift after chunk N"
    )
    return parser.parse_args()


def main() -> None:
    """Load NSL-KDD chunks and publish JSON batches to Kafka."""
    args = parse_args()

    try:
        from kafka import KafkaProducer
    except ImportError:
        print('Kafka client missing. Run: pip install -e ".[kafka]"')
        sys.exit(1)

    from data.nsl_kdd_loader import load_nsl_kdd
    from data.stream_simulator import StreamSimulator

    print("[Producer] Loading NSL-KDD dataset...")
    x_data, y_labels, feature_names = load_nsl_kdd(
        split="train", fit_normal_only=True
    )

    print(f"[Producer] Connecting to Kafka at {args.broker}...")
    producer = KafkaProducer(
        bootstrap_servers=[args.broker],
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        acks="all",
        retries=3,
        request_timeout_ms=10_000,
    )

    sim = StreamSimulator(
        x_data,
        y_labels,
        chunk_size=200,
        drift_after_chunk=args.drift_at,
    )

    print(
        f"[Producer] Publishing {args.chunks} chunks -> topic='{args.topic}' "
        f"(delay={args.delay}s, drift_at={args.drift_at})\n"
    )

    for chunk in sim.stream(n_chunks=args.chunks):
        message = {
            "chunk_id": chunk.chunk_id,
            "chunk_size": len(chunk.X),
            "feature_names": feature_names,
            "data": chunk.X.tolist(),
            "label": chunk.dominant_class,
            "timestamp": time.time(),
        }
        record = producer.send(args.topic, value=message).get(timeout=10)
        print(
            f"[Producer] Chunk {chunk.chunk_id:02d}/{args.chunks} -> "
            f"partition={record.partition}, offset={record.offset}, "
            f"label={chunk.dominant_class}, size={len(chunk.X)}"
        )
        time.sleep(args.delay)

    producer.flush()
    producer.close()
    print("\n[Producer] Stream complete. All chunks published.")


if __name__ == "__main__":
    main()
