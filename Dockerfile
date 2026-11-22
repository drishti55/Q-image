# Q-ImageLab hosted demo: one container serves the React app and the FastAPI /api on $PORT (Render sets PORT).
# Lite mode keeps it inside a free 512 MB instance (see README → Deployment).

# ── 1. build the frontend ──
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ── 2. API + built frontend ──
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg \
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    QIL_LITE=1
WORKDIR /app
COPY requirements-render.txt .
RUN pip install --no-cache-dir -r requirements-render.txt
COPY . .
COPY --from=web /web/dist ./frontend/dist
# frozen FRQI training density matrices → memory-mapped file (no runtime memory spike); also builds the image cache
RUN python scripts/v4/precompute_frozen.py
EXPOSE 10000
CMD ["sh", "-c", "uvicorn api_main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1"]
