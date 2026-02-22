import csv
import json
import sys

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
        medals = entry["medalsNumber"][0]
        results.append(
            {
                "rank": entry["rank"],
                "code": entry["organisation"],
                "country": entry["description"],
                "gold": medals["gold"],
                "silver": medals["silver"],
                "bronze": medals["bronze"],
                "total": medals["total"],
            }
        )

    return results


def save_csv(data: list[dict], path: str = "medals.csv") -> None:
    fieldnames = ["rank", "code", "country", "gold", "silver", "bronze", "total"]
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
    save_csv(data)


if __name__ == "__main__":
    main()
