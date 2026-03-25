---
name: review-scraper
description: 'Scrape product reviews from any ecommerce site into standardized JSONL. Use when the user says "scrape reviews," "pull reviews," "get reviews from," "grab reviews," or provides a product/review page URL and wants review data.'
---

# Review Scraper

Scrape product reviews from any ecommerce site. Detects the review platform automatically, adapts the appropriate reference scraper, runs it, and outputs standardized JSONL.

Always scrape both the brand's own reviews AND competitor reviews. The user will provide URLs for each.

---

## Dependencies

Before running any scraper, confirm these are installed:

```bash
pip install httpx playwright
playwright install chromium
```

---

## Standard Output Schema

Every scraper outputs JSONL (one JSON object per line) with this schema:

```json
{
  "review_id": "",
  "author_name": "",
  "rating": 5,
  "title": "",
  "body": "",
  "date": "",
  "verified_buyer": true,
  "product_title": "",
  "source_url": "",
  "scraped_at": ""
}
```

All reference scripts already output this format. When adapting scripts, map platform-specific fields into this schema. Additional platform-specific fields (e.g. `language`, `helpful_votes`, `photo_urls`) can be included alongside the standard fields but the core fields above must always be present.

---

## Step 1: Detect the Review Platform

Given the user's URL, detect which review platform the site uses. Use Playwright to load the page and inspect the source.

### Detection logic (check in order):

| Platform | Detection Method |
|---|---|
| **Trustpilot** | URL contains `trustpilot.com` — no page load needed |
| **Yotpo** | Page source contains `staticw2.yotpo.com` OR `yotpo` in script tags |
| **Junip** | Page source contains `juniphq.com` OR network requests to `juniphq.com` |
| **Okendo** | Page source contains `okendo` OR DOM has `oke-reviews` widget elements |
| **Stamped.io** | Page source contains `stamped.io` |
| **Loox** | Page source contains `loox.io` |
| **Judge.me** | Page source contains `judge.me` |

### Quick detection script:

```python
from playwright.sync_api import sync_playwright
import time

def detect_platform(url: str) -> str:
    if "trustpilot.com" in url:
        return "trustpilot"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        captured_domains = set()
        def handle_request(request):
            captured_domains.add(request.url)
        page.on("request", handle_request)

        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(5)

        html = page.content()
        network_str = " ".join(captured_domains)
        browser.close()

    if "staticw2.yotpo.com" in html or "yotpo" in html.lower():
        return "yotpo"
    if "juniphq.com" in html or "juniphq.com" in network_str:
        return "junip"
    if "okendo" in html.lower() or "oke-reviews" in html:
        return "okendo"
    if "stamped.io" in html:
        return "stamped"
    if "loox.io" in html:
        return "loox"
    if "judge.me" in html:
        return "judgeme"

    return "unknown"
```

Tell the user which platform was detected before proceeding.

---

## Step 2: Load the Reference Script

Based on the detected platform, read the corresponding reference script from this skill's `references/` directory:

| Platform | Reference Script |
|---|---|
| Yotpo | `references/yotpo.py` |
| Junip | `references/junip.py` |
| Okendo | `references/okendo.py` |
| Stamped.io | `references/stamped.py` |
| Trustpilot | `references/trustpilot.py` |
| Loox | `references/loox.py` |

### Credential-finding utilities

If automatic credential extraction fails, use the dedicated finder scripts:

- **Yotpo**: `references/find_yotpo_key.py` — visits product pages and extracts the app key + product IDs using 6 different strategies (DOM attributes, script tags, network interception, regex).
- **Okendo**: `references/find_okendo_id.py` — visits a product page and extracts the subscriber ID using DOM attributes, network interception, and regex.

Run these if the main scraper cannot auto-detect credentials.

---

## Step 3: Adapt the Script to the User's URL

Take the reference script and modify it for the user's specific target:

1. **Replace the URL/domain** — Swap the hardcoded product URL or domain with the user's URL.
2. **Replace product IDs** — If the reference script has hardcoded product IDs, remove them. The script should auto-detect or the user will provide them.
3. **Set the output path** — Default to writing `reviews.jsonl` in the current working directory, or wherever the user specifies.
4. **Keep all core logic intact** — The pagination, parsing, deduplication, and retry logic in the reference scripts is battle-tested. Do not rewrite it.

### Platform-specific adaptation notes:

**Yotpo:**
- App key and product ID are auto-extracted from the page via Playwright.
- The public API endpoint is `https://api.yotpo.com/v1/widget/{app_key}/products/{product_id}/reviews.json`.
- Supports up to 150 reviews per page.
- If the primary endpoint fails, falls back to `https://api.yotpo.com/products/{app_key}/{product_id}/reviews`.

**Junip:**
- Store key is intercepted from network requests (sent as `Junip-Store-Key` header).
- Also findable in DOM: `<junip-all-reviews-page store-key="...">`.
- API endpoint: `https://api.juniphq.com/v2/product_overview/reviews`.
- Uses cursor-based pagination (`meta.after`).

**Okendo:**
- Subscriber ID is in `data-oke-reviews-subscriber-id` DOM attributes or intercepted from `api.okendo.io` network calls.
- Product ID format is `shopify-{numeric_id}`.
- API endpoint: `https://api.okendo.io/v1/stores/{subscriber_id}/products/{product_id}/reviews`.
- Uses cursor-based pagination via `nextUrl` in response.
- Important: `nextUrl` is often missing the `/v1` prefix — prepend it.

**Stamped.io:**
- API key is a public query parameter on widget requests.
- Find it by intercepting requests to `stamped.io/api/widget`.
- Store URL is the bare domain (e.g. `example.com`).
- API endpoint: `https://stamped.io/api/widget/reviews?apiKey={key}&storeUrl={domain}`.
- Uses simple page-based pagination.

**Trustpilot:**
- No credentials needed. Reviews are in server-rendered HTML.
- Reviews are inside `<script id="__NEXT_DATA__">` JSON blob.
- Hard limit: 10 pages per filter combination.
- Maximize coverage by iterating star ratings (1-5) x sort orders (recency, relevance) x languages.
- Must use random delays (1.5-3s) and rotate user agents to avoid 403/429.

**Loox:**
- No REST API. Reviews are rendered in a JavaScript widget.
- Widget URL: `https://loox.io/widget/{client_id}/reviews/{product_id}`.
- Client ID is in script tags: `loox.io/widget/{client_id}/...`.
- Must use Playwright (async) to click "Load More" repeatedly.
- Uses `async_playwright` — the scraper runs with `asyncio.run()`.

---

## Step 4: Run the Scraper

Run the adapted script. Monitor the output for:
- Successful credential detection
- Page-by-page progress
- Any errors or rate limiting

If credential detection fails:
1. Try the dedicated finder utility (`find_yotpo_key.py` or `find_okendo_id.py`).
2. Ask the user to provide the credentials manually (app key, subscriber ID, etc.).
3. As a last resort, try DOM-based extraction as a fallback.

---

## Step 5: Validate and Report

After the scrape completes:

1. **Count**: Report total reviews scraped and unique count after deduplication.
2. **Rating distribution**: Show the breakdown (5-star through 1-star).
3. **Date range**: Show earliest and latest review dates.
4. **Verified buyer %**: What percentage are verified purchases.
5. **Output location**: Confirm the JSONL file path and size.

### Sample summary output:

```
Scraped 2,847 unique reviews
Rating distribution:
  5-star: 1,892 (66.4%)
  4-star:   512 (18.0%)
  3-star:   201 (7.1%)
  2-star:   134 (4.7%)
  1-star:   108 (3.8%)
Average: 4.39
Date range: 2021-03-15 to 2026-03-24
Verified buyers: 2,103 (73.9%)
Output: reviews.jsonl (1.2 MB)
```

---

## Handling Multiple Products / Competitor Scrapes

The user will always want to scrape both brand reviews and competitor reviews. Handle this by:

1. Scraping the brand's product(s) first.
2. Then scraping each competitor URL the user provides.
3. Output each to a separate JSONL file (e.g. `brand_reviews.jsonl`, `competitor_reviews.jsonl`) or a single file with a `source_url` field distinguishing them.

If the user provides multiple product URLs for the same brand, scrape each and combine into one JSONL file, deduplicating by `review_id`.

---

## Troubleshooting

### "Could not find app key / store key / subscriber ID"
- The page may require longer load times. Increase `time.sleep()` after navigation.
- The review widget may load lazily. Scroll to the reviews section before extracting.
- Try the dedicated finder utilities in `references/`.
- Some sites use custom implementations. Ask the user to inspect network requests manually.

### Rate limiting (429 errors)
- Increase delays between requests.
- For Trustpilot: use longer random delays (3-5s) and fewer filter combos.
- For Okendo: the script has built-in exponential backoff (10s x retry count).

### Empty responses
- The product may genuinely have few/no reviews.
- The API structure may have changed. Check raw API response for new field names.
- For Junip: the store may need a paid plan for API access.

### Judge.me (no reference script)
- Judge.me uses a public API similar to Stamped.io.
- API endpoint: `https://judge.me/api/v1/reviews?shop_domain={domain}&api_token={token}&page={n}`
- The API token is in the page source. Search for `judge.me` script tags.
- Adapt the Stamped.io reference as a starting point — same page-based pagination pattern.
