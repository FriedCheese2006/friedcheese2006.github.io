# ── Stage 1: Build the Vue frontend ──────────────────────────────────────────
FROM node:26-alpine AS frontend-build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --prefer-offline

COPY index.html jsconfig.json vite.config.mjs ./
COPY public/ public/
COPY src/ src/

ARG VITE_BACKEND_ENABLED=true
RUN npm run build

# ── Stage 2: Python backend serving the built frontend ────────────────────────
FROM python:3.15.1-slim AS app

WORKDIR /app

RUN apt-get update \
	&& apt-get upgrade -y \
	&& rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN python -m pip install --no-cache-dir --require-hashes -r requirements.txt \
	&& python -m pip uninstall --yes pip

# Copy backend source
COPY backend/ backend/

# Copy built frontend from Stage 1
COPY --from=frontend-build /app/dist dist/

RUN groupadd --gid 10001 app \
	&& useradd --uid 10001 --gid app --no-create-home app \
	&& mkdir -p /app/data \
	&& chown app:app /app/data
ENV DATABASE_PATH=/app/data/prospector.db
VOLUME ["/app/data"]

USER 10001:10001

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
