import csv
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
    rows = soup.find_all("div", attrs={"data-testid": "noc-row"})
    if not rows:
        print("Error: no medal rows found. The page structure may have changed.", file=sys.stderr)
        sys.exit(1)

    results = []
    for rank, row in enumerate(rows, start=1):
        cells = row.find_all("div", attrs={"role": "cell"})
        # cells: [rank_cell, country_cell, gold, silver, bronze, total, details_button]
        if len(cells) < 6:
            continue

        country_cell = cells[1]
        code_span = country_cell.find("span", attrs={"translate": "no"})
        code = code_span.get_text(strip=True) if code_span else ""
        # The country name is in a second translate="no" span
        name_spans = country_cell.find_all("span", attrs={"translate": "no"})
        name = name_spans[1].get_text(strip=True) if len(name_spans) > 1 else code

        gold = cells[2].get_text(strip=True)
        silver = cells[3].get_text(strip=True)
        bronze = cells[4].get_text(strip=True)
        total = cells[5].get_text(strip=True)

        results.append(
            {
                "rank": rank,
                "code": code,
                "country": name,
                "gold": int(gold),
                "silver": int(silver),
                "bronze": int(bronze),
                "total": int(total),
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
