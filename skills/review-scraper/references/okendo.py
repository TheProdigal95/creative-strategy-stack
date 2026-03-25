#!/usr/bin/env python3
"""
Okendo Review Scraper — Reference Implementation

Platform: Okendo (https://okendo.io)
Detection: Look for `okendo` in page source, or `oke-reviews` widget elements.

How to get credentials:
  - The "subscriber ID" is PUBLIC and embedded in the storefront HTML.
  - Find it via: data-oke-reviews-subscriber-id attribute on DOM elements,
    or intercept network requests to api.okendo.io/v1/stores/<subscriber_id>/...
  - The product ID format is typically "shopify-<numeric_id>".
  - No private API token needed — the widget API is unauthenticated.

Finding the subscriber ID (run in browser console or via Playwright):
  1. Check DOM: document.querySelector('[data-oke-reviews-subscriber-id]')
  2. Check network requests for okendo.io/v1/stores/<id>/...
  3. Search page source for: subscriber[_-]?id or okendo\.io/v\d/stores/([^/"]+)

Usage:
    python okendo.py <product_url> [--subscriber-id <id>] [--product-id <id>] [--output reviews.jsonl]

Example:
    python okendo.py https://example.com/products/my-product
    python okendo.py https://example.com/products/my-product --subscriber-id abc123 --product-id shopify-12345
"""

from __future__ import annotations

import argparse
import json
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

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OKENDO_API_BASE = "https://api.okendo.io"
PAGE_LIMIT = 100
MAX_REVIEWS = 15000
RATE_LIMIT_DELAY = 0.4
RATE_LIMIT_RETRY_DELAY = 10


# ---------------------------------------------------------------------------
# Credential extraction
# ---------------------------------------------------------------------------

def extract_okendo_credentials(product_url: str) -> dict:
    """Visit a product page and extract Okendo subscriber ID + product ID."""
    credentials = {"subscriber_id": None, "product_id": None}

    print("Launching browser to extract Okendo credentials...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        api_calls = []

        def handle_request(request):
            url = request.url
            if "okendo" in url.lower():
                api_calls.append(url)

        page.on("request", handle_request)

        try:
            page.goto(product_url, wait_until="networkidle", timeout=60000)
            time.sleep(3)

            # Method 1: data-oke-reviews-subscriber-id attribute
            oke_elements = page.query_selector_all("[data-oke-reviews-subscriber-id]")
            for el in oke_elements:
                sid = el.get_attribute("data-oke-reviews-subscriber-id")
                if sid:
                    credentials["subscriber_id"] = sid
                    print(f"  Found subscriber ID from DOM attribute: {sid}")

            # Method 2: scan all data-oke-* attributes
            oke_attrs = page.evaluate("""() => {
                const results = {};
                const all = document.querySelectorAll('*');
                for (const el of all) {
                    for (const attr of el.attributes) {
                        if (attr.name.startsWith('data-oke')) {
                            results[attr.name] = attr.value;
                        }
                    }
                }
                return results;
            }""")
            if oke_attrs:
                for attr_name, attr_value in oke_attrs.items():
                    print(f"  Found {attr_name}={attr_value}")
                    if "subscriber" in attr_name and not credentials["subscriber_id"]:
                        credentials["subscriber_id"] = attr_value
                    if "product-id" in attr_name and not credentials["product_id"]:
                        credentials["product_id"] = attr_value

            # Method 3: regex search on HTML source
            html = page.content()
            patterns = [
                (r'okendo\.io/v\d/stores/([^/"]+)', "subscriber_id"),
                (r'subscriber[_-]?id["\s:=]+["\']?([a-zA-Z0-9-]+)', "subscriber_id"),
            ]
            for pat, key in patterns:
                matches = re.findall(pat, html, re.IGNORECASE)
                if matches and not credentials[key]:
                    credentials[key] = matches[0]
                    print(f"  Found {key} via regex: {matches[0]}")

            # Method 4: from intercepted API calls
            for api_url in api_calls:
                m = re.search(r'stores/([^/]+)/', api_url)
                if m and not credentials["subscriber_id"]:
                    credentials["subscriber_id"] = m.group(1)
                    print(f"  Found subscriber ID from API call: {m.group(1)}")

            # Get Shopify product ID if not found via Okendo attributes
            if not credentials["product_id"]:
                shopify_pid = page.evaluate("""() => {
                    if (window.ShopifyAnalytics && window.ShopifyAnalytics.meta && window.ShopifyAnalytics.meta.product) {
                        return String(window.ShopifyAnalytics.meta.product.id);
                    }
                    const scripts = document.querySelectorAll('script[type="application/json"]');
                    for (const s of scripts) {
                        try {
                            const data = JSON.parse(s.textContent);
                            if (data && data.product && data.product.id) return String(data.product.id);
                        } catch(e) {}
                    }
                    return null;
                }""")
                if shopify_pid:
                    credentials["product_id"] = f"shopify-{shopify_pid}"
                    print(f"  Constructed product ID: shopify-{shopify_pid}")

        except Exception as e:
            print(f"  Browser error: {e}")
        finally:
            browser.close()

    return credentials


# ---------------------------------------------------------------------------
# API fetching
# ---------------------------------------------------------------------------

def parse_review(raw: dict, source_url: str) -> dict | None:
    """Parse a raw Okendo API review into our standard format."""
    if not raw:
        return None

    review_id = raw.get("reviewId")
    rating = raw.get("rating")
    body = raw.get("body", "") or ""
    title = raw.get("title", "") or ""
    date_str = raw.get("dateCreated")

    reviewer = raw.get("reviewer", {}) or {}
    author_name = reviewer.get("displayName", "Anonymous") or "Anonymous"
    is_verified = reviewer.get("isVerified", False)

    product_name = raw.get("productName", "") or ""

    return {
        "review_id": str(review_id) if review_id else None,
        "author_name": str(author_name).strip(),
        "rating": rating,
        "title": title.strip(),
        "body": body.strip(),
        "date": date_str,
        "verified_buyer": is_verified,
        "product_title": product_name,
        "source_url": source_url,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


def fetch_reviews_for_product(
    client: httpx.Client,
    subscriber_id: str,
    product_id: str,
    source_url: str,
) -> list[dict]:
    """Fetch all reviews for a product using Okendo cursor pagination."""
    all_reviews = []
    page_num = 0

    url = f"{OKENDO_API_BASE}/v1/stores/{subscriber_id}/products/{product_id}/reviews"
    params = {"limit": PAGE_LIMIT, "orderBy": "date desc"}

    while True:
        page_num += 1

        if len(all_reviews) >= MAX_REVIEWS:
            print(f"Hit safety cap of {MAX_REVIEWS} reviews.")
            break

        print(f"  Fetching page {page_num} (have {len(all_reviews)} so far)...")

        retries = 0
        resp = None
        while retries < 5:
            try:
                resp = client.get(url, params=params, timeout=30.0)

                if resp.status_code == 429:
                    retries += 1
                    wait = RATE_LIMIT_RETRY_DELAY * retries
                    print(f"  Rate limited (429). Waiting {wait}s (retry {retries}/5)...")
                    time.sleep(wait)
                    continue

                if resp.status_code != 200:
                    print(f"  API returned {resp.status_code}: {resp.text[:500]}")
                    return all_reviews

                break

            except httpx.HTTPError as e:
                retries += 1
                print(f"  HTTP error: {e}. Retry {retries}/5...")
                time.sleep(RATE_LIMIT_RETRY_DELAY)
                continue
        else:
            print("  Max retries exceeded. Stopping.")
            return all_reviews

        if resp is None:
            break

        try:
            data = resp.json()
        except json.JSONDecodeError as e:
            print(f"  JSON decode error: {e}")
            break

        reviews = data.get("reviews", [])

        if not reviews:
            print(f"  No reviews on page {page_num}. Done.")
            break

        new_count = 0
        for raw in reviews:
            parsed = parse_review(raw, source_url)
            if parsed:
                all_reviews.append(parsed)
                new_count += 1

        print(f"  Page {page_num}: {len(reviews)} fetched, {new_count} parsed (total: {len(all_reviews)})")

        # Handle cursor-based pagination via nextUrl
        next_url = data.get("nextUrl")
        if not next_url:
            print("  No nextUrl. All pages fetched.")
            break

        # nextUrl may be missing the /v1 prefix
        if next_url.startswith("/stores/"):
            url = f"{OKENDO_API_BASE}/v1{next_url}"
        elif next_url.startswith("/v1/"):
            url = f"{OKENDO_API_BASE}{next_url}"
        elif next_url.startswith("/"):
            url = f"{OKENDO_API_BASE}{next_url}"
        else:
            url = next_url

        params = {}  # params are embedded in nextUrl
        time.sleep(RATE_LIMIT_DELAY)

    return all_reviews


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Scrape Okendo reviews from a product page")
    parser.add_argument("url", help="Product page URL")
    parser.add_argument("--subscriber-id", help="Okendo subscriber ID (auto-detected if omitted)")
    parser.add_argument("--product-id", help="Okendo product ID, e.g. shopify-12345 (auto-detected if omitted)")
    parser.add_argument("--output", "-o", default="reviews.jsonl", help="Output JSONL file path")
    args = parser.parse_args()

    product_url = args.url
    output_path = Path(args.output)

    print("=" * 60)
    print("Okendo Review Scraper")
    print(f"Target: {product_url}")
    print("=" * 60)

    subscriber_id = args.subscriber_id
    product_id = args.product_id

    if not subscriber_id or not product_id:
        creds = extract_okendo_credentials(product_url)
        subscriber_id = subscriber_id or creds["subscriber_id"]
        product_id = product_id or creds["product_id"]

    if not subscriber_id:
        print("ERROR: Could not find Okendo subscriber ID.")
        sys.exit(1)

    if not product_id:
        print("ERROR: Could not find product ID.")
        sys.exit(1)

    print(f"\nSubscriber ID: {subscriber_id}")
    print(f"Product ID: {product_id}")

    # Fetch reviews
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    }

    with httpx.Client(headers=headers) as client:
        all_reviews = fetch_reviews_for_product(client, subscriber_id, product_id, product_url)

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
