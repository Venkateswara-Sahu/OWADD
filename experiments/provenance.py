from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from importlib import metadata
import json
from pathlib import Path
import platform as platform_module
import subprocess
import sys
from typing import Sequence

import psutil


@dataclass(frozen=True)
class Provenance:
    """Environment and data identity associated with one result."""

    git_commit: str
    git_dirty: bool
    python_version: str
    platform: str
    cpu: str
    total_ram_bytes: int
    dependency_versions: dict[str, str]
    dataset_checksums: dict[str, str]
    captured_at_utc: str

    def canonical_dict(self, *, include_timestamp: bool = True) -> dict[str, object]:
        values = asdict(self)
        if not include_timestamp:
            values.pop("captured_at_utc")
        return values

    @property
    def identity_hash(self) -> str:
        identity = {
            "git_commit": self.git_commit,
            "dataset_checksums": self.dataset_checksums,
        }
        payload = json.dumps(identity, sort_keys=True, separators=(",", ":"))
        return sha256(payload.encode("utf-8")).hexdigest()[:16]


def sha256_file(path: Path) -> str:
    """Hash a file without loading it fully into memory."""

    digest = sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _git_output(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def capture_provenance(dataset_paths: Sequence[Path]) -> Provenance:
    """Capture reproducibility metadata for the current process and datasets."""

    dependencies: dict[str, str] = {}
    for package in ("numpy", "pandas", "scipy", "scikit-learn", "torch"):
        try:
            dependencies[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            dependencies[package] = "not-installed"

    checksums = {
        str(path.resolve()): sha256_file(path)
        for path in sorted(dataset_paths, key=lambda item: str(item.resolve()))
    }
    return Provenance(
        git_commit=_git_output("rev-parse", "HEAD"),
        git_dirty=bool(_git_output("status", "--porcelain")),
        python_version=platform_module.python_version(),
        platform=platform_module.platform(),
        cpu=platform_module.processor() or "unknown",
        total_ram_bytes=int(psutil.virtual_memory().total),
        dependency_versions=dependencies,
        dataset_checksums=checksums,
        captured_at_utc=datetime.now(timezone.utc).isoformat(),
    )
