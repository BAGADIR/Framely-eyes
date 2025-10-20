# Framely-Eyes Makefile
# Convenience commands for development and deployment

.PHONY: help build up down restart logs test clean health analyze

help:  ## Show this help message
	@echo "Framely-Eyes - Video Perception OS"
	@echo ""
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# Docker commands
build:  ## Build Docker images
	docker compose -f docker/docker-compose.yml build

up:  ## Start all services
	docker compose -f docker/docker-compose.yml up -d
	@echo ""
	@echo "✓ Services started!"
	@echo "  API:   http://localhost:8000"
	@echo "  Docs:  http://localhost:8000/docs"
	@echo "  Qwen:  http://localhost:8001"
	@echo ""

down:  ## Stop all services
	docker compose -f docker/docker-compose.yml down

restart:  ## Restart all services
	docker compose -f docker/docker-compose.yml restart

logs:  ## Show logs (use 'make logs service=api' for specific service)
	@if [ -z "$(service)" ]; then \
		docker compose -f docker/docker-compose.yml logs -f; \
	else \
		docker compose -f docker/docker-compose.yml logs -f $(service); \
	fi

# Development commands
install:  ## Install Python dependencies locally
	pip install -r requirements.txt

format:  ## Format code with black and isort
	black services/
	isort services/

lint:  ## Lint code
	flake8 services/ --max-line-length=100
	mypy services/

test:  ## Run tests
	pytest services/qa/

smoke-test:  ## Run smoke test
	bash scripts/smoke_test.sh

# Utility commands
health:  ## Check service health
	@curl -s http://localhost:8000/health | jq '.'

analyze:  ## Analyze a video (use 'make analyze video_id=test url=https://...')
	@if [ -z "$(video_id)" ] || [ -z "$(url)" ]; then \
		echo "Usage: make analyze video_id=my_video url=https://example.com/video.mp4"; \
	else \
		curl -X POST http://localhost:8000/analyze \
			-H "Content-Type: application/json" \
			-d '{"video_id":"$(video_id)","media_url":"$(url)"}' | jq '.'; \
	fi

status:  ## Check video analysis status (use 'make status video_id=test')
	@if [ -z "$(video_id)" ]; then \
		echo "Usage: make status video_id=my_video"; \
	else \
		curl -s http://localhost:8000/status/$(video_id) | jq '.'; \
	fi

result:  ## Get analysis result (use 'make result video_id=test')
	@if [ -z "$(video_id)" ]; then \
		echo "Usage: make result video_id=my_video"; \
	else \
		curl -s http://localhost:8000/result/$(video_id) | jq '.'; \
	fi

clean:  ## Clean up generated files and containers
	docker compose -f docker/docker-compose.yml down -v
	rm -rf store/*
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "smoke_test_vab_*.json" -delete

# Documentation
docs:  ## Open documentation
	@echo "Opening documentation..."
	@echo "  README:        file://$(PWD)/README.md"
	@echo "  QUICKSTART:    file://$(PWD)/QUICKSTART.md"
	@echo "  ARCHITECTURE:  file://$(PWD)/ARCHITECTURE.md"
	@echo "  API Docs:      http://localhost:8000/docs"

# Quick setup
setup: build up health  ## Complete setup (build + start + health check)
	@echo ""
	@echo "✓ Setup complete!"
	@echo "  Run 'make analyze video_id=test url=YOUR_VIDEO_URL' to test"

# Default target
.DEFAULT_GOAL := help
