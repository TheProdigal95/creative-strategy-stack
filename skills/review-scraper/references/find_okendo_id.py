#!/usr/bin/env python3
"""
Okendo Credential Finder — Utility

Visits a product page and extracts the Okendo subscriber ID + product IDs
using DOM attributes, network interception, and regex on HTML source.

Usage:
    python find_okendo_id.py <product_url>

Example:
    python find_okendo_id.py https://example.com/products/my-product
"""

import json
import re
import sys
from playwright.sync_api import sync_playwright


def main():
    if len(sys.argv) < 2:
        print("Usage: python find_okendo_id.py <product_url>")
        sys.exit(1)

    product_url = sys.argv[1]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        api_calls = []

        def handle_request(request):
            url = request.url
            if "okendo" in url.lower():
                api_calls.append(url)
                print(f"[OKENDO REQUEST] {url}")

        page.on("request", handle_request)

        print(f"Loading: {product_url}")
        page.goto(product_url, wait_until="networkidle", timeout=60000)

        # Method 1: data-oke-reviews-subscriber-id attribute
        oke_elements = page.query_selector_all("[data-oke-reviews-subscriber-id]")
        for el in oke_elements:
            sid = el.get_attribute("data-oke-reviews-subscriber-id")
            print(f"[SUBSCRIBER ID from attribute] {sid}")

        # Method 2: scan all data-oke-* attributes
        oke_any = page.evaluate("""() => {
            const results = [];
            const all = document.querySelectorAll('*');
            for (const el of all) {
                for (const attr of el.attributes) {
                    if (attr.name.startsWith('data-oke')) {
                        results.push({tag: el.tagName, attr: attr.name, value: attr.value});
                    }
                }
            }
            return results;
        }""")
        if oke_any:
            print(f"\n[ALL OKE ATTRIBUTES] Found {len(oke_any)} elements:")
            for item in oke_any:
                print(f"  <{item['tag']}> {item['attr']}=\"{item['value']}\"")

        # Method 3: regex on page source
        html = page.content()
        patterns = [
            r'subscriber[_-]?id["\s:=]+["\']?([a-zA-Z0-9-]+)',
            r'oke[_-]?subscriber["\s:=]+["\']?([a-zA-Z0-9-]+)',
            r'okendo\.io/v\d/stores/([^/"]+)',
        ]
        for pat in patterns:
            matches = re.findall(pat, html, re.IGNORECASE)
            if matches:
                print(f"\n[REGEX MATCH] Pattern: {pat}")
                for m in matches:
                    print(f"  => {m}")

        # Method 4: from intercepted API calls
        print(f"\n[API CALLS] {len(api_calls)} Okendo requests intercepted:")
        for url in api_calls:
            print(f"  {url}")

        browser.close()


if __name__ == "__main__":
    main()
