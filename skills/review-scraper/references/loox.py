#!/usr/bin/env python3
"""
Loox Review Scraper — Reference Implementation

Platform: Loox (https://loox.app)
Detection: Look for `loox.io` in page source.

How it works:
  - Loox renders reviews in a JavaScript widget (no public REST API).
  - This scraper uses Playwright to load the Loox widget page directly
    and paginate through reviews by clicking "Load More".
  - The widget URL is: https://loox.io/widget/<client_id>/reviews/<product_id>
  - Both the client ID and product ID are extracted automatically from the product page.

How to get credentials:
  - The Loox "client ID" is embedded in script tags: loox.io/widget/<client_id>/...
  - The Shopify product ID is extracted from page meta/JS variables.
  - No private API key needed — the widget is public.

Usage:
    python loox.py <product_url> [--output reviews.jsonl]

Example:
    python loox.py https://example.com/products/my-product
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from playwright.async_api import async_playwright, Page
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Credential extraction
# ---------------------------------------------------------------------------

async def extract_product_id(page: Page) -> str | None:
    """Extract the Shopify product ID from the page."""
    product_id = await page.evaluate(r"""
        () => {
            const metaProductId = document.querySelector('meta[property="product:id"]');
            if (metaProductId) return metaProductId.content;

            if (window.__st && window.__st.rid) return String(window.__st.rid);

            if (window.ShopifyAnalytics && window.ShopifyAnalytics.meta && window.ShopifyAnalytics.meta.product) {
                return String(window.ShopifyAnalytics.meta.product.id);
            }

            const scripts = document.querySelectorAll('script[type="application/json"]');
            for (const script of scripts) {
                try {
                    const data = JSON.parse(script.textContent);
                    if (data.product && data.product.id) return String(data.product.id);
                    if (data.id && data.title && data.variants) return String(data.id);
                } catch (e) {}
            }

            return null;
        }
    """)
    return product_id


async def extract_loox_client_id(page: Page) -> str | None:
    """Extract the Loox client ID from script tags."""
    loox_client_id = await page.evaluate(r"""
        () => {
            const scripts = document.querySelectorAll('script[src*="loox.io"]');
            for (const script of scripts) {
                const match = script.src.match(/loox\.io\/widget\/([^\/]+)/);
                if (match) return match[1];
            }
            return null;
        }
    """)
    return loox_client_id


# ---------------------------------------------------------------------------
# Review extraction
# ---------------------------------------------------------------------------

async def extract_reviews_from_page(page: Page) -> list[dict]:
    """Extract all reviews currently visible on the page."""
    reviews = await page.evaluate(r"""
        () => {
            const reviews = [];
            const reviewCards = document.querySelectorAll('.grid-item-wrap[data-id]');

            for (const card of reviewCards) {
                try {
                    const reviewId = card.getAttribute('data-id');
                    if (!reviewId) continue;

                    const titleEl = card.querySelector('.title');
                    const authorName = titleEl ? titleEl.textContent.trim() : 'Anonymous';

                    const verifiedBadge = card.querySelector('.loox-verified-badge');
                    const verified = !!verifiedBadge;

                    const timeEl = card.querySelector('.time');
                    let dateStr = null;
                    if (timeEl) {
                        dateStr = timeEl.textContent.trim();
                    }

                    const starsEl = card.querySelector('.stars');
                    let rating = 5;
                    if (starsEl) {
                        const fullStars = starsEl.querySelectorAll('svg[data-lx-fill="full"]');
                        rating = fullStars.length;
                    }

                    const textEl = card.querySelector('.main-text');
                    let body = '';
                    if (textEl) {
                        body = textEl.textContent.trim();
                    }

                    if (body) {
                        reviews.push({
                            review_id: reviewId,
                            author_name: authorName,
                            rating: rating,
                            title: '',
                            body: body,
                            date: dateStr,
                            verified_buyer: verified,
                        });
                    }
                } catch (e) {}
            }

            return reviews;
        }
    """)
    return reviews


async def click_load_more(page: Page) -> bool:
    """Click the load more button if present."""
    try:
        load_more_btn = await page.query_selector('.load-more-button')
        if load_more_btn:
            is_disabled = await load_more_btn.get_attribute('disabled')
            if not is_disabled:
                await load_more_btn.click()
                return True
        return False
    except Exception:
        return False


async def scrape_loox_reviews(page: Page, widget_url: str, product_url: str) -> list[dict]:
    """Scrape all reviews from the Loox widget with pagination."""
    all_reviews = []
    seen_ids = set()
    page_num = 0
    consecutive_no_new = 0

    print(f"Loading Loox widget: {widget_url}")
    await page.goto(widget_url, wait_until="networkidle", timeout=60000)
    await asyncio.sleep(3)

    while True:
        page_num += 1
        print(f"Processing page {page_num}...")

        current_reviews = await extract_reviews_from_page(page)

        new_count = 0
        for review in current_reviews:
            rid = review.get("review_id", "")
            if rid and rid not in seen_ids:
                seen_ids.add(rid)
                review["source_url"] = product_url
                review["product_title"] = None  # Set by caller if known
                review["scraped_at"] = datetime.now(timezone.utc).isoformat()
                all_reviews.append(review)
                new_count += 1

        print(f"  Found {len(current_reviews)} reviews, {new_count} new (total: {len(all_reviews)})")

        if new_count == 0:
            consecutive_no_new += 1
            if consecutive_no_new >= 3:
                print("  No new reviews after 3 attempts, stopping.")
                break
        else:
            consecutive_no_new = 0

        clicked = await click_load_more(page)

        if clicked:
            print("  Loading more reviews...")
            await asyncio.sleep(2)
            await page.wait_for_load_state("networkidle")
        else:
            print("  No more 'Load More' button found.")
            break

    return all_reviews


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def async_main():
    parser = argparse.ArgumentParser(description="Scrape Loox reviews from a product page")
    parser.add_argument("url", help="Product page URL")
    parser.add_argument("--output", "-o", default="reviews.jsonl", help="Output JSONL file path")
    args = parser.parse_args()

    product_url = args.url
    output_path = Path(args.output)

    print("=" * 60)
    print("Loox Review Scraper")
    print(f"Target: {product_url}")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()

        try:
            print("Loading product page...")
            await page.goto(product_url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(2)

            # Extract credentials
            product_id = await extract_product_id(page)
            loox_client_id = await extract_loox_client_id(page)

            print(f"Product ID: {product_id}")
            print(f"Loox Client ID: {loox_client_id}")

            if not loox_client_id or not product_id:
                print("ERROR: Could not extract Loox client ID or product ID.")
                sys.exit(1)

            widget_url = f"https://loox.io/widget/{loox_client_id}/reviews/{product_id}"

            # Scrape reviews
            all_reviews = await scrape_loox_reviews(page, widget_url, product_url)

        finally:
            await browser.close()

    # Deduplicate
    seen_ids = set()
    unique_reviews = []
    for review in all_reviews:
        rid = review.get("review_id", "")
        if rid and rid not in seen_ids:
            seen_ids.add(rid)
            unique_reviews.append(review)

    # Save
    with open(output_path, "w", encoding="utf-8") as f:
        for review in unique_reviews:
            f.write(json.dumps(review, ensure_ascii=False) + "\n")

    print(f"\nSaved {len(unique_reviews)} unique reviews to {output_path}")


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
