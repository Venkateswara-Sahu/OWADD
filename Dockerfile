# ─── Stage 1: base ───────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy package metadata first (cache-friendly — only re-installs if deps change)
COPY pyproject.toml ./
COPY owadd_sentinel/ ./owadd_sentinel/

# Install core + api dependencies
RUN pip install --no-cache-dir -e ".[api,mlflow]"

# ─── Stage 2: API service ─────────────────────────────────────────────────────
FROM base AS api

COPY api/ ./api/
COPY data/ ./data/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]

# ─── Stage 3: Streamlit dashboard ─────────────────────────────────────────────
FROM base AS dashboard

RUN pip install --no-cache-dir streamlit plotly

COPY dashboard/ ./dashboard/
COPY data/ ./data/

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

CMD ["streamlit", "run", "dashboard/app.py", \
     "--server.address", "0.0.0.0", \
     "--server.port", "8501", \
     "--server.headless", "true"]
