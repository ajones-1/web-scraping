import csv
import json
import sys
from datetime import datetime

import requests
import truststore
from bs4 import BeautifulSoup
from loguru import logger

truststore.inject_into_ssl()

URL = "https://www.olympics.com/en/milano-cortina-2026/medals"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "identity",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


def fetch_page(url: str) -> BeautifulSoup:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def parse_medal_table(soup: BeautifulSoup) -> list[dict]:
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
                "code": entry["organisation"],
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


def save_csv(data: list[dict], path: str = "medals.csv") -> None:
    fieldnames = [
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
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    logger.info(f"Saved to {path}")


def main() -> None:
    logger.info(f"Fetching medal table from {URL} ...")
    soup = fetch_page(URL)
    data = parse_medal_table(soup)
    logger.info(f"Found {len(data)} countries\n")
    current_date = datetime.now().strftime("%Y-%m-%d")
    save_csv(data, f"medals_{current_date}.csv")
    logger.info("Script Completed.")


if __name__ == "__main__":
    main()
