#!/usr/bin/env python3
"""
Reddit Scraper - Step 02 of Research Engine

Scrapes Reddit threads using JSON API (no PRAW required).
Supports two-stage verification: test run first, then scale-up.

Usage:
    python3 engine/step02_reddit_scraper.py <brand> <sprint>
    python3 engine/step02_reddit_scraper.py <brand> <sprint> --stage2

Example:
    python3 engine/step02_reddit_scraper.py pureplank 01_weight-loss-men-dads
    python3 engine/step02_reddit_scraper.py pureplank 01_weight-loss-men-dads --stage2

Input:
    brands/<brand>/sprints/<sprint>/_intermediate/scrape_config.json

Output:
    brands/<brand>/sprints/<sprint>/_intermediate/reddit_raw.jsonl
    brands/<brand>/sprints/<sprint>/_intermediate/reddit_failures.csv
"""

import csv
import json
import random
import re
import sys
import time
import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

import requests

# Rate limiting
MIN_DELAY = 2.0
MAX_DELAY = 6.0
MAX_CONSECUTIVE_ERRORS = 3

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


class RedditScraper:
    def __init__(self, config: dict, stage: int = 1):
        self.config = config
        self.stage = stage
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

        self.consecutive_errors = 0
        self.status_counts = Counter()
        self.keyword_counts = Counter()
        self.candidates = {}  # thread_id -> {url, num_comments, title, selftext}
        self.collected = []
        self.failures = []
        self.already_collected_ids = set()

    def _load_already_collected(self, jsonl_path: Path):
        """Load thread IDs already in JSONL for resume support."""
        if jsonl_path.exists():
            try:
                with open(jsonl_path) as f:
                    for line in f:
                        if line.strip():
                            record = json.loads(line)
                            if "thread_id" in record:
                                self.already_collected_ids.add(record["thread_id"])
                print(f"Resume: found {len(self.already_collected_ids)} already collected threads")
            except Exception as e:
                print(f"Warning: Could not load existing JSONL: {e}")

    def _delay(self):
        """Random delay between requests."""
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    def _request(self, url: str, retries: int = 3) -> dict | None:
        """Make request with retries and backoff."""
        for attempt in range(retries):
            try:
                self._delay()
                response = self.session.get(url, timeout=30)
                self.status_counts[response.status_code] += 1

                if response.status_code == 200:
                    self.consecutive_errors = 0
                    return response.json()

                if response.status_code in [403, 429]:
                    self.consecutive_errors += 1
                    if self.consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        print(f"\n*** HARD STOP: {MAX_CONSECUTIVE_ERRORS} consecutive {response.status_code} errors ***")
                        return None

                    # Exponential backoff
                    backoff = (2 ** attempt) * 5
                    print(f"    Rate limited ({response.status_code}), waiting {backoff}s...")
                    time.sleep(backoff)
                    continue

                print(f"    Unexpected status: {response.status_code}")
                return None

            except requests.RequestException as e:
                print(f"    Request error: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)

        return None

    def _extract_thread_id(self, url: str) -> str | None:
        """Extract thread ID from Reddit URL."""
        match = re.search(r"/comments/([a-z0-9]+)", url)
        return match.group(1) if match else None

    def _passes_relevance_filter(self, title: str, selftext: str, theme_keywords: list[str]) -> bool:
        """Check if title + selftext contains at least one theme keyword."""
        if not theme_keywords:
            return True  # No filter if no keywords provided
        combined = (title + " " + selftext).lower()
        return any(kw.lower() in combined for kw in theme_keywords)

    def discover_candidates(self, max_candidates: int, min_comments: int, search_limit: int) -> list[str]:
        """Discover candidate thread URLs with quality filters."""
        subreddits = self.config.get("subreddits", [])
        queries = self.config.get("search_queries", [])
        theme_keywords = self.config.get("theme_keywords", [])

        print(f"\n=== DISCOVERY ===")
        print(f"Target: {max_candidates} candidates")
        print(f"Min comments: {min_comments}")
        print(f"Search limit per query: {search_limit}")
        print(f"Subreddits: {', '.join(subreddits)}")
        print(f"Queries: {len(queries)}")

        for subreddit in subreddits:
            if len(self.candidates) >= max_candidates:
                break

            for query in queries:
                if len(self.candidates) >= max_candidates:
                    break

                # Search endpoint
                encoded_query = quote_plus(query)
                url = f"https://www.reddit.com/r/{subreddit}/search.json?q={encoded_query}&restrict_sr=1&sort=relevance&limit={search_limit}"

                print(f"  r/{subreddit}: '{query}'...", end=" ")

                data = self._request(url)
                if data is None:
                    print("FAILED")
                    if self.consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        return self._finalize_candidates(max_candidates)
                    continue

                posts = data.get("data", {}).get("children", [])
                added = 0

                for post in posts:
                    post_data = post.get("data", {})
                    thread_id = post_data.get("id")
                    permalink = post_data.get("permalink")
                    num_comments = post_data.get("num_comments", 0)
                    title = post_data.get("title", "")
                    selftext = post_data.get("selftext", "")

                    if not thread_id or not permalink:
                        continue

                    if thread_id in self.candidates:
                        continue

                    # Quality filter: min comments
                    if num_comments < min_comments:
                        continue

                    # Relevance filter: theme keywords
                    if not self._passes_relevance_filter(title, selftext, theme_keywords):
                        continue

                    full_url = f"https://www.reddit.com{permalink}"
                    self.candidates[thread_id] = {
                        "url": full_url,
                        "num_comments": num_comments,
                        "title": title,
                        "selftext": selftext,
                    }
                    added += 1

                print(f"+{added} (total: {len(self.candidates)})")

        return self._finalize_candidates(max_candidates)

    def discover_candidates_stage2(self, max_candidates: int, min_comments: int) -> list[str]:
        """Stage 2 discovery with quality filters and fallback logic."""
        print(f"\n=== STAGE 2 DISCOVERY ===")

        # First pass: min_comments threshold, limit=25, sort=relevance
        self.candidates = {}
        print(f"\n--- Pass 1: min_comments={min_comments}, limit=25, sort=relevance ---")
        self._discover_pass(min_comments=min_comments, search_limit=25, sort="relevance", max_candidates=max_candidates)
        count_at_threshold = len(self.candidates)
        print(f"After pass 1: {count_at_threshold} candidates with {min_comments}+ comments")

        # Second pass: sort=comments
        if len(self.candidates) < max_candidates:
            print(f"\n--- Pass 2: min_comments={min_comments}, limit=25, sort=comments ---")
            self._discover_pass(min_comments=min_comments, search_limit=25, sort="comments", max_candidates=max_candidates)
            print(f"After pass 2: {len(self.candidates)} candidates")

        # Fallback: lower threshold by 5
        if len(self.candidates) < max_candidates and min_comments > 10:
            fallback_threshold = max(10, min_comments - 5)
            print(f"\n--- Pass 3 (fallback): min_comments={fallback_threshold}, limit=25 ---")
            print(f"    (Got {len(self.candidates)} at threshold {min_comments}+, lowering to {fallback_threshold})")
            self._discover_pass(min_comments=fallback_threshold, search_limit=25, sort="relevance", max_candidates=max_candidates)
            self._discover_pass(min_comments=fallback_threshold, search_limit=25, sort="comments", max_candidates=max_candidates)
            print(f"After pass 3: {len(self.candidates)} candidates")

        return self._finalize_candidates(max_candidates)

    def _discover_pass(self, min_comments: int, search_limit: int, sort: str, max_candidates: int = None):
        """Single discovery pass."""
        subreddits = self.config.get("subreddits", [])
        queries = self.config.get("search_queries", [])
        theme_keywords = self.config.get("theme_keywords", [])

        for subreddit in subreddits:
            if max_candidates and len(self.candidates) >= max_candidates:
                break

            for query in queries:
                if max_candidates and len(self.candidates) >= max_candidates:
                    break
                encoded_query = quote_plus(query)
                url = f"https://www.reddit.com/r/{subreddit}/search.json?q={encoded_query}&restrict_sr=1&sort={sort}&limit={search_limit}"

                print(f"  r/{subreddit}: '{query}' (sort={sort})...", end=" ")

                data = self._request(url)
                if data is None:
                    print("FAILED")
                    if self.consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        return
                    continue

                posts = data.get("data", {}).get("children", [])
                added = 0

                for post in posts:
                    post_data = post.get("data", {})
                    thread_id = post_data.get("id")
                    permalink = post_data.get("permalink")
                    num_comments = post_data.get("num_comments", 0)
                    title = post_data.get("title", "")
                    selftext = post_data.get("selftext", "")

                    if not thread_id or not permalink:
                        continue

                    if thread_id in self.candidates:
                        continue

                    if num_comments < min_comments:
                        continue

                    if not self._passes_relevance_filter(title, selftext, theme_keywords):
                        continue

                    full_url = f"https://www.reddit.com{permalink}"
                    self.candidates[thread_id] = {
                        "url": full_url,
                        "num_comments": num_comments,
                        "title": title,
                        "selftext": selftext,
                    }
                    added += 1

                print(f"+{added} (total: {len(self.candidates)})")

    def _finalize_candidates(self, max_candidates: int) -> list[str]:
        """Sort candidates by num_comments DESC and return top N URLs."""
        sorted_candidates = sorted(
            self.candidates.items(),
            key=lambda x: x[1]["num_comments"],
            reverse=True
        )[:max_candidates]

        urls = [c[1]["url"] for c in sorted_candidates]
        print(f"\nFinalized {len(urls)} candidates (sorted by comment count)")
        return urls

    def _is_high_signal_comment(self, text: str, high_signal_keywords: list[str]) -> bool:
        """Check if comment contains high-signal keywords."""
        if not text or len(text.strip()) < 20:
            return False

        text_lower = text.lower()

        # Skip very short comments
        if len(text.strip()) < 30:
            return False

        # If no keywords provided, accept all comments over length threshold
        if not high_signal_keywords:
            return True

        # Check for high-signal keywords and count them
        matched = False
        for kw in high_signal_keywords:
            if kw.lower() in text_lower:
                self.keyword_counts[kw] += 1
                matched = True

        return matched

    def _extract_comments(self, comments_data: list, max_comments: int) -> list[dict]:
        """Recursively extract comments from Reddit JSON structure."""
        extracted = []
        high_signal_keywords = self.config.get("high_signal_keywords", [])

        def process_comment(item):
            if len(extracted) >= max_comments:
                return

            if item.get("kind") != "t1":
                return

            data = item.get("data", {})
            body = data.get("body", "")

            if self._is_high_signal_comment(body, high_signal_keywords):
                extracted.append({
                    "id": data.get("id"),
                    "author": data.get("author"),
                    "body": body,
                    "score": data.get("score", 0),
                    "created_utc": data.get("created_utc"),
                })

            # Process replies
            replies = data.get("replies")
            if isinstance(replies, dict):
                children = replies.get("data", {}).get("children", [])
                for child in children:
                    process_comment(child)

        for item in comments_data:
            if len(extracted) >= max_comments:
                break
            process_comment(item)

        return extracted

    def collect_threads(self, urls: list[str], max_threads: int, jsonl_path: Path = None, failures_path: Path = None) -> list[dict]:
        """Fetch threads and extract content with incremental saving."""
        max_comments_per_thread = self.config.get("max_comments_per_thread", 80)

        print(f"\n=== COLLECTION ===")
        print(f"Fetching up to {min(max_threads, len(urls))} of {len(urls)} candidates")

        # Filter out already collected
        urls_to_fetch = []
        for url in urls[:max_threads]:
            thread_id = self._extract_thread_id(url)
            if thread_id and thread_id not in self.already_collected_ids:
                urls_to_fetch.append(url)
            elif thread_id in self.already_collected_ids:
                print(f"  Skipping (already collected): {thread_id}")

        if len(urls_to_fetch) < len(urls[:max_threads]):
            print(f"  Skipped {len(urls[:max_threads]) - len(urls_to_fetch)} already-collected threads")

        for i, url in enumerate(urls_to_fetch, 1):
            thread_id = self._extract_thread_id(url)
            print(f"\n[{i}/{len(urls_to_fetch)}] {url[:60]}...")

            # Fetch thread JSON
            json_url = url.rstrip("/") + ".json"
            data = self._request(json_url)

            if data is None:
                failure = {
                    "url": url,
                    "error": f"Request failed",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                self.failures.append(failure)
                print("    FAILED")

                # Append failure incrementally
                if failures_path:
                    self._append_failure(failures_path, failure)

                if self.consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    print("\n*** HARD STOP triggered ***")
                    break
                continue

            if not isinstance(data, list) or len(data) < 2:
                failure = {
                    "url": url,
                    "error": "Unexpected JSON structure",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                self.failures.append(failure)
                print("    FAILED: Unexpected structure")

                if failures_path:
                    self._append_failure(failures_path, failure)
                continue

            # Extract post data
            post_data = data[0].get("data", {}).get("children", [{}])[0].get("data", {})

            # Extract comments
            comments_data = data[1].get("data", {}).get("children", [])
            comments = self._extract_comments(comments_data, max_comments=max_comments_per_thread)

            record = {
                "thread_id": thread_id,
                "url": url,
                "subreddit": post_data.get("subreddit"),
                "title": post_data.get("title"),
                "selftext": post_data.get("selftext", ""),
                "score": post_data.get("score", 0),
                "num_comments": post_data.get("num_comments", 0),
                "created_utc": post_data.get("created_utc"),
                "comments": comments,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            }

            self.collected.append(record)
            print(f"    SUCCESS: {len(comments)} high-signal comments")

            # Append to JSONL incrementally
            if jsonl_path:
                self._append_jsonl(jsonl_path, record)

        return self.collected

    def _append_jsonl(self, path: Path, record: dict):
        """Append a single record to JSONL file."""
        with open(path, "a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _append_failure(self, path: Path, failure: dict):
        """Append a single failure to CSV file."""
        file_exists = path.exists()
        with open(path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["url", "error", "timestamp"])
            if not file_exists:
                writer.writeheader()
            writer.writerow(failure)

    def print_report(self, urls: list[str]):
        """Print verification report."""
        print(f"\n{'=' * 70}")
        print(f"STAGE {self.stage} REPORT")
        print("=" * 70)

        print(f"\n# Candidate URLs found (after filter): {len(urls)}")
        print(f"# Threads successfully fetched: {len(self.collected)}")

        total_comments = sum(len(r.get("comments", [])) for r in self.collected)
        print(f"# Total comments captured: {total_comments}")

        if self.collected:
            avg_comments = total_comments / len(self.collected)
            print(f"# Average high-signal comments per thread: {avg_comments:.1f}")

        print(f"\nResponse status distribution:")
        for status, count in sorted(self.status_counts.items()):
            print(f"  {status}: {count}")

        # Top 20 keywords
        if self.keyword_counts:
            print(f"\nTop 20 high-signal keywords matched:")
            for kw, count in self.keyword_counts.most_common(20):
                print(f"  {kw}: {count}")

        # Show sample comments
        sample_count = 3 if self.stage == 1 else 5
        print(f"\n--- Sample Extracted Comments ({sample_count}) ---")
        samples_shown = 0
        for record in self.collected:
            if samples_shown >= sample_count:
                break
            for comment in record.get("comments", [])[:1]:
                print(f"\nURL: {record['url'][:60]}...")
                snippet = comment["body"][:200].replace("\n", " ")
                print(f"Snippet: \"{snippet}...\"")
                samples_shown += 1
                if samples_shown >= sample_count:
                    break

        print(f"\n{'=' * 70}")
        if self.consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            print("STATUS: PARTIAL - Rate limited (hard stop triggered)")
        elif len(self.collected) > 0:
            print(f"STATUS: SUCCESS - Stage {self.stage} complete")
        else:
            print("STATUS: FAILED - No threads collected")
        print("=" * 70)


def load_config(config_path: Path) -> dict:
    """Load scraping configuration from JSON file."""
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}")
        sys.exit(1)

    with open(config_path) as f:
        return json.load(f)


def run_stage1(brand: str, sprint: str, config: dict):
    """Run Stage 1 verification."""
    print("=" * 70)
    print("Reddit Scraper - STAGE 1 (Verification)")
    print("=" * 70)
    print(f"Brand: {brand}")
    print(f"Sprint: {sprint}")

    # Setup paths — sprint-level intermediate directory
    output_dir = Path(f"brands/{brand}/sprints/{sprint}/_intermediate")
    output_dir.mkdir(parents=True, exist_ok=True)

    jsonl_path = output_dir / "reddit_raw_stage1.jsonl"
    failures_path = output_dir / "reddit_failures_stage1.csv"

    # Initialize scraper
    scraper = RedditScraper(config, stage=1)

    # Stage 1: Discovery
    max_candidates = config.get("max_threads_stage1", 15)
    min_comments = config.get("min_comments", 20)
    urls = scraper.discover_candidates(
        max_candidates=max_candidates,
        min_comments=min_comments,
        search_limit=10
    )

    if not urls:
        print("\nNo candidates found. Aborting.")
        return False

    # Stage 1: Collection
    scraper.collect_threads(
        urls,
        max_threads=max_candidates,
        jsonl_path=jsonl_path,
        failures_path=failures_path
    )

    # Report
    scraper.print_report(urls)

    print(f"\nOutput files:")
    print(f"  JSONL: {jsonl_path}")
    print(f"  Failures: {failures_path}")

    return len(scraper.collected) > 0


def run_stage2(brand: str, sprint: str, config: dict):
    """Run Stage 2 scale-up."""
    print("=" * 70)
    print("Reddit Scraper - STAGE 2 (Scale-up)")
    print("=" * 70)
    print(f"Brand: {brand}")
    print(f"Sprint: {sprint}")

    # Setup paths — sprint-level intermediate directory
    output_dir = Path(f"brands/{brand}/sprints/{sprint}/_intermediate")
    output_dir.mkdir(parents=True, exist_ok=True)

    jsonl_path = output_dir / "reddit_raw.jsonl"
    failures_path = output_dir / "reddit_failures.csv"

    # Initialize scraper
    scraper = RedditScraper(config, stage=2)

    # Load already collected for resume
    scraper._load_already_collected(jsonl_path)

    # Initialize failures CSV if not exists
    if not failures_path.exists():
        with open(failures_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["url", "error", "timestamp"])
            writer.writeheader()

    # Stage 2: Discovery with quality filters
    max_candidates = config.get("max_threads_stage2", 50)
    min_comments = config.get("min_comments", 20)
    urls = scraper.discover_candidates_stage2(
        max_candidates=max_candidates,
        min_comments=min_comments
    )

    if not urls:
        print("\nNo candidates found. Aborting.")
        return False

    # Stage 2: Collection with incremental saving
    max_threads = config.get("max_threads_stage2", 50)
    scraper.collect_threads(
        urls,
        max_threads=max_threads,
        jsonl_path=jsonl_path,
        failures_path=failures_path
    )

    # Report
    scraper.print_report(urls)

    print(f"\nOutput files:")
    print(f"  JSONL: {jsonl_path}")
    print(f"  Failures: {failures_path}")

    return len(scraper.collected) > 0


def main():
    parser = argparse.ArgumentParser(description='Scrape Reddit threads using JSON API')
    parser.add_argument('brand', help='Brand name (e.g., pureplank)')
    parser.add_argument('sprint', help='Sprint folder name (e.g., 01_weight-loss-men-dads)')
    parser.add_argument('--stage2', action='store_true',
                       help='Run stage 2 (scale-up) instead of stage 1 (verification)')

    args = parser.parse_args()

    # Load config
    config_path = Path(f"brands/{args.brand}/sprints/{args.sprint}/_intermediate/scrape_config.json")
    config = load_config(config_path)

    # Run stage
    if args.stage2:
        success = run_stage2(args.brand, args.sprint, config)
        if success:
            print("\n>>> Stage 2 complete. Ready for processing. <<<")
    else:
        success = run_stage1(args.brand, args.sprint, config)
        if success:
            print("\n>>> Stage 1 complete. Run with '--stage2' to scale up. <<<")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
