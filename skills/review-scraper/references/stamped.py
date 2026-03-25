#!/usr/bin/env python3
"""
Stamped.io Review Scraper — Reference Implementation

Platform: Stamped.io (https://stamped.io)
Detection: Look for `stamped.io` in page source.

How to get credentials:
  - The Stamped.io "API key" is PUBLIC and embedded in the storefront HTML.
  - Find it via: network requests to stamped.io/api/widget containing apiKey param,
    or search page source for patterns like `apiKey`, `stamped-api-key`, etc.
  - The "store URL" is the bare domain (e.g. "example.com").
  - No private API token needed — the widget API is unauthenticated.

Finding credentials with Playwright:
  1. Intercept network requests containing stamped.io — the apiKey is a query param.
  2. Search page source for: data-api-key, stamped-api-key, apiKey patterns.
  3. Look at script tags with src containing stamped.io.

Usage:
    python stamped.py <store_domain> --api-key <key> [--output reviews.jsonl]

Example:
    python stamped.py example.com --api-key YOUR_STAMPED_API_KEY
"""

from __future__ import annotations

import argparse
import json
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

STAMPED_API_BASE = "https://stamped.io/api/widget/reviews"
PAGE_SIZE = 100
MAX_REVIEWS = 30000
MAX_PAGES = 500


# ---------------------------------------------------------------------------
# API fetching
# ---------------------------------------------------------------------------

def parse_review(raw: dict, store_url: str) -> dict | None:
    """Parse a raw Stamped.io review into our standard format."""
    if not raw:
        return None

    review_id = raw.get("id")
    rating = raw.get("reviewRating")
    body = raw.get("reviewMessage", "")
    title = raw.get("reviewTitle", "")
    author_name = raw.get("author", "Anonymous")

    date_str = raw.get("dateCreated") or raw.get("reviewDate")
    verified_type = raw.get("reviewVerifiedType")
    verified = verified_type == 2 or verified_type == "2"

    product_id = raw.get("productId")
    product_name = raw.get("productName")

    return {
        "review_id": str(review_id) if review_id else None,
        "author_name": author_name.strip() if author_name else "Anonymous",
        "rating": rating,
        "title": title.strip() if title else "",
        "body": body.strip() if body else "",
        "date": date_str,
        "verified_buyer": verified,
        "product_title": product_name,
        "source_url": f"https://{store_url}",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


def fetch_all_reviews(api_key: str, store_url: str) -> list[dict]:
    """Fetch all reviews from the Stamped.io API using page-based pagination."""
    all_reviews = []
    page_num = 0

    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    }

    with httpx.Client(timeout=30.0) as client:
        while True:
            page_num += 1

            if page_num > MAX_PAGES:
                print(f"Reached max pages cap: {MAX_PAGES}")
                break

            if len(all_reviews) >= MAX_REVIEWS:
                print(f"Reached max reviews cap: {MAX_REVIEWS}")
                break

            params = {
                "apiKey": api_key,
                "storeUrl": store_url,
                "page": page_num,
                "take": PAGE_SIZE,
            }

            print(f"Fetching page {page_num} (reviews so far: {len(all_reviews)})...")

            try:
                resp = client.get(STAMPED_API_BASE, headers=headers, params=params)

                if resp.status_code != 200:
                    print(f"API returned status {resp.status_code}: {resp.text[:500]}")
                    break

                data = resp.json()

            except httpx.HTTPError as e:
                print(f"HTTP error on page {page_num}: {e}")
                time.sleep(5)
                try:
                    resp = client.get(STAMPED_API_BASE, headers=headers, params=params)
                    if resp.status_code != 200:
                        print(f"Retry also failed: {resp.status_code}")
                        break
                    data = resp.json()
                except Exception as e2:
                    print(f"Retry failed: {e2}")
                    break
            except json.JSONDecodeError as e:
                print(f"JSON decode error on page {page_num}: {e}")
                break

            # Stamped returns reviews in data or as top-level array
            reviews = []
            if isinstance(data, dict):
                reviews = data.get("data", []) or data.get("reviews", []) or []
                if not reviews and "results" in data:
                    reviews = data["results"]
            elif isinstance(data, list):
                reviews = data

            if not reviews:
                print(f"No reviews on page {page_num}, stopping.")
                break

            new_count = 0
            for review in reviews:
                parsed = parse_review(review, store_url)
                if parsed and parsed.get("review_id"):
                    all_reviews.append(parsed)
                    new_count += 1

            print(f"  Page {page_num}: {len(reviews)} fetched, {new_count} parsed (total: {len(all_reviews)})")

            if len(reviews) < PAGE_SIZE:
                print(f"Got {len(reviews)} < {PAGE_SIZE}, reached last page.")
                break

            time.sleep(0.3)

    return all_reviews


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Scrape Stamped.io reviews")
    parser.add_argument("store_url", help="Store domain (e.g. example.com)")
    parser.add_argument("--api-key", required=True, help="Stamped.io public API key")
    parser.add_argument("--output", "-o", default="reviews.jsonl", help="Output JSONL file path")
    args = parser.parse_args()

    store_url = args.store_url
    api_key = args.api_key
    output_path = Path(args.output)

    print("=" * 60)
    print("Stamped.io Review Scraper")
    print(f"Store: {store_url}")
    print("=" * 60)

    # Fetch all reviews
    print("\nFetching reviews from Stamped.io API...")
    all_reviews = fetch_all_reviews(api_key, store_url)

    if not all_reviews:
        print("No reviews fetched.")
        sys.exit(1)

    # Deduplicate and save
    seen = set()
    unique = []
    for r in all_reviews:
        rid = r.get("review_id")
        if rid and rid in seen:
            continue
        if rid:
            seen.add(rid)
        unique.append(r)

    with open(output_path, "w", encoding="utf-8") as f:
        for review in unique:
            f.write(json.dumps(review, ensure_ascii=False) + "\n")

    print(f"\nSaved {len(unique)} unique reviews to {output_path}")


if __name__ == "__main__":
    main()
