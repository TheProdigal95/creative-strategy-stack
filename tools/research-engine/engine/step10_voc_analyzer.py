#!/usr/bin/env python3
"""
VoC Analyzer - Step 10 of Research Engine

Analyzes voice of customer for each insight by retrieving ALL matched evidence
and using LLM to extract authentic quotes and language patterns.

Adds VoC and Keep columns to the existing insights_final.csv.

Usage:
    python3 engine/step10_voc_analyzer.py mybrand 01_weight-loss-men-dads
    python3 engine/step10_voc_analyzer.py mybrand "03 - Time Scarcity for Busy People"
    python3 engine/step10_voc_analyzer.py mybrand 01_weight-loss-men-dads --verbose
"""

import os
import sys
import json
import argparse
import asyncio
import re
import random
import shutil
import pandas as pd
from pathlib import Path
from datetime import datetime
from claude_code_sdk import query, ClaudeCodeOptions


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

class Logger:
    """Simple file + stdout logger."""

    def __init__(self, log_path):
        self.log_path = log_path
        self.lines = []

    def log(self, msg):
        timestamp = datetime.now().strftime('%H:%M:%S')
        line = f"[{timestamp}] {msg}"
        print(line)
        self.lines.append(line)

    def warn(self, msg):
        self.log(f"WARNING: {msg}")

    def save(self):
        with open(self.log_path, 'w') as f:
            f.write('\n'.join(self.lines) + '\n')


# ---------------------------------------------------------------------------
# Validation & Loading
# ---------------------------------------------------------------------------

def resolve_sprint_dir(brand, sprint):
    """Resolve sprint directory, handling both naming formats."""
    base = f"brands/{brand}/sprints"
    direct = os.path.join(base, sprint)
    if os.path.isdir(direct):
        return direct

    # Try matching by prefix number
    if os.path.isdir(base):
        for entry in os.listdir(base):
            entry_path = os.path.join(base, entry)
            if os.path.isdir(entry_path):
                # Match on leading digits
                entry_prefix = entry.split('_')[0].split(' ')[0].split('-')[0]
                sprint_prefix = sprint.split('_')[0].split(' ')[0].split('-')[0]
                if entry_prefix == sprint_prefix:
                    return entry_path

    return direct  # Fall through, will fail at validation


def validate_inputs(sprint_dir):
    """Verify all required input files exist. Returns paths dict or exits.

    Step 10 now reads from themes_discovered.json (Step 08 output) instead of
    insights_complete.json (Step 09 output), enabling concurrent execution with Step 09.
    """
    paths = {
        'themes_json': os.path.join(sprint_dir, '_intermediate', 'themes_discovered.json'),
        'evidence_csv': os.path.join(sprint_dir, '_intermediate', 'evidence_filtered.csv'),
    }

    # Also check for insights_complete.json as fallback (backward compat with existing sprints)
    insights_complete = os.path.join(sprint_dir, '_intermediate', 'insights_complete.json')
    if os.path.exists(insights_complete):
        paths['insights_json'] = insights_complete

    missing = []
    for label, path in paths.items():
        if not os.path.exists(path):
            missing.append(f"  {label}: {path}")

    if missing:
        print("ERROR: Missing required input files:")
        for m in missing:
            print(m)
        print("\nEnsure Step 08 (Evidence Matching) has completed for this sprint.")
        sys.exit(1)

    return paths


def load_themes_json(json_path):
    """Load themes_discovered.json and build lookup + insight list.

    Returns:
        (insights_list, insights_lookup) where:
        - insights_list: list of dicts with insight_text, theme, persona
        - insights_lookup: dict keyed by insight text with full insight data
    """
    with open(json_path, 'r') as f:
        data = json.load(f)

    insights_list = []
    lookup = {}
    for theme in data.get('themes', []):
        theme_name = theme.get('theme_name', '')
        for insight in theme.get('insights', []):
            key = insight.get('insight', '').strip()
            if key:
                lookup[key] = insight
                # Build persona display name (snake_case to Title Case)
                persona_raw = insight.get('persona_normalized', '')
                persona = ' '.join(w.capitalize() for w in persona_raw.split('_')) if persona_raw else ''
                insights_list.append({
                    'insight_text': key,
                    'theme': theme_name,
                    'persona': persona,
                })

    return insights_list, lookup


def load_evidence(csv_path):
    """Load evidence_filtered.csv."""
    df = pd.read_csv(csv_path)
    # Ensure relevance_score is numeric
    df['relevance_score'] = pd.to_numeric(df['relevance_score'], errors='coerce').fillna(0)
    return df


# ---------------------------------------------------------------------------
# Evidence Retrieval
# ---------------------------------------------------------------------------

def matches_pattern(text, pattern):
    """Check if pattern matches in text using word boundary matching."""
    if pd.isna(text) or not text:
        return False
    pattern_escaped = re.escape(pattern.lower())
    regex = r'\b' + pattern_escaped + r'\b'
    return bool(re.search(regex, str(text).lower()))


def retrieve_evidence_by_ids(evidence_ids, evidence_df):
    """Retrieve evidence by pre-computed IDs from Step 08 — single isin() lookup."""
    if not evidence_ids:
        return pd.DataFrame()

    matched = evidence_df[evidence_df['evidence_id'].isin(evidence_ids)]
    return matched


def retrieve_evidence_by_regex(patterns, evidence_df):
    """Retrieve evidence by regex matching — fallback for old sprints without matched_evidence_ids."""
    if not patterns:
        return pd.DataFrame()

    matched_indices = set()
    for pattern in patterns:
        mask = evidence_df['text'].apply(lambda t: matches_pattern(t, pattern))
        matched_indices.update(evidence_df[mask].index.tolist())

    if not matched_indices:
        return pd.DataFrame()

    return evidence_df.loc[sorted(matched_indices)]


def sample_evidence(matched_df, top_n=10, community_n=5, short_n=5):
    """Sample 20 evidence pieces: top by relevance + community diversity + short quotes.

    - top_n: highest relevance_score (strongest signal)
    - community_n: from underrepresented communities (diversity)
    - short_n: short pieces under 200 chars (most quotable)
    """
    if len(matched_df) == 0:
        return matched_df

    total_budget = top_n + community_n + short_n

    if len(matched_df) <= total_budget:
        return matched_df.sort_values('relevance_score', ascending=False)

    sorted_df = matched_df.sort_values('relevance_score', ascending=False)
    selected_indices = set()

    # 1. Top N by relevance score
    top = sorted_df.head(top_n)
    selected_indices.update(top.index.tolist())

    # 2. From underrepresented communities (not already in top)
    top_communities = set(top['community'].dropna().unique())
    remaining = sorted_df[~sorted_df.index.isin(selected_indices)]
    underrep = remaining[~remaining['community'].isin(top_communities)]
    if len(underrep) > 0:
        community_sample = underrep.head(community_n)
        selected_indices.update(community_sample.index.tolist())

    # 3. Short pieces under 200 chars (most quotable)
    remaining = sorted_df[~sorted_df.index.isin(selected_indices)]
    short_mask = remaining['text'].apply(lambda t: isinstance(t, str) and 0 < len(t) < 200)
    short_pieces = remaining[short_mask]
    if len(short_pieces) > 0:
        short_sample = short_pieces.sort_values('relevance_score', ascending=False).head(short_n)
        selected_indices.update(short_sample.index.tolist())

    combined = sorted_df.loc[sorted(selected_indices)]
    return combined.sort_values('relevance_score', ascending=False)


# ---------------------------------------------------------------------------
# LLM Interaction
# ---------------------------------------------------------------------------

VOC_SYSTEM_INSTRUCTIONS = """You are analyzing voice of customer (VoC) evidence from Reddit discussions.

For each insight below, you'll see real quotes from people discussing the topic.

YOUR TASK: Analyze how people actually speak about each topic.

For each insight:
- Extract the best direct quotes that capture how they speak. Include what's genuinely good — typically 3-7 quotes but could be more or fewer based on quality. Prefer quotes that are vivid, emotional, or reveal authentic language patterns. Trim surrounding filler but keep the speaker's exact words.
- Note the tone(s) you observe: humor, self-deprecating, blunt, clinical, serious, hopeful, frustrated, etc. Only report tones actually present — don't force categories.
- Note how they express pain vs desire, recurring phrases, notable word choices.

Be honest. If there's great humor, report it. If language is mostly clinical, say that. If multiple tones exist, report all of them. If evidence is thin or generic, say so.

OUTPUT FORMAT — follow this exactly for each insight:

=== INSIGHT {n} VOC ===
QUOTES:
- "exact quote"
- "exact quote"

GENERAL: [1-2 sentences on tone, patterns, language]
=== END INSIGHT {n} ===

CRITICAL: Output ONLY the formatted blocks above. No preamble, no commentary outside the blocks."""


def build_voc_batch_data(batch):
    """Build the variable per-batch data prompt (insight + evidence only)."""

    prompt = ""

    for i, item in enumerate(batch, 1):
        prompt += f"\n{'—'*60}\n"
        prompt += f"INSIGHT {i}: {item['insight_text']}\n"
        prompt += f"Theme: {item['theme']}\n"
        prompt += f"Persona: {item['persona']}\n"
        prompt += f"\nEvidence samples ({len(item['evidence_texts'])} pieces):\n"

        for j, ev_text in enumerate(item['evidence_texts'], 1):
            # Truncate individual evidence to 300 chars (matches Step 08 best_quotes length)
            text = ev_text[:300] + "..." if len(ev_text) > 300 else ev_text
            prompt += f"[{j}] {text}\n"

    return prompt


def parse_voc_response(response_text, expected_count):
    """Parse VoC response into per-insight results."""
    results = {}

    for i in range(1, expected_count + 1):
        start_marker = f"=== INSIGHT {i} VOC ==="
        end_marker = f"=== END INSIGHT {i} ==="

        start_idx = response_text.find(start_marker)
        end_idx = response_text.find(end_marker)

        if start_idx == -1 or end_idx == -1:
            results[i] = None
            continue

        block = response_text[start_idx + len(start_marker):end_idx].strip()

        # Extract quotes
        quotes = []
        general = ""

        lines = block.split('\n')
        in_quotes = False
        for line in lines:
            stripped = line.strip()
            if stripped.upper().startswith('QUOTES:'):
                in_quotes = True
                continue
            if stripped.upper().startswith('GENERAL:'):
                in_quotes = False
                general = stripped[len('GENERAL:'):].strip()
                continue

            if in_quotes and stripped.startswith('- '):
                quote = stripped[2:].strip()
                # Remove surrounding quotes if present
                if quote.startswith('"') and quote.endswith('"'):
                    quote = quote[1:-1]
                if quote:
                    quotes.append(quote)
            elif not in_quotes and stripped and not general:
                # Continuation of general line
                general += ' ' + stripped

        results[i] = {
            'quotes': quotes,
            'general': general.strip(),
        }

    return results


def format_voc_cell(voc_data):
    """Format VoC data into a single cell value."""
    if not voc_data:
        return "VoC analysis failed - check logs"

    parts = []
    for quote in voc_data['quotes']:
        parts.append(f'- "{quote}"')

    if voc_data['general']:
        parts.append('')
        parts.append(f"General: {voc_data['general']}")

    return '\n'.join(parts)


async def call_llm(prompt, logger, retries=2, system_prompt=None):
    """Call Claude with retry logic.

    Args:
        prompt: User prompt (variable data)
        logger: Logger instance
        retries: Number of retry attempts
        system_prompt: Optional system prompt (static instructions, cached by API)
    """
    options = ClaudeCodeOptions(model="claude-sonnet-4-6", max_turns=3)
    if system_prompt:
        options = ClaudeCodeOptions(model="claude-sonnet-4-6", system_prompt=system_prompt, max_turns=3)

    for attempt in range(retries + 1):
        try:
            response_text = ""
            async for message in query(
                prompt=prompt,
                options=options
            ):
                if hasattr(message, 'content'):
                    for block in message.content:
                        if hasattr(block, 'text'):
                            response_text += block.text
            return response_text

        except Exception as e:
            # SDK throws on unknown message types (e.g. rate_limit_event).
            # If we already collected a response, return it instead of retrying.
            if "Unknown message type" in str(e) and response_text:
                logger.warn(f"SDK parse warning (non-fatal, got response): {e}")
                return response_text

            if attempt < retries:
                logger.warn(f"LLM call failed (attempt {attempt + 1}): {e}. Retrying...")
                await asyncio.sleep(2)
            else:
                logger.warn(f"LLM call failed after {retries + 1} attempts: {e}")
                raise


# ---------------------------------------------------------------------------
# Main Processing
# ---------------------------------------------------------------------------

async def process_all_insights(insights_list, insights_lookup, evidence_df, logger,
                               batch_size=5, verbose=False, max_concurrent=3):
    """Process all insights: retrieve evidence, call LLM, return VoC results.

    Args:
        insights_list: list of dicts with insight_text, theme, persona
        insights_lookup: dict keyed by insight text with full insight data (from themes JSON)
        evidence_df: DataFrame of filtered evidence
        logger: Logger instance
        batch_size: insights per LLM batch
        verbose: print LLM prompts
        max_concurrent: max concurrent LLM calls

    Runs up to max_concurrent LLM batch calls concurrently.
    """

    voc_results = {}  # keyed by insight text

    # Build work items
    work_items = []
    for item in insights_list:
        insight_text = item['insight_text']
        theme = item.get('theme', '')
        persona = item.get('persona', '')

        # Match to JSON data
        json_data = insights_lookup.get(insight_text)
        if not json_data:
            logger.warn(f"No JSON match for insight: {insight_text[:80]}...")
            voc_results[insight_text] = None
            continue

        # Use pre-computed IDs from Step 08 if available, fall back to regex
        evidence_ids = json_data.get('matched_evidence_ids')
        if evidence_ids:
            matched = retrieve_evidence_by_ids(evidence_ids, evidence_df)
            total_matched = len(matched)
        else:
            # Fallback for sprints run before matched_evidence_ids was added
            patterns = json_data.get('matching_patterns', [])
            if not patterns:
                logger.warn(f"No matching_patterns for: {insight_text[:80]}...")
                voc_results[insight_text] = None
                continue
            matched = retrieve_evidence_by_regex(patterns, evidence_df)
            total_matched = len(matched)

        if total_matched == 0:
            logger.warn(f"  No evidence matched for: {insight_text[:80]}...")
            voc_results[insight_text] = None
            continue

        # Sample for LLM
        sampled = sample_evidence(matched)
        evidence_texts = sampled['text'].dropna().tolist()

        logger.log(f"  {insight_text[:60]}... → {total_matched} matched, {len(evidence_texts)} sampled")

        work_items.append({
            'insight_text': insight_text,
            'theme': theme,
            'persona': persona,
            'evidence_texts': evidence_texts,
            'total_matched': total_matched,
        })

    # Build batches
    total = len(work_items)
    logger.log(f"\nProcessing {total} insights in batches of {batch_size} (concurrency: {max_concurrent})...")

    batches = []
    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch = work_items[batch_start:batch_end]
        batch_num = batch_start // batch_size + 1
        batches.append((batch_num, batch_start, batch_end, batch))

    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_batch(batch_num, batch_start, batch_end, batch):
        async with semaphore:
            logger.log(f"\n  Batch {batch_num}: insights {batch_start + 1}-{batch_end} of {total}")

            # Skip batch if all items have no evidence
            if all(len(item['evidence_texts']) == 0 for item in batch):
                logger.warn(f"  Skipping batch — no evidence for any insight")
                batch_results = {}
                for item in batch:
                    batch_results[item['insight_text']] = {
                        'quotes': [],
                        'general': 'No matching evidence found.',
                    }
                return batch_results

            data_prompt = build_voc_batch_data(batch)

            if verbose:
                print("\n" + "=" * 80)
                print("SYSTEM PROMPT (cached across batches):")
                print("=" * 80)
                print(VOC_SYSTEM_INSTRUCTIONS[:500] + "\n... [truncated]")
                print("=" * 80)
                print("USER PROMPT (batch data):")
                print("=" * 80)
                print(data_prompt[:3000] + "\n... [truncated]" if len(data_prompt) > 3000 else data_prompt)
                print("=" * 80 + "\n")

            batch_results = {}
            try:
                response_text = await call_llm(data_prompt, logger, system_prompt=VOC_SYSTEM_INSTRUCTIONS)
                parsed = parse_voc_response(response_text, len(batch))

                for i, item in enumerate(batch, 1):
                    batch_results[item['insight_text']] = parsed.get(i)
                    if parsed.get(i) is None:
                        logger.warn(f"  Failed to parse VoC for: {item['insight_text'][:60]}...")

                logger.log(f"  Batch complete — {sum(1 for i in range(1, len(batch)+1) if parsed.get(i))} of {len(batch)} parsed successfully")

            except Exception as e:
                logger.warn(f"  Batch failed: {e}")
                for item in batch:
                    batch_results[item['insight_text']] = None

            return batch_results

    # Run all batches concurrently (limited by semaphore)
    tasks = [process_batch(bn, bs, be, b) for bn, bs, be, b in batches]
    results = await asyncio.gather(*tasks)

    # Merge batch results into voc_results
    for batch_results in results:
        voc_results.update(batch_results)

    return voc_results


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def add_voc_columns(insights_df, voc_results):
    """Add VoC and Keep columns to the dataframe."""
    voc_values = []
    for _, row in insights_df.iterrows():
        insight_text = row['Insight']
        voc_data = voc_results.get(insight_text)
        voc_values.append(format_voc_cell(voc_data))

    insights_df['VoC'] = voc_values
    insights_df['Keep'] = ''

    return insights_df


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

async def main_async():
    parser = argparse.ArgumentParser(description='Analyze voice of customer for each insight')
    parser.add_argument('brand', help='Brand name (e.g., mybrand)')
    parser.add_argument('sprint', help='Sprint folder name')
    parser.add_argument('--batch-size', type=int, default=5,
                        help='Insights per LLM batch (default: 5)')
    parser.add_argument('--verbose', action='store_true',
                        help='Print LLM prompts')

    args = parser.parse_args()

    # Resolve paths
    sprint_dir = resolve_sprint_dir(args.brand, args.sprint)
    intermediate_dir = os.path.join(sprint_dir, '_intermediate')

    print("=" * 80)
    print("VOC ANALYZER - STEP 10")
    print("=" * 80)
    print(f"Brand: {args.brand}")
    print(f"Sprint: {args.sprint}")
    print(f"Sprint dir: {sprint_dir}")
    print()

    # Validate
    paths = validate_inputs(sprint_dir)

    # Set up logger
    log_path = os.path.join(intermediate_dir, 'voc_analysis_log.txt')
    logger = Logger(log_path)
    logger.log(f"VoC Analyzer started for {args.brand} / {args.sprint}")

    # Load inputs — read from themes_discovered.json (Step 08 output)
    print("Loading data...")
    insights_list, insights_lookup = load_themes_json(paths['themes_json'])
    logger.log(f"Loaded themes_discovered.json: {len(insights_list)} insights")

    evidence_df = load_evidence(paths['evidence_csv'])
    logger.log(f"Loaded evidence_filtered.csv: {len(evidence_df):,} evidence pieces")

    # Process
    logger.log("\nRetrieving evidence and analyzing VoC...")
    voc_results = await process_all_insights(
        insights_list, insights_lookup, evidence_df, logger,
        batch_size=args.batch_size, verbose=args.verbose
    )

    # Save VoC results as JSON (for merge step to pick up)
    voc_json_path = os.path.join(intermediate_dir, 'voc_analysis.json')
    voc_serializable = {}
    for key, val in voc_results.items():
        if val is not None:
            voc_serializable[key] = val
        else:
            voc_serializable[key] = {'quotes': [], 'general': 'VoC analysis failed - check logs'}

    with open(voc_json_path, 'w') as f:
        json.dump(voc_serializable, f, indent=2, ensure_ascii=False)
    logger.log(f"\nSaved VoC results to: {voc_json_path}")

    # Also merge into insights_final.csv if it exists (backward compat / standalone usage)
    insights_csv_path = os.path.join(sprint_dir, 'insights_final.csv')
    if os.path.exists(insights_csv_path):
        insights_df = pd.read_csv(insights_csv_path)
        backup_path = os.path.join(intermediate_dir, 'insights_final_backup.csv')
        shutil.copy2(insights_csv_path, backup_path)
        logger.log(f"Backed up original to: {backup_path}")

        updated_df = add_voc_columns(insights_df, voc_results)
        updated_df.to_csv(insights_csv_path, index=False)
        logger.log(f"Saved updated insights_final.csv with VoC and Keep columns")

    # Summary
    total = len(insights_list)
    with_voc = sum(1 for v in voc_results.values() if v is not None and v.get('quotes'))
    failed = total - with_voc

    logger.log(f"\n{'='*80}")
    logger.log(f"COMPLETE")
    logger.log(f"  {total} insights processed")
    logger.log(f"  {with_voc} with VoC analysis")
    logger.log(f"  {failed} failed or empty")
    logger.log(f"{'='*80}")

    # Save log
    logger.save()
    print(f"\nLog saved to: {log_path}")


def main():
    asyncio.run(main_async())


if __name__ == '__main__':
    main()
