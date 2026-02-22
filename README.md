# Winter Olympics 2026 Medal Table Scraper

Scrapes the medal standings for the Milano Cortina 2026 Winter Olympics from the [official Olympics website](https://www.olympics.com/en/milano-cortina-2026/medals).

Outputs a formatted table to the terminal and saves the results to `medals.csv`.

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## Setup

Install all dependencies (including dev tools like ruff):

```sh
make install
```

This runs `uv sync --all-groups`, which creates a virtual environment in `.venv/` and installs everything from the lockfile.

## Usage

```sh
make run
```

Example output:

```
Rank   Code   Country                          Gold   Silver   Bronze   Total
-----------------------------------------------------------------------------
1      NOR    Norway                             18       11       11      40
2      USA    United States of America           11       12        9      32
3      NED    Netherlands                        10        7        3      20
...
```

Results are saved to `medals.csv`.

## Development

Lint:

```sh
make lint
```

Auto-format:

```sh
make format
```

Clean generated files:

```sh
make clean
```
