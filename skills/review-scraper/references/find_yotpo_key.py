#!/usr/bin/env python3
"""
Yotpo Credential Finder — Utility

Visits a product page and extracts the Yotpo app key + product IDs
using multiple detection strategies (DOM attributes, script tags,
network interception, regex on HTML source).

Usage:
    python find_yotpo_key.py <product_url> [<product_url_2> ...]

Example:
    python find_yotpo_key.py https://example.com/products/my-product
"""

import asyncio
import json
import re
import sys
from playwright.async_api import async_playwright


async def main():
    if len(sys.argv) < 2:
        print("Usage: python find_yotpo_key.py <product_url> [<product_url_2> ...]")
        sys.exit(1)

    product_urls = sys.argv[1:]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(ignore_https_errors=True)

        yotpo_keys = set()
        yotpo_api_calls = []
        product_ids = {}

        page = await context.new_page()

        async def handle_request(request):
            url = request.url
            if 'yotpo' in url.lower():
                yotpo_api_calls.append(url)

        page.on("request", handle_request)

        for product_url in product_urls:
            print(f"\nVisiting: {product_url}")
            try:
                await page.goto(product_url, wait_until='networkidle', timeout=30000)
            except Exception as e:
                print(f"  Navigation warning: {e}")

            await asyncio.sleep(5)

            # Method 1: data-appkey attribute
            appkey_elements = await page.query_selector_all('[data-appkey]')
            for el in appkey_elements:
                key = await el.get_attribute('data-appkey')
                if key:
                    yotpo_keys.add(key)
                    print(f"  Found appkey via data-appkey: {key}")

            # Method 2: regex on page source
            content = await page.content()
            patterns = [
                r'appkey["\s:=]+["\']?([a-zA-Z0-9]+)["\']?',
                r'app_key["\s:=]+["\']?([a-zA-Z0-9]+)["\']?',
                r'yotpo\.com/v1/widget/([a-zA-Z0-9]+)',
                r'staticw2\.yotpo\.com/([a-zA-Z0-9]+)',
                r'data-appkey="([^"]+)"',
            ]
            for pat in patterns:
                matches = re.findall(pat, content, re.IGNORECASE)
                for m in matches:
                    if len(m) > 5:
                        yotpo_keys.add(m)
                        print(f"  Found key via regex: {m}")

            # Method 3: Yotpo widget div
            yotpo_divs = await page.query_selector_all('.yotpo')
            for div in yotpo_divs:
                pid = await div.get_attribute('data-product-id')
                appk = await div.get_attribute('data-appkey')
                name = await div.get_attribute('data-name')
                if pid:
                    product_ids[product_url] = pid
                    print(f"  Product ID: {pid}")
                if appk:
                    yotpo_keys.add(appk)

            # Method 4: from intercepted network calls
            for url in yotpo_api_calls:
                api_key_match = re.search(r'/widget/([a-zA-Z0-9]+)/', url)
                if api_key_match:
                    yotpo_keys.add(api_key_match.group(1))
                api_key_match2 = re.search(r'staticw2\.yotpo\.com/([a-zA-Z0-9]+)/', url)
                if api_key_match2:
                    yotpo_keys.add(api_key_match2.group(1))

        await browser.close()

        print(f"\n{'='*60}")
        print("RESULTS:")
        print(f"Yotpo App Keys: {yotpo_keys}")
        print(f"Product IDs: {json.dumps(product_ids, indent=2)}")
        print(f"Yotpo API calls intercepted: {len(yotpo_api_calls)}")


if __name__ == "__main__":
    asyncio.run(main())
