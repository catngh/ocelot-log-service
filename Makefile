.PHONY: help setup dev test test-cov lint clean deploy sqs-worker sync-opensearch

help:  ## Show this help menu
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup:  ## Set up the development environment
	python3 -m venv venv
	. venv/bin/activate && pip install -r requirements.txt


dev:  ## Run the development server
	. venv/bin/activate && python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

sync-opensearch:  ## Sync logs from MongoDB to OpenSearch
	. venv/bin/activate && python3 scripts/sync_mongodb_to_opensearch.py

test:  ## Run tests
	. venv/bin/activate && python3 tests/run_tests.py

test-cov:  ## Run tests with coverage report
	. venv/bin/activate && python3 tests/run_tests.py --cov=app --cov-report=term --cov-report=html

lint:  ## Run linters
	. venv/bin/activate && flake8 app/ tests/

clean:  ## Clean up temporary files
	rm -rf __pycache__
	rm -rf .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf htmlcov
	rm -f .coverage

deploy:  ## Deploy to AWS
	. venv/bin/activate && python3 infrastructure/deploy.py

docker-build:  ## Build Docker image
	docker build -t ocelot-log-service .

docker-run:  ## Run Docker container locally
	docker run -p 8000:8000 --env-file .env ocelot-log-service

docker-compose-up:  ## Run with docker-compose
	docker-compose -f infrastructure/docker-compose.yml up

docker-compose-down:  ## Stop docker-compose
	docker-compose -f infrastructure/docker-compose.yml down 