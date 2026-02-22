import csv
import json
import sys

import requests
import truststore
from bs4 import BeautifulSoup

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
        print(
            "Error: no embedded JSON data found. The page structure may have changed.",
            file=sys.stderr,
        )
        sys.exit(1)

    page_data = json.loads(script_tag.string)
    medals_table = (
        page_data.get("result_medals_data", {})
        .get("initialMedals", {})
        .get("medalStandings", {})
        .get("medalsTable", [])
    )
    if not medals_table:
        print("Error: no medal table data found in JSON.", file=sys.stderr)
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


def print_table(data: list[dict]) -> None:
    header = (
        f"{'Rank':<6} {'Code':<6} {'Country':<30} "
        f"{'Gold':>6} {'Silver':>8} {'Bronze':>8} {'Total':>7}"
    )
    print(header)
    print("-" * len(header))
    for row in data:
        print(
            f"{row['rank']:<6} {row['code']:<6} {row['country']:<30} "
            f"{row['gold']:>6} {row['silver']:>8} {row['bronze']:>8} {row['total']:>7}"
        )
    print("-" * len(header))
    totals = {k: sum(r[k] for r in data) for k in ("gold", "silver", "bronze", "total")}
    print(
        f"{'':>6} {'':>6} {'Total':<30} "
        f"{totals['gold']:>6} {totals['silver']:>8} {totals['bronze']:>8} {totals['total']:>7}"
    )


def save_csv(data: list[dict], path: str = "medals.csv") -> None:
    fieldnames = ["rank", "code", "country", "gold", "silver", "bronze", "total"]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    print(f"\nSaved to {path}")


def main() -> None:
    print(f"Fetching medal table from {URL} ...")
    soup = fetch_page(URL)
    data = parse_medal_table(soup)
    print(f"Found {len(data)} countries\n")
    print_table(data)
    save_csv(data)


if __name__ == "__main__":
    main()
