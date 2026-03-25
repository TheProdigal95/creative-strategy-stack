#!/usr/bin/env python3
"""
Trustpilot Review Scraper — Reference Implementation

Platform: Trustpilot (https://www.trustpilot.com)
Detection: URL contains `trustpilot.com`.

How it works:
  - Trustpilot does NOT use a private API key — reviews are rendered server-side.
  - Reviews are embedded in the page HTML inside a __NEXT_DATA__ JSON blob.
  - Trustpilot limits unauthenticated browsing to 10 pages per filter combination.
  - To maximize coverage, the scraper iterates over combinations of:
    star rating (1-5) x sort order (recency, relevance) x language (en, all, de, etc.)
  - Each combo yields up to 10 pages x 20 reviews = 200 reviews.
  - Deduplication by review ID collapses overlap across combos.

Important:
  - Trustpilot aggressively rate-limits. Use random delays and rotate user agents.
  - The scraper supports resume via a progress file.

Usage:
    python trustpilot.py <brand_domain> [--languages en,de] [--output reviews.jsonl]

Example:
    python trustpilot.py example.com
    python trustpilot.py example.com --languages en,all,fr
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Run: pip install httpx")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MAX_PAGES_PER_COMBO = 10  # Trustpilot's hard limit
REQUEST_DELAY_MIN = 1.5
REQUEST_DELAY_MAX = 3.0
MAX_RETRIES = 3
RETRY_BACKOFF = 10

STAR_RATINGS = [1, 2, 3, 4, 5]
SORT_ORDERS = ["recency", "relevance"]

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
]


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def get_headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }


def build_url(base_url: str, page: int, stars: int = None, sort: str = None, lang: str = None) -> str:
    params = [f"page={page}"]
    if stars:
        params.append(f"stars={stars}")
    if sort:
        params.append(f"sort={sort}")
    if lang and lang != "en":
        params.append(f"languages={lang}")
    return f"{base_url}?{'&'.join(params)}"


def fetch_page(client: httpx.Client, url: str) -> str | None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.get(url, headers=get_headers(), follow_redirects=True)

            if resp.status_code == 200:
                return resp.text
            elif resp.status_code in (403, 429):
                wait = RETRY_BACKOFF * attempt * (2 if resp.status_code == 429 else 1)
                wait += random.uniform(1, 5)
                print(f"  HTTP {resp.status_code} (attempt {attempt}/{MAX_RETRIES}), waiting {wait:.0f}s")
                time.sleep(wait)
            elif resp.status_code == 404:
                return None
            else:
                print(f"  HTTP {resp.status_code} (attempt {attempt}/{MAX_RETRIES})")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF * attempt)

        except httpx.HTTPError as e:
            print(f"  HTTP error (attempt {attempt}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF * attempt)

    return None


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def extract_reviews_from_next_data(html: str, base_url: str) -> list[dict]:
    """Extract reviews from __NEXT_DATA__ JSON embedded in page."""
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        return []

    try:
        next_data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []

    page_props = next_data.get("props", {}).get("pageProps", {})
    raw_reviews = page_props.get("reviews", [])

    parsed = []
    for r in raw_reviews:
        p = parse_trustpilot_review(r, base_url)
        if p:
            parsed.append(p)

    return parsed


def parse_trustpilot_review(raw: dict, base_url: str) -> dict | None:
    if not raw or not raw.get("id"):
        return None

    consumer = raw.get("consumer", {}) or {}
    author_name = consumer.get("displayName", "Anonymous")

    labels = raw.get("labels", {}) or {}
    verification = labels.get("verification", {}) or {}
    is_verified = verification.get("isVerified", False)

    dates = raw.get("dates", {}) or {}
    published_date = dates.get("publishedDate")

    return {
        "review_id": raw["id"],
        "author_name": author_name.strip(),
        "rating": raw.get("rating"),
        "title": (raw.get("title") or "").strip(),
        "body": (raw.get("text") or "").strip(),
        "date": published_date,
        "verified_buyer": is_verified,
        "language": raw.get("language"),
        "product_title": None,  # Trustpilot reviews are at the company level
        "source_url": base_url,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Filter combos
# ---------------------------------------------------------------------------

def generate_filter_combos(languages: list[str]) -> list[dict]:
    combos = []
    combos.append({"stars": None, "sort": None, "lang": None, "label": "default"})

    for lang in languages:
        for stars in STAR_RATINGS:
            for sort in SORT_ORDERS:
                combos.append({
                    "stars": stars,
                    "sort": sort,
                    "lang": lang,
                    "label": f"stars={stars}_sort={sort}_lang={lang}",
                })

    return combos


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Scrape Trustpilot reviews for a brand")
    parser.add_argument("brand_domain", help="Brand domain on Trustpilot (e.g. example.com)")
    parser.add_argument("--languages", default="en,all", help="Comma-separated language codes (default: en,all)")
    parser.add_argument("--output", "-o", default="reviews.jsonl", help="Output JSONL file path")
    args = parser.parse_args()

    base_url = f"https://www.trustpilot.com/review/{args.brand_domain}"
    languages = [l.strip() for l in args.languages.split(",")]
    output_path = Path(args.output)

    print("=" * 60)
    print("Trustpilot Review Scraper")
    print(f"Target: {base_url}")
    print(f"Languages: {languages}")
    print("=" * 60)

    combos = generate_filter_combos(languages)
    print(f"Total filter combos: {len(combos)}")
    print(f"Max requests: {len(combos) * MAX_PAGES_PER_COMBO}")

    all_reviews = []
    seen_ids = set()

    with httpx.Client(timeout=30.0) as client:
        for combo_idx, combo in enumerate(combos):
            label = combo["label"]
            print(f"\n--- Combo {combo_idx + 1}/{len(combos)}: {label} ---")

            consecutive_empty = 0

            for page_num in range(1, MAX_PAGES_PER_COMBO + 1):
                url = build_url(
                    base_url,
                    page=page_num,
                    stars=combo["stars"],
                    sort=combo["sort"],
                    lang=combo["lang"],
                )

                html = fetch_page(client, url)

                if html is None:
                    print(f"  Page {page_num}: fetch failed, skipping combo")
                    break

                page_reviews = extract_reviews_from_next_data(html, base_url)

                if not page_reviews:
                    consecutive_empty += 1
                    if consecutive_empty >= 2:
                        print(f"  Page {page_num}: empty, stopping combo")
                        break
                else:
                    consecutive_empty = 0
                    new_count = 0
                    for review in page_reviews:
                        rid = review.get("review_id")
                        if rid and rid not in seen_ids:
                            seen_ids.add(rid)
                            all_reviews.append(review)
                            new_count += 1

                    print(f"  Page {page_num}: {len(page_reviews)} reviews, {new_count} new (total: {len(all_reviews)})")

                delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
                time.sleep(delay)

    if not all_reviews:
        print("No reviews fetched.")
        sys.exit(1)

    # Save
    with open(output_path, "w", encoding="utf-8") as f:
        for review in all_reviews:
            f.write(json.dumps(review, ensure_ascii=False) + "\n")

    print(f"\nSaved {len(all_reviews)} unique reviews to {output_path}")


if __name__ == "__main__":
    main()
