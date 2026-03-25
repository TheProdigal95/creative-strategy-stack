#!/usr/bin/env python3
"""
Reddit to Evidence Transformer - Step 03 of Research Engine

Transforms raw Reddit JSONL into evidence rows and inserts them into evidence.db.
NO synthetic fields - pure transformation only.

Usage:
    python3 engine/step03_reddit_to_evidence.py <brand> <sprint>

Example:
    python3 engine/step03_reddit_to_evidence.py pureplank "01 - Back Pain from Desk Jobs"

Input:
    brands/<brand>/sprints/<sprint>/_intermediate/reddit_raw.jsonl

Output:
    Inserts into brands/<brand>/evidence.db

Evidence Schema (12 fields):
    - evidence_id: Unique identifier (reddit_{thread_id}_post or reddit_{thread_id}_{comment_id})
    - source: Always "reddit"
    - url: Thread URL
    - date_iso: ISO 8601 date (YYYY-MM-DD)
    - community: Subreddit name
    - author: Reddit username
    - score: Upvote count
    - text: Post/comment body
    - parent_context: Thread title + first 200 chars of OP (for comments only)
    - thread_id: Reddit thread ID
    - item_type: "post" or "comment"
    - comment_id: Comment ID (empty for posts)
"""

import json
import argparse
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.evidence_db import init_db, insert_evidence_batch, get_evidence_count


EVIDENCE_FIELDS = [
    "evidence_id", "source", "url", "date_iso", "community",
    "author", "score", "text", "parent_context",
    "thread_id", "item_type", "comment_id",
]


def unix_to_iso(unix_ts):
    """Convert Unix timestamp to ISO 8601 date string."""
    if not unix_ts:
        return ""
    try:
        dt = datetime.fromtimestamp(float(unix_ts), tz=timezone.utc)
        return dt.strftime("%Y-%m-%d")
    except (ValueError, OSError):
        return ""


def truncate_text(text, max_len=200):
    """Truncate text to max_len chars, adding ellipsis if needed."""
    if not text:
        return ""
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0] + "..."


def clean_text(text):
    """Clean text for storage."""
    if not text:
        return ""
    text = " ".join(text.split())
    return text.strip()


def process_thread(record):
    """Process a single thread record into evidence rows."""
    evidence_rows = []

    thread_id = record.get("thread_id", "")
    url = record.get("url", "")
    subreddit = record.get("subreddit", "")
    title = record.get("title", "")
    selftext = record.get("selftext", "")
    post_score = record.get("score", 0)
    post_created = record.get("created_utc")
    comments = record.get("comments", [])

    # Build parent context: title + first 200 chars of selftext
    parent_context = title
    if selftext:
        parent_context += " | " + truncate_text(selftext, 200)

    # A) Post row (title + selftext combined)
    post_text = title
    if selftext:
        post_text += "\n\n" + selftext

    post_row = {
        "evidence_id": f"reddit_{thread_id}_post",
        "source": "reddit",
        "url": url,
        "date_iso": unix_to_iso(post_created),
        "community": subreddit,
        "author": record.get("author", "[OP]"),
        "score": post_score,
        "text": clean_text(post_text),
        "parent_context": "",
        "thread_id": thread_id,
        "item_type": "post",
        "comment_id": "",
    }
    evidence_rows.append(post_row)

    # B) Comment rows
    for comment in comments:
        cmt_id = comment.get("id", "")
        comment_row = {
            "evidence_id": f"reddit_{thread_id}_{cmt_id}",
            "source": "reddit",
            "url": url,
            "date_iso": unix_to_iso(comment.get("created_utc")),
            "community": subreddit,
            "author": comment.get("author", "[deleted]"),
            "score": comment.get("score", 0),
            "text": clean_text(comment.get("body", "")),
            "parent_context": clean_text(parent_context),
            "thread_id": thread_id,
            "item_type": "comment",
            "comment_id": cmt_id,
        }
        evidence_rows.append(comment_row)

    return evidence_rows


def main():
    parser = argparse.ArgumentParser(description='Transform Reddit JSONL to evidence DB')
    parser.add_argument('brand', help='Brand name (e.g., pureplank)')
    parser.add_argument('sprint', help='Sprint folder name')

    args = parser.parse_args()

    # Input: sprint-level JSONL
    input_jsonl = Path(f"brands/{args.brand}/sprints/{args.sprint}/_intermediate/reddit_raw.jsonl")

    print("=" * 70)
    print("Reddit to Evidence Transformer - Step 03")
    print("=" * 70)
    print(f"Brand: {args.brand}")
    print(f"Sprint: {args.sprint}")
    print()

    # Check input exists
    if not input_jsonl.exists():
        print(f"ERROR: Input file not found: {input_jsonl}")
        return False

    # Initialize DB
    init_db(args.brand)

    # Process all threads
    all_evidence = []
    subreddit_counts = Counter()
    thread_count = 0

    print(f"Reading: {input_jsonl}")

    with open(input_jsonl, "r") as f:
        for line in f:
            if not line.strip():
                continue

            record = json.loads(line)
            thread_count += 1

            rows = process_thread(record)
            all_evidence.extend(rows)

            subreddit = record.get("subreddit", "unknown")
            subreddit_counts[subreddit] += len(rows)

    print(f"Processed {thread_count} threads")
    print(f"Generated {len(all_evidence)} evidence rows")

    # Insert into DB
    print(f"\nInserting into evidence.db...")
    inserted, skipped = insert_evidence_batch(args.brand, all_evidence, args.sprint)

    # Calculate stats
    post_count = sum(1 for r in all_evidence if r["item_type"] == "post")
    comment_count = sum(1 for r in all_evidence if r["item_type"] == "comment")
    total_in_db = get_evidence_count(args.brand)

    # Print report
    print(f"\n{'=' * 70}")
    print("TRANSFORMATION REPORT")
    print("=" * 70)

    print(f"\nThis sprint: {len(all_evidence)} evidence rows")
    print(f"  Posts: {post_count}")
    print(f"  Comments: {comment_count}")
    print(f"  New (inserted): {inserted}")
    print(f"  Duplicates (skipped): {skipped}")
    print(f"\nTotal in evidence.db: {total_in_db:,}")

    print(f"\nTop 10 subreddits by row count:")
    for subreddit, count in subreddit_counts.most_common(10):
        pct = count / len(all_evidence) * 100 if all_evidence else 0
        print(f"  r/{subreddit}: {count} ({pct:.1f}%)")

    # Sample 3 rows
    if all_evidence:
        print(f"\nSample 3 rows:")
        print("-" * 70)
        sample_indices = [0, len(all_evidence) // 2, len(all_evidence) - 1]
        for idx in sample_indices:
            row = all_evidence[idx]
            text_preview = row["text"][:120] if len(row["text"]) > 120 else row["text"]
            print(f"  evidence_id: {row['evidence_id']}")
            print(f"  item_type:   {row['item_type']}")
            print(f"  community:   r/{row['community']}")
            print(f"  text:        {text_preview}...")
            print("-" * 70)

    print(f"\n{'=' * 70}")
    print("STATUS: SUCCESS - Step 03 complete")
    print("=" * 70)

    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
