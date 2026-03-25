#!/usr/bin/env python3
"""
VoC Curator - Step 11 of Research Engine

Reads insights_final.csv, finds rows marked for keeping, and stores their
VoC data to SQLite (evidence.db) organized by Theme > Persona.

This is a MANUAL tool — not part of the orchestrator.
User reviews insights_final.csv, marks rows in Keep column, then runs this.

Usage:
    python3 engine/step11_voc_curator.py pureplank "04 - Men Over 40 Fitness Recovery"
    python3 engine/step11_voc_curator.py pureplank 01_weight-loss-men-dads
    python3 engine/step11_voc_curator.py pureplank 01_weight-loss-men-dads --export-json
"""

import os
import sys
import argparse
import pandas as pd
from datetime import datetime

from engine.evidence_db import (
    init_db,
    upsert_voc_curated,
    upsert_voc_findings,
    get_voc_by_theme_persona,
    export_voc_json,
    get_voc_stats,
)


KEEP_VALUES = {"y", "yes", "x", "1"}


def resolve_sprint_dir(brand, sprint):
    """Resolve sprint directory, handling both naming formats."""
    base = f"brands/{brand}/sprints"
    direct = os.path.join(base, sprint)
    if os.path.isdir(direct):
        return direct

    if os.path.isdir(base):
        for entry in os.listdir(base):
            entry_path = os.path.join(base, entry)
            if os.path.isdir(entry_path):
                entry_prefix = entry.split('_')[0].split(' ')[0].split('-')[0]
                sprint_prefix = sprint.split('_')[0].split(' ')[0].split('-')[0]
                if entry_prefix == sprint_prefix:
                    return entry_path

    return direct


def parse_voc_cell(voc_text):
    """Parse a VoC cell into quotes and general findings."""
    quotes = []
    general_findings = []

    if not voc_text or pd.isna(voc_text):
        return quotes, general_findings

    for line in str(voc_text).split('\n'):
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith('- '):
            quote = stripped[2:].strip()
            # Strip surrounding quotes
            if quote.startswith('"') and quote.endswith('"'):
                quote = quote[1:-1].strip()
            if quote:
                quotes.append(quote)

        elif stripped.lower().startswith('general:'):
            finding = stripped[len('general:'):].strip()
            if finding:
                general_findings.append(finding)

    return quotes, general_findings


def main():
    parser = argparse.ArgumentParser(
        description='Curate VoC data from marked insights into SQLite'
    )
    parser.add_argument('brand', help='Brand name (e.g., pureplank)')
    parser.add_argument('sprint', help='Sprint folder name')
    parser.add_argument('--export-json', action='store_true',
                        help='Also export curated VoC to voc_master.json')

    args = parser.parse_args()

    sprint_dir = resolve_sprint_dir(args.brand, args.sprint)
    sprint_name = os.path.basename(sprint_dir)
    csv_path = os.path.join(sprint_dir, 'insights_final.csv')

    print("=" * 70)
    print("VOC CURATOR - STEP 11")
    print("=" * 70)
    print(f"Brand: {args.brand}")
    print(f"Sprint: {sprint_name}")
    print()

    # --- Validation ---

    if not os.path.exists(csv_path):
        print(f"ERROR: insights_final.csv not found: {csv_path}")
        print("Run Steps 09 and 10 first.")
        sys.exit(1)

    df = pd.read_csv(csv_path)

    if 'VoC' not in df.columns or 'Keep' not in df.columns:
        print("ERROR: insights_final.csv is missing VoC and/or Keep columns.")
        print("Run Step 10 (VoC Analyzer) first.")
        sys.exit(1)

    kept = df[df['Keep'].astype(str).str.strip().str.lower().isin(KEEP_VALUES)]

    if len(kept) == 0:
        print("No rows marked for keeping.")
        print("Mark rows with 'Y' in the Keep column and re-run.")
        sys.exit(0)

    print(f"Found {len(kept)} rows marked for keeping.")

    # --- Ensure VoC tables exist ---
    init_db(args.brand)

    # --- Process kept rows ---

    stats = {
        'rows_kept': len(kept),
        'rows_with_voc': 0,
        'rows_skipped_empty': 0,
        'quotes_added': 0,
        'quotes_duplicate': 0,
        'findings_added': 0,
        'findings_duplicate': 0,
        'updated_pairs': set(),
    }

    for _, row in kept.iterrows():
        theme = str(row.get('Theme', '')).strip()
        persona = str(row.get('Persona', '')).strip()
        voc_text = row.get('VoC', '')
        insight_text = str(row.get('Insight', ''))[:80]

        if not theme or not persona:
            print(f"  WARNING: Missing Theme/Persona for: {insight_text}...")
            stats['rows_skipped_empty'] += 1
            continue

        if not voc_text or pd.isna(voc_text) or str(voc_text).strip() == '':
            print(f"  WARNING: Empty VoC for: {insight_text}...")
            stats['rows_skipped_empty'] += 1
            continue

        quotes, findings = parse_voc_cell(voc_text)

        if not quotes and not findings:
            print(f"  WARNING: No parseable VoC content for: {insight_text}...")
            stats['rows_skipped_empty'] += 1
            continue

        stats['rows_with_voc'] += 1

        # Insert quotes into SQLite (deduplication via UNIQUE constraint)
        if quotes:
            inserted, skipped = upsert_voc_curated(
                args.brand, theme, persona, quotes, source_sprint=sprint_name
            )
            stats['quotes_added'] += inserted
            stats['quotes_duplicate'] += skipped

        # Insert findings into SQLite
        if findings:
            inserted, skipped = upsert_voc_findings(
                args.brand, theme, persona, findings, source_sprint=sprint_name
            )
            stats['findings_added'] += inserted
            stats['findings_duplicate'] += skipped

        stats['updated_pairs'].add((theme, persona))

    # --- Optional JSON export ---
    if args.export_json:
        export_voc_json(args.brand)

    # --- Summary ---

    voc_stats = get_voc_stats(args.brand)

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Rows marked for keeping:  {stats['rows_kept']}")
    print(f"  Rows with valid VoC:      {stats['rows_with_voc']}")
    print(f"  Rows skipped (empty VoC): {stats['rows_skipped_empty']}")
    print()
    print(f"  Quotes added:             {stats['quotes_added']}")
    print(f"  Quotes skipped (dupes):   {stats['quotes_duplicate']}")
    print(f"  Findings added:           {stats['findings_added']}")
    print(f"  Findings skipped (dupes): {stats['findings_duplicate']}")
    print()
    print(f"  Theme/Persona pairs updated this run:")
    voc_data = get_voc_by_theme_persona(args.brand)
    for theme, persona in sorted(stats['updated_pairs']):
        count = len(voc_data.get(theme, {}).get(persona, {}).get('quotes', []))
        print(f"    {theme} > {persona}: {count} quotes total")
    print()
    print(f"  Brand VoC totals: {voc_stats['quotes']:,} quotes, "
          f"{voc_stats['findings']:,} findings, "
          f"{voc_stats['theme_persona_pairs']} pairs")
    print(f"  Stored in: brands/{args.brand}/evidence.db")
    print("=" * 70)


if __name__ == '__main__':
    main()
