# Winter Olympics 2026 Medal Table Scraper

Scrapes the medal standings for the Milano Cortina 2026 Winter Olympics from the [official Olympics website](https://www.olympics.com/en/milano-cortina-2026/medals).

Produces four dated CSV files:
- `medals_YYYY-MM-DD.csv` — full medal table with gender breakdowns (16 columns)
- `medals_men_YYYY-MM-DD.csv` — men's events only
- `medals_women_YYYY-MM-DD.csv` — women's events only
- `medals_mixed_YYYY-MM-DD.csv` — mixed events only

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## Setup

```sh
make install
```

This runs `uv sync --all-groups`, which creates a virtual environment in `.venv/` and installs everything from the lockfile.

## Usage

```sh
make run
```

This fetches the latest medal standings, runs a sanity check that gender breakdowns add up to the totals, and writes the four CSV files.

## Development

```sh
make lint       # ruff check + format check
make format     # auto-fix lint issues and format code
make test       # run unit and e2e tests
make clean      # remove generated CSV files
```

## CI

GitHub Actions workflows run on PRs to `main`:
- **Lint** (`.github/workflows/lint.yml`) — ruff check and format check
- **Test** (`.github/workflows/test.yml`) — full pytest suite
