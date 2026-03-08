import csv
import json
import sys
from datetime import datetime

import pandas as pd
import requests
import truststore
from bs4 import BeautifulSoup
from loguru import logger

from config import URL, HEADERS

truststore.inject_into_ssl()


def fetch_page(url: str) -> BeautifulSoup:
    """
    Fetch the page content and return a BeautifulSoup object.
    Args:
        url: The URL of the page to fetch.
    Returns:
        BeautifulSoup object of the page content.
    """
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def parse_medal_table(soup: BeautifulSoup) -> list[dict]:
    """
    Parse the medal table data from the page's embedded JSON.

    Args:
        soup: BeautifulSoup object of the page content.
    Returns:
        A list of dictionaries, each containing medal counts and related info for a country.
    """
    # The page uses a virtualized list that only SSR-renders ~19 rows.
    # The full dataset is in an embedded JSON script block.
    script_tag = soup.find("script", attrs={"type": "application/json"})
    if not script_tag or not script_tag.string:
        logger.error("Error: no embedded JSON data found. The page structure may have changed.")
        sys.exit(1)

    page_data = json.loads(script_tag.string)
    medals_table = (
        page_data.get("result_medals_data", {})
        .get("initialMedals", {})
        .get("medalStandings", {})
        .get("medalsTable", [])
    )
    if not medals_table:
        logger.error("Error: no medal table data found in JSON.")
        sys.exit(1)

    results = []
    for entry in medals_table:
        by_type = {m["type"]: m for m in entry["medalsNumber"]}
        totals = by_type["Total"]
        men = by_type.get("Men", {})
        women = by_type.get("Women", {})
        mixed = by_type.get("Mixed", {})
        results.append(
            {
                "rank": entry["rank"],
                "country": entry["description"],
                "gold": totals["gold"],
                "silver": totals["silver"],
                "bronze": totals["bronze"],
                "total": totals["total"],
                "men_gold": men.get("gold", 0),
                "men_silver": men.get("silver", 0),
                "men_bronze": men.get("bronze", 0),
                "women_gold": women.get("gold", 0),
                "women_silver": women.get("silver", 0),
                "women_bronze": women.get("bronze", 0),
                "mixed_gold": mixed.get("gold", 0),
                "mixed_silver": mixed.get("silver", 0),
                "mixed_bronze": mixed.get("bronze", 0),
            }
        )

    return results


def check_gender_totals_add_up(data: list[dict]) -> None:
    """
    A sanity check to ensure the total medals for each country and type match the sum of the
    gender-specific counts. This is not a test of the code itself, but rather a check that the
    source data is consistent and correctly parsed.

    Args:
        data: List of dictionaries containing medal counts for each country.
    """
    mismatches = 0
    for row in data:
        country = row["country"]
        for medal in ("gold", "silver", "bronze"):
            gender_sum = row[f"men_{medal}"] + row[f"women_{medal}"] + row[f"mixed_{medal}"]
            if gender_sum != row[medal]:
                logger.warning(
                    f"{country} {medal} mismatch: men({row[f'men_{medal}']})"
                    f" + women({row[f'women_{medal}']})"
                    f" + mixed({row[f'mixed_{medal}']})"
                    f" = {gender_sum}, expected {row[medal]}"
                )
                mismatches += 1
    if mismatches:
        logger.warning(f"{mismatches} gender total mismatch(es) found")
    else:
        logger.info("All gender totals add up correctly!")


def save_csv(data: list[dict], path: str = "medals.csv") -> None:
    """
    Save data to a CSV file.
    Args:
        data: List of dictionaries containing data to save.
        path: The file path to save the CSV to.
    """
    fieldnames = [
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
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    logger.info(f"Saved to {path}")


def save_gender_csvs(data: list[dict], date_str: str) -> None:
    """
    Create separate medal table CSVs for men, women, and mixed events.

    Each CSV contains country, gold, silver, bronze, and total columns,
    sorted by gold (desc), silver (desc), bronze (desc).

    Args:
        data: List of dictionaries containing medal counts for each country.
        date_str: String to include in the filename, typically the current date.
    """
    df = pd.DataFrame(data)

    gender_configs = {
        "men": ("men_gold", "men_silver", "men_bronze"),
        "women": ("women_gold", "women_silver", "women_bronze"),
        "mixed": ("mixed_gold", "mixed_silver", "mixed_bronze"),
    }

    for gender, (gold_col, silver_col, bronze_col) in gender_configs.items():
        gender_df = df[["country", gold_col, silver_col, bronze_col]].copy()
        gender_df = gender_df.rename(
            columns={gold_col: "gold", silver_col: "silver", bronze_col: "bronze"}
        )
        gender_df["total"] = gender_df["gold"] + gender_df["silver"] + gender_df["bronze"]
        gender_df = gender_df[gender_df["total"] > 0]
        gender_df = gender_df.sort_values(
            ["gold", "silver", "bronze"], ascending=False, ignore_index=True
        )
        gender_df.insert(0, "rank", range(1, len(gender_df) + 1))

        path = f"medals_{gender}_{date_str}.csv"
        gender_df.to_csv(path, index=False)
        logger.info(f"Saved {gender} medals ({len(gender_df)} countries) to {path}")


def main() -> None:
    logger.info(f"Fetching medal table from {URL} ...")
    soup = fetch_page(URL)
    data = parse_medal_table(soup)
    logger.info(f"Found {len(data)} countries\n")

    logger.info("Running sanity checks on parsed data...")
    check_gender_totals_add_up(data)

    logger.info("Saving data to CSV...")
    current_date = datetime.now().strftime("%Y-%m-%d")
    save_csv(data, f"medals_{current_date}.csv")
    save_gender_csvs(data, current_date)

    logger.info("Script Completed!")


if __name__ == "__main__":
    main()
