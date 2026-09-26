# Read-only public demo: FastAPI serving the built React app and a snapshot of
# the pipeline's outputs. Build after running the pipeline locally:
#   docker build -t ai-market-intelligence .
#   docker run -p 8000:8000 ai-market-intelligence

# --- frontend ---------------------------------------------------------------
FROM node:24-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

# --- api ----------------------------------------------------------------------
FROM python:3.13-slim
# xgboost needs the OpenMP runtime
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt

COPY src/ src/
COPY api/ api/
COPY --from=web /web/dist web/dist
# Data snapshot: only what the API reads (see .dockerignore). No .env, no raw
# provider caches, no API keys.
COPY data/ data/
COPY outputs/ outputs/

ENV APP_MODE=public \
    PYTHONUNBUFFERED=1
RUN useradd --create-home app && chown -R app /app
USER app
EXPOSE 8000
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
