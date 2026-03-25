#!/usr/bin/env python3
"""
Junip Review Scraper — Reference Implementation

Platform: Junip (https://junip.co)
Detection: Look for `juniphq.com` in page source or network requests.

How to get credentials:
  - The Junip "store key" is PUBLIC and sent as a header in widget API requests.
  - This script auto-extracts it by intercepting network requests on the reviews page.
  - You can also find it in DOM elements: <junip-all-reviews-page store-key="...">
  - No private API token needed.

Usage:
    python junip.py <reviews_page_url> [--output reviews.jsonl]

Example:
    python junip.py https://example.com/pages/reviews
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Run: pip install httpx")
    sys.exit(1)

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

JUNIP_API_BASE = "https://api.juniphq.com"
PAGE_SIZE = 50
MAX_REVIEWS = 10000
MAX_PAGES = 500


# ---------------------------------------------------------------------------
# Credential extraction
# ---------------------------------------------------------------------------

def extract_store_key(page_url: str) -> str | None:
    """Load the reviews page with Playwright and intercept Junip API calls to get the store key."""
    store_key = None

    print("Launching browser to extract Junip store key...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        captured_keys = []

        def handle_request(request):
            url = request.url
            if "juniphq.com" in url:
                headers = request.headers
                key = headers.get("junip-store-key")
                if key and key not in captured_keys:
                    captured_keys.append(key)
                    print(f"  Captured Junip-Store-Key from network: {key}")

        page.on("request", handle_request)

        try:
            page.goto(page_url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(5)

            # Also try to extract from DOM data attributes
            dom_key = page.evaluate("""
                () => {
                    const els = document.querySelectorAll('[data-store-key], [data-junip-store-key]');
                    for (const el of els) {
                        const key = el.getAttribute('data-store-key') || el.getAttribute('data-junip-store-key');
                        if (key) return key;
                    }
                    const junipEls = document.querySelectorAll('junip-store-key, junip-product-summary, junip-product-review, junip-all-reviews-page, junip-store-review');
                    for (const el of junipEls) {
                        const key = el.getAttribute('store-key');
                        if (key) return key;
                    }
                    return null;
                }
            """)

            if dom_key:
                print(f"  Found store key in DOM: {dom_key}")
                captured_keys.append(dom_key)

            # Scroll to trigger widget if not found yet
            if not captured_keys:
                print("  No store key from initial load, scrolling...")
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(3)

        except Exception as e:
            print(f"  Browser error: {e}")
        finally:
            browser.close()

        if captured_keys:
            store_key = captured_keys[0]

    return store_key


# ---------------------------------------------------------------------------
# API fetching
# ---------------------------------------------------------------------------

def parse_review(raw: dict, source_url: str) -> dict | None:
    """Parse a raw Junip API review into our standard format."""
    if not raw:
        return None

    review_id = raw.get("id")
    rating = raw.get("rating")
    body = raw.get("body", "")
    title = raw.get("title", "")

    customer = raw.get("customer", {}) or {}
    first_name = customer.get("first_name", "")
    last_name = customer.get("last_name", "")
    if first_name and last_name:
        author_name = f"{first_name} {last_name[0]}."
    elif first_name:
        author_name = first_name
    else:
        author_name = "Anonymous"

    date_str = raw.get("created_at")
    verified = raw.get("verified_buyer")

    product = raw.get("product", {}) or {}
    product_title = raw.get("target_title") or product.get("title")

    return {
        "review_id": str(review_id) if review_id else None,
        "author_name": author_name.strip(),
        "rating": rating,
        "title": title.strip() if title else "",
        "body": body.strip() if body else "",
        "date": date_str,
        "verified_buyer": verified,
        "product_title": product_title,
        "source_url": source_url,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


def fetch_all_reviews(store_key: str, source_url: str) -> list[dict]:
    """Fetch all reviews from the Junip API using cursor-based pagination."""
    all_reviews = []
    page_num = 0
    cursor = None

    headers = {
        "Junip-Store-Key": store_key,
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

            params = {"page_size": PAGE_SIZE}
            if cursor:
                params["page_after"] = cursor

            url = f"{JUNIP_API_BASE}/v2/product_overview/reviews"
            print(f"Fetching page {page_num}...")

            try:
                resp = client.get(url, headers=headers, params=params)

                if resp.status_code != 200:
                    print(f"API returned status {resp.status_code}: {resp.text[:500]}")
                    break

                data = resp.json()

            except httpx.HTTPError as e:
                print(f"HTTP error: {e}")
                break
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                break

            reviews = data.get("data", [])

            if not reviews:
                print(f"No reviews in response on page {page_num}, stopping.")
                break

            new_count = 0
            for review in reviews:
                parsed = parse_review(review, source_url)
                if parsed:
                    all_reviews.append(parsed)
                    new_count += 1

            print(f"  Page {page_num}: {len(reviews)} fetched, {new_count} parsed (total: {len(all_reviews)})")

            # Get next cursor
            meta = data.get("meta", {})
            cursor = meta.get("after") if isinstance(meta, dict) else None

            if not cursor:
                print("No next cursor found, reached last page.")
                break

            time.sleep(0.5)

    return all_reviews


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Scrape Junip reviews from a store's reviews page")
    parser.add_argument("url", help="Reviews page URL (e.g. https://example.com/pages/reviews)")
    parser.add_argument("--output", "-o", default="reviews.jsonl", help="Output JSONL file path")
    args = parser.parse_args()

    source_url = args.url
    output_path = Path(args.output)

    print("=" * 60)
    print("Junip Review Scraper")
    print(f"Target: {source_url}")
    print("=" * 60)

    # Step 1: Extract store key
    store_key = extract_store_key(source_url)

    if not store_key:
        print("ERROR: Failed to extract Junip store key.")
        sys.exit(1)

    print(f"Store Key: {store_key}")

    # Step 2: Fetch all reviews
    print("\nFetching reviews from Junip API...")
    all_reviews = fetch_all_reviews(store_key, source_url)

    if not all_reviews:
        print("No reviews fetched.")
        sys.exit(1)

    # Step 3: Deduplicate and save
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
