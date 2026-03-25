#!/usr/bin/env python3
"""
Yotpo Review Scraper — Reference Implementation

Platform: Yotpo (https://www.yotpo.com)
Detection: Look for `staticw2.yotpo.com` in page source, or `yotpo` in script tags.

How to get credentials:
  - The Yotpo "app key" is PUBLIC and embedded in the storefront HTML.
  - This script auto-extracts it by visiting a product page with Playwright.
  - You do NOT need any private API token — the widget API is unauthenticated.
  - The product ID is also extracted from the page (Shopify product ID or Yotpo widget attribute).

Usage:
    python yotpo.py <product_url> [--output reviews.jsonl]
"""

import argparse
import json
import re
import sys
import time
import datetime
import pathlib
from typing import Optional, List, Dict

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
# Credential extraction
# ---------------------------------------------------------------------------

def extract_yotpo_app_key(page) -> Optional[str]:
    """Try multiple strategies to find the Yotpo app key from a rendered page."""
    strategies = [
        # Strategy 1: data-app-key attribute
        lambda: page.evaluate('''() => {
            const el = document.querySelector('[data-app-key]');
            return el ? el.getAttribute('data-app-key') : null;
        }'''),
        # Strategy 2: yotpoAppKey in scripts
        lambda: page.evaluate('''() => {
            const scripts = document.querySelectorAll('script');
            for (const s of scripts) {
                const text = s.textContent || s.innerText || '';
                const m = text.match(/yotpo(?:App|_app)[Kk_]ey['":\\s]+['"]([a-zA-Z0-9]+)['"]/);
                if (m) return m[1];
            }
            return null;
        }'''),
        # Strategy 3: window.yotpo variables
        lambda: page.evaluate('''() => {
            if (window.yotpo_app_key) return window.yotpo_app_key;
            if (window.yotpoConfig && window.yotpoConfig.appKey) return window.yotpoConfig.appKey;
            if (window.__yotpo && window.__yotpo.app_key) return window.__yotpo.app_key;
            return null;
        }'''),
        # Strategy 4: Yotpo script src
        lambda: page.evaluate('''() => {
            const scripts = document.querySelectorAll('script[src*="yotpo"]');
            for (const s of scripts) {
                const m = s.src.match(/staticw2\\.yotpo\\.com\\/([a-zA-Z0-9]+)\\/widget/);
                if (m) return m[1];
            }
            return null;
        }'''),
        # Strategy 5: .yotpo element with data-appkey
        lambda: page.evaluate('''() => {
            const el = document.querySelector('.yotpo[data-appkey]');
            return el ? el.getAttribute('data-appkey') : null;
        }'''),
        # Strategy 6: broad HTML scan
        lambda: page.evaluate('''() => {
            const html = document.documentElement.innerHTML;
            const m = html.match(/staticw2\\.yotpo\\.com\\/([a-zA-Z0-9]+)/);
            if (m) return m[1];
            const m2 = html.match(/app[_-]?key['":\\s]*['"]([a-zA-Z0-9]{20,})['"]/i);
            if (m2) return m2[1];
            return null;
        }'''),
    ]

    for i, strategy in enumerate(strategies):
        try:
            result = strategy()
            if result:
                print(f"  Found Yotpo app key via strategy {i+1}: {result}")
                return result
        except Exception as e:
            print(f"  Strategy {i+1} failed: {e}")
    return None


def extract_product_id(page, url: str) -> Optional[str]:
    """Extract Shopify / Yotpo product ID from a rendered page."""
    strategies = [
        lambda: page.evaluate('''() => {
            const el = document.querySelector('.yotpo[data-product-id]');
            return el ? el.getAttribute('data-product-id') : null;
        }'''),
        lambda: page.evaluate('''() => {
            const scripts = document.querySelectorAll('script[type="application/json"]');
            for (const s of scripts) {
                try {
                    const data = JSON.parse(s.textContent);
                    if (data && data.product && data.product.id) return String(data.product.id);
                } catch(e) {}
            }
            return null;
        }'''),
        lambda: page.evaluate('''() => {
            if (window.ShopifyAnalytics && window.ShopifyAnalytics.meta && window.ShopifyAnalytics.meta.product) {
                return String(window.ShopifyAnalytics.meta.product.id);
            }
            const meta = document.querySelector('meta[name="product-id"]');
            if (meta) return meta.getAttribute('content');
            return null;
        }'''),
        lambda: page.evaluate('''() => {
            const html = document.documentElement.innerHTML;
            const m = html.match(/product[_-]?[Ii]d['":\\s]*['"]?(\\d{5,})/);
            if (m) return m[1];
            return null;
        }'''),
    ]

    for i, strategy in enumerate(strategies):
        try:
            result = strategy()
            if result:
                print(f"  Found product ID via strategy {i+1}: {result}")
                return result
        except Exception as e:
            print(f"  Strategy {i+1} failed: {e}")
    return None


def extract_product_title(page) -> str:
    """Extract the product title from the page."""
    try:
        title = page.evaluate('''() => {
            const h1 = document.querySelector('h1');
            return h1 ? h1.textContent.trim() : document.title;
        }''')
        return title or "Unknown Product"
    except:
        return "Unknown Product"


def intercept_yotpo_requests(page, url: str) -> dict:
    """Navigate to a product page and intercept Yotpo network requests."""
    captured = {"app_key": None, "product_id": None}

    def handle_request(request):
        req_url = request.url
        if "yotpo.com" in req_url:
            m = re.search(r'widget/([a-zA-Z0-9]+)/', req_url)
            if m:
                captured["app_key"] = m.group(1)
            m = re.search(r'products/([a-zA-Z0-9]+)/', req_url)
            if m and m.group(1) != captured.get("app_key"):
                captured["product_id"] = m.group(1)
            m = re.search(r'staticw2\.yotpo\.com/([a-zA-Z0-9]+)/', req_url)
            if m:
                captured["app_key"] = m.group(1)

    page.on("request", handle_request)

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        time.sleep(5)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        time.sleep(3)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(3)
    except Exception as e:
        print(f"  Navigation issue: {e}")

    page.remove_listener("request", handle_request)
    return captured


# ---------------------------------------------------------------------------
# API fetching
# ---------------------------------------------------------------------------

def fetch_reviews_yotpo_api(
    app_key: str,
    product_id: str,
    product_title: str,
    source_url: str,
    client: httpx.Client,
) -> List[Dict]:
    """Fetch all reviews for a product via the Yotpo public widget API."""
    reviews = []
    page_num = 1
    per_page = 150  # Yotpo allows up to 150

    while True:
        url = f"https://api.yotpo.com/v1/widget/{app_key}/products/{product_id}/reviews.json"
        params = {"per_page": per_page, "page": page_num}

        try:
            resp = client.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"    API error on page {page_num}: {e}")
            if page_num == 1:
                print("    Trying alternative Yotpo endpoint...")
                try:
                    alt_url = f"https://api.yotpo.com/products/{app_key}/{product_id}/reviews"
                    resp = client.get(alt_url, params=params, timeout=30)
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as e2:
                    print(f"    Alternative also failed: {e2}")
                    break
            else:
                break

        response_data = data.get("response", {})
        page_reviews = response_data.get("reviews", [])

        if not page_reviews:
            break

        pagination = response_data.get("pagination", {})
        total = pagination.get("total", 0)

        for r in page_reviews:
            review = {
                "review_id": str(r.get("id", "")),
                "author_name": r.get("user", {}).get("display_name", r.get("name", "")),
                "rating": r.get("score", 0),
                "title": r.get("title", ""),
                "body": r.get("content", ""),
                "date": r.get("created_at", ""),
                "verified_buyer": r.get("verified_buyer", False),
                "product_title": product_title,
                "source_url": source_url,
                "scraped_at": datetime.datetime.utcnow().isoformat() + "Z",
            }
            reviews.append(review)

        print(f"    Page {page_num}: got {len(page_reviews)} reviews (total so far: {len(reviews)}/{total})")

        if len(reviews) >= total or len(page_reviews) < per_page:
            break

        page_num += 1
        time.sleep(0.5)

    return reviews


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Scrape Yotpo reviews from a product page")
    parser.add_argument("url", help="Product page URL")
    parser.add_argument("--output", "-o", default="reviews.jsonl", help="Output JSONL file path")
    args = parser.parse_args()

    product_url = args.url
    output_path = pathlib.Path(args.output)

    print("=" * 60)
    print("Yotpo Review Scraper")
    print(f"Target: {product_url}")
    print("=" * 60)

    app_key = None
    product_id = None
    product_title = "Unknown Product"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
        )
        page = context.new_page()

        # Intercept network requests while navigating
        captured = intercept_yotpo_requests(page, product_url)

        if captured["app_key"]:
            app_key = captured["app_key"]
            print(f"  Captured app key from network: {app_key}")

        if not app_key:
            app_key = extract_yotpo_app_key(page)

        product_id = captured.get("product_id") or extract_product_id(page, product_url)
        product_title = extract_product_title(page)

        browser.close()

    if not app_key:
        print("\nERROR: Could not find Yotpo app key.")
        sys.exit(1)

    if not product_id:
        print("\nERROR: Could not find product ID.")
        sys.exit(1)

    print(f"\nApp Key: {app_key}")
    print(f"Product ID: {product_id}")
    print(f"Product Title: {product_title}")

    # Fetch reviews via Yotpo API
    print(f"\nFetching reviews via Yotpo API...")

    with httpx.Client(
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json",
        },
        follow_redirects=True,
    ) as client:
        all_reviews = fetch_reviews_yotpo_api(
            app_key, product_id, product_title, product_url, client
        )

    # Deduplicate
    seen_ids = set()
    unique_reviews = []
    for r in all_reviews:
        rid = r["review_id"]
        if rid and rid not in seen_ids:
            seen_ids.add(rid)
            unique_reviews.append(r)
        elif not rid:
            unique_reviews.append(r)

    # Save
    with open(output_path, "w", encoding="utf-8") as f:
        for r in unique_reviews:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\nSaved {len(unique_reviews)} unique reviews to {output_path}")


if __name__ == "__main__":
    main()
