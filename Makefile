.PHONY: install dev test lint typecheck clean docker

install:
	pip install .

dev:
	pip install -e ".[dev,telegram,discord,slack]"

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=pyclaw --cov-report=term-missing

lint:
	ruff check src/ tests/

lint-fix:
	ruff check --fix src/ tests/

typecheck:
	mypy src/pyclaw/

clean:
	rm -rf build/ dist/ *.egg-info src/*.egg-info .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

docker:
	docker build -t pyclaw:latest .

docker-run:
	docker run --rm -v ~/.pyclaw:/root/.pyclaw pyclaw:latest
