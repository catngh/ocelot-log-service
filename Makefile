.PHONY: help setup dev dev-consumer test test-cov lint clean deploy docker-build-api docker-build-consumer docker-run-api docker-run-consumer docker-build-all

help:  ## Show this help menu
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup:  ## Set up the development environment
	python3 -m venv venv
	. venv/bin/activate && pip install -r requirements.txt


dev:  ## Run the API development server
	. venv/bin/activate && python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

dev-consumer:  ## Run the Consumer service in development mode
	. venv/bin/activate && python3 consumer.py

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

docker-build-api:  ## Build API service Docker image
	docker build -t ocelot-log-service-api -f Dockerfile.api .

docker-build-consumer:  ## Build Consumer service Docker image
	docker build -t ocelot-log-service-consumer -f Dockerfile.consumer .

docker-build-all:  ## Build both API and Consumer Docker images
	$(MAKE) docker-build-api
	$(MAKE) docker-build-consumer

docker-run-api:  ## Run API service Docker container locally
	docker run -p 8000:8000 --env-file .env ocelot-log-service-api

docker-run-consumer:  ## Run Consumer service Docker container locally
	docker run --env-file .env ocelot-log-service-consumer