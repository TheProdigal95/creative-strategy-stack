#!/usr/bin/env python3
"""
Migration Script - Migrates existing CSV/JSON data to SQLite evidence.db.

Reads evidence_master.csv and personas.json, creates evidence.db with all data.
Original files are kept as backup (not deleted).

Usage:
    python3 engine/migrate_to_sqlite.py <brand>
    python3 engine/migrate_to_sqlite.py --all

Examples:
    python3 engine/migrate_to_sqlite.py mybrand
    python3 engine/migrate_to_sqlite.py --all
"""

import csv
import json
import argparse
import sys
from pathlib import Path

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.evidence_db import (
    init_db, insert_evidence_batch_fast, load_personas, upsert_personas,
    get_evidence_count, db_path, get_connection
)


def migrate_evidence_csv(brand):
    """Migrate evidence_master.csv into evidence.db."""
    csv_path = Path(f"brands/{brand}/evidence/evidence_master.csv")

    if not csv_path.exists():
        print(f"  No evidence_master.csv found — skipping evidence migration")
        return 0

    # Read CSV
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("evidence_id"):
                rows.append(row)

    if not rows:
        print(f"  evidence_master.csv is empty — skipping")
        return 0

    print(f"  Read {len(rows):,} rows from evidence_master.csv")

    # Insert into DB (all marked as migrated from CSV)
    total = insert_evidence_batch_fast(brand, rows, sprint="__migrated__")

    print(f"  Inserted into evidence.db: {total:,} rows")
    return len(rows)


def migrate_personas_json(brand):
    """Migrate personas.json into evidence.db."""
    json_path = Path(f"brands/{brand}/personas.json")

    if not json_path.exists():
        print(f"  No personas.json found — skipping personas migration")
        return 0

    with open(json_path, "r") as f:
        ledger = json.load(f)

    personas = ledger.get("personas", [])
    if not personas:
        print(f"  personas.json is empty — skipping")
        return 0

    print(f"  Read {len(personas)} personas from personas.json")

    upsert_personas(brand, ledger)

    print(f"  Inserted {len(personas)} personas into evidence.db")
    return len(personas)


def verify_migration(brand, expected_evidence, expected_personas):
    """Verify migrated data matches source counts."""
    actual_evidence = get_evidence_count(brand)
    actual_personas = len(load_personas(brand).get("personas", []))

    ok = True

    if actual_evidence != expected_evidence:
        print(f"  WARNING: Evidence count mismatch — expected {expected_evidence}, got {actual_evidence}")
        ok = False
    else:
        print(f"  Evidence: {actual_evidence:,} rows — OK")

    if actual_personas != expected_personas:
        print(f"  WARNING: Personas count mismatch — expected {expected_personas}, got {actual_personas}")
        ok = False
    else:
        print(f"  Personas: {actual_personas} — OK")

    return ok


def migrate_brand(brand):
    """Run full migration for a single brand."""
    print(f"\n{'='*60}")
    print(f"Migrating: {brand}")
    print(f"{'='*60}")

    # Check if DB already exists
    existing_db = db_path(brand)
    if existing_db.exists():
        count = get_evidence_count(brand)
        if count > 0:
            print(f"  evidence.db already exists with {count:,} rows")
            print(f"  Skipping (delete evidence.db first to re-migrate)")
            return True

    # Initialize DB
    init_db(brand)
    print(f"  Created {existing_db}")

    # Migrate evidence
    evidence_count = migrate_evidence_csv(brand)

    # Migrate personas
    persona_count = migrate_personas_json(brand)

    # Verify
    print(f"\n  Verification:")
    ok = verify_migration(brand, evidence_count, persona_count)

    if ok:
        print(f"\n  Migration complete. Original files preserved as backup.")
    else:
        print(f"\n  Migration completed with warnings — check counts above.")

    return ok


def find_all_brands():
    """Find all brand directories."""
    brands_dir = Path("brands")
    if not brands_dir.exists():
        return []
    return sorted([
        d.name for d in brands_dir.iterdir()
        if d.is_dir() and (d / "brand_brief.yaml").exists()
    ])


def main():
    parser = argparse.ArgumentParser(description="Migrate CSV/JSON to SQLite")
    parser.add_argument("brand", nargs="?", help="Brand name (e.g., mybrand)")
    parser.add_argument("--all", action="store_true", help="Migrate all brands")

    args = parser.parse_args()

    if not args.brand and not args.all:
        parser.print_help()
        sys.exit(1)

    if args.all:
        brands = find_all_brands()
        if not brands:
            print("No brands found in brands/ directory")
            sys.exit(1)

        print(f"Found {len(brands)} brands: {', '.join(brands)}")
        all_ok = True
        for brand in brands:
            ok = migrate_brand(brand)
            if not ok:
                all_ok = False

        print(f"\n{'='*60}")
        if all_ok:
            print("All migrations completed successfully.")
        else:
            print("Some migrations had warnings — review output above.")
        print(f"{'='*60}")

    else:
        brand_path = Path(f"brands/{args.brand}")
        if not brand_path.exists():
            print(f"Error: Brand folder not found: {brand_path}")
            sys.exit(1)

        ok = migrate_brand(args.brand)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
