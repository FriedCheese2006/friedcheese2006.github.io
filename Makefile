.PHONY: install dev build test catalog update-game-assets docker-build security-scan

## install — install all frontend and backend dependencies
install:
	npm install
	pip install -r backend/requirements.txt

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
	docker build -t icarus-calc:local .

## security-scan — build and scan for vulnerabilities with available fixes
security-scan: docker-build
	docker run --rm \
		-v /var/run/docker.sock:/var/run/docker.sock \
		-v "$(CURDIR):/work:ro" \
		anchore/grype:latest docker:icarus-calc:local --only-fixed --vex /work/security/openvex.json
