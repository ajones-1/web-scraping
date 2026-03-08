"""End-to-end test that fetches live data from olympics.com and validates the full pipeline."""

import csv

import pandas as pd
import pytest
import truststore

truststore.inject_into_ssl()

from main import (
    URL,
    fetch_page,
    parse_medal_table,
    save_csv,
    save_gender_csvs,
)


@pytest.fixture(scope="module")
def live_data():
    soup = fetch_page(URL)
    return parse_medal_table(soup)


class TestE2E:
    def test_fetches_at_least_one_country(self, live_data):
        assert len(live_data) > 0

    def test_all_rows_have_required_fields(self, live_data):
        required = [
            "rank",
            "country",
            "total_women",
            "total_men",
            "total_mixed",
            "total",
            "men_gold",
            "men_silver",
            "men_bronze",
            "women_gold",
            "women_silver",
            "women_bronze",
            "mixed_gold",
            "mixed_silver",
            "mixed_bronze",
        ]
        for row in live_data:
            for field in required:
                assert field in row, f"Missing field '{field}' in {row['country']}"

    def test_medal_counts_are_non_negative(self, live_data):
        medal_fields = [
            "total_women",
            "total_men",
            "total_mixed",
            "total",
            "men_gold",
            "men_silver",
            "men_bronze",
            "women_gold",
            "women_silver",
            "women_bronze",
            "mixed_gold",
            "mixed_silver",
            "mixed_bronze",
        ]
        for row in live_data:
            for field in medal_fields:
                assert row[field] >= 0, f"{row['country']} has negative {field}"

    def test_total_equals_gender_sums(self, live_data):
        for row in live_data:
            assert row["total_women"] + row["total_men"] + row["total_mixed"] == row["total"], (
                f"{row['country']}: {row['total_women']}+{row['total_men']}+{row['total_mixed']}"
                f" != {row['total']}"
            )

    def test_gender_totals_add_up(self, live_data):
        for row in live_data:
            women_sum = row["women_gold"] + row["women_silver"] + row["women_bronze"]
            assert women_sum == row["total_women"], (
                f"{row['country']} women: {women_sum} != {row['total_women']}"
            )
            men_sum = row["men_gold"] + row["men_silver"] + row["men_bronze"]
            assert men_sum == row["total_men"], (
                f"{row['country']} men: {men_sum} != {row['total_men']}"
            )
            mixed_sum = row["mixed_gold"] + row["mixed_silver"] + row["mixed_bronze"]
            assert mixed_sum == row["total_mixed"], (
                f"{row['country']} mixed: {mixed_sum} != {row['total_mixed']}"
            )

    def test_ranks_are_positive(self, live_data):
        for row in live_data:
            assert row["rank"] >= 1

    def test_no_duplicate_countries(self, live_data):
        countries = [row["country"] for row in live_data]
        assert len(countries) == len(set(countries))

    def test_full_pipeline_writes_csvs(self, live_data, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        save_csv(live_data, str(tmp_path / "medals.csv"))
        save_gender_csvs(live_data, "test")

        # Verify main CSV
        with open(tmp_path / "medals.csv") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == len(live_data)

        # Verify gender CSVs exist and have fewer or equal rows
        for gender in ("men", "women", "mixed"):
            df = pd.read_csv(tmp_path / f"medals_{gender}_test.csv")
            assert len(df) <= len(live_data)
