#!/usr/bin/env python3
"""
Language Miner - Step 12 of Research Engine

Produces a structured language report showing how the target audience actually
talks — phrases, humor patterns, tone, slang — for direct copywriter use.

Runs after Step 10 (VoC Analyzer). Reads evidence_filtered.csv (from Step 05)
and sprint_config.txt. Outputs language_report.json in the sprint root.

How it works:
1. Quantitative pre-pass: extract 2-4 word n-grams, count frequencies
2. Sample evidence if pool > 200
3. Single LLM call with sampled evidence + top n-grams
4. Write structured JSON report

Usage:
    python3 engine/step12_language_miner.py pureplank "05 - Dad Bod Comeback Humor"
    python3 engine/step12_language_miner.py pureplank 05
"""

import os
import sys
import json
import argparse
import asyncio
import re
import random
from collections import Counter
from pathlib import Path
from datetime import datetime
from claude_code_sdk import query, ClaudeCodeOptions
import pandas as pd


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
# Path Resolution & Loading
# ---------------------------------------------------------------------------

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


def load_evidence(csv_path):
    """Load evidence_filtered.csv and return DataFrame."""
    df = pd.read_csv(csv_path)
    df['relevance_score'] = pd.to_numeric(df['relevance_score'], errors='coerce').fillna(0)
    return df


def load_sprint_config(txt_path):
    """Load sprint_config.txt and return research direction."""
    with open(txt_path, 'r') as f:
        content = f.read()

    research_direction = ""
    for line in content.split('\n'):
        line_lower = line.lower().strip()
        if line_lower.startswith("research direction:") or line_lower.startswith("research_direction:"):
            research_direction = line.split(":", 1)[1].strip()
            break

    return research_direction


# ---------------------------------------------------------------------------
# Quantitative Pre-Pass: N-Gram Extraction
# ---------------------------------------------------------------------------

def clean_text(text):
    """Lowercase, strip URLs, strip markdown, keep only alpha + spaces."""
    if pd.isna(text):
        return ""
    text = str(text).lower()
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    # Remove HTML entities (amp, nbsp, etc.)
    text = re.sub(r'&\w+;?', ' ', text)
    text = re.sub(r'\bamp\b', ' ', text)
    text = re.sub(r'\bnbsp\b', ' ', text)
    # Remove markdown table formatting (|, --, x patterns in tables)
    text = re.sub(r'\|', ' ', text)
    text = re.sub(r'(?:^|\s)[-x]+(?:\s|$)', ' ', text)
    # Remove markdown links
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Remove markdown formatting
    text = re.sub(r'[*_#>`~]', '', text)
    # Keep alpha, apostrophes, hyphens, spaces
    text = re.sub(r"[^a-z'\-\s]", ' ', text)
    # Remove standalone single characters and bare hyphens
    text = re.sub(r'\b[a-z]\b', ' ', text)
    text = re.sub(r'(?:^|\s)-+(?:\s|$)', ' ', text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


STOPWORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'is', 'was', 'are', 'were', 'be', 'been',
    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
    'could', 'should', 'may', 'might', 'shall', 'can', 'not', 'no', 'nor',
    'if', 'then', 'than', 'so', 'as', 'it', 'its', 'that', 'this', 'those',
    'these', 'there', 'here', 'what', 'which', 'who', 'whom', 'when', 'where',
    'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
    'some', 'such', 'only', 'own', 'same', 'too', 'very', 'just', 'about',
    'also', 'into', 'out', 'up', 'down', 'over', 'under', 'again', 'further',
    'once', 'any', 'my', 'your', 'his', 'her', 'our', 'their', 'me', 'him',
    'she', 'he', 'we', 'they', 'you', 'i', 'am', 'much', 'many', 'still',
    'get', 'got', 'go', 'went', 'going', 'one', 'two', 'don', 'didn', 'doesn',
    'like', 'really', 'even', 'think', 'know', 'want', 'make', 'way', 'thing',
    'things', 'lot', 'time', 'year', 'years', 'people', 'back', 'good',
    'well', 'right', 'now', 'day', 'days', 'see', 'take', 'come', 'need',
    'work', 'try', 'new', 'first', 'last', 'long', 'great', 'little', 'after',
    'before', 'through', 'between', 'never', 'always', 'something', 'anything',
    'nothing', 'everything', 'someone', 'anyone', 'everyone', 'since', 'while',
    'been', 'them', 'us', 'because', 'until', 'during', 'without', 'around',
    'made', 'said', 'say', 'start', 'started', 'keep', 'feel', 'point',
    'put', 'find', 'help', 'tell', 'told', 'give', 'let', 'end', 'life',
    'look', 'looking', 'pretty', 'sure', 'actually', 'though', 'enough',
    've', 're', 'll', 'don\'t', 'didn\'t', 'doesn\'t', 'won\'t', 'can\'t',
    'isn\'t', 'wasn\'t', 'aren\'t', 'weren\'t', 'wouldn\'t', 'couldn\'t',
    'shouldn\'t',
}


def extract_ngrams(texts, min_n=2, max_n=4, min_freq=3):
    """Extract n-grams from texts, filtered by frequency threshold.

    Returns list of (ngram_string, count) sorted by count descending.
    """
    counters = {n: Counter() for n in range(min_n, max_n + 1)}

    for text in texts:
        cleaned = clean_text(text)
        words = cleaned.split()

        for n in range(min_n, max_n + 1):
            for i in range(len(words) - n + 1):
                gram = tuple(words[i:i + n])
                # Skip if first or last word is a stopword
                if gram[0] in STOPWORDS or gram[-1] in STOPWORDS:
                    continue
                # Skip if ALL words are stopwords
                if all(w in STOPWORDS for w in gram):
                    continue
                counters[n][gram] += 1

    # Merge all n-gram sizes, filter by frequency
    all_ngrams = []
    for n in range(min_n, max_n + 1):
        for gram, count in counters[n].items():
            if count >= min_freq:
                all_ngrams.append((' '.join(gram), count))

    # Sort by frequency descending
    all_ngrams.sort(key=lambda x: (-x[1], x[0]))
    return all_ngrams


# ---------------------------------------------------------------------------
# Evidence Sampling
# ---------------------------------------------------------------------------

def sample_evidence_for_llm(df, max_total=200):
    """Sample evidence for LLM call.

    If <= max_total, send all. Otherwise: top 50 by relevance + 150 stratified.
    """
    if len(df) <= max_total:
        return df.sort_values('relevance_score', ascending=False)

    sorted_df = df.sort_values('relevance_score', ascending=False)

    # Top 50 by relevance
    top = sorted_df.head(50)
    remaining = sorted_df.iloc[50:]

    # Stratified sample of remaining 150
    sample_size = min(150, len(remaining))

    # If categories_matched exists, stratify by it; otherwise random sample
    if 'categories_matched' in remaining.columns:
        # Group by categories_matched, sample proportionally
        groups = remaining.groupby('categories_matched', group_keys=False)
        sampled_parts = []
        total_remaining = len(remaining)

        for name, group in groups:
            proportion = len(group) / total_remaining
            n_samples = max(1, int(proportion * sample_size))
            n_samples = min(n_samples, len(group))
            sampled_parts.append(group.sample(n=n_samples, random_state=42))

        stratified = pd.concat(sampled_parts)
        # Trim to exact sample_size
        if len(stratified) > sample_size:
            stratified = stratified.sample(n=sample_size, random_state=42)
    else:
        stratified = remaining.sample(n=sample_size, random_state=42)

    combined = pd.concat([top, stratified])
    return combined.sort_values('relevance_score', ascending=False)


# ---------------------------------------------------------------------------
# LLM Integration
# ---------------------------------------------------------------------------

def build_language_mining_prompt(evidence_texts, ngram_table, research_direction):
    """Build the prompt for language mining LLM call."""

    # Format top n-grams for reference
    ngram_section = ""
    if ngram_table:
        ngram_lines = []
        for phrase, count in ngram_table[:80]:  # Top 80 n-grams
            ngram_lines.append(f"  {phrase}: {count}")
        ngram_section = "\n".join(ngram_lines)

    prompt = f"""You are a language analyst mining authentic audience language for a copywriter.

RESEARCH DIRECTION: "{research_direction}"

Your job: analyze how this audience ACTUALLY talks — their phrases, humor, tone, slang, metaphors — so a copywriter can mirror their real voice.

QUANTITATIVE N-GRAM DATA (extracted from ALL evidence, showing phrases appearing 3+ times):
{ngram_section}

Use these frequency counts as ground truth. When you report a phrase frequency, reference this table — do NOT guess or hallucinate counts. If a phrase appears in this table, use that exact count. If you mention a phrase not in this table, mark its frequency as 0 (observed but below threshold).

EVIDENCE ({len(evidence_texts)} pieces from Reddit discussions):
"""

    for i, text in enumerate(evidence_texts, 1):
        # Truncate individual evidence to 400 chars
        truncated = text[:400] + "..." if len(text) > 400 else text
        prompt += f"\n[{i}] {truncated}"

    prompt += f"""

ANALYZE this evidence and produce a structured language report. Be thorough and honest.

OUTPUT FORMAT — Return valid JSON matching this exact structure:
{{
  "language_categories": [
    {{
      "category_name": "descriptive name for this language cluster",
      "description": "what this category captures and why it matters for copy",
      "dominance": "high|medium|low",
      "phrases": [
        {{"phrase": "exact phrase", "frequency": N, "context": "how/when people use it"}}
      ],
      "example_quotes": ["verbatim quote from evidence showing this language in use"]
    }}
  ],
  "tone_profile": {{
    "dominant_tones": ["tone1", "tone2"],
    "pain_expression": "how they describe their pain/frustration",
    "desire_expression": "how they describe what they want",
    "register": "humorous|clinical|emotional|mixed",
    "notable_observations": "anything surprising about how they communicate"
  }},
  "top_phrases": [
    {{"phrase": "...", "frequency": N, "category": "which language_category it belongs to"}}
  ],
  "copywriter_gold": [
    {{
      "phrase_or_quote": "the exact gold — a phrase, quote, or metaphor",
      "why_it_works": "why a copywriter should use this",
      "source_type": "phrase|quote|metaphor"
    }}
  ]
}}

RULES:
- Create 4-10 language categories based on what you actually see. Don't force categories.
- For phrase frequencies: use the n-gram table above. Don't invent counts.
- top_phrases: pick the 15-25 most useful phrases for a copywriter, sorted by frequency.
- copywriter_gold: the 5-15 absolute best pieces — vivid, emotional, memorable language a copywriter would kill for. Include a mix of recurring phrases, standout quotes, and metaphors.
- Be honest about tone. If humor is dominant, say so. If it's mostly clinical, say that.
- All quotes must be real — pulled verbatim from the evidence above.

Return ONLY the JSON object. No markdown fences, no preamble, no commentary outside the JSON."""

    return prompt


def parse_llm_json(response_text, logger):
    """Parse LLM response as JSON, with fallback cleanup."""
    text = response_text.strip()

    # Strip markdown code fences if present
    if text.startswith('```'):
        # Remove first line (```json or ```)
        first_newline = text.index('\n')
        text = text[first_newline + 1:]
    if text.endswith('```'):
        text = text[:-3].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warn(f"JSON parse failed: {e}")

        # Try to find JSON object boundaries
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError as e2:
                logger.warn(f"JSON fallback parse also failed: {e2}")

    return None


async def call_llm(prompt, logger, retries=2):
    """Call Claude with retry logic."""
    for attempt in range(retries + 1):
        try:
            response_text = ""
            async for message in query(
                prompt=prompt,
                options=ClaudeCodeOptions(model="claude-sonnet-4-6", max_turns=3)
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
# Main
# ---------------------------------------------------------------------------

async def main_async():
    parser = argparse.ArgumentParser(description='Mine audience language patterns from evidence')
    parser.add_argument('brand', help='Brand name (e.g., pureplank)')
    parser.add_argument('sprint', help='Sprint folder name')
    parser.add_argument('--verbose', action='store_true', help='Print LLM prompt')

    args = parser.parse_args()

    # Resolve paths
    sprint_dir = resolve_sprint_dir(args.brand, args.sprint)
    intermediate_dir = os.path.join(sprint_dir, '_intermediate')

    evidence_path = os.path.join(intermediate_dir, 'evidence_filtered.csv')
    config_path = os.path.join(sprint_dir, 'sprint_config.txt')
    output_path = os.path.join(sprint_dir, 'language_report.json')
    log_path = os.path.join(intermediate_dir, 'language_miner_log.txt')

    print("=" * 80)
    print("LANGUAGE MINER - STEP 12")
    print("=" * 80)
    print(f"Brand: {args.brand}")
    print(f"Sprint: {args.sprint}")
    print(f"Sprint dir: {sprint_dir}")
    print()

    # Validate inputs
    missing = []
    if not os.path.exists(evidence_path):
        missing.append(f"  evidence: {evidence_path}")
    if not os.path.exists(config_path):
        missing.append(f"  config: {config_path}")

    if missing:
        print("ERROR: Missing required input files:")
        for m in missing:
            print(m)
        print("\nEnsure Step 05 has completed for this sprint.")
        sys.exit(1)

    # Set up logger
    logger = Logger(log_path)
    logger.log(f"Language Miner started for {args.brand} / {args.sprint}")

    # Load inputs
    research_direction = load_sprint_config(config_path)
    logger.log(f"Research direction: {research_direction}")

    evidence_df = load_evidence(evidence_path)
    pool_size = len(evidence_df)
    logger.log(f"Loaded evidence_filtered.csv: {pool_size:,} pieces")

    # --- Step 1: Quantitative n-gram extraction ---
    logger.log("\n--- Quantitative pre-pass: n-gram extraction ---")
    all_texts = evidence_df['text'].dropna().tolist()
    ngram_table = extract_ngrams(all_texts, min_n=2, max_n=4, min_freq=3)
    total_ngrams = len(ngram_table)
    logger.log(f"Extracted {total_ngrams} n-grams appearing 3+ times")
    if ngram_table:
        logger.log(f"Top 10: {', '.join(f'{p}({c})' for p, c in ngram_table[:10])}")

    # --- Step 2: Sample evidence ---
    logger.log("\n--- Sampling evidence ---")
    sampled_df = sample_evidence_for_llm(evidence_df)
    sampled_count = len(sampled_df)
    logger.log(f"Evidence for LLM: {sampled_count} of {pool_size} pieces")

    sampled_texts = sampled_df['text'].dropna().tolist()

    # --- Step 3: LLM call ---
    logger.log("\n--- Building LLM prompt ---")
    prompt = build_language_mining_prompt(sampled_texts, ngram_table, research_direction)
    logger.log(f"Prompt length: {len(prompt):,} chars")

    if args.verbose:
        print("\n" + "=" * 80)
        print("FULL LLM PROMPT:")
        print("=" * 80)
        print(prompt[:5000] + "\n... [truncated]" if len(prompt) > 5000 else prompt)
        print("=" * 80 + "\n")

    logger.log("\nCalling LLM for language analysis...")
    response_text = await call_llm(prompt, logger)
    logger.log(f"LLM response: {len(response_text):,} chars")

    # --- Step 4: Parse and assemble output ---
    logger.log("\n--- Parsing response ---")
    llm_result = parse_llm_json(response_text, logger)

    if not llm_result:
        logger.warn("Failed to parse LLM response as JSON")
        logger.warn(f"Raw response (first 500 chars): {response_text[:500]}")
        logger.save()
        sys.exit(1)

    # Assemble final report with metadata + quantitative summary
    report = {
        "metadata": {
            "brand": args.brand,
            "sprint": os.path.basename(sprint_dir),
            "research_direction": research_direction,
            "evidence_pool_size": pool_size,
            "evidence_analyzed": sampled_count,
            "generated_at": datetime.now().isoformat(),
        },
        "language_categories": llm_result.get("language_categories", []),
        "tone_profile": llm_result.get("tone_profile", {}),
        "top_phrases": llm_result.get("top_phrases", []),
        "copywriter_gold": llm_result.get("copywriter_gold", []),
        "quantitative_summary": {
            "total_ngrams_extracted": total_ngrams,
            "ngrams_above_threshold": total_ngrams,
            "top_20_ngrams": [
                {"phrase": phrase, "frequency": count}
                for phrase, count in ngram_table[:20]
            ],
        },
    }

    # Write output
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.log(f"\nWrote language_report.json: {output_path}")
    logger.log(f"  Categories: {len(report['language_categories'])}")
    logger.log(f"  Top phrases: {len(report['top_phrases'])}")
    logger.log(f"  Copywriter gold: {len(report['copywriter_gold'])}")

    logger.log(f"\n{'='*80}")
    logger.log("COMPLETE")
    logger.log(f"{'='*80}")

    logger.save()
    print(f"\nLog saved to: {log_path}")


def main():
    asyncio.run(main_async())


if __name__ == '__main__':
    main()
