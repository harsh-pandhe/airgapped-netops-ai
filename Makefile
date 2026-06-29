CONTAINER_TAG ?= latest
EXPORT_FILE   ?= dist/sentinel-mpls-images.tar.gz

.PHONY: build up down logs test pull-model export import

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

test:
	cd backend && python -m pytest tests/ -v

export:
	mkdir -p dist
	docker save \
		$$(docker compose config --images | tr '\n' ' ') \
		sentinel_backend sentinel_frontend \
	| gzip > $(EXPORT_FILE)
	@echo "Saved to $(EXPORT_FILE)"

import:
	docker load < $(EXPORT_FILE)
	docker compose up -d