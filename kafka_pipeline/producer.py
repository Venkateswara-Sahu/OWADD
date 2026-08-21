"""
Kafka Producer — Vigil
================================
Simulates a real-time network traffic stream by reading NSL-KDD chunks
and publishing them to a Kafka topic for the consumer/detector to process.

Usage:
    # With docker-compose running:
    python kafka/producer.py

    # Or point at a different broker:
    python kafka/producer.py --broker localhost:9092 --topic network-stream
"""

import argparse
import json
import sys
import time
import numpy as np

sys.path.insert(0, ".")


def main():
    parser = argparse.ArgumentParser(description="OWADD Kafka Producer")
    parser.add_argument("--broker",    default="localhost:9092", help="Kafka broker address")
    parser.add_argument("--topic",     default="network-stream", help="Topic to produce to")
    parser.add_argument("--chunks",    type=int, default=25,     help="Number of chunks to send")
    parser.add_argument("--delay",     type=float, default=1.0,  help="Seconds between chunks")
    parser.add_argument("--drift-at",  type=int, default=10,     help="Inject drift at chunk N")
    args = parser.parse_args()

    try:
        from kafka import KafkaProducer
    except ImportError:
        print("kafka-python not installed. Run: pip install kafka-python")
        sys.exit(1)

    from data.nsl_kdd_loader import load_nsl_kdd
    from data.stream_simulator import StreamSimulator

    print(f"[Producer] Loading NSL-KDD dataset...")
    X, y, feature_names = load_nsl_kdd(split="train")

    print(f"[Producer] Connecting to Kafka at {args.broker}...")
    producer = KafkaProducer(
        bootstrap_servers=[args.broker],
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        acks="all",                 # wait for leader + replicas to acknowledge
        retries=3,
        request_timeout_ms=10_000,
    )

    sim = StreamSimulator(X, y, chunk_size=200, drift_after_chunk=args.drift_at)

    print(f"[Producer] Starting stream → topic='{args.topic}'")
    print(f"           {args.chunks} chunks, {args.delay}s delay, drift at chunk {args.drift_at}")
    print()

    for chunk in sim.stream(n_chunks=args.chunks):
        message = {
            "chunk_id":     chunk.chunk_id,
            "chunk_size":   len(chunk.X),
            "feature_names": feature_names,
            "data":         chunk.X.tolist(),
            "label":        chunk.dominant_class,
            "timestamp":    time.time(),
        }

        future = producer.send(args.topic, value=message)
        record_metadata = future.get(timeout=10)

        print(
            f"[Producer] Chunk {chunk.chunk_id:02d}/{args.chunks} → "
            f"partition={record_metadata.partition}, offset={record_metadata.offset}, "
            f"label={chunk.dominant_class}, size={len(chunk.X)}"
        )

        time.sleep(args.delay)

    producer.flush()
    producer.close()
    print("\n[Producer] Stream complete. All chunks published.")


if __name__ == "__main__":
    main()
