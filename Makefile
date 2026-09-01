.PHONY: install requirements-tools requirements-lock requirements-check dev build test catalog update-game-assets docker-build security-scan

PYTHON ?= python3
PIP_VERSION := 25.3
PIP_TOOLS_VERSION := 7.5.3

## install — install all frontend and backend dependencies
install:
	npm install
	$(PYTHON) -m pip install --require-hashes -r backend/requirements.txt

## requirements-tools — install the pinned Python lockfile toolchain
requirements-tools:
	$(PYTHON) -m pip install "pip==$(PIP_VERSION)" "pip-tools==$(PIP_TOOLS_VERSION)"

## requirements-lock — update the Python lockfile from direct dependencies
requirements-lock: requirements-tools
	CUSTOM_COMPILE_COMMAND='make requirements-lock' $(PYTHON) -m piptools compile --upgrade --generate-hashes --strip-extras --output-file=backend/requirements.txt backend/requirements.in

## requirements-check — verify direct dependencies and the lockfile agree
requirements-check: requirements-tools
	@lock_check="$$(mktemp)"; trap 'rm -f "$$lock_check"' EXIT; \
		CUSTOM_COMPILE_COMMAND='make requirements-lock' $(PYTHON) -m piptools compile --quiet --generate-hashes --strip-extras --output-file="$$lock_check" backend/requirements.in; \
		diff --unified backend/requirements.txt "$$lock_check"

## dev — start Vite dev server and FastAPI backend concurrently
##        Copy .env.example to .env to configure optional SSO
dev:
	@trap 'kill 0' INT; \
	uvicorn backend.main:app --reload --port 8001 & \
	npm run dev; \
	wait

## build — compile the Vue frontend into dist/
build:
	npm run build

## test — run frontend and game-data tests
test:
	npm test
	npm run test:data
	npm run build
	npm run test:backend
	npm run test:pwa
	npm run prepare:pages

## catalog — regenerate and audit the crafting catalog from public game data
catalog:
	npm run catalog

## update-game-assets DIR=... — sync assets from a UE4 export directory
##   Example: make update-game-assets DIR=~/exports/IcarusExport
update-game-assets:
	@if [ -z "$(DIR)" ]; then \
		echo "Usage: make update-game-assets DIR=/path/to/UE4Export"; \
		exit 1; \
	fi
	python3 scripts/scan_assets.py $(DIR)

## docker-build — build the application container locally
docker-build:
	docker build -t prospector:local .

## security-scan — build and scan for vulnerabilities with available fixes
security-scan: docker-build
	docker run --rm \
		-v /var/run/docker.sock:/var/run/docker.sock \
		-v "$(CURDIR):/work:ro" \
		anchore/grype:latest docker:prospector:local --only-fixed --vex /work/security/openvex.json
	docker run --rm \
		-v /var/run/docker.sock:/var/run/docker.sock \
		aquasec/trivy:latest image --scanners vuln --ignore-unfixed \
		--severity MEDIUM,HIGH,CRITICAL --exit-code 1 prospector:local
