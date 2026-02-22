.PHONY: install run lint format clean

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

clean:
	rm -f medals.csv
	rm -rf __pycache__
