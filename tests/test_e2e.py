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
            "code",
            "country",
            "gold",
            "silver",
            "bronze",
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
                assert field in row, f"Missing field '{field}' in {row['code']}"

    def test_medal_counts_are_non_negative(self, live_data):
        medal_fields = [
            "gold",
            "silver",
            "bronze",
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

    def test_total_equals_gold_silver_bronze(self, live_data):
        for row in live_data:
            assert row["gold"] + row["silver"] + row["bronze"] == row["total"], (
                f"{row['country']}: {row['gold']}+{row['silver']}+{row['bronze']} != {row['total']}"
            )

    def test_gender_totals_add_up(self, live_data):
        for row in live_data:
            for medal in ("gold", "silver", "bronze"):
                gender_sum = row[f"men_{medal}"] + row[f"women_{medal}"] + row[f"mixed_{medal}"]
                assert gender_sum == row[medal], (
                    f"{row['country']} {medal}: "
                    f"{row[f'men_{medal}']}+{row[f'women_{medal}']}"
                    f"+{row[f'mixed_{medal}']} != {row[medal]}"
                )

    def test_country_codes_are_three_letters(self, live_data):
        for row in live_data:
            assert len(row["code"]) == 3, f"Bad code: {row['code']}"
            assert row["code"].isalpha(), f"Non-alpha code: {row['code']}"

    def test_ranks_are_positive(self, live_data):
        for row in live_data:
            assert row["rank"] >= 1

    def test_no_duplicate_country_codes(self, live_data):
        codes = [row["code"] for row in live_data]
        assert len(codes) == len(set(codes))

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
