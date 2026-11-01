"""Tests for the LaTeX/markdown table renderer used by the paper."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

RENDERER = (
    Path(__file__).resolve().parents[2]
    / "paper"
    / "scripts"
    / "render_calibrated_tables.py"
)
FEATURES = 20


def _load_renderer():
    spec = importlib.util.spec_from_file_location("render_calibrated_tables", RENDERER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def summary(tmp_path_factory) -> dict:
    from experiments.calibrated_study import run_study

    output = tmp_path_factory.mktemp("study")
    run_study(
        output / "run",
        null_trials=1,
        seeds=(101,),
        n_permutations=49,
        include_real=False,
        trials=1,
    )
    return json.loads((output / "run" / "summary.json").read_text(encoding="utf-8"))


def test_localization_table_renders_both_formats(summary: dict) -> None:
    renderer = _load_renderer()

    md, tex = renderer._localization_table(summary)

    markdown = "\n".join(md)
    latex = "\n".join(tex)
    assert "| dataset | condition | chance |" in markdown
    assert "Peeling" in markdown
    # The no-injection cell belongs to the error-rate table, not this one.
    assert "null" not in {line.split("|")[2].strip() for line in md[2:] if line}
    assert latex.count(r"\begin{table*}") == latex.count(r"\end{table*}")
    assert latex.count(r"\toprule") == latex.count(r"\bottomrule")


def test_copula_and_pearson_are_labelled_separately() -> None:
    renderer = _load_renderer()

    assert renderer.LOC_LABELS["copula_asymptotic"] == "Copula"
    assert renderer.LOC_LABELS["pearson_asymptotic"] == "Pearson"
    assert renderer.NULL_LABELS["copula_asymptotic"].startswith("Copula (")
    assert renderer.NULL_LABELS["pearson_asymptotic"] == "Pearson (raw)"
    assert "copula_asymptotic" in renderer.LOC_METHODS
    assert "copula_asymptotic" in renderer.NULL_METHODS


def test_chance_line_comes_from_the_recorded_feature_count(summary: dict) -> None:
    renderer = _load_renderer()

    assert summary["localization"]["d"] == FEATURES
    assert renderer._uniform_recall(summary) == pytest.approx(3 / FEATURES)


def test_uniform_recall_rejects_a_summary_without_a_dimension() -> None:
    renderer = _load_renderer()

    with pytest.raises(ValueError, match="neither"):
        renderer._uniform_recall({"localization": {}})


def test_render_writes_tex_and_markdown(summary: dict, tmp_path) -> None:
    renderer = _load_renderer()
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    md_path = renderer.main(
        ["--summary", str(summary_path), "--out-prefix", str(tmp_path / "calibrated")]
    )
    tex_path = md_path.with_suffix(".tex")

    assert md_path.exists() and tex_path.exists()
    assert "## Null calibration" in md_path.read_text(encoding="utf-8")
    tex = tex_path.read_text(encoding="utf-8")
    assert tex.count(r"\begin{table*}") == tex.count(r"\end{table*}")
    assert r"\label{tab:null-calibration}" in tex
    assert r"\label{tab:localization}" in tex


def test_significance_table_uses_holm_and_recorded_alpha(summary: dict) -> None:
    renderer = _load_renderer()

    md, tex = renderer._significance_table(summary)

    assert md and tex
    assert any("Holm p" in line for line in md[:2])
