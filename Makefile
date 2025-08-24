# Serverless ECS Scaler Makefile
# Common commands for development and deployment

.PHONY: help install test lint format clean deploy deploy-dev deploy-prod remove logs

# Default target
help:
	@echo "Serverless ECS Scaler - Available Commands:"
	@echo ""
	@echo "Development:"
	@echo "  install     Install Python and Node.js dependencies"
	@echo "  test        Run unit tests with pytest"
	@echo "  lint        Run linting with flake8"
	@echo "  format      Format code with black"
	@echo "  clean       Clean up generated files"
	@echo ""
	@echo "Deployment:"
	@echo "  deploy      Deploy to default environment (dev)"
	@echo "  deploy-dev  Deploy to development environment"
	@echo "  deploy-prod Deploy to production environment"
	@echo "  remove      Remove deployment"
	@echo "  logs        Show Lambda function logs"
	@echo ""
	@echo "Examples:"
	@echo "  make deploy CLUSTER=my-cluster SERVICE=my-service QUEUE=my-queue"
	@echo "  make deploy-prod CLUSTER=prod-cluster SERVICE=prod-service QUEUE=prod-queue"

# Variables
STAGE ?= dev
REGION ?= us-east-1
CLUSTER ?= your-cluster-name
SERVICE ?= your-service-name
QUEUE ?= your-queue-name
SCALE_UP_TARGET ?= 1
SCALE_DOWN_THRESHOLD ?= 2

# Install dependencies
install:
	@echo "Installing Python dependencies..."
	pip install -r requirements-dev.txt
	@echo "Installing Node.js dependencies..."
	npm install
	@echo "Installing pre-commit hooks..."
	pre-commit install

# Run tests
test:
	@echo "Running tests..."
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term

# Run linting
lint:
	@echo "Running linting..."
	flake8 src/ tests/ --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 src/ tests/ --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

# Format code
format:
	@echo "Formatting code..."
	black src/ tests/
	isort src/ tests/

# Clean up
clean:
	@echo "Cleaning up..."
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .serverless/
	rm -rf node_modules/
	rm -rf __pycache__/
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

# Deploy to default environment
deploy: deploy-dev

# Deploy to development
deploy-dev:
	@echo "Deploying to development environment..."
	serverless deploy \
		--stage $(STAGE) \
		--region $(REGION) \
		--cluster $(CLUSTER) \
		--service $(SERVICE) \
		--queue $(QUEUE) \
		--scale-up-target $(SCALE_UP_TARGET) \
		--scale-down-threshold $(SCALE_DOWN_THRESHOLD) \
		--verbose

# Deploy to production
deploy-prod:
	@echo "Deploying to production environment..."
	serverless deploy \
		--stage prod \
		--region $(REGION) \
		--cluster $(CLUSTER) \
		--service $(SERVICE) \
		--queue $(QUEUE) \
		--scale-up-target $(SCALE_UP_TARGET) \
		--scale-down-threshold $(SCALE_DOWN_THRESHOLD) \
		--verbose

# Remove deployment
remove:
	@echo "Removing deployment..."
	serverless remove --stage $(STAGE) --region $(REGION) --verbose

# Show logs
logs:
	@echo "Showing Lambda function logs..."
	serverless logs -f ecsScaler --stage $(STAGE) --tail

# Security check
security:
	@echo "Running security checks..."
	safety check
	bandit -r src/ -f json -o bandit-report.json

# Pre-commit hooks
pre-commit:
	@echo "Running pre-commit hooks..."
	pre-commit run --all-files

# Local testing
test-local:
	@echo "Setting up test environment variables..."
	@export SQS_QUEUE_URL="test-queue-url"
	@export ECS_CLUSTER_NAME="$(CLUSTER)"
	@export ECS_SERVICE_NAME="$(SERVICE)"
	@export SCALE_UP_TARGET="$(SCALE_UP_TARGET)"
	@export SCALE_DOWN_THRESHOLD="$(SCALE_DOWN_THRESHOLD)"
	@echo "Running Lambda function locally..."
	python src/scaler.py

# Performance test
perf-test:
	@echo "Running performance test..."
	@echo "Sending test messages to trigger scaling..."
	@for i in {1..5}; do \
		aws sqs send-message \
			--queue-url $$(aws sqs get-queue-url --queue-name $(QUEUE) --region $(REGION) --output text) \
			--message-body "{\"test\": \"message $$i\"}" \
			--region $(REGION); \
	done
	@echo "Monitoring scaling behavior..."
	@echo "Check ECS service status with:"
	@echo "aws ecs describe-services --cluster $(CLUSTER) --services $(SERVICE) --region $(REGION)"

# Documentation
docs:
	@echo "Generating documentation..."
	@echo "Documentation is available in:"
	@echo "  - README.md (main documentation)"
	@echo "  - examples/ (configuration examples)"
	@echo "  - docs/ (additional documentation)"

# Release preparation
release:
	@echo "Preparing release..."
	@echo "Current version: $$(node -p "require('./package.json').version")"
	@echo "Please update version in package.json and create a git tag"
	@echo "Example: git tag v1.0.0 && git push origin v1.0.0"

# Quick start
quick-start:
	@echo "Quick start guide:"
	@echo "1. Install dependencies: make install"
	@echo "2. Configure your ECS cluster, service, and queue names"
	@echo "3. Deploy: make deploy CLUSTER=my-cluster SERVICE=my-service QUEUE=my-queue"
	@echo "4. Test: make perf-test"
	@echo "5. Monitor: make logs"
