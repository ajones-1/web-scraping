import csv
import io
import json

import pandas as pd
import pytest
from bs4 import BeautifulSoup
from loguru import logger

from main import check_gender_totals_add_up, parse_medal_table, save_csv, save_gender_csvs


def _make_medal_entry(code, name, rank=1, men=(0, 0, 0), women=(0, 0, 0), mixed=(0, 0, 0)):
    """Helper to build a medal table JSON entry matching the olympics.com structure."""
    total = tuple(m + w + x for m, w, x in zip(men, women, mixed))
    return {
        "organisation": code,
        "description": name,
        "rank": rank,
        "medalsNumber": [
            {"type": "Men", "gold": men[0], "silver": men[1], "bronze": men[2], "total": sum(men)},
            {
                "type": "Women",
                "gold": women[0],
                "silver": women[1],
                "bronze": women[2],
                "total": sum(women),
            },
            {
                "type": "Mixed",
                "gold": mixed[0],
                "silver": mixed[1],
                "bronze": mixed[2],
                "total": sum(mixed),
            },
            {
                "type": "Total",
                "gold": total[0],
                "silver": total[1],
                "bronze": total[2],
                "total": sum(total),
            },
        ],
    }


def _build_soup(entries):
    """Wrap medal entries in the page JSON structure and embed in HTML."""
    page_data = {
        "result_medals_data": {
            "initialMedals": {
                "medalStandings": {
                    "medalsTable": entries,
                }
            }
        }
    }
    html = f'<html><body><script type="application/json">{json.dumps(page_data)}</script></body>'
    return BeautifulSoup(html, "html.parser")


SAMPLE_ENTRIES = [
    _make_medal_entry("NOR", "Norway", rank=1, men=(10, 3, 5), women=(3, 4, 2), mixed=(1, 0, 1)),
    _make_medal_entry("USA", "United States", rank=2, men=(2, 4, 1), women=(5, 1, 3)),
    _make_medal_entry("BEL", "Belgium", rank=3, mixed=(0, 0, 1)),
]


# --- parse_medal_table ---


class TestParseMedalTable:
    def test_parses_all_countries(self):
        soup = _build_soup(SAMPLE_ENTRIES)
        data = parse_medal_table(soup)
        assert len(data) == 3

    def test_country_fields(self):
        soup = _build_soup(SAMPLE_ENTRIES)
        data = parse_medal_table(soup)
        nor = data[0]
        assert nor["country"] == "Norway"
        assert nor["rank"] == 1

    def test_total_medals(self):
        soup = _build_soup(SAMPLE_ENTRIES)
        data = parse_medal_table(soup)
        nor = data[0]
        assert nor["gold"] == 14
        assert nor["silver"] == 7
        assert nor["bronze"] == 8
        assert nor["total"] == 29

    def test_gender_breakdown(self):
        soup = _build_soup(SAMPLE_ENTRIES)
        data = parse_medal_table(soup)
        nor = data[0]
        assert nor["men_gold"] == 10
        assert nor["women_silver"] == 4
        assert nor["mixed_bronze"] == 1

    def test_missing_gender_defaults_to_zero(self):
        soup = _build_soup(SAMPLE_ENTRIES)
        data = parse_medal_table(soup)
        usa = data[1]
        assert usa["mixed_gold"] == 0
        assert usa["mixed_silver"] == 0
        assert usa["mixed_bronze"] == 0

    def test_exits_on_missing_json(self):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        with pytest.raises(SystemExit):
            parse_medal_table(soup)

    def test_exits_on_empty_medals_table(self):
        page_data = {
            "result_medals_data": {"initialMedals": {"medalStandings": {"medalsTable": []}}}
        }
        html = (
            f'<html><body><script type="application/json">{json.dumps(page_data)}</script></body>'
        )
        soup = BeautifulSoup(html, "html.parser")
        with pytest.raises(SystemExit):
            parse_medal_table(soup)


# --- check_gender_totals_add_up ---


class TestCheckGenderTotals:
    def test_no_warnings_when_consistent(self):
        soup = _build_soup(SAMPLE_ENTRIES)
        data = parse_medal_table(soup)
        sink = io.StringIO()
        handler_id = logger.add(sink, format="{message}")
        try:
            check_gender_totals_add_up(data)
        finally:
            logger.remove(handler_id)
        assert "mismatch" not in sink.getvalue().lower()

    def test_warns_on_mismatch(self):
        soup = _build_soup(SAMPLE_ENTRIES)
        data = parse_medal_table(soup)
        data[0]["gold"] = 999  # break the total
        sink = io.StringIO()
        handler_id = logger.add(sink, format="{message}")
        try:
            check_gender_totals_add_up(data)
        finally:
            logger.remove(handler_id)
        output = sink.getvalue()
        assert "mismatch" in output.lower()
        assert "Norway" in output


# --- save_csv ---


class TestSaveCsv:
    def test_writes_all_rows(self, tmp_path):
        soup = _build_soup(SAMPLE_ENTRIES)
        data = parse_medal_table(soup)
        path = tmp_path / "test.csv"
        save_csv(data, str(path))

        with open(path) as f:
            reader = list(csv.DictReader(f))
        assert len(reader) == 3

    def test_csv_columns(self, tmp_path):
        soup = _build_soup(SAMPLE_ENTRIES)
        data = parse_medal_table(soup)
        path = tmp_path / "test.csv"
        save_csv(data, str(path))

        with open(path) as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
        expected = [
            "rank",
            "country",
            "women_gold",
            "men_gold",
            "mixed_gold",
            "women_silver",
            "men_silver",
            "mixed_silver",
            "women_bronze",
            "men_bronze",
            "mixed_bronze",
            "gold",
            "silver",
            "bronze",
            "total",
        ]
        assert fieldnames == expected

    def test_csv_values_match_data(self, tmp_path):
        soup = _build_soup(SAMPLE_ENTRIES)
        data = parse_medal_table(soup)
        path = tmp_path / "test.csv"
        save_csv(data, str(path))

        with open(path) as f:
            rows = list(csv.DictReader(f))
        assert rows[0]["country"] == "Norway"
        assert rows[0]["gold"] == "14"
        assert rows[2]["country"] == "Belgium"


# --- save_gender_csvs ---


class TestSaveGenderCsvs:
    def test_creates_three_files(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        soup = _build_soup(SAMPLE_ENTRIES)
        data = parse_medal_table(soup)
        save_gender_csvs(data, "2026-01-01")

        assert (tmp_path / "medals_men_2026-01-01.csv").exists()
        assert (tmp_path / "medals_women_2026-01-01.csv").exists()
        assert (tmp_path / "medals_mixed_2026-01-01.csv").exists()

    def test_excludes_zero_medal_countries(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        soup = _build_soup(SAMPLE_ENTRIES)
        data = parse_medal_table(soup)
        save_gender_csvs(data, "2026-01-01")

        men_df = pd.read_csv(tmp_path / "medals_men_2026-01-01.csv")
        # BEL has no men's medals, only mixed
        assert "Belgium" not in men_df["country"].values

    def test_sorted_by_gold_desc(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        soup = _build_soup(SAMPLE_ENTRIES)
        data = parse_medal_table(soup)
        save_gender_csvs(data, "2026-01-01")

        women_df = pd.read_csv(tmp_path / "medals_women_2026-01-01.csv")
        golds = women_df["gold"].tolist()
        assert golds == sorted(golds, reverse=True)

    def test_gender_csv_columns(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        soup = _build_soup(SAMPLE_ENTRIES)
        data = parse_medal_table(soup)
        save_gender_csvs(data, "2026-01-01")

        men_df = pd.read_csv(tmp_path / "medals_men_2026-01-01.csv")
        expected_cols = ["rank", "country", "gold", "silver", "bronze", "total"]
        assert list(men_df.columns) == expected_cols

    def test_total_column_is_sum(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        soup = _build_soup(SAMPLE_ENTRIES)
        data = parse_medal_table(soup)
        save_gender_csvs(data, "2026-01-01")

        for gender in ("men", "women", "mixed"):
            df = pd.read_csv(tmp_path / f"medals_{gender}_2026-01-01.csv")
            expected_total = df["gold"] + df["silver"] + df["bronze"]
            assert (df["total"] == expected_total).all(), f"{gender} totals don't match"
