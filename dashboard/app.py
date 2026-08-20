"""
Vigil — SOC Dashboard
======================
Security Operations Center style real-time drift monitoring dashboard.

Architecture: one chunk processed per st.rerun() — no loops in main script.

Run with:
    streamlit run dashboard/app.py
"""

import time
import sys
import numpy as np
import streamlit as st
import plotly.graph_objects as go

sys.path.insert(0, ".")

# ─── Page config — must be first ─────────────────────────────────────────────
st.set_page_config(
    page_title="Vigil | SOC Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Dark SOC CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@300;400;600;700&display=swap');

html, body, [class*="css"] { background-color: #0d1117; color: #e6edf3; font-family: 'Inter', sans-serif; }
.stApp { background-color: #0d1117; }
section[data-testid="stSidebar"] { background-color: #090d13; border-right: 1px solid #21262d; }
#MainMenu, footer, header { visibility: hidden; }

.metric-card {
    background: #161b22; border: 1px solid #21262d; border-radius: 10px;
    padding: 18px 22px; text-align: center; transition: border-color 0.3s;
}
.metric-card:hover { border-color: #58a6ff; }
.metric-value { font-family: 'JetBrains Mono', monospace; font-size: 2.2rem; font-weight: 700; line-height: 1.1; }
.metric-label { font-size: 0.72rem; color: #8b949e; letter-spacing: 0.1em; text-transform: uppercase; margin-top: 4px; }

.badge-live { display:inline-block; background:#0a2a0a; color:#3fb950; border:1px solid #3fb950; border-radius:20px; padding:3px 12px; font-size:0.8rem; font-family:'JetBrains Mono',monospace; }
.badge-drift { display:inline-block; background:#2d0a0a; color:#f85149; border:1px solid #f85149; border-radius:20px; padding:3px 12px; font-size:0.8rem; font-family:'JetBrains Mono',monospace; }
.badge-warning { display:inline-block; background:#2d1f0a; color:#d29922; border:1px solid #d29922; border-radius:20px; padding:3px 12px; font-size:0.8rem; font-family:'JetBrains Mono',monospace; }

.alert-drift { background:linear-gradient(90deg,#2d0a0a,#1a0505); border:1px solid #f85149; border-left:4px solid #f85149; border-radius:8px; padding:14px 20px; margin:10px 0; font-family:'JetBrains Mono',monospace; font-size:0.9rem; color:#f85149; }
.alert-novelty { background:linear-gradient(90deg,#2d1f0a,#1a1205); border:1px solid #d29922; border-left:4px solid #d29922; border-radius:8px; padding:14px 20px; margin:10px 0; font-family:'JetBrains Mono',monospace; font-size:0.9rem; color:#d29922; }
.alert-normal { background:linear-gradient(90deg,#0a1a0a,#051005); border:1px solid #3fb950; border-left:4px solid #3fb950; border-radius:8px; padding:14px 20px; margin:10px 0; font-size:0.9rem; color:#3fb950; }

.chunk-log { background:#090d13; border:1px solid #21262d; border-radius:8px; padding:10px 14px; font-family:'JetBrains Mono',monospace; font-size:0.72rem; color:#8b949e; max-height:200px; overflow-y:auto; }
.section-header { font-size:0.7rem; color:#8b949e; letter-spacing:0.15em; text-transform:uppercase; border-bottom:1px solid #21262d; padding-bottom:6px; margin-bottom:14px; }
.stButton > button { background:#1f6feb; color:white; border:none; border-radius:6px; font-weight:600; padding:10px 24px; width:100%; }
.stButton > button:hover { background:#388bfd; }
</style>
""", unsafe_allow_html=True)


# ─── Session state defaults ───────────────────────────────────────────────────
DEFAULTS = {
    "running": False,
    "fitted": False,
    "chunk_id": 0,
    "n_total_chunks": 25,
    "errors": [],
    "severities": [],
    "novelty_props": [],
    "drift_events": [],
    "n_drifts": 0,
    "n_novelty": 0,
    "last_status": "WAITING",
    "last_attribution": None,
    "log_entries": [],
    "sentinel": None,
    "X": None,
    "y": None,
    "feature_names": None,
    "drift_at": 5,
    "novelty_at": 14,
    "chunk_delay": 0.7,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─── Data loading (cached) ───────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_data():
    try:
        from data.nsl_kdd_loader import load_nsl_kdd
        return load_nsl_kdd(split="train")
    except Exception:
        np.random.seed(42)
        X = np.random.randn(5000, 41).astype(np.float32)
        y = np.array(["normal"] * 3000 + ["neptune"] * 1500 + ["smurf"] * 500)
        return X, y, [f"feature_{i}" for i in range(41)]


# ─── Chart helpers ────────────────────────────────────────────────────────────
PAPER_BG = "#161b22"
PLOT_BG  = "#0d1117"
GRID_COL = "#21262d"
FONT_COL = "#c9d1d9"


def error_timeline(errors, severities, drift_events):
    x = list(range(1, len(errors) + 1))
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=errors, mode="lines", name="Recon. Error",
        line=dict(color="#58a6ff", width=2),
        fill="tozeroy", fillcolor="rgba(88,166,255,0.07)",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=severities, mode="lines", name="Drift Severity",
        line=dict(color="#d29922", width=1.5, dash="dot"), yaxis="y2",
    ))
    for de in drift_events:
        if de <= len(errors):
            fig.add_vline(x=de, line=dict(color="#f85149", width=2, dash="dash"),
                          annotation_text="DRIFT", annotation_font=dict(color="#f85149", size=9))
    fig.add_hline(y=0.3, line=dict(color="#f85149", width=1, dash="dot"),
                  annotation_text="Threshold", annotation_font=dict(color="#f85149", size=8),
                  yref="y2")
    fig.update_layout(
        paper_bgcolor=PAPER_BG, plot_bgcolor=PLOT_BG,
        font=dict(color=FONT_COL, family="JetBrains Mono"),
        margin=dict(l=10, r=10, t=36, b=10),
        title=dict(text="RECONSTRUCTION ERROR TIMELINE", font=dict(size=11, color="#8b949e")),
        xaxis=dict(gridcolor=GRID_COL, zerolinecolor=GRID_COL),
        yaxis=dict(title="Error", gridcolor=GRID_COL, zerolinecolor=GRID_COL),
        yaxis2=dict(title="Severity", overlaying="y", side="right",
                    range=[0, 1], gridcolor=GRID_COL, showgrid=False),
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=-0.18, font=dict(size=10)),
        height=290,
    )
    return fig


def attribution_chart(top_features):
    if not top_features:
        fig = go.Figure()
        fig.update_layout(paper_bgcolor=PAPER_BG, plot_bgcolor=PLOT_BG,
                          font=dict(color=FONT_COL), height=240,
                          title=dict(text="FEATURE ATTRIBUTION", font=dict(size=11, color="#8b949e")),
                          xaxis=dict(gridcolor=GRID_COL), yaxis=dict(gridcolor=GRID_COL),
                          margin=dict(l=10, r=10, t=36, b=10))
        return fig
    feats = [f["feature_name"] for f in top_features][::-1]
    pcts  = [f["contribution"] * 100 for f in top_features][::-1]
    colors = [f"rgba({248 - i*18},{81 + i*12},{73 + i*12},0.85)" for i in range(len(feats))]
    fig = go.Figure(go.Bar(
        x=pcts, y=feats, orientation="h",
        marker=dict(color=colors[::-1]),
        text=[f"{p:.1f}%" for p in pcts], textposition="outside",
        textfont=dict(size=10, color=FONT_COL),
    ))
    fig.update_layout(
        paper_bgcolor=PAPER_BG, plot_bgcolor=PLOT_BG,
        font=dict(color=FONT_COL, family="JetBrains Mono"),
        margin=dict(l=10, r=10, t=36, b=10),
        title=dict(text="TOP DRIFTED FEATURES (%)", font=dict(size=11, color="#8b949e")),
        xaxis=dict(title="Contribution %", range=[0, max(pcts) * 1.35], gridcolor=GRID_COL),
        yaxis=dict(gridcolor=GRID_COL),
        height=260, showlegend=False,
    )
    return fig


def novelty_gauge(val):
    color = "#f85149" if val > 0.2 else "#d29922" if val > 0.1 else "#3fb950"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=val * 100,
        number=dict(suffix="%", font=dict(size=30, color=color, family="JetBrains Mono")),
        gauge=dict(
            axis=dict(range=[0, 100], tickfont=dict(size=9, color="#8b949e")),
            bar=dict(color=color, thickness=0.3),
            bgcolor=PLOT_BG, bordercolor=GRID_COL,
            steps=[dict(range=[0, 10], color=PLOT_BG),
                   dict(range=[10, 20], color="#1a1005"),
                   dict(range=[20, 100], color="#1a0505")],
            threshold=dict(line=dict(color="#f85149", width=2), value=20),
        ),
    ))
    fig.update_layout(
        paper_bgcolor=PAPER_BG, font=dict(color=FONT_COL),
        title=dict(text="NOVELTY PROPORTION", font=dict(size=11, color="#8b949e")),
        height=230, margin=dict(l=20, r=20, t=40, b=10),
    )
    return fig


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:10px 0 20px">
        <div style="font-size:2rem">🛡️</div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:1rem;color:#58a6ff;font-weight:700">OWADD SENTINEL</div>
        <div style="font-size:0.7rem;color:#8b949e;margin-top:4px">Network Drift Detection System</div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-header">Stream Status</div>', unsafe_allow_html=True)
    s = st.session_state.last_status
    if s == "LIVE":
        st.markdown('<span class="badge-live">● LIVE</span>', unsafe_allow_html=True)
    elif s == "DRIFT":
        st.markdown('<span class="badge-drift">⚠ DRIFT DETECTED</span>', unsafe_allow_html=True)
    elif s == "NOVELTY":
        st.markdown('<span class="badge-warning">◈ NOVEL CLASS</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span style="color:#8b949e;font-size:0.8rem">● WAITING</span>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">Stream Config</div>', unsafe_allow_html=True)

    chunk_delay = st.slider("Chunk delay (sec)", 0.1, 2.0, 0.7, 0.1)
    n_total     = st.slider("Total chunks", 10, 40, 25)
    drift_at    = st.slider("Drift at chunk", 3, 15, 5)
    novelty_at  = st.slider("Novelty at chunk", 5, 25, 14)

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        start_btn = st.button("▶ Start", use_container_width=True)
    with col2:
        reset_btn = st.button("↺ Reset", use_container_width=True)

    if reset_btn:
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">About</div>', unsafe_allow_html=True)
    st.markdown("""<div style="font-size:0.72rem;color:#8b949e;line-height:1.6">
    Detects concept drift and novel attack classes in network traffic streams without labels.<br><br>
    Based on <a href="https://arxiv.org/abs/2605.29834" style="color:#58a6ff">arXiv:2605.29834</a><br>
    + Feature Attribution (novel contribution)
    </div>""", unsafe_allow_html=True)
    st.markdown('<div style="margin-top:16px;font-size:0.7rem"><a href="https://github.com/Venkateswara-Sahu/OWADD" style="color:#58a6ff">GitHub ↗</a></div>', unsafe_allow_html=True)


# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:14px;padding:10px 0 20px;border-bottom:1px solid #21262d;margin-bottom:20px">
    <div style="font-size:1.5rem">🛡️</div>
    <div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:1.25rem;font-weight:700;color:#e6edf3">OWADD Sentinel</div>
        <div style="font-size:0.75rem;color:#8b949e">Real-Time Network Intrusion Drift Detection &nbsp;·&nbsp; NSL-KDD Stream</div>
    </div>
</div>""", unsafe_allow_html=True)

# ─── Metric cards ─────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
drift_col  = "#f85149" if st.session_state.n_drifts  > 0 else "#3fb950"
nov_col    = "#d29922" if st.session_state.n_novelty > 0 else "#8b949e"
model_col  = "#3fb950" if st.session_state.fitted else "#8b949e"
model_txt  = "READY"   if st.session_state.fitted else "OFFLINE"

for col, val, color, label in [
    (c1, st.session_state.n_drifts,  drift_col, "Drift Events"),
    (c2, st.session_state.n_novelty, nov_col,   "Novelty Alerts"),
    (c3, st.session_state.chunk_id,  "#58a6ff", "Chunks Processed"),
]:
    col.markdown(f'<div class="metric-card"><div class="metric-value" style="color:{color}">{val}</div><div class="metric-label">{label}</div></div>', unsafe_allow_html=True)

c4.markdown(f'<div class="metric-card"><div class="metric-value" style="color:{model_col};font-size:1.4rem">{model_txt}</div><div class="metric-label">Model Status</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── Alert banner ─────────────────────────────────────────────────────────────
status = st.session_state.last_status
cid    = st.session_state.chunk_id
if status == "DRIFT":
    st.markdown(f'<div class="alert-drift">⚠ CONCEPT DRIFT DETECTED — Chunk {cid} — Model adapting to new distribution...</div>', unsafe_allow_html=True)
elif status == "NOVELTY":
    st.markdown(f'<div class="alert-novelty">◈ NOVEL CLASS DETECTED — Chunk {cid} — Unknown attack pattern identified</div>', unsafe_allow_html=True)
elif status == "LIVE":
    st.markdown(f'<div class="alert-normal">✓ STREAM STABLE — Chunk {cid} — All traffic within expected distribution bounds</div>', unsafe_allow_html=True)
else:
    st.markdown('<div style="color:#8b949e;font-size:0.85rem;padding:12px 0">Click ▶ Start in the sidebar to begin stream simulation.</div>', unsafe_allow_html=True)

# ─── Charts ───────────────────────────────────────────────────────────────────
left, right = st.columns([3, 2])

with left:
    errs = st.session_state.errors
    sevs = st.session_state.severities
    devs = st.session_state.drift_events
    if errs:
        st.plotly_chart(error_timeline(errs, sevs, devs), use_container_width=True, key="et")
    else:
        st.markdown('<div style="background:#161b22;border:1px solid #21262d;border-radius:10px;padding:60px;text-align:center;color:#8b949e;height:290px">Start stream to see live data</div>', unsafe_allow_html=True)

with right:
    nov_val = st.session_state.novelty_props[-1] if st.session_state.novelty_props else 0.0
    st.plotly_chart(novelty_gauge(nov_val), use_container_width=True, key="ng")
    st.plotly_chart(attribution_chart(st.session_state.last_attribution), use_container_width=True, key="ac")

# ─── Chunk log ────────────────────────────────────────────────────────────────
if st.session_state.log_entries:
    log_html = '<div class="chunk-log">' + "<br>".join(st.session_state.log_entries[-25:]) + "</div>"
    st.markdown(log_html, unsafe_allow_html=True)

# ─── Progress bar (shown only while running) ──────────────────────────────────
progress_placeholder = st.empty()
if st.session_state.running:
    n_tot = st.session_state.n_total_chunks
    pct   = min(cid / max(n_tot, 1), 1.0)
    progress_placeholder.progress(pct, text=f"Processing chunk {cid} / {n_tot}...")


# ─── START: initialise sentinel + simulator ───────────────────────────────────
if start_btn and not st.session_state.running:
    with st.spinner("Loading NSL-KDD dataset..."):
        X, y, feat_names = load_data()
        st.session_state.X = X
        st.session_state.y = y
        st.session_state.feature_names = feat_names

    from owadd_sentinel import OWADDSentinel
    from data.stream_simulator import StreamSimulator

    sim = StreamSimulator(X, y, chunk_size=200,
                          drift_after_chunk=drift_at, novelty_after_chunk=novelty_at)
    first = next(sim.stream(n_chunks=1))

    with st.spinner("Training OWADD Sentinel on initial traffic baseline..."):
        sentinel = OWADDSentinel(feature_names=feat_names, top_k_features=5, buffer_size=400)
        sentinel.fit(first.X, verbose=False)

    st.session_state.sentinel         = sentinel
    st.session_state.fitted           = True
    st.session_state.running          = True
    st.session_state.chunk_id         = 1
    st.session_state.n_total_chunks   = n_total
    st.session_state.drift_at         = drift_at
    st.session_state.novelty_at       = novelty_at
    st.session_state.chunk_delay      = chunk_delay
    st.session_state.last_status      = "LIVE"
    st.session_state.log_entries.append(
        f'<span style="color:#58a6ff">[{time.strftime("%H:%M:%S")}] 🔧 CHUNK 01 — TRAINING '
        f'(offline phase — {first.X.shape[0]} samples, {first.X.shape[1]} features)</span>'
    )
    st.rerun()


# ─── RUNNING: process one chunk per rerun ─────────────────────────────────────
if st.session_state.running:
    sentinel     = st.session_state.sentinel
    X            = st.session_state.X
    y            = st.session_state.y
    feat_names   = st.session_state.feature_names
    cid_next     = st.session_state.chunk_id + 1
    n_tot        = st.session_state.n_total_chunks
    drift_at_s   = st.session_state.drift_at
    novelty_at_s = st.session_state.novelty_at

    if cid_next > n_tot:
        st.session_state.running = False
        st.success("✅ Stream simulation complete.")
        st.rerun()
    else:
        from data.stream_simulator import StreamSimulator
        # Re-create simulator and fast-forward to the right chunk
        sim = StreamSimulator(X, y, chunk_size=200,
                              drift_after_chunk=drift_at_s,
                              novelty_after_chunk=novelty_at_s,
                              seed=42)
        # Get the specific chunk we need
        target_chunk = None
        for chunk in sim.stream(n_chunks=cid_next):
            if chunk.chunk_id == cid_next:
                target_chunk = chunk
                break

        result = sentinel.detect(target_chunk.X)

        # Update state
        st.session_state.chunk_id = cid_next
        st.session_state.errors.append(result.drift_result.batch_error_mean)
        st.session_state.severities.append(result.drift_severity)
        st.session_state.novelty_props.append(result.novelty_proportion)

        ts = time.strftime("%H:%M:%S")
        if result.drift_detected:
            st.session_state.n_drifts += 1
            st.session_state.drift_events.append(cid_next)
            st.session_state.last_status = "DRIFT"
            if result.attribution:
                st.session_state.last_attribution = result.attribution.top_features
            st.session_state.log_entries.append(
                f'<span style="color:#f85149">[{ts}] ⚠ CHUNK {cid_next:02d} — DRIFT '
                f'(severity={result.drift_severity:.2f}, novelty={result.novelty_proportion:.1%})</span>'
            )
        elif result.novelty_proportion > 0.1:
            st.session_state.n_novelty += 1
            st.session_state.last_status = "NOVELTY"
            st.session_state.log_entries.append(
                f'<span style="color:#d29922">[{ts}] ◈ CHUNK {cid_next:02d} — NOVEL CLASS '
                f'({result.novelty_proportion:.1%} unknown)</span>'
            )
        else:
            st.session_state.last_status = "LIVE"
            st.session_state.log_entries.append(
                f'<span style="color:#3fb950">[{ts}] ✓ CHUNK {cid_next:02d} — STABLE '
                f'(error={result.drift_result.batch_error_mean:.4f})</span>'
            )

        time.sleep(st.session_state.chunk_delay)
        st.rerun()
