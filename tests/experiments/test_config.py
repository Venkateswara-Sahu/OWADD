from pathlib import Path

import pytest

from experiments.config import ExperimentConfig


def test_config_hash_is_key_order_independent(tmp_path: Path) -> None:
    first = tmp_path / "first.yaml"
    second = tmp_path / "second.yaml"
    first.write_text(
        "seed: 42\ndataset: synthetic\nmethod: vigil\n", encoding="utf-8"
    )
    second.write_text(
        "method: vigil\ndataset: synthetic\nseed: 42\n", encoding="utf-8"
    )

    assert (
        ExperimentConfig.from_yaml(first).config_hash
        == ExperimentConfig.from_yaml(second).config_hash
    )


def test_config_rejects_unknown_keys(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text(
        "dataset: synthetic\nseed: 42\nmethod: vigil\nsurprise: true\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown configuration keys"):
        ExperimentConfig.from_yaml(path)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"seed": -1}, "seed must be non-negative"),
        ({"chunk_size": 1}, "chunk_size must be at least 2"),
        ({"tolerance_chunks": -1}, "tolerance_chunks must be non-negative"),
    ],
)
def test_config_rejects_invalid_numeric_values(
    overrides: dict[str, int], message: str
) -> None:
    values = {"dataset": "synthetic", "method": "vigil", "seed": 42}
    values.update(overrides)

    with pytest.raises(ValueError, match=message):
        ExperimentConfig(**values)
