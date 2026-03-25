#!/usr/bin/env python3
"""
SQLite Evidence Store - Concurrent-safe storage for the Research Engine.

Replaces evidence_master.csv and personas.json with a single SQLite database
per brand. WAL mode enables concurrent reads/writes from parallel sprints.

Usage as module:
    from engine.evidence_db import get_connection, init_db, insert_evidence_batch
    from engine.evidence_db import get_all_evidence_df, load_personas, upsert_personas

Usage as CLI (export):
    python3 engine/evidence_db.py <brand> --export
"""

import sqlite3
import json
import argparse
import sys
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

# Anchor all brand paths to the project root regardless of cwd
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

DB_FILENAME = "evidence.db"

EVIDENCE_FIELDS = [
    "evidence_id", "source", "url", "date_iso", "community",
    "author", "score", "text", "parent_context",
    "thread_id", "item_type", "comment_id",
]


@contextmanager
def get_connection(brand):
    """Context manager for a WAL-mode SQLite connection with busy timeout."""
    db_path = _PROJECT_ROOT / "brands" / brand / DB_FILENAME
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(brand):
    """Create tables and indexes if they don't exist."""
    with get_connection(brand) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS evidence (
                evidence_id TEXT PRIMARY KEY,
                source TEXT,
                url TEXT,
                date_iso TEXT,
                community TEXT,
                author TEXT,
                score INTEGER,
                text TEXT,
                parent_context TEXT,
                thread_id TEXT,
                item_type TEXT,
                comment_id TEXT,
                first_seen_sprint TEXT,
                ingested_at TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_evidence_community
                ON evidence(community);
            CREATE INDEX IF NOT EXISTS idx_evidence_thread
                ON evidence(thread_id);

            CREATE TABLE IF NOT EXISTS personas (
                id TEXT PRIMARY KEY,
                label TEXT,
                description TEXT,
                justification TEXT,
                first_seen_sprint TEXT,
                insight_count INTEGER DEFAULT 0,
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS voc_curated (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                theme TEXT NOT NULL,
                persona TEXT NOT NULL,
                quote TEXT NOT NULL,
                source_sprint TEXT,
                curated_at TEXT DEFAULT (datetime('now')),
                UNIQUE(theme, persona, quote)
            );

            CREATE INDEX IF NOT EXISTS idx_voc_curated_theme_persona
                ON voc_curated(theme, persona);

            CREATE TABLE IF NOT EXISTS voc_general_findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                theme TEXT NOT NULL,
                persona TEXT NOT NULL,
                finding TEXT NOT NULL,
                source_sprint TEXT,
                curated_at TEXT DEFAULT (datetime('now')),
                UNIQUE(theme, persona, finding)
            );

            CREATE INDEX IF NOT EXISTS idx_voc_findings_theme_persona
                ON voc_general_findings(theme, persona);
        """)
    return db_path(brand)


def db_path(brand):
    """Return the Path to the evidence.db for a brand."""
    return _PROJECT_ROOT / "brands" / brand / DB_FILENAME


def insert_evidence_batch(brand, rows, sprint):
    """Insert evidence rows, ignoring duplicates by evidence_id.

    Args:
        brand: Brand name
        rows: List of dicts with EVIDENCE_FIELDS keys
        sprint: Sprint name (stored as first_seen_sprint for new rows)

    Returns:
        (inserted, skipped) counts
    """
    evidence_ids = [row.get("evidence_id", "") for row in rows]

    with get_connection(brand) as conn:
        conn.executemany("""
            INSERT OR IGNORE INTO evidence
                (evidence_id, source, url, date_iso, community,
                 author, score, text, parent_context,
                 thread_id, item_type, comment_id,
                 first_seen_sprint)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (
                row.get("evidence_id", ""),
                row.get("source", ""),
                row.get("url", ""),
                row.get("date_iso", ""),
                row.get("community", ""),
                row.get("author", ""),
                row.get("score", 0),
                row.get("text", ""),
                row.get("parent_context", ""),
                row.get("thread_id", ""),
                row.get("item_type", ""),
                row.get("comment_id", ""),
                sprint,
            )
            for row in rows
        ])

        # Count how many of our IDs ended up with this sprint tag (= truly new)
        placeholders = ",".join("?" * len(evidence_ids))
        inserted = conn.execute(
            f"SELECT COUNT(*) FROM evidence WHERE evidence_id IN ({placeholders}) AND first_seen_sprint = ?",
            evidence_ids + [sprint]
        ).fetchone()[0]

    skipped = len(rows) - inserted
    return inserted, skipped


def insert_evidence_batch_fast(brand, rows, sprint):
    """Fast batch insert for migration — skips per-row counting.

    Returns total rows in DB after insert.
    """
    with get_connection(brand) as conn:
        conn.executemany("""
            INSERT OR IGNORE INTO evidence
                (evidence_id, source, url, date_iso, community,
                 author, score, text, parent_context,
                 thread_id, item_type, comment_id,
                 first_seen_sprint)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (
                row.get("evidence_id", ""),
                row.get("source", ""),
                row.get("url", ""),
                row.get("date_iso", ""),
                row.get("community", ""),
                row.get("author", ""),
                row.get("score", 0),
                row.get("text", ""),
                row.get("parent_context", ""),
                row.get("thread_id", ""),
                row.get("item_type", ""),
                row.get("comment_id", ""),
                sprint,
            )
            for row in rows
        ])

    with get_connection(brand) as conn:
        total = conn.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]

    return total


def get_evidence_count(brand):
    """Return total evidence count."""
    with get_connection(brand) as conn:
        return conn.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]


def get_all_evidence_df(brand):
    """Load all evidence as a pandas DataFrame (drop-in replacement for CSV read)."""
    with get_connection(brand) as conn:
        df = pd.read_sql_query(
            f"SELECT {', '.join(EVIDENCE_FIELDS)} FROM evidence",
            conn
        )
    return df


def get_evidence_by_ids(brand, evidence_ids):
    """Load specific evidence rows by ID as a pandas DataFrame.

    Useful for retrieving pre-matched evidence without re-running regex.
    Batches queries in chunks of 500 to avoid SQLite variable limits.
    """
    if not evidence_ids:
        return pd.DataFrame(columns=EVIDENCE_FIELDS)

    chunks = [evidence_ids[i:i+500] for i in range(0, len(evidence_ids), 500)]
    frames = []

    with get_connection(brand) as conn:
        for chunk in chunks:
            placeholders = ",".join("?" * len(chunk))
            df = pd.read_sql_query(
                f"SELECT {', '.join(EVIDENCE_FIELDS)} FROM evidence WHERE evidence_id IN ({placeholders})",
                conn,
                params=chunk
            )
            frames.append(df)

    if not frames:
        return pd.DataFrame(columns=EVIDENCE_FIELDS)

    return pd.concat(frames, ignore_index=True)


def load_personas(brand):
    """Load personas from DB as a dict matching the old JSON format.

    Returns: {"personas": [{"id": ..., "label": ..., ...}, ...]}
    """
    with get_connection(brand) as conn:
        cursor = conn.execute(
            "SELECT id, label, description, justification, first_seen_sprint, insight_count "
            "FROM personas ORDER BY id"
        )
        personas = []
        for row in cursor:
            personas.append({
                "id": row["id"],
                "label": row["label"],
                "description": row["description"],
                "justification": row["justification"],
                "first_seen_sprint": row["first_seen_sprint"],
                "insight_count": row["insight_count"],
            })

    return {"personas": personas}


def upsert_personas(brand, ledger_data):
    """Write personas to DB from the ledger dict format.

    Args:
        brand: Brand name
        ledger_data: Dict with "personas" list (same format as personas.json)
    """
    with get_connection(brand) as conn:
        for p in ledger_data.get("personas", []):
            conn.execute("""
                INSERT INTO personas (id, label, description, justification,
                                      first_seen_sprint, insight_count, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(id) DO UPDATE SET
                    label = excluded.label,
                    description = excluded.description,
                    justification = excluded.justification,
                    insight_count = excluded.insight_count,
                    updated_at = datetime('now')
            """, (
                p["id"],
                p.get("label", ""),
                p.get("description", ""),
                p.get("justification", ""),
                p.get("first_seen_sprint", ""),
                p.get("insight_count", 0),
            ))


def upsert_voc_curated(brand, theme, persona, quotes, source_sprint=None):
    """Insert curated VoC quotes, ignoring duplicates.

    Args:
        brand: Brand name
        theme: Theme name
        persona: Persona name
        quotes: List of quote strings
        source_sprint: Sprint that sourced these quotes

    Returns:
        (inserted, skipped) counts
    """
    inserted = 0
    skipped = 0
    with get_connection(brand) as conn:
        for quote in quotes:
            try:
                conn.execute(
                    "INSERT INTO voc_curated (theme, persona, quote, source_sprint) "
                    "VALUES (?, ?, ?, ?)",
                    (theme, persona, quote, source_sprint)
                )
                inserted += 1
            except sqlite3.IntegrityError:
                skipped += 1
    return inserted, skipped


def upsert_voc_findings(brand, theme, persona, findings, source_sprint=None):
    """Insert general VoC findings, ignoring duplicates.

    Returns:
        (inserted, skipped) counts
    """
    inserted = 0
    skipped = 0
    with get_connection(brand) as conn:
        for finding in findings:
            try:
                conn.execute(
                    "INSERT INTO voc_general_findings (theme, persona, finding, source_sprint) "
                    "VALUES (?, ?, ?, ?)",
                    (theme, persona, finding, source_sprint)
                )
                inserted += 1
            except sqlite3.IntegrityError:
                skipped += 1
    return inserted, skipped


def get_voc_by_theme_persona(brand, theme=None, persona=None):
    """Retrieve curated VoC data, optionally filtered by theme and/or persona.

    Returns:
        Dict of {theme: {persona: {"quotes": [...], "general_findings": [...], "sources": [...]}}}
    """
    result = {}

    with get_connection(brand) as conn:
        # Build quotes query
        q_sql = "SELECT theme, persona, quote, source_sprint FROM voc_curated"
        q_params = []
        conditions = []
        if theme:
            conditions.append("theme = ?")
            q_params.append(theme)
        if persona:
            conditions.append("persona = ?")
            q_params.append(persona)
        if conditions:
            q_sql += " WHERE " + " AND ".join(conditions)
        q_sql += " ORDER BY theme, persona, curated_at"

        for row in conn.execute(q_sql, q_params):
            t, p = row["theme"], row["persona"]
            result.setdefault(t, {}).setdefault(p, {"quotes": [], "general_findings": [], "sources": []})
            result[t][p]["quotes"].append(row["quote"])
            sprint = row["source_sprint"]
            if sprint and sprint not in result[t][p]["sources"]:
                result[t][p]["sources"].append(sprint)

        # Build findings query
        f_sql = "SELECT theme, persona, finding, source_sprint FROM voc_general_findings"
        f_params = []
        conditions = []
        if theme:
            conditions.append("theme = ?")
            f_params.append(theme)
        if persona:
            conditions.append("persona = ?")
            f_params.append(persona)
        if conditions:
            f_sql += " WHERE " + " AND ".join(conditions)
        f_sql += " ORDER BY theme, persona, curated_at"

        for row in conn.execute(f_sql, f_params):
            t, p = row["theme"], row["persona"]
            result.setdefault(t, {}).setdefault(p, {"quotes": [], "general_findings": [], "sources": []})
            result[t][p]["general_findings"].append(row["finding"])
            sprint = row["source_sprint"]
            if sprint and sprint not in result[t][p]["sources"]:
                result[t][p]["sources"].append(sprint)

    return result


def export_voc_json(brand, output_path=None):
    """Export curated VoC data to JSON format (backward-compatible with voc_master.json).

    Args:
        brand: Brand name
        output_path: Optional output path. Defaults to brands/<brand>/voc_master.json

    Returns:
        Path to the exported file
    """
    from datetime import datetime

    if output_path is None:
        output_path = _PROJECT_ROOT / "brands" / brand / "voc_master.json"

    voc_data = get_voc_by_theme_persona(brand)

    master = {
        "last_updated": datetime.now().isoformat(),
        "themes": voc_data,
    }

    with open(output_path, 'w') as f:
        json.dump(master, f, indent=2)

    print(f"Exported VoC data to {output_path}")
    return output_path


def get_voc_stats(brand):
    """Return VoC statistics for a brand."""
    with get_connection(brand) as conn:
        # Check if VoC tables exist (DB may predate VoC migration)
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        if 'voc_curated' not in tables:
            return {"quotes": 0, "findings": 0, "themes": 0, "theme_persona_pairs": 0}

        quotes_count = conn.execute("SELECT COUNT(*) FROM voc_curated").fetchone()[0]
        findings_count = conn.execute("SELECT COUNT(*) FROM voc_general_findings").fetchone()[0]
        themes = conn.execute("SELECT COUNT(DISTINCT theme) FROM voc_curated").fetchone()[0]
        pairs = conn.execute(
            "SELECT COUNT(*) FROM (SELECT DISTINCT theme, persona FROM voc_curated)"
        ).fetchone()[0]
    return {
        "quotes": quotes_count,
        "findings": findings_count,
        "themes": themes,
        "theme_persona_pairs": pairs,
    }


def export_evidence_csv(brand, output_path=None):
    """Export evidence.db to CSV for inspection or backup.

    Args:
        brand: Brand name
        output_path: Optional output path. Defaults to brands/<brand>/evidence_export.csv
    """
    if output_path is None:
        output_path = _PROJECT_ROOT / "brands" / brand / "evidence_export.csv"

    df = get_all_evidence_df(brand)
    df.to_csv(output_path, index=False)
    print(f"Exported {len(df)} rows to {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Evidence DB utilities")
    parser.add_argument("brand", help="Brand name")
    parser.add_argument("--export", action="store_true", help="Export evidence.db to CSV")
    parser.add_argument("--output", help="Output path for export")
    parser.add_argument("--stats", action="store_true", help="Print DB statistics")
    parser.add_argument("--init", action="store_true", help="Initialize DB (create tables)")

    args = parser.parse_args()

    if args.init:
        init_db(args.brand)
        print(f"Initialized {db_path(args.brand)}")

    elif args.export:
        output = Path(args.output) if args.output else None
        export_evidence_csv(args.brand, output)

    elif args.stats:
        count = get_evidence_count(args.brand)
        personas = load_personas(args.brand)
        p_count = len(personas.get("personas", []))
        voc = get_voc_stats(args.brand)
        print(f"Brand: {args.brand}")
        print(f"Evidence: {count:,} rows")
        print(f"Personas: {p_count}")
        print(f"VoC quotes: {voc['quotes']:,}")
        print(f"VoC findings: {voc['findings']:,}")
        print(f"VoC theme/persona pairs: {voc['theme_persona_pairs']}")
        print(f"DB path: {db_path(args.brand)}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
