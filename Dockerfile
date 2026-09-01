# ── Stage 1: Build the Vue frontend ──────────────────────────────────────────
FROM node:22-alpine AS frontend-build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --prefer-offline

COPY index.html jsconfig.json vite.config.mjs ./
COPY public/ public/
COPY src/ src/

ARG VITE_BACKEND_ENABLED=true
RUN npm run build

# ── Stage 2: Python backend serving the built frontend ────────────────────────
FROM python:3.12-slim AS app

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ backend/

# Copy built frontend from Stage 1
COPY --from=frontend-build /app/dist dist/

RUN groupadd --gid 10001 app \
	&& useradd --uid 10001 --gid app --no-create-home app \
	&& mkdir -p /app/data \
	&& chown app:app /app/data
ENV DATABASE_PATH=/app/data/icarus.db
VOLUME ["/app/data"]

USER app

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
