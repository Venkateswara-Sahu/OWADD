from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from experiments.config import ExperimentConfig
from experiments.io import (
    ResultEnvelope,
    ResultIntegrityError,
    load_completed_result,
    write_result_atomic,
)
from experiments.provenance import Provenance, sha256_file


@pytest.fixture
def config() -> ExperimentConfig:
    return ExperimentConfig(dataset="synthetic", method="vigil", seed=42)


@pytest.fixture
def provenance() -> Provenance:
    return Provenance(
        git_commit="abc123",
        git_dirty=False,
        python_version="3.11",
        platform="Windows-test",
        cpu="test-cpu",
        total_ram_bytes=1024,
        dependency_versions={"numpy": "1.0"},
        dataset_checksums={"data.csv": "checksum"},
        captured_at_utc="2026-09-19T00:00:00+00:00",
    )


def test_result_is_complete_only_after_marker(
    tmp_path: Path, config: ExperimentConfig, provenance: Provenance
) -> None:
    envelope = ResultEnvelope(
        config=config.canonical_dict(),
        provenance=provenance,
        metrics={"score": 0.5},
    )

    result_path = write_result_atomic(tmp_path, envelope)

    assert result_path.exists()
    assert result_path.with_suffix(".complete").exists()


def test_changed_dataset_checksum_prevents_resume(
    tmp_path: Path, config: ExperimentConfig, provenance: Provenance
) -> None:
    write_result_atomic(
        tmp_path,
        ResultEnvelope(config.canonical_dict(), provenance, {"score": 0.5}),
    )
    changed = dataclasses.replace(
        provenance, dataset_checksums={"data.csv": "different"}
    )

    assert load_completed_result(tmp_path, config, changed) is None


def test_result_without_completion_marker_does_not_resume(
    tmp_path: Path, config: ExperimentConfig, provenance: Provenance
) -> None:
    path = write_result_atomic(
        tmp_path,
        ResultEnvelope(config.canonical_dict(), provenance, {"score": 0.5}),
    )
    path.with_suffix(".complete").unlink()

    assert load_completed_result(tmp_path, config, provenance) is None


def test_corrupt_completed_result_raises_integrity_error(
    tmp_path: Path, config: ExperimentConfig, provenance: Provenance
) -> None:
    path = write_result_atomic(
        tmp_path,
        ResultEnvelope(config.canonical_dict(), provenance, {"score": 0.5}),
    )
    path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(ResultIntegrityError, match="invalid result JSON"):
        load_completed_result(tmp_path, config, provenance)


def test_serialization_failure_creates_no_completion_marker(
    tmp_path: Path,
    config: ExperimentConfig,
    provenance: Provenance,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_serialization(*args: object, **kwargs: object) -> str:
        raise TypeError("cannot serialize")

    monkeypatch.setattr("experiments.io.json.dumps", fail_serialization)
    with pytest.raises(TypeError, match="cannot serialize"):
        write_result_atomic(
            tmp_path,
            ResultEnvelope(config.canonical_dict(), provenance, {"score": 0.5}),
        )

    assert not list(tmp_path.rglob("*.complete"))


def test_sha256_file_reads_complete_file(tmp_path: Path) -> None:
    path = tmp_path / "data.bin"
    path.write_bytes(b"abc" * 500_000)

    assert sha256_file(path) == (
        "206c8387a6fd09a951f4945cb98bd65ae2b9a59d4069f70e00a9d9acd7c86515"
    )


def test_completed_result_cannot_be_overwritten(tmp_path, config, provenance):
    envelope = ResultEnvelope(config.canonical_dict(), provenance, {"score": 0.5})
    path = write_result_atomic(tmp_path, envelope)
    original = path.read_bytes()
    with pytest.raises(ResultIntegrityError, match="already exists"):
        write_result_atomic(
            tmp_path, dataclasses.replace(envelope, metrics={"score": 0.9})
        )
    assert path.read_bytes() == original
    assert load_completed_result(tmp_path, config, provenance).metrics == {"score": 0.5}


def test_valid_json_tampering_is_detected(tmp_path, config, provenance):
    path = write_result_atomic(
        tmp_path, ResultEnvelope(config.canonical_dict(), provenance, {"score": 0.5})
    )
    path.write_text(path.read_text().replace("0.5", "0.9"), encoding="utf-8")
    with pytest.raises(ResultIntegrityError, match="checksum"):
        load_completed_result(tmp_path, config, provenance)


def test_environment_changes_prevent_resume(tmp_path, config, provenance):
    write_result_atomic(
        tmp_path, ResultEnvelope(config.canonical_dict(), provenance, {"score": 0.5})
    )
    changed = dataclasses.replace(provenance, dependency_versions={"numpy": "2.0"})
    assert load_completed_result(tmp_path, config, changed) is None


def test_dirty_source_changes_have_distinct_identities(tmp_path, monkeypatch):
    import subprocess
    from experiments.provenance import capture_provenance

    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "--allow-empty",
            "-m",
            "fixture",
        ],
        check=True,
        capture_output=True,
    )
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "model.py"
    source.write_text("score = 1\n")
    first = capture_provenance([])
    source.write_text("score = 2\n")
    second = capture_provenance([])
    assert first.identity_hash != second.identity_hash
    assert first.git_dirty and second.git_dirty
