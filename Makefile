CONTAINER_TAG ?= latest
EXPORT_FILE   ?= dist/netops-ai-images.tar.gz

.PHONY: build up down logs test lint fmt typecheck install-dev pre-commit pull-model export import release

# ── Dev setup ────────────────────────────────────────────────────────
install-dev:
	pip install -r backend/requirements-dev.txt
	pre-commit install --install-hooks

# ── Code quality ─────────────────────────────────────────────────────
lint:
	ruff check backend/

fmt:
	ruff format backend/
	ruff check --fix backend/

typecheck:
	mypy backend/ --ignore-missing-imports

pre-commit:
	pre-commit run --all-files

# ── Tests ────────────────────────────────────────────────────────────
test:
	pytest backend/tests/ -v \
		--cov=backend \
		--cov-report=term-missing \
		--cov-fail-under=70

test-fast:
	pytest backend/tests/ -v -x --no-cov

# ── Docker ───────────────────────────────────────────────────────────
build:
	docker compose build --no-cache

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

pull-model:
	docker exec sentinel_ollama ollama pull qwen2.5:3b

# ── Air-gap bundle ───────────────────────────────────────────────────
export:
	mkdir -p dist
	docker save \
		$$(docker compose config --images | tr '\n' ' ') \
	| gzip > $(EXPORT_FILE)
	@echo "Air-gap bundle → $(EXPORT_FILE)"

import:
	docker load < $(EXPORT_FILE)
	docker compose up -d

# ── Release ──────────────────────────────────────────────────────────
# Usage: make release VERSION=1.2.0
release:
	@test -n "$(VERSION)" || (echo "Usage: make release VERSION=x.y.z" && exit 1)
	git tag -a "v$(VERSION)" -m "Release v$(VERSION)"
	git push origin "v$(VERSION)"
