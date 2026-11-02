"""Vigil Signal Observatory — Interactive Drift & Attribution Workbench.

Bespoke research and operations dashboard for `vigil-drift` (v0.1.5), aligned
with the design system of `docs/index.html`:
  01 / LIVE TELEMETRY     — Real-time NSL-KDD stream monitoring with dual-AE
                            severity, KDE novelty, and Marginal vs. Relational
                            pathway attribution.
  02 / EDGE-PEELING LAB   — Controlled window-pair sandbox comparing asymptotic
                            Decomposed Copula-KS against Westfall-Young
                            permutation-calibrated greedy edge peeling.
  03 / BENCHMARK EVIDENCE — Interactive explorer for the paper's provenance-
                            locked calibration, block-null, and power studies.

Run from the repository root:
  streamlit run dashboard/app.py
"""

from __future__ import annotations

import html
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from scipy import stats

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import vigil  # noqa: E402
from data.nsl_kdd_loader import (  # noqa: E402
    get_nsl_kdd_feature_groups,
    load_nsl_kdd,
)
from data.stream_simulator import StreamSimulator  # noqa: E402
from vigil import Vigil  # noqa: E402
from vigil.attribution import compute_decomposed_scores  # noqa: E402
from vigil.calibration import compute_calibrated_scores  # noqa: E402

# ─────────────────────────────────────────────
# Observatory palette & constants (docs/index.html)
# ─────────────────────────────────────────────

BG_COLOR = "#101716"
PANEL_COLOR = "#17211f"
INSET_COLOR = "#0c1210"
LINE_COLOR = "#354640"
GRID_COLOR = "#22302b"
INK_COLOR = "#f1f0e9"
MUTED_COLOR = "#a9bbb5"
MINT_ACCENT = "#a1e6cf"
CORAL_ACCENT = "#f07167"
AMBER_ACCENT = "#e9c46a"
SLATE_ACCENT = "#587068"
DARK_INK = "#12241d"

FONT_MONO = "JetBrains Mono, Consolas, Liberation Mono, monospace"
FONT_SANS = "Inter, Segoe UI, Arial, sans-serif"

DRIFT_ALERT_THRESHOLD = 0.30
NOVELTY_ALERT_THRESHOLD = 0.15
NOMINAL_ALPHA = 0.05
ASYMPTOTIC_EVIDENCE_CUTOFF = float(-np.log10(NOMINAL_ALPHA))
BASELINE_FIT_ROWS = 1000
CHUNK_SIZE = 200
TOP_K_DISPLAY = 8
LAB_FEATURES = 20
LAB_TARGET_PAIR = (0, 1)
LAB_TOP_RANK_DISPLAY = 6
MIN_CORR_SAMPLES = 4
SD_FLOOR = 1e-12
PVAL_CLIP_MIN = 1e-6
ZERO_INFLATION_PROB = 0.62
MAX_LOG_LINES = 60

BRAND_SVG = (
    '<svg viewBox="0 0 28 32" width="24" height="28" fill="none" '
    'aria-hidden="true">'
    '<path d="M3 3h7l4 17 4-17h7L14 29 3 3Z" stroke="#a1e6cf" '
    'stroke-width="1.6"/>'
    '<path d="M1 15h8m10 0h8" stroke="#a1e6cf" stroke-width="1.2"/>'
    "</svg>"
)

OBSERVATORY_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {{
  --bg: {BG_COLOR};
  --panel: {PANEL_COLOR};
  --inset: {INSET_COLOR};
  --line: {LINE_COLOR};
  --ink: {INK_COLOR};
  --muted: {MUTED_COLOR};
  --accent: {MINT_ACCENT};
  --coral: {CORAL_ACCENT};
  --amber: {AMBER_ACCENT};
}}

html, body, [data-testid="stAppViewContainer"], .stApp {{
  background-color: {BG_COLOR} !important;
  color: {INK_COLOR} !important;
  font-family: {FONT_SANS};
}}

#MainMenu, footer, [data-testid="stDecoration"] {{
  display: none !important;
}}

header[data-testid="stHeader"] {{
  background: transparent !important;
}}

.block-container {{
  padding-top: 1.4rem !important;
  padding-bottom: 3rem !important;
  max-width: 1380px !important;
}}

section[data-testid="stSidebar"] {{
  background-color: {INSET_COLOR} !important;
  border-right: 1px solid {LINE_COLOR} !important;
}}

section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span {{
  color: {INK_COLOR};
}}

.vigil-masthead {{
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 18px 22px;
  background: linear-gradient(145deg, #192622, {PANEL_COLOR});
  border: 1px solid {LINE_COLOR};
  border-radius: 8px;
  margin-bottom: 14px;
}}

.vigil-brand-row {{
  display: flex;
  align-items: center;
  gap: 14px;
}}

.vigil-wordmark {{
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -1px;
  color: {INK_COLOR};
  line-height: 1;
}}

.vigil-wordmark span {{
  color: {MINT_ACCENT};
}}

.vigil-subtitle {{
  font-size: 13px;
  color: {MUTED_COLOR};
  margin-top: 4px;
}}

.vigil-pill-group {{
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}}

.vigil-pill {{
  font-family: {FONT_MONO};
  font-size: 11px;
  letter-spacing: 0.6px;
  text-transform: uppercase;
  padding: 6px 11px;
  border: 1px solid {LINE_COLOR};
  border-radius: 4px;
  background: {INSET_COLOR};
  color: {MUTED_COLOR};
}}

.vigil-pill strong {{
  color: {MINT_ACCENT};
  font-weight: 500;
}}

.telemetry-strip {{
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  border: 1px solid {LINE_COLOR};
  border-radius: 8px;
  overflow: hidden;
  background: {PANEL_COLOR};
  margin-bottom: 20px;
}}

.telemetry-cell {{
  padding: 15px 18px;
  border-right: 1px solid {LINE_COLOR};
  min-width: 0;
}}

.telemetry-cell:last-child {{
  border-right: none;
}}

.telemetry-eyebrow {{
  font-family: {FONT_MONO};
  font-size: 10px;
  letter-spacing: 1.3px;
  text-transform: uppercase;
  color: {MUTED_COLOR};
  margin-bottom: 7px;
}}

.telemetry-value {{
  font-family: {FONT_MONO};
  font-size: 21px;
  font-weight: 600;
  letter-spacing: -0.6px;
  color: {INK_COLOR};
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}

.telemetry-sub {{
  font-family: {FONT_MONO};
  font-size: 11px;
  color: {MUTED_COLOR};
  margin-top: 4px;
}}

.status-dot {{
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  margin-right: 8px;
  vertical-align: middle;
}}

.section-header {{
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  border-bottom: 1px solid {LINE_COLOR};
  padding-bottom: 8px;
  margin: 8px 0 12px 0;
}}

.section-eyebrow {{
  font-family: {FONT_MONO};
  font-size: 11px;
  letter-spacing: 1.4px;
  text-transform: uppercase;
  color: {MINT_ACCENT};
}}

.section-note {{
  font-family: {FONT_MONO};
  font-size: 11px;
  color: {MUTED_COLOR};
}}

.sidebar-eyebrow {{
  font-family: {FONT_MONO};
  font-size: 10px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: {MINT_ACCENT};
  border-bottom: 1px solid {LINE_COLOR};
  padding-bottom: 6px;
  margin: 16px 0 10px 0;
}}

.signal-ledger {{
  background: {INSET_COLOR};
  border: 1px solid {LINE_COLOR};
  border-radius: 6px;
  padding: 13px 15px;
  height: 235px;
  overflow-y: auto;
  font-family: {FONT_MONO};
  font-size: 11.5px;
  line-height: 1.65;
}}

.ledger-row {{
  border-bottom: 1px solid #1b2723;
  padding: 3px 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}

.diagnostic-banner {{
  background: {PANEL_COLOR};
  border: 1px solid {LINE_COLOR};
  border-left: 3px solid {MINT_ACCENT};
  border-radius: 6px;
  padding: 12px 16px;
  font-size: 12.5px;
  color: {MUTED_COLOR};
  margin: 8px 0 14px 0;
}}

.diagnostic-banner strong {{
  color: {INK_COLOR};
}}

div[data-testid="stTabs"] button[data-baseweb="tab"] {{
  font-family: {FONT_MONO} !important;
  font-size: 11.5px !important;
  letter-spacing: 1.1px !important;
  text-transform: uppercase !important;
  color: {MUTED_COLOR} !important;
  padding: 10px 18px !important;
}}

div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {{
  color: {MINT_ACCENT} !important;
}}

div.stButton > button {{
  font-family: {FONT_MONO} !important;
  font-size: 11.5px !important;
  letter-spacing: 0.7px !important;
  text-transform: uppercase !important;
  border-radius: 5px !important;
  border: 1px solid {LINE_COLOR} !important;
  background-color: {PANEL_COLOR} !important;
  color: {INK_COLOR} !important;
}}

div.stButton > button[kind="primary"] {{
  background-color: {MINT_ACCENT} !important;
  border-color: {MINT_ACCENT} !important;
  color: {DARK_INK} !important;
  font-weight: 600 !important;
}}

div.stButton > button:hover {{
  border-color: {MINT_ACCENT} !important;
}}

@media (max-width: 960px) {{
  .telemetry-strip {{
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }}
}}
</style>
"""


# ─────────────────────────────────────────────
# Configuration & state dataclasses
# ─────────────────────────────────────────────


@dataclass(frozen=True)
class StreamConfig:
    """Sidebar parameters controlling the live NSL-KDD stream."""

    chunk_delay: float
    n_total: int
    drift_at: int
    novelty_at: int
    attribution_mode: str
    adaptation_mode: str
    use_feature_groups: bool
    n_permutations: int
    block_size: int


@dataclass(frozen=True)
class LabConfig:
    """Parameters for a controlled window-pair attribution experiment."""

    population: str
    shift_regime: str
    window_size: int
    n_permutations: int
    block_size: int
    seed: int


# ─────────────────────────────────────────────
# Cached data & artifact loaders
# ─────────────────────────────────────────────


@st.cache_resource(show_spinner=False)
def load_cached_nsl_kdd() -> tuple[
    np.ndarray, np.ndarray, list[str], dict[str, tuple[int, ...]]
]:
    """Load NSL-KDD features, labels, names, and logical one-hot groups once."""
    x_data, y_labels, feature_names = load_nsl_kdd(
        split="train", fit_normal_only=True
    )
    raw_groups = get_nsl_kdd_feature_groups(feature_names)
    tuple_groups = {name: tuple(idxs) for name, idxs in raw_groups.items()}
    return x_data, y_labels, feature_names, tuple_groups


@st.cache_data(show_spinner=False)
def load_paper_artifacts() -> dict[str, Any]:
    """Load provenance-locked benchmark JSONs from `artifacts/` if present."""
    runs_dir = ROOT_DIR / "artifacts/runs"
    paths = {
        "study_v3": runs_dir / "calibrated-study-v3/summary.json",
        "blocknull_v2": runs_dir / "calibrated-blocknull-v2/summary.json",
        "power_w400": runs_dir / "calibrated-power-v1/power.json",
        "power_w800": runs_dir / "calibrated-power-w800/power.json",
        "power_w1600": runs_dir / "calibrated-power-w1600/power.json",
        "cost": ROOT_DIR / "artifacts/benchmarks/calibrated_cost.json",
    }
    loaded: dict[str, Any] = {}
    for key, path in paths.items():
        if path.exists():
            loaded[key] = json.loads(path.read_text(encoding="utf-8"))
    return loaded


# ─────────────────────────────────────────────
# Shared Plotly layout helper
# ─────────────────────────────────────────────


def apply_observatory_layout(
    fig: go.Figure,
    *,
    height: int,
    margin: dict[str, int] | None = None,
) -> go.Figure:
    """Apply consistent `docs/index.html` dark pine-slate styling to Plotly."""
    fig.update_layout(
        paper_bgcolor=PANEL_COLOR,
        plot_bgcolor=BG_COLOR,
        font={"family": FONT_MONO, "color": INK_COLOR, "size": 11},
        height=height,
        margin=margin or {"l": 52, "r": 28, "t": 34, "b": 42},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0.0,
            "bgcolor": "rgba(0,0,0,0)",
            "font": {"size": 10.5, "color": MUTED_COLOR},
        },
        hoverlabel={
            "bgcolor": INSET_COLOR,
            "bordercolor": LINE_COLOR,
            "font": {"family": FONT_MONO, "size": 11, "color": INK_COLOR},
        },
    )
    fig.update_xaxes(
        gridcolor=GRID_COLOR,
        linecolor=LINE_COLOR,
        zerolinecolor=GRID_COLOR,
        tickfont={"color": MUTED_COLOR, "size": 10},
    )
    fig.update_yaxes(
        gridcolor=GRID_COLOR,
        linecolor=LINE_COLOR,
        zerolinecolor=GRID_COLOR,
        tickfont={"color": MUTED_COLOR, "size": 10},
    )
    return fig


def render_section_header(eyebrow: str, note: str = "") -> None:
    """Render an uppercase monospace section divider."""
    safe_eyebrow = html.escape(eyebrow)
    safe_note = html.escape(note)
    st.markdown(
        f'<div class="section-header">'
        f'<span class="section-eyebrow">{safe_eyebrow}</span>'
        f'<span class="section-note">{safe_note}</span>'
        f"</div>",
        unsafe_allow_html=True,
    )


def _max_ref_corr(meta: dict[str, Any]) -> float:
    """Extract peak reference correlation scalar from scalar or per-col list."""
    raw = meta.get("max_abs_ref_corr")
    if raw is None:
        return 0.0
    arr = np.asarray(raw, dtype=float)
    return float(np.nanmax(arr)) if arr.size else 0.0


# ─────────────────────────────────────────────
# Stream state management (Workspace 01)
# ─────────────────────────────────────────────


def default_stream_state() -> dict[str, Any]:
    """Return a clean session-state dictionary for the live stream."""
    return {
        "status": "STANDBY",
        "config_signature": None,
        "sentinel": None,
        "chunks_list": [],
        "cursor": 0,
        "chunk_ids": [],
        "batch_errors": [],
        "ref_errors": [],
        "severities": [],
        "novelties": [],
        "drift_flags": [],
        "dominant_classes": [],
        "latest_attribution": None,
        "latest_chunk_id": None,
        "dominant_regime": "baseline",
        "logs": [],
        "n_drifts": 0,
        "n_novelties": 0,
    }


def ensure_stream_state() -> dict[str, Any]:
    """Initialise `st.session_state.observatory` on first render."""
    if "observatory" not in st.session_state:
        st.session_state.observatory = default_stream_state()
    return st.session_state.observatory


def prepare_stream_engine(cfg: StreamConfig) -> None:
    """Fit `Vigil` on normal NSL-KDD traffic and pre-materialize stream chunks."""
    obs = ensure_stream_state()
    sig = (
        cfg.n_total,
        cfg.drift_at,
        cfg.novelty_at,
        cfg.attribution_mode,
        cfg.adaptation_mode,
        cfg.use_feature_groups,
        cfg.n_permutations,
        cfg.block_size,
    )
    if obs["sentinel"] is not None and obs["config_signature"] == sig:
        return

    x_data, y_labels, feature_names, tuple_groups = load_cached_nsl_kdd()
    normal_mask = y_labels == "normal"
    x_baseline = x_data[normal_mask][:BASELINE_FIT_ROWS]

    sentinel = Vigil(
        feature_names=feature_names,
        top_k_features=TOP_K_DISPLAY,
        initial_epochs=200,
        update_epochs=30,
        attribution_mode=cfg.attribution_mode,
        adaptation_mode=cfg.adaptation_mode,
        feature_groups=tuple_groups if cfg.use_feature_groups else None,
        n_permutations=cfg.n_permutations,
        block_size=cfg.block_size,
        seed=42,
    )
    sentinel.fit(x_baseline, verbose=False)

    sim = StreamSimulator(
        x_data,
        y_labels,
        chunk_size=CHUNK_SIZE,
        drift_after_chunk=cfg.drift_at,
        novelty_after_chunk=cfg.novelty_at,
        novelty_proportion=0.25,
        seed=42,
    )
    chunks = list(sim.stream(n_chunks=cfg.n_total))

    fresh = default_stream_state()
    fresh["config_signature"] = sig
    fresh["sentinel"] = sentinel
    fresh["chunks_list"] = chunks
    fresh["status"] = "READY"
    fresh["logs"].append(
        {
            "level": "info",
            "text": (
                f"[{time.strftime('%H:%M:%S')}] BASELINE FIT · "
                f"n={len(x_baseline)} normal flows · d={x_baseline.shape[1]} · "
                f"mode={cfg.attribution_mode}"
            ),
        }
    )
    st.session_state.observatory = fresh


def process_next_chunk() -> bool:
    """Evaluate one chunk from the stream queue; return True if a chunk ran."""
    obs = ensure_stream_state()
    cursor = int(obs["cursor"])
    chunks = obs["chunks_list"]
    sentinel: Vigil | None = obs["sentinel"]
    if sentinel is None or cursor >= len(chunks):
        obs["status"] = "COMPLETE"
        return False

    chunk = chunks[cursor]
    result = sentinel.detect(chunk.X)
    obs["cursor"] = cursor + 1
    obs["chunk_ids"].append(chunk.chunk_id)
    obs["batch_errors"].append(float(result.drift_result.batch_error_mean))
    obs["ref_errors"].append(float(result.drift_result.reference_error_mean))
    obs["severities"].append(float(result.drift_severity))
    obs["novelties"].append(float(result.novelty_proportion))
    obs["drift_flags"].append(bool(result.drift_detected))
    obs["dominant_classes"].append(str(chunk.dominant_class))

    is_novel = result.novelty_proportion > NOVELTY_ALERT_THRESHOLD
    if is_novel:
        obs["n_novelties"] += 1

    ts = time.strftime("%H:%M:%S")
    if result.drift_detected and result.attribution is not None:
        obs["n_drifts"] += 1
        obs["latest_attribution"] = result.attribution
        obs["latest_chunk_id"] = chunk.chunk_id
        regime = str(
            result.attribution.metadata.get(
                "dominant_drift_regime", "reconstruction"
            )
        )
        obs["dominant_regime"] = regime
        obs["status"] = "DRIFT ALERT"
        lead_feat = (
            result.attribution.top_features[0]["feature_name"]
            if result.attribution.top_features
            else "n/a"
        )
        verdict = "DRIFT+NOVEL" if is_novel else "DRIFT"
        level = "drift"
        detail = (
            f"sev={result.drift_severity:.2f} · nov={result.novelty_proportion:.1%} · "
            f"regime={regime} · top={lead_feat} · gt={chunk.dominant_class}"
        )
    elif is_novel:
        obs["status"] = "NOVELTY ALERT"
        verdict = "NOVELTY"
        level = "novel"
        detail = (
            f"sev={result.drift_severity:.2f} · nov={result.novelty_proportion:.1%} · "
            f"gt={chunk.dominant_class}"
        )
    else:
        obs["status"] = "MONITORING"
        verdict = "STABLE"
        level = "ok"
        detail = (
            f"sev={result.drift_severity:.2f} · nov={result.novelty_proportion:.1%} · "
            f"gt={chunk.dominant_class}"
        )

    obs["logs"].insert(
        0,
        {
            "level": level,
            "text": f"[{ts}] CHUNK {chunk.chunk_id:02d} · {verdict:<11s} · {detail}",
        },
    )
    del obs["logs"][MAX_LOG_LINES:]
    if obs["cursor"] >= len(chunks):
        obs["status"] = "COMPLETE"
    return True


# ─────────────────────────────────────────────
# Masthead & 5-cell telemetry strip
# ─────────────────────────────────────────────


def render_masthead_and_strip(cfg: StreamConfig, obs: dict[str, Any]) -> None:
    """Render the `docs/index.html` brand bar and 5-column telemetry strip."""
    mode_badge = cfg.attribution_mode.upper()
    if cfg.attribution_mode == "calibrated":
        mode_badge = f"CALIBRATED (B={cfg.n_permutations}, L={cfg.block_size})"

    ver_txt = html.escape(vigil.__version__)
    mode_txt = html.escape(mode_badge)
    adapt_txt = html.escape(cfg.adaptation_mode.upper())
    col_txt = "41 LOGICAL GROUPS" if cfg.use_feature_groups else "122 RAW"

    st.markdown(
        f"""
        <div class="vigil-masthead">
          <div class="vigil-brand-row">
            {BRAND_SVG}
            <div>
              <div class="vigil-wordmark">vigil<span>.</span></div>
              <div class="vigil-subtitle">
                Signal Observatory · Drift, Novelty &amp; Copula-KS Attribution
              </div>
            </div>
          </div>
          <div class="vigil-pill-group">
            <span class="vigil-pill">PKG <strong>v{ver_txt}</strong></span>
            <span class="vigil-pill">MODE <strong>{mode_txt}</strong></span>
            <span class="vigil-pill">POLICY <strong>{adapt_txt}</strong></span>
            <span class="vigil-pill">COLS <strong>{col_txt}</strong></span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    state_label = html.escape(str(obs["status"]))
    dot_color = SLATE_ACCENT
    if obs["status"] == "DRIFT ALERT":
        dot_color = CORAL_ACCENT
    elif obs["status"] == "NOVELTY ALERT":
        dot_color = AMBER_ACCENT
    elif obs["status"] in ("MONITORING", "READY", "COMPLETE"):
        dot_color = MINT_ACCENT

    n_seen = len(obs["chunk_ids"])
    last_sev = obs["severities"][-1] if obs["severities"] else 0.0
    last_nov = obs["novelties"][-1] if obs["novelties"] else 0.0
    regime_txt = html.escape(str(obs["dominant_regime"]).upper())
    drift_col = CORAL_ACCENT if obs["n_drifts"] else INK_COLOR
    novel_col = AMBER_ACCENT if obs["n_novelties"] else INK_COLOR
    onset_sub = f"onset: c{cfg.drift_at:02d} drift · c{cfg.novelty_at:02d} novel"

    dot_html = f'<span class="status-dot" style="background:{dot_color}"></span>'
    st.markdown(
        f"""
        <div class="telemetry-strip">
          <div class="telemetry-cell">
            <div class="telemetry-eyebrow">01 / Stream State</div>
            <div class="telemetry-value">{dot_html}{state_label}</div>
            <div class="telemetry-sub">NSL-KDD · {CHUNK_SIZE} rows/batch</div>
          </div>
          <div class="telemetry-cell">
            <div class="telemetry-eyebrow">02 / Batches Observed</div>
            <div class="telemetry-value">{n_seen:02d} / {cfg.n_total:02d}</div>
            <div class="telemetry-sub">{onset_sub}</div>
          </div>
          <div class="telemetry-cell">
            <div class="telemetry-eyebrow">03 / Drift Rejections</div>
            <div class="telemetry-value" style="color:{drift_col}">
              {obs['n_drifts']:02d}
            </div>
            <div class="telemetry-sub">welch sev = {last_sev:.2f} (thr 0.30)</div>
          </div>
          <div class="telemetry-cell">
            <div class="telemetry-eyebrow">04 / Novelty Alerts</div>
            <div class="telemetry-value" style="color:{novel_col}">
              {obs['n_novelties']:02d}
            </div>
            <div class="telemetry-sub">latest kde outlier = {last_nov:.1%}</div>
          </div>
          <div class="telemetry-cell">
            <div class="telemetry-eyebrow">05 / Dominant Pathway</div>
            <div class="telemetry-value" style="color:{MINT_ACCENT}">
              {regime_txt}
            </div>
            <div class="telemetry-sub">diagnostic score · non-causal</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# Workspace 01 charts: Timeline, Split Attribution, Novelty + Ledger
# ─────────────────────────────────────────────


def build_stream_timeline_figure(
    obs: dict[str, Any], cfg: StreamConfig
) -> go.Figure:
    """Create the dual-axis AE reconstruction error + Welch severity chart."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    cids = obs["chunk_ids"]

    if cids:
        max_cid = max(max(cids), cfg.n_total - 1)
        if max_cid >= cfg.drift_at:
            fig.add_vrect(
                x0=cfg.drift_at - 0.5,
                x1=min(cfg.novelty_at - 0.5, max_cid + 0.5),
                fillcolor="rgba(240, 113, 103, 0.06)",
                line_width=0,
                annotation_text="KNOWN ATTACK REGIME",
                annotation_position="top left",
                annotation_font={"size": 9, "color": CORAL_ACCENT},
            )
        if max_cid >= cfg.novelty_at:
            fig.add_vrect(
                x0=cfg.novelty_at - 0.5,
                x1=max_cid + 0.5,
                fillcolor="rgba(233, 196, 106, 0.07)",
                line_width=0,
                annotation_text="NOVEL CLASS REGIME",
                annotation_position="top left",
                annotation_font={"size": 9, "color": AMBER_ACCENT},
            )

        fig.add_trace(
            go.Scatter(
                x=cids,
                y=obs["ref_errors"],
                name="Reference AE MSE",
                mode="lines",
                line={"color": MUTED_COLOR, "width": 1.5, "dash": "dot"},
            ),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=cids,
                y=obs["batch_errors"],
                name="Current Batch AE MSE",
                mode="lines+markers",
                line={"color": MINT_ACCENT, "width": 2.2},
                marker={"size": 5, "color": MINT_ACCENT},
                fill="tozeroy",
                fillcolor="rgba(161, 230, 207, 0.09)",
            ),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=cids,
                y=obs["severities"],
                name="Welch Drift Severity",
                mode="lines+markers",
                line={"color": CORAL_ACCENT, "width": 1.8},
                marker={
                    "size": [9 if flg else 4 for flg in obs["drift_flags"]],
                    "color": [
                        CORAL_ACCENT if flg else SLATE_ACCENT
                        for flg in obs["drift_flags"]
                    ],
                },
            ),
            secondary_y=True,
        )
        fig.add_hline(
            y=DRIFT_ALERT_THRESHOLD,
            line_dash="dash",
            line_color=CORAL_ACCENT,
            line_width=1.0,
            opacity=0.65,
            secondary_y=True,
        )
    else:
        fig.add_annotation(
            text="STANDBY · PRESS [RUN STREAM] OR [STEP +1 BATCH] IN SIDEBAR",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font={"size": 12, "color": MUTED_COLOR},
        )

    apply_observatory_layout(
        fig, height=315, margin={"l": 56, "r": 56, "t": 36, "b": 40}
    )
    fig.update_xaxes(title_text="STREAM BATCH INDEX")
    fig.update_yaxes(title_text="RECONSTRUCTION MSE", secondary_y=False)
    fig.update_yaxes(
        title_text="WELCH SEVERITY [0-1]",
        range=[0.0, 1.08],
        secondary_y=True,
        showgrid=False,
    )
    return fig


def build_pathway_attribution_figure(
    obs: dict[str, Any],
    cfg: StreamConfig,
    tuple_groups: dict[str, tuple[int, ...]],
) -> tuple[go.Figure, str]:
    """Create the Marginal (KS) vs. Relational (Copula) attribution bar chart."""
    attr = obs["latest_attribution"]
    fig = go.Figure()
    if attr is None:
        fig.add_annotation(
            text="AWAITING DRIFT REJECTION TO COMPUTE FEATURE EVIDENCE",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font={"size": 11, "color": MUTED_COLOR},
        )
        apply_observatory_layout(fig, height=345)
        return fig, "no drift event yet"

    meta = attr.metadata
    marg_raw = meta.get("marginal_evidence")
    rel_raw = meta.get("relational_evidence")
    has_pathways = isinstance(marg_raw, list) and isinstance(rel_raw, list)

    if has_pathways:
        marg_arr = np.asarray(marg_raw, dtype=float)
        rel_arr = np.asarray(rel_raw, dtype=float)
        if cfg.use_feature_groups and "grouped_top_features" in meta:
            rows = []
            for grp in meta["grouped_top_features"][:TOP_K_DISPLAY]:
                gname = str(grp["group_name"])
                g_idx = list(tuple_groups.get(gname, ()))
                m_val = float(marg_arr[g_idx].max()) if g_idx else 0.0
                r_val = float(rel_arr[g_idx].max()) if g_idx else 0.0
                ncols = int(grp["n_columns"])
                label = f"{gname} ({ncols}c)" if ncols > 1 else gname
                rows.append((label, m_val, r_val))
        else:
            rows = [
                (
                    str(item["feature_name"]),
                    float(marg_arr[int(item["feature_index"])]),
                    float(rel_arr[int(item["feature_index"])]),
                )
                for item in attr.top_features[:TOP_K_DISPLAY]
            ]

        rows.reverse()
        labels = [r[0] for r in rows]
        m_vals = [r[1] for r in rows]
        r_vals = [r[2] for r in rows]

        fig.add_trace(
            go.Bar(
                y=labels,
                x=m_vals,
                name="Marginal KS (-log10 p)",
                orientation="h",
                marker_color=MINT_ACCENT,
            )
        )
        fig.add_trace(
            go.Bar(
                y=labels,
                x=r_vals,
                name="Relational Copula (-log10 p)",
                orientation="h",
                marker_color=CORAL_ACCENT,
            )
        )
        fig.update_layout(barmode="group")
        fig.update_xaxes(title_text="PATHWAY LOG10 EVIDENCE")
    else:
        source_items = (
            meta.get("grouped_top_features", [])
            if cfg.use_feature_groups and "grouped_top_features" in meta
            else attr.top_features
        )
        items = list(source_items[:TOP_K_DISPLAY])[::-1]
        labels = [
            str(it.get("group_name", it.get("feature_name", "?"))) for it in items
        ]
        shares = [float(it["contribution"]) * 100.0 for it in items]
        fig.add_trace(
            go.Bar(
                y=labels,
                x=shares,
                name="Normalized AE Delta (%)",
                orientation="h",
                marker_color=MINT_ACCENT,
            )
        )
        fig.update_xaxes(title_text="NORMALIZED CONTRIBUTION (%)")

    caption = f"chunk {obs['latest_chunk_id']:02d}"
    if "significant_features" in meta:
        n_sig = len(meta["significant_features"])
        max_corr = _max_ref_corr(meta)
        caption += f" · {n_sig} FWER-significant cols · max|R_ref|={max_corr:.2f}"

    apply_observatory_layout(
        fig, height=345, margin={"l": 145, "r": 24, "t": 34, "b": 42}
    )
    return fig, caption


def build_novelty_trace_figure(obs: dict[str, Any]) -> go.Figure:
    """Create a compact bar trace of KDE out-of-support novelty proportion."""
    fig = go.Figure()
    cids = obs["chunk_ids"]
    if cids:
        novs = [v * 100.0 for v in obs["novelties"]]
        colors = [
            AMBER_ACCENT if v > NOVELTY_ALERT_THRESHOLD * 100.0 else SLATE_ACCENT
            for v in novs
        ]
        fig.add_trace(
            go.Bar(
                x=cids,
                y=novs,
                name="KDE Outliers (%)",
                marker_color=colors,
            )
        )
        fig.add_hline(
            y=NOVELTY_ALERT_THRESHOLD * 100.0,
            line_dash="dot",
            line_color=AMBER_ACCENT,
            line_width=1.0,
        )
    else:
        fig.add_annotation(
            text="KDE NOVELTY TRACE IDLE",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font={"size": 10.5, "color": MUTED_COLOR},
        )
    apply_observatory_layout(
        fig, height=130, margin={"l": 48, "r": 18, "t": 14, "b": 28}
    )
    fig.update_yaxes(title_text="NOVEL %", range=[0, 100])
    fig.update_layout(showlegend=False)
    return fig


def render_signal_ledger(obs: dict[str, Any]) -> None:
    """Render the monospace terminal ledger for stream diagnostics."""
    if not obs["logs"]:
        body = (
            f'<div style="color:{MUTED_COLOR}">'
            "Awaiting telemetry batches. Configure parameters in the left rail."
            "</div>"
        )
    else:
        color_map = {
            "drift": CORAL_ACCENT,
            "novel": AMBER_ACCENT,
            "ok": MUTED_COLOR,
            "info": MINT_ACCENT,
        }
        lines = [
            f'<div class="ledger-row" '
            f'style="color:{color_map.get(entry["level"], MUTED_COLOR)}">'
            f'{html.escape(entry["text"])}</div>'
            for entry in obs["logs"]
        ]
        body = "".join(lines)
    st.markdown(f'<div class="signal-ledger">{body}</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Workspace 02: Controlled Edge-Peeling Lab
# ─────────────────────────────────────────────


def generate_lab_windows(
    cfg: LabConfig,
) -> tuple[np.ndarray, np.ndarray, tuple[int, ...], str]:
    """Synthesize `(X_ref, X_cur)` and ground-truth shifted indices."""
    rng = np.random.default_rng(cfg.seed)
    n = cfg.window_size
    d = LAB_FEATURES

    # Equicorrelated latent structure so correlation-destroying shifts have
    # realistic background partners (matching the paper's mechanism study).
    rho_bg = 0.45
    cov = np.full((d, d), rho_bg, dtype=float)
    np.fill_diagonal(cov, 1.0)
    chol = np.linalg.cholesky(cov)

    def sample_base(rows: int) -> np.ndarray:
        z = rng.standard_normal((rows, d)) @ chol.T
        if cfg.population == "multivariate_t3":
            chi = rng.chisquare(df=3.0, size=(rows, 1))
            return z / np.sqrt(chi / 3.0)
        if cfg.population == "zero_inflated_tied":
            zero_mask = rng.random((rows, d)) < ZERO_INFLATION_PROB
            quantized = np.round(np.exp(0.55 * z), 1)
            quantized[zero_mask] = 0.0
            return quantized
        return z

    x_ref = sample_base(n)
    x_cur = sample_base(n).copy()
    j0, j1 = LAB_TARGET_PAIR
    perturbed: tuple[int, ...] = (j0, j1)

    if cfg.shift_regime == "permute_k2":
        x_cur[:, j0] = rng.permutation(x_cur[:, j0])
        x_cur[:, j1] = rng.permutation(x_cur[:, j1])
        desc = (
            "Independently permuted columns f00 and f01: marginals stay identical, "
            "all background correlations with f00 and f01 break simultaneously."
        )
    elif cfg.shift_regime == "paircorr_0.8":
        shared = rng.standard_normal(n)
        x_cur[:, j0] = np.sqrt(0.82) * shared + np.sqrt(0.18) * rng.standard_normal(n)
        x_cur[:, j1] = np.sqrt(0.82) * shared + np.sqrt(0.18) * rng.standard_normal(n)
        desc = "Injected strong pairwise coupling (rho ~ 0.82) between f00 and f01."
    elif cfg.shift_regime == "mean_0.5":
        sd = np.maximum(x_ref[:, [j0, j1]].std(axis=0), SD_FLOOR)
        x_cur[:, [j0, j1]] += 0.5 * sd
        desc = "Shifted f00 and f01 upward by +0.5 reference SD across all rows."
    elif cfg.shift_regime == "scale_0.5":
        mu = x_ref[:, [j0, j1]].mean(axis=0)
        x_cur[:, [j0, j1]] = mu + 0.5 * (x_cur[:, [j0, j1]] - mu)
        desc = "Contracted variance of f00 and f01 by 0.5x around reference mean."
    elif cfg.shift_regime == "sparse20_mean_0.5":
        n_sub = max(1, int(0.20 * n))
        rows = rng.choice(n, size=n_sub, replace=False)
        sd = np.maximum(x_ref[:, [j0, j1]].std(axis=0), SD_FLOOR)
        x_cur[np.ix_(rows, [j0, j1])] += 0.5 * sd
        desc = (
            "Shifted f00 and f01 by +0.5 SD in only 20% of rows (illustrating the "
            "paper's sparse sub-population sensitivity trade-off)."
        )
    else:
        perturbed = ()
        desc = (
            "Null control (H0: P_ref == P_cur). Nothing injected; any rejection "
            "is a false alarm against the nominal 5% FWER budget."
        )

    return x_ref, x_cur, perturbed, desc


def _recall_at_k(scores: np.ndarray, targets: tuple[int, ...], k: int = 3) -> float:
    """Compute fraction of `targets` recovered in top-`k` indices of `scores`."""
    if not targets:
        return float("nan")
    order = np.argsort(-scores, kind="mergesort")[:k]
    hits = sum(1 for t in targets if t in set(order.tolist()))
    return hits / len(targets)


def _pearson_maxedge_scores(x_ref: np.ndarray, x_cur: np.ndarray) -> np.ndarray:
    """Compute raw sample Pearson `max_{k != j} |R_cur - R_ref|` baseline."""
    d = x_ref.shape[1]
    if len(x_ref) < MIN_CORR_SAMPLES or len(x_cur) < MIN_CORR_SAMPLES:
        return np.zeros(d, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        r_ref = np.nan_to_num(np.corrcoef(x_ref, rowvar=False), nan=0.0)
        r_cur = np.nan_to_num(np.corrcoef(x_cur, rowvar=False), nan=0.0)
    diff = np.abs(r_cur - r_ref)
    np.fill_diagonal(diff, 0.0)
    return diff.max(axis=1)


@st.cache_data(show_spinner=False)
def run_lab_experiment(cfg: LabConfig) -> dict[str, Any]:
    """Execute Decomposed, Calibrated Peeling, KS, and Pearson on one pair."""
    x_ref, x_cur, targets, desc = generate_lab_windows(cfg)
    feature_names = [f"f{idx:02d}" for idx in range(LAB_FEATURES)]

    t0 = time.perf_counter()
    dec_marg, dec_rel, dec_comb = compute_decomposed_scores(x_ref, x_cur)
    dec_ms = (time.perf_counter() - t0) * 1000.0

    t1 = time.perf_counter()
    cal = compute_calibrated_scores(
        x_ref,
        x_cur,
        n_permutations=cfg.n_permutations,
        alpha=NOMINAL_ALPHA,
        block_size=cfg.block_size,
        seed=cfg.seed,
    )
    cal_ms = (time.perf_counter() - t1) * 1000.0

    ks_scores = np.array(
        [
            float(stats.ks_2samp(x_ref[:, j], x_cur[:, j]).statistic)
            for j in range(LAB_FEATURES)
        ]
    )
    pearson_scores = _pearson_maxedge_scores(x_ref, x_cur)

    return {
        "feature_names": feature_names,
        "targets": targets,
        "description": desc,
        "dec_marg": dec_marg,
        "dec_rel": dec_rel,
        "dec_comb": dec_comb,
        "dec_ms": dec_ms,
        "dec_rejected": bool(np.max(dec_comb) >= ASYMPTOTIC_EVIDENCE_CUTOFF),
        "cal_scores": cal.combined_scores,
        "cal_marg_ev": cal.marginal_evidence,
        "cal_rel_ev": cal.relational_evidence,
        "cal_marg_p": cal.marginal_pvalues,
        "cal_edge_p": cal.edge_pvalues,
        "cal_peel_order": list(cal.peel_order),
        "cal_sig": cal.significant_features(),
        "cal_max_ref_corr": _max_ref_corr(cal.metadata),
        "cal_ms": cal_ms,
        "ks_scores": ks_scores,
        "pearson_scores": pearson_scores,
        "recall3": {
            "Calibrated Peeling": _recall_at_k(cal.combined_scores, targets, 3),
            "Decomposed Max-Edge": _recall_at_k(dec_comb, targets, 3),
            "Univariate KS": _recall_at_k(ks_scores, targets, 3),
            "Pearson |dR|": _recall_at_k(pearson_scores, targets, 3),
        },
    }


def render_lab_workspace() -> None:
    """Render Workspace 02: Interactive Attribution & Edge-Peeling Lab."""
    render_section_header(
        "02 / Controlled Window-Pair Attribution & Edge-Peeling Sandbox",
        "d = 20 features · ground-truth perturbed pair: (f00, f01)",
    )

    c1, c2, c3, c4, c5, c6 = st.columns([1.35, 1.55, 0.8, 0.85, 0.75, 0.75])
    pop_options = {
        "Multivariate t3 (heavy-tailed)": "multivariate_t3",
        "Zero-Inflated Tied (62% zeros)": "zero_inflated_tied",
        "Gaussian (equicorrelated)": "gaussian",
    }
    shift_options = {
        "Column Permutation (2 cols)": "permute_k2",
        "Null Control (No Shift / H0)": "null",
        "Small Mean Shift (+0.5 SD)": "mean_0.5",
        "Variance Contraction (x0.5 SD)": "scale_0.5",
        "Pairwise Coupling (rho=0.82)": "paircorr_0.8",
        "Sparse Mean (20% rows, +0.5 SD)": "sparse20_mean_0.5",
    }

    with c1:
        pop_label = st.selectbox("Base Population", list(pop_options.keys()), index=0)
    with c2:
        shift_label = st.selectbox(
            "Injected Regime", list(shift_options.keys()), index=0
        )
    with c3:
        win_n = st.selectbox("Window n", [200, 400, 800], index=1)
    with c4:
        n_perm = st.selectbox("Permutations B", [99, 199, 399], index=1)
    with c5:
        blk = st.selectbox("Block L", [1, 10, 25], index=0)
    with c6:
        seed_val = int(
            st.number_input("Seed", min_value=0, max_value=9999, value=42, step=1)
        )

    lab_cfg = LabConfig(
        population=pop_options[pop_label],
        shift_regime=shift_options[shift_label],
        window_size=int(win_n),
        n_permutations=int(n_perm),
        block_size=int(blk),
        seed=seed_val,
    )
    res = run_lab_experiment(lab_cfg)
    targets = res["targets"]
    sig_feats = res["cal_sig"]
    min_marg_p = float(np.min(res["cal_marg_p"]))
    min_edge_p = float(np.min(res["cal_edge_p"]))

    asym_verdict = "REJECTS H0" if res["dec_rejected"] else "RETAINS H0"
    cal_verdict = f"REJECTS ({len(sig_feats)} cols)" if sig_feats else "RETAINS H0"
    r3_peel = res["recall3"]["Calibrated Peeling"]
    r3_dec = res["recall3"]["Decomposed Max-Edge"]
    r3_text = (
        "NULL CONTROL (N/A)"
        if not targets
        else f"{r3_peel * 100:.0f}% vs {r3_dec * 100:.0f}% max-edge"
    )
    peel_preview = html.escape(
        str([f"f{i:02d}" for i in res["cal_peel_order"][:5]])
    )
    dec_ms_txt = f"{res['dec_ms']:.1f} ms"
    cal_stats = (
        f"min p_marg = {min_marg_p:.3f}, min p_edge = {min_edge_p:.3f}, "
        f"{res['cal_ms']:.0f} ms"
    )

    st.markdown(
        f"""
        <div class="diagnostic-banner">
          <strong>Experiment Protocol:</strong> {html.escape(res['description'])}<br>
          <span>Asymptotic Decomposed: <strong>{asym_verdict}</strong>
          ({dec_ms_txt})</span>
          &nbsp;·&nbsp;
          <span>Calibrated Split-Alpha (alpha/2 = 0.025):
          <strong>{cal_verdict}</strong> ({cal_stats})</span>
          &nbsp;·&nbsp;
          <span>Recall@3: <strong>{r3_text}</strong></span>
          &nbsp;·&nbsp;
          <span>Peel Order: <strong>{peel_preview}</strong>
          (max|R_ref| = {res['cal_max_ref_corr']:.2f})</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _render_lab_charts(res)


def _render_lab_charts(res: dict[str, Any]) -> None:
    """Render side-by-side ranking bars, summary table, and edge heatmap."""
    targets = res["targets"]
    left_col, right_col = st.columns([1.15, 1.0])

    with left_col:
        render_section_header(
            "Top-6 Feature Rankings: Decomposed Max-Edge vs. Calibrated Peeling",
            "mint = ground-truth shifted feature · slate = unshifted decoy",
        )
        rank_fig = make_subplots(
            rows=1,
            cols=2,
            subplot_titles=(
                "DECOMPOSED (MAX-EDGE)",
                "CALIBRATED (EDGE PEELING)",
            ),
            horizontal_spacing=0.16,
        )
        for col_idx, (scores, x_title) in enumerate(
            [
                (res["dec_comb"], "Asymptotic Evidence"),
                (res["cal_scores"], "Tiered Calibrated Score"),
            ],
            start=1,
        ):
            top_idx = np.argsort(-scores, kind="mergesort")[
                :LAB_TOP_RANK_DISPLAY
            ][::-1]
            names = [
                f"* {res['feature_names'][i]}"
                if i in targets
                else res["feature_names"][i]
                for i in top_idx
            ]
            colors = [
                MINT_ACCENT if i in targets else SLATE_ACCENT for i in top_idx
            ]
            rank_fig.add_trace(
                go.Bar(
                    y=names,
                    x=[float(scores[i]) for i in top_idx],
                    orientation="h",
                    marker_color=colors,
                    showlegend=False,
                ),
                row=1,
                col=col_idx,
            )
            rank_fig.update_xaxes(title_text=x_title, row=1, col=col_idx)

        apply_observatory_layout(
            rank_fig, height=340, margin={"l": 64, "r": 22, "t": 44, "b": 44}
        )
        st.plotly_chart(rank_fig, width="stretch")

        summary_rows = []
        for method_name, scores in [
            ("Calibrated Edge-Peeling (Proposed)", res["cal_scores"]),
            ("Decomposed Copula-KS (Asymptotic)", res["dec_comb"]),
            ("Univariate KS Statistic", res["ks_scores"]),
            ("Raw Pearson |dR| Max-Edge", res["pearson_scores"]),
        ]:
            top3 = [
                res["feature_names"][i]
                for i in np.argsort(-scores, kind="mergesort")[:3]
            ]
            r3_val = _recall_at_k(scores, targets, 3)
            summary_rows.append(
                {
                    "Method": method_name,
                    "Top-3 Ranked": ", ".join(top3),
                    "Recall@3": "—" if np.isnan(r3_val) else f"{r3_val * 100:.1f}%",
                }
            )
        st.dataframe(
            pd.DataFrame(summary_rows),
            width="stretch",
            hide_index=True,
        )

    with right_col:
        render_section_header(
            "Relational Edge Evidence Matrix (-log10 Adjusted p_edge)",
            "hubs explain why greedy vertex cover beats max-edge",
        )
        edge_p = np.clip(res["cal_edge_p"], PVAL_CLIP_MIN, 1.0)
        neg_log_p = -np.log10(edge_p)
        np.fill_diagonal(neg_log_p, 0.0)
        heat_fig = go.Figure(
            data=go.Heatmap(
                z=neg_log_p,
                x=res["feature_names"],
                y=res["feature_names"],
                colorscale=[
                    [0.0, INSET_COLOR],
                    [0.35, "#1f3d34"],
                    [0.7, MINT_ACCENT],
                    [1.0, CORAL_ACCENT],
                ],
                colorbar={"title": "-log10(p)", "thickness": 12},
            )
        )
        apply_observatory_layout(
            heat_fig, height=445, margin={"l": 54, "r": 24, "t": 20, "b": 48}
        )
        st.plotly_chart(heat_fig, width="stretch")


# ─────────────────────────────────────────────
# Workspace 03: Paper Benchmark Evidence Explorer
# ─────────────────────────────────────────────


def _render_null_and_blocknull_row(
    s3: dict[str, Any], artifacts: dict[str, Any]
) -> None:
    """Render the Null FWER and Block-Permutation Scope charts."""
    col_a, col_b = st.columns(2)

    with col_a:
        render_section_header(
            "Null Calibration FWER (Nominal alpha = 5.0%)",
            "500 window pairs per pool · nothing injected",
        )
        pops = s3["null"]["populations"]
        pop_order = [
            "gaussian",
            "zero_inflated_tied",
            "multivariate_t3",
            "real_tuesday",
            "real_heldout",
        ]
        pop_labels = [p for p in pop_order if p in pops]
        fwer_fig = go.Figure()
        for key, label, color in [
            ("decomposed_asymptotic", "Asymptotic Decomposed", CORAL_ACCENT),
            ("peeling_separate", "Permutation (Uncorrected Union)", AMBER_ACCENT),
            ("peeling_joint", "Calibrated Joint (alpha/2 Split)", MINT_ACCENT),
        ]:
            vals = [
                float(pops[p]["methods"][key]["fwer"]) * 100.0 for p in pop_labels
            ]
            fwer_fig.add_trace(
                go.Bar(x=pop_labels, y=vals, name=label, marker_color=color)
            )
        fwer_fig.add_hline(
            y=NOMINAL_ALPHA * 100.0,
            line_dash="dash",
            line_color=INK_COLOR,
            line_width=1.1,
            annotation_text="5% nominal",
            annotation_position="top right",
        )
        fwer_fig.update_layout(barmode="group")
        apply_observatory_layout(fwer_fig, height=320)
        fwer_fig.update_yaxes(title_text="EMPIRICAL FWER (%)")
        st.plotly_chart(fwer_fig, width="stretch")

    with col_b:
        render_section_header(
            "Exchangeability Scope: Block-Permutation Null FWER",
            "300 trials · recorded packet order vs. exchangeable pools",
        )
        if "blocknull_v2" in artifacts:
            bn = artifacts["blocknull_v2"]
            b_sizes = [str(b) for b in bn["block_sizes"]]
            bn_fig = go.Figure()
            palette = {
                "real_tuesday": CORAL_ACCENT,
                "nsl_kdd": MINT_ACCENT,
                "multivariate_t3": AMBER_ACCENT,
                "gaussian": SLATE_ACCENT,
            }
            for pool_name, pool_data in bn["pools"].items():
                rates = [
                    float(pool_data["null"][b]["rate"]) * 100.0 for b in b_sizes
                ]
                bn_fig.add_trace(
                    go.Scatter(
                        x=[f"L={b}" for b in b_sizes],
                        y=rates,
                        mode="lines+markers",
                        name=pool_name,
                        line={
                            "width": 2.2,
                            "color": palette.get(pool_name, INK_COLOR),
                        },
                        marker={"size": 7},
                    )
                )
            bn_fig.add_hline(
                y=NOMINAL_ALPHA * 100.0,
                line_dash="dash",
                line_color=INK_COLOR,
                line_width=1.0,
            )
            apply_observatory_layout(bn_fig, height=320)
            bn_fig.update_yaxes(title_text="NULL REJECTION RATE (%)")
            st.plotly_chart(bn_fig, width="stretch")


def _render_power_and_localization_row(
    s3: dict[str, Any], artifacts: dict[str, Any]
) -> None:
    """Render the Sparse-Shift Power curve and 65-Cell Localization table."""
    col_c, col_d = st.columns([0.95, 1.35])

    with col_c:
        render_section_header(
            "Sparse-Shift Floor Across Window Lengths",
            "+0.5 SD shift on k=2 cols · structural <=20% floor",
        )
        pw_fig = go.Figure()
        for key, label, color in [
            ("power_w400", "n = 400", SLATE_ACCENT),
            ("power_w800", "n = 800", AMBER_ACCENT),
            ("power_w1600", "n = 1600", MINT_ACCENT),
        ]:
            if key in artifacts:
                rbf = artifacts[key]["summary"]["rows_by_fraction"]
                fracs = sorted(rbf.keys(), key=float)
                declared = [
                    float(rbf[f]["delta_0.5"]["declared"]) * 100.0 for f in fracs
                ]
                pw_fig.add_trace(
                    go.Scatter(
                        x=[f"{float(f) * 100:.0f}%" for f in fracs],
                        y=declared,
                        mode="lines+markers",
                        name=label,
                        line={"width": 2.2, "color": color},
                    )
                )
        apply_observatory_layout(pw_fig, height=320)
        pw_fig.update_xaxes(title_text="SHIFTED ROW FRACTION")
        pw_fig.update_yaxes(title_text="DECLARED DETECTION (%)", range=[-3, 105])
        st.plotly_chart(pw_fig, width="stretch")

    with col_d:
        render_section_header(
            "65-Cell Localization Benchmark Table",
            "Recall@3 (%) and MRR across 20 seeds per cell",
        )
        cells = s3["localization"]["cells"]
        datasets = sorted({cell_key.split(":")[0] for cell_key in cells})
        ds_choice = st.selectbox(
            "Filter population / dataset",
            ["All populations", *datasets],
            index=0,
        )
        table_rows = []
        for cell_key, payload in sorted(cells.items()):
            ds_name, cond_name = cell_key.split(":", 1)
            if cond_name == "null" or ds_choice not in {
                "All populations",
                ds_name,
            }:
                continue
            m = payload["methods"]
            dec_r3 = m["decomposed_asymptotic"]["recall@3"] * 100.0
            max_r3 = m["maxedge_joint"]["recall@3"] * 100.0
            peel_r3 = m["peeling_joint"]["recall@3"] * 100.0
            det_pct = m["peeling_joint"]["detection_rate"] * 100.0
            table_rows.append(
                {
                    "Dataset": ds_name,
                    "Condition": cond_name,
                    "Decomposed R@3": f"{dec_r3:.1f}%",
                    "Max-Edge R@3": f"{max_r3:.1f}%",
                    "Peeling R@3": f"{peel_r3:.1f}%",
                    "Peeling MRR": f"{m['peeling_joint']['mrr']:.3f}",
                    "Declared %": f"{det_pct:.0f}%",
                }
            )
        st.dataframe(
            pd.DataFrame(table_rows),
            width="stretch",
            hide_index=True,
            height=265,
        )


def render_evidence_workspace() -> None:
    """Render Workspace 03 from provenance-locked JSON study artifacts."""
    artifacts = load_paper_artifacts()
    if "study_v3" not in artifacts:
        st.info(
            "Benchmark JSON artifacts were not found under `artifacts/runs/`. "
            "Run from a repository checkout to explore the benchmark tables."
        )
        return

    s3 = artifacts["study_v3"]
    cost = artifacts.get("cost", {})
    asym_ms = cost.get("asymptotic_decomposed_ms", 7.62)
    b_val = s3.get("n_permutations", 199)
    n_null = s3.get("null_trials", 500)

    render_section_header(
        "03 / Provenance-Locked Paper Artifacts",
        f"study-v3 (B={b_val}, null={n_null}) · decomposed {asym_ms:.2f} ms",
    )
    _render_null_and_blocknull_row(s3, artifacts)
    _render_power_and_localization_row(s3, artifacts)


# ─────────────────────────────────────────────
# Sidebar & application entry point
# ─────────────────────────────────────────────


def render_sidebar() -> tuple[StreamConfig, bool, bool, bool]:
    """Render sidebar controls and return `(config, run_all, step_once, reset)`."""
    with st.sidebar:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:10px;padding:4px 0 8px">'
            f"{BRAND_SVG}"
            f'<span style="font-weight:700;font-size:19px;letter-spacing:-0.6px">'
            f'vigil<span style="color:{MINT_ACCENT}">.</span>console</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="sidebar-eyebrow">01 / Stream Execution</div>',
            unsafe_allow_html=True,
        )
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            run_all = st.button("Run Stream", type="primary", width="stretch")
        with btn_c2:
            step_once = st.button("Step +1", width="stretch")
        reset_clicked = st.button("Reset Baseline", width="stretch")

        st.markdown(
            '<div class="sidebar-eyebrow">02 / Attribution Engine</div>',
            unsafe_allow_html=True,
        )
        attribution_mode = st.selectbox(
            "Attribution Mode",
            options=[
                "decomposed",
                "calibrated",
                "positive_delta",
                "absolute_delta",
                "standardized_delta",
            ],
            index=0,
            help=(
                "'decomposed' runs fast Copula-KS (~7.6 ms); 'calibrated' adds "
                "Westfall-Young permutation FWER control and greedy edge peeling."
            ),
        )
        use_feature_groups = st.checkbox(
            "Group 122 columns into 41 NSL-KDD attributes",
            value=True,
            help="Consolidates one-hot protocol/service/flag indicators.",
        )

        if attribution_mode == "calibrated":
            n_permutations = int(
                st.select_slider(
                    "Permutations (B)",
                    options=[49, 99, 199, 399],
                    value=99,
                    help="B=199 is paper default; B=99 keeps live streaming fast.",
                )
            )
            block_size = int(
                st.select_slider(
                    "Block Length (L)",
                    options=[1, 10, 25, 50],
                    value=1,
                    help="Contiguous row block length for serially correlated streams.",
                )
            )
        else:
            n_permutations = 199
            block_size = 1

        adaptation_mode = st.selectbox(
            "Adaptation Policy",
            options=["verified_only", "auto", "frozen"],
            index=0,
            help="'verified_only' prevents unlabelled attack poisoning (97.9% F1).",
        )

        st.markdown(
            '<div class="sidebar-eyebrow">03 / Stream Schedule</div>',
            unsafe_allow_html=True,
        )
        chunk_delay = float(st.slider("Batch cadence (s)", 0.0, 1.0, 0.08, 0.04))
        n_total = int(st.slider("Horizon (batches)", 12, 35, 22))
        drift_at = int(st.slider("Known-attack onset", 2, 10, 5))
        default_nov = max(13, drift_at + 4)
        novelty_at = int(
            st.slider("Novel-class onset", drift_at + 3, n_total - 2, default_nov)
        )

    cfg = StreamConfig(
        chunk_delay=chunk_delay,
        n_total=n_total,
        drift_at=drift_at,
        novelty_at=novelty_at,
        attribution_mode=attribution_mode,
        adaptation_mode=adaptation_mode,
        use_feature_groups=use_feature_groups,
        n_permutations=n_permutations,
        block_size=block_size,
    )
    return cfg, run_all, step_once, reset_clicked


def render_live_stream_workspace(
    cfg: StreamConfig,
    obs: dict[str, Any],
    tuple_groups: dict[str, tuple[int, ...]],
) -> None:
    """Render Workspace 01 charts and terminal ledger."""
    render_section_header(
        "01 / Dual-Autoencoder Reconstruction & Replicated Welch Severity",
        f"15x30 Welch t-tests · alert threshold = {DRIFT_ALERT_THRESHOLD:.2f}",
    )
    st.plotly_chart(build_stream_timeline_figure(obs, cfg), width="stretch")

    left_col, right_col = st.columns([1.15, 1.0])
    with left_col:
        attr_fig, attr_caption = build_pathway_attribution_figure(
            obs, cfg, tuple_groups
        )
        render_section_header(
            "Decomposed Feature Evidence (Marginal KS vs. Relational Copula)",
            attr_caption,
        )
        st.plotly_chart(attr_fig, width="stretch")

    with right_col:
        render_section_header(
            "KDE Out-of-Support Novelty Trace & Telemetry Ledger",
            f"novelty alert > {NOVELTY_ALERT_THRESHOLD:.0%}",
        )
        st.plotly_chart(build_novelty_trace_figure(obs), width="stretch")
        render_signal_ledger(obs)


def main() -> None:
    """Entry point for the Vigil Signal Observatory Streamlit application."""
    st.set_page_config(
        page_title="Vigil — Signal Observatory",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(OBSERVATORY_CSS, unsafe_allow_html=True)

    cfg, run_all, step_once, reset_clicked = render_sidebar()
    _, _, _, tuple_groups = load_cached_nsl_kdd()

    if reset_clicked:
        st.session_state.observatory = default_stream_state()
        prepare_stream_engine(cfg)

    obs = ensure_stream_state()

    if step_once:
        prepare_stream_engine(cfg)
        process_next_chunk()
        obs = ensure_stream_state()

    if run_all:
        st.session_state.observatory = default_stream_state()
        prepare_stream_engine(cfg)
        obs = ensure_stream_state()
        progress = st.progress(0.0, text="Streaming NSL-KDD batches...")
        total = max(len(obs["chunks_list"]), 1)
        while process_next_chunk():
            done = int(obs["cursor"])
            progress.progress(
                min(done / total, 1.0),
                text=f"Processed batch {done:02d}/{total:02d}",
            )
            if cfg.chunk_delay > 0:
                time.sleep(cfg.chunk_delay)
        progress.empty()

    render_masthead_and_strip(cfg, obs)

    tab_stream, tab_lab, tab_evidence = st.tabs(
        [
            "01 / Live Telemetry Stream",
            "02 / Attribution & Edge-Peeling Lab",
            "03 / Paper Benchmark Evidence",
        ]
    )

    with tab_stream:
        render_live_stream_workspace(cfg, obs, tuple_groups)

    with tab_lab:
        render_lab_workspace()

    with tab_evidence:
        render_evidence_workspace()


if __name__ == "__main__":
    main()
