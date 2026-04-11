.PHONY: install install-all test test-quick test-cov lint format clean help

## Default target
help:
	@echo "ASI:BUILD development targets:"
	@echo ""
	@echo "  install      Install package with dev dependencies"
	@echo "  install-all  Install package with ALL optional dependencies"
	@echo "  test         Run full test suite (verbose)"
	@echo "  test-quick   Run tests, stop on first failure"
	@echo "  test-cov     Run tests with coverage report"
	@echo "  lint         Check formatting (black) + types (mypy)"
	@echo "  format       Auto-format with black"
	@echo "  clean        Remove __pycache__, .pyc, build artifacts"

## Install with dev dependencies
install:
	pip install -e ".[dev]"

## Install with all optional dependencies
install-all:
	pip install -e ".[all]"

## Run full test suite
test:
	pytest tests/ -v

## Quick test run — stops on first failure
test-quick:
	pytest tests/ -x -q

## Run tests with coverage report
test-cov:
	pytest tests/ -v --cov=asi_build --cov-report=term-missing --cov-report=html:htmlcov
	@echo "Coverage HTML report: htmlcov/index.html"

## Check formatting and types
lint:
	black --check src/ tests/
	mypy src/asi_build/

## Auto-format with black
format:
	black src/ tests/

## Remove all cache and build artifacts
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ .pytest_cache/ .mypy_cache/ htmlcov/ .coverage
