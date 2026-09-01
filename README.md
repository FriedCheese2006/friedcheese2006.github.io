# PROSPECTOR

**Planetary Resource Order & Surface Prep Engine for Crafting, Tallying, Output & Requisitions**

PROSPECTOR is a browser-based crafting planner for [ICARUS](https://store.steampowered.com/app/1149460/ICARUS/). Build item and food plans, compare recipe alternatives, expand ingredient trees, and track completed requirements.

## Attribution and Disclaimer

PROSPECTOR is based on [Drumstix42's Icarus Calculator](https://github.com/Drumstix42/drumstix42.github.io). Its game-file extraction and import workflow, including the Ue4Export setup, data-table mapping, and item-icon flow, was derived from that project and subsequently modified. The upstream project and this derivative are distributed under the [Apache License 2.0](LICENSE).

PROSPECTOR is an unofficial fan project. It is not affiliated with, endorsed by, or sponsored by ICARUS, RocketWerkz, or any of their subsidiaries. Game names, data, imagery, and related marks remain the property of their respective owners.

## Usage

Open the hosted app at [friedcheese2006.github.io](https://friedcheese2006.github.io/).

Plans and settings are stored in your browser. The app can be installed from a supported browser and remains available offline after its core files and required game assets have been cached.

To install it:

1. Open the app in Chrome, Edge, or another browser with PWA support.
2. Use the browser's **Install app** command.
3. Launch it from your desktop or application menu.

Clearing site data removes locally stored plans. Export or preserve browser data before clearing it when those plans matter.

## Container Deployment

A multi-architecture image is published to GitHub Container Registry:

```text
ghcr.io/friedcheese2006/prospector:latest
```

Download [docker-compose.image.yml](docker-compose.image.yml), then start the app:

```bash
docker compose -f docker-compose.image.yml up -d
```

Open `http://localhost:8000`. The `prospector_data` volume preserves account and synchronized workspace data across container replacements. Anonymous plans continue to use browser storage.

The image and Compose definitions run as UID/GID `10001`, use a read-only root filesystem, drop all Linux capabilities, and prevent privilege escalation. Only `/app/data` and the bounded `/tmp` filesystem are writable. If you replace the named volume with a bind mount, its directory must be writable by UID/GID `10001`.

### Optional OpenID Connect SSO

Copy [.env.example](.env.example) to `.env` and configure an OpenID Connect confidential client. The provider must publish standard discovery metadata and support the authorization code flow with PKCE.

Generate the signing key with `openssl rand -base64 48`, then place its output in `JWT_SECRET_KEY`:

```dotenv
APP_BASE_URL=https://prospector.example.com
JWT_SECRET_KEY=
OIDC_ISSUER=https://identity.example.com/tenant
OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-client-secret
```

Set the provider's redirect URI to:

```text
https://prospector.example.com/auth/callback
```

The issuer is used to load `/.well-known/openid-configuration`; authorization, token, and user-info endpoints are read from that document.

Restart the stack after changing the environment:

```bash
docker compose -f docker-compose.image.yml up -d
```

Signed-in users synchronize plans and settings through the container's SQLite database. Terminate TLS at a reverse proxy and set `APP_BASE_URL` to the externally reachable HTTPS origin.

### Backup and Restore

Stop the application before copying its database. Find the volume name with `docker volume ls`; Compose normally names it `<project>_prospector_data`.

```bash
docker compose -f docker-compose.image.yml stop app
docker run --rm -v <volume-name>:/data:ro -v "$PWD:/backup" alpine cp /data/prospector.db /backup/prospector.db
docker compose -f docker-compose.image.yml start app
```

To restore a backup, stop the application and copy the file in the other direction:

```bash
docker compose -f docker-compose.image.yml stop app
docker run --rm -v <volume-name>:/data -v "$PWD:/backup:ro" alpine sh -c 'cp /backup/prospector.db /data/prospector.db && chown 10001:10001 /data/prospector.db'
docker compose -f docker-compose.image.yml start app
```

To build from the repository instead of using the published image:

```bash
cp .env.example .env
docker compose up -d --build
```

## Local Development

### Prerequisites

- Node.js 22
- Python 3.13
- Docker, when testing the container

Install dependencies and start both development servers:

```bash
cp .env.example .env
npm install
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --require-hashes -r backend/requirements.txt
make dev
```

Vite runs at `http://localhost:5173` and FastAPI runs at `http://localhost:8001`. The standalone Vite app uses browser storage. To exercise SSO and server synchronization locally, build and run the container so the frontend and API share one origin.

Direct Python dependencies are declared in [backend/requirements.in](backend/requirements.in), while [backend/requirements.txt](backend/requirements.txt) is the generated, hash-verified lockfile. After changing direct dependencies, regenerate and verify the lockfile:

```bash
make requirements-lock
make requirements-check
```

Run all automated checks:

```bash
make test
npm run build
```

Build a local container image:

```bash
make docker-build
```

Build and scan it with Grype and Trivy, including the VEX record for the backported CPython security fix:

```bash
make security-scan
```

### Updating Game Data and Icons

[public/icarus-game](public/icarus-game) is the runtime source used by local builds, GitHub Pages, the PWA, and the container image. The ignored `export/` directory is import input only.

1. Download [Ue4Export](https://github.com/CrystalFerrai/Ue4Export/releases) and install .NET 8.
2. Copy the files from [scripts/Ue4ExportFiles](scripts/Ue4ExportFiles) beside `Ue4Export.exe`.
3. Update `export.bat` for the local ICARUS installation and run it.
4. Import the resulting data and icons:

```bash
npm run update-game-assets -- /path/to/Ue4Export
```

The importer updates the required source tables, synchronizes referenced item icons, removes orphaned icons, and generates `public/icarus-game/Data/D_CraftingCatalog.json`. Do not edit the generated catalog directly.

Regenerate and validate the catalog without importing a new export:

```bash
npm run catalog
npm run test:data
```

## Deployment Automation

A push to `main` runs tests and deploys the compiled static artifact. Configure the repository's Pages source as **GitHub Actions** before the first deployment. The container workflow publishes `latest` and commit-tagged images; tags matching `v*` additionally publish semantic-version image tags.
