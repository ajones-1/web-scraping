.PHONY: install run lint format test clean

install:
	uv sync --all-groups

run:
	uv run main.py

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

test:
	uv run pytest

clean:
	rm -f medals.csv
	rm -rf __pycache__
