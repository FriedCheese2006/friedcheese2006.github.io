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
FROM python:3.14.7-slim AS app

WORKDIR /app

COPY security/CVE-2025-15367.patch /tmp/CVE-2025-15367.patch
RUN apt-get update \
	&& apt-get upgrade -y \
	&& apt-get install -y --no-install-recommends patch \
	&& patch --directory=/usr/local/lib/python3.13 --strip=0 < /tmp/CVE-2025-15367.patch \
	&& python -c "import poplib, unittest; client = object.__new__(poplib.POP3); client._debugging = 0; client.encoding = 'UTF-8'; unittest.TestCase().assertRaises(ValueError, client._putcmd, 'USER attacker\\r\\nDELE 1')" \
	&& apt-get purge -y patch \
	&& rm -f /tmp/CVE-2025-15367.patch \
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
