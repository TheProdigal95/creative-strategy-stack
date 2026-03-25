#!/usr/bin/env python3
"""
Evidence Verifier - Step 04 of Research Engine

Verifies evidence.db health and prints statistics.
With SQLite, merging is handled automatically by INSERT OR IGNORE in Step 03.
This step now serves as a verification checkpoint.

Usage:
    python3 engine/step04_merge_evidence.py <brand>

Example:
    python3 engine/step04_merge_evidence.py mybrand
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.evidence_db import get_connection, get_evidence_count, db_path, init_db


def verify_db(brand):
    """Verify evidence.db health and print stats."""
    print("=" * 70)
    print("EVIDENCE VERIFIER - Step 04")
    print("=" * 70)
    print(f"Brand: {brand}")
    print()

    evidence_db = db_path(brand)
    if not evidence_db.exists():
        print(f"ERROR: evidence.db not found at {evidence_db}")
        print("Run Step 03 first to create the database.")
        return False

    # Initialize tables if needed (no-op if they exist)
    init_db(brand)

    with get_connection(brand) as conn:
        # Total evidence
        total = conn.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]

        # By source
        sources = conn.execute(
            "SELECT source, COUNT(*) as cnt FROM evidence GROUP BY source ORDER BY cnt DESC"
        ).fetchall()

        # By item_type
        types = conn.execute(
            "SELECT item_type, COUNT(*) as cnt FROM evidence GROUP BY item_type ORDER BY cnt DESC"
        ).fetchall()

        # Top communities
        communities = conn.execute(
            "SELECT community, COUNT(*) as cnt FROM evidence GROUP BY community ORDER BY cnt DESC LIMIT 10"
        ).fetchall()

        # By sprint
        sprints = conn.execute(
            "SELECT first_seen_sprint, COUNT(*) as cnt FROM evidence GROUP BY first_seen_sprint ORDER BY cnt DESC"
        ).fetchall()

        # Personas count
        persona_count = conn.execute("SELECT COUNT(*) FROM personas").fetchone()[0]

    print(f"Total evidence: {total:,} rows")
    print(f"Personas: {persona_count}")
    print()

    print("By source:")
    for row in sources:
        print(f"  {row['source']}: {row['cnt']:,}")

    print("\nBy type:")
    for row in types:
        print(f"  {row['item_type']}: {row['cnt']:,}")

    print("\nTop 10 communities:")
    for row in communities:
        pct = row['cnt'] / total * 100 if total > 0 else 0
        print(f"  r/{row['community']}: {row['cnt']:,} ({pct:.1f}%)")

    print("\nBy sprint:")
    for row in sprints:
        print(f"  {row['first_seen_sprint']}: {row['cnt']:,}")

    print(f"\n{'=' * 70}")

    if total > 0:
        print("STATUS: SUCCESS - Evidence DB verified")
    else:
        print("STATUS: WARNING - Evidence DB is empty")

    print("=" * 70)

    return total > 0


def main():
    parser = argparse.ArgumentParser(description='Verify evidence.db health')
    parser.add_argument('brand', help='Brand name (e.g., mybrand)')
    args = parser.parse_args()

    success = verify_db(args.brand)
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
