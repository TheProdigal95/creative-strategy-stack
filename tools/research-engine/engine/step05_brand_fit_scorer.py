#!/usr/bin/env python3
"""
Brand-Fit Scorer - Step 05 of Research Engine

Filters large evidence base down to pieces relevant to a specific brand + sprint.

Two-step process:
1. LLM generates expanded relevance vocabulary from brand brief + sprint config
2. Python scores all evidence using pattern matching

Usage:
    python3 engine/step05_brand_fit_scorer.py mybrand 01_weight-loss-men-dads
    python3 engine/step05_brand_fit_scorer.py mybrand 01_weight-loss-men-dads --threshold 20
"""

import os
import sys
import yaml
import json
import pandas as pd
import argparse
import asyncio
import re
from pathlib import Path
from datetime import datetime
from claude_code_sdk import query, ClaudeCodeOptions

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.evidence_db import get_all_evidence_df, db_path


def load_brand_brief(yaml_path):
    """Load brand brief YAML file."""
    with open(yaml_path, 'r') as f:
        return yaml.safe_load(f)

def load_sprint_config(txt_path):
    """Load sprint config text file."""
    with open(txt_path, 'r') as f:
        content = f.read()

    lines = content.strip().split('\n')
    research_direction = ""
    focus_areas = []

    for line in lines:
        if line.startswith("Research Direction:"):
            research_direction = line.replace("Research Direction:", "").strip()
        elif line.strip().startswith("-"):
            focus_areas.append(line.strip()[1:].strip())

    return {
        'research_direction': research_direction,
        'focus_areas': focus_areas
    }

def build_vocabulary_prompt(brand_brief, sprint_config):
    """Build prompt for LLM to generate relevance vocabulary."""

    prompt = f"""You are helping build a relevance filter for market research evidence.

THIS SPRINT'S RESEARCH DIRECTION (this is your PRIMARY constraint):
"{sprint_config['research_direction']}"

EVERY category you generate must be directly relevant to the research direction above.
Do NOT generate categories for the broader brand audience — ONLY for this specific research angle.

PRODUCT CONTEXT (for understanding what the product is — NOT for expanding scope):
Brand: {brand_brief['brand_name']}
Product: {brand_brief['product']}

Key selling points:
"""
    for sp in brand_brief.get('main_selling_points', []):
        prompt += f"- {sp['name']}: {sp['description']}\n"

    prompt += f"""
The product context tells you WHAT the product does so you can create bridgeable categories.
But the RESEARCH DIRECTION determines WHO you're looking for and WHAT topics to cover.

YOUR TASK:
Generate a relevance vocabulary that identifies people matching the research direction above.
Every category must be something a person described in the research direction would talk about.

ASK YOURSELF FOR EACH CATEGORY: "Would a person described in the research direction talk about this?"
If no, don't include it. If the research direction says "men over 40 weight loss", don't include categories about desk posture, new mothers, or gym equipment unless the direction specifically mentions those.

People express themselves in two directions — capture BOTH:
1. AWAY FROM (problems): Complaints, frustrations, barriers, pain points
2. TOWARD (desires): Aspirations, goals, what they want to achieve or become

CRITICAL INSTRUCTIONS:

1. Generate categories ONLY for the specific audience and topic in the research direction
2. Focus on UPSTREAM signals — problems and desires BEFORE discovering this product
3. Think about what the product SOLVES and ENABLES, but only for the audience in the research direction
4. DO NOT require people to mention the product category
5. DO NOT generate broad brand-level categories that go beyond the research direction

PATTERN LENGTH REQUIREMENTS:

CRITICAL: Most patterns must be 2-3 words to avoid false positives from generic single words.
- 2-3 word patterns should be 80%+ of all patterns
- Single-word patterns are ONLY allowed if they are domain-specific terms that rarely appear outside this topic (e.g., "planks", "obliques", "sciatica", "deadlift", "burpees")
- Do NOT use generic English words as single-word patterns. Words like "better", "same", "change", "lost", "ready", "enough", "again", "before", "simple", "support", "results", "improve", "age", "floor", "basic", "carry", "show", "decide", "finally", "longer", "stopped", "return", "tone", "prime" match too many unrelated contexts and create false positives.
- Avoid 4+ word phrases that require exact matching

GOOD pattern examples (specific enough to avoid false positives):
✓ "no time" (2 words - specific to time scarcity)
✓ "gave up" (2 words - specific to quitting)
✓ "back pain" (2 words - specific to pain)
✓ "feel confident" (2 words - specific to confidence)
✓ "dad bod" (2 words - domain-specific)
✓ "weak core" (2 words - domain-specific)
✓ "sciatica" (1 word - domain-specific, never appears in unrelated contexts)
✓ "planks" (1 word - domain-specific)

BAD pattern examples:
✗ "better" (single generic word - matches "a better deal", "better weather")
✗ "change" (single generic word - matches politics, career, weather)
✗ "lost" (single generic word - matches "lost my keys", "lost the game")
✗ "support" (single generic word - matches "tech support", "emotional support")
✗ "no time to work out" (too long - requires exact match)
✗ "I want to feel confident again" (too long)

DIRECTION-CONSTRAINED EXAMPLES:

If the research direction is "men over 40 who want to lose weight":
GOOD categories: "midlife_belly_fat", "metabolism_slowdown", "dad_bod_identity", "aging_body_frustration", "comeback_after_40"
BAD categories: "desk_posture" (not specific to the direction), "new_mother_fitness" (wrong audience), "gym_equipment" (not mentioned in direction)

If the research direction is "back pain from desk jobs":
GOOD categories: "sitting_induced_pain", "desk_posture", "office_worker_stiffness", "core_weakness_back_link"
BAD categories: "dad_bod_identity" (not about desk workers), "aging_metabolism" (not mentioned in direction)

NOW GENERATE THE VOCABULARY:

Based on the RESEARCH DIRECTION above (your primary constraint) and the product context:

1. Identify 8-12 core categories — each must be directly relevant to the research direction
2. For each category, generate 15-25 patterns mixing BOTH:
   - Problem expressions (how people in the research direction complain)
   - Desire expressions (how people in the research direction describe what they want)
3. CRITICAL: Make 80%+ of patterns 2-3 words. Only use single words for domain-specific terms (e.g., "sciatica", "obliques", "deadlift") that would never appear in unrelated conversations.
4. Focus on language used BEFORE product discovery
5. DO NOT require mentions of the product category
6. DO NOT use generic English words as single-word patterns — they cause massive false positives
7. DO NOT generate categories outside the scope of the research direction

Output as JSON:
{{
  "categories": {{
    "category_name": {{
      "description": "What this category captures (both problem and desire sides)",
      "patterns": ["problem expression", "desire expression", ...]
    }}
  }}
}}

REMEMBER: We want to find people who are prospects — whether they're complaining about problems OR expressing desires this product addresses.

IMPORTANT: Output ONLY the JSON object. No preamble, no explanation. Start with the opening brace {{.
"""

    return prompt

async def generate_vocabulary(brand_brief, sprint_config):
    """Call Claude to generate relevance vocabulary."""
    print("Generating relevance vocabulary with Claude...")

    prompt = build_vocabulary_prompt(brand_brief, sprint_config)

    response_text = ""
    try:
        async for message in query(
            prompt=prompt,
            options=ClaudeCodeOptions(model="claude-sonnet-4-6", max_turns=3)
        ):
            if hasattr(message, 'content'):
                for block in message.content:
                    if hasattr(block, 'text'):
                        response_text += block.text
    except Exception as e:
        if "Unknown message type" in str(e) and response_text:
            pass  # SDK parse warning — response already collected
        else:
            raise

    # Parse JSON response
    json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
    if json_match:
        response_text = json_match.group(1)

    # Extract JSON object
    if not response_text.strip().startswith('{'):
        start = response_text.find('{')
        end = response_text.rfind('}')
        if start != -1 and end != -1 and end > start:
            response_text = response_text[start:end+1]

    vocabulary_data = json.loads(response_text)

    return vocabulary_data

def save_vocabulary(vocabulary_data, brand, sprint, output_path):
    """Save vocabulary with metadata."""
    output = {
        "generated_for": {
            "brand": brand,
            "sprint": sprint,
            "timestamp": datetime.now().isoformat()
        },
        "categories": vocabulary_data['categories']
    }

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"✓ Saved vocabulary to: {output_path}")

    # Print stats
    total_categories = len(output['categories'])
    total_patterns = sum(len(cat['patterns']) for cat in output['categories'].values())
    print(f"  - Categories: {total_categories}")
    print(f"  - Total patterns: {total_patterns}")

def load_vocabulary(vocab_path):
    """Load vocabulary from JSON file."""
    with open(vocab_path, 'r') as f:
        return json.load(f)

def score_evidence_piece(text, vocabulary):
    """
    Score a single evidence piece using word-boundary-aware pattern matching.

    Returns dict with:
    - score: int
    - categories_matched: int
    - total_patterns: int
    - matches_by_category: dict
    """
    text_lower = text.lower()
    matches = {}

    for category, data in vocabulary['categories'].items():
        category_matches = []

        for pattern in data['patterns']:
            # Multi-word patterns: exact phrase match
            if ' ' in pattern:
                if pattern.lower() in text_lower:
                    category_matches.append(pattern)
            else:
                # Single word: word boundary match with stemming
                # Matches "lose", "losing", "lost" when pattern is "lose"
                regex = r'\b' + re.escape(pattern.lower()) + r'\w*\b'
                if re.search(regex, text_lower):
                    category_matches.append(pattern)

        if category_matches:
            matches[category] = category_matches

    # Calculate score
    categories_matched = len(matches)
    total_patterns = sum(len(patterns) for patterns in matches.values())

    score = (categories_matched * 10) + total_patterns

    return {
        'score': score,
        'categories_matched': categories_matched,
        'total_patterns': total_patterns,
        'matches_by_category': matches
    }

def score_all_evidence(evidence_df, vocabulary, threshold=15):
    """
    Score all evidence pieces and filter by threshold.

    Returns DataFrame with scoring columns added.
    """
    print(f"\nScoring {len(evidence_df)} evidence pieces...")

    scores = []
    categories_matched_list = []
    total_patterns_list = []
    matched_categories_list = []
    matched_patterns_list = []

    for idx, row in evidence_df.iterrows():
        if idx > 0 and idx % 500 == 0:
            print(f"  Processed {idx}/{len(evidence_df)}...")

        text = str(row['text']) if pd.notna(row['text']) else ""

        result = score_evidence_piece(text, vocabulary)

        scores.append(result['score'])
        categories_matched_list.append(result['categories_matched'])
        total_patterns_list.append(result['total_patterns'])
        matched_categories_list.append(';'.join(result['matches_by_category'].keys()))
        matched_patterns_list.append(json.dumps(result['matches_by_category']))

    print(f"  Processed {len(evidence_df)}/{len(evidence_df)}")

    # Add scoring columns
    evidence_df['relevance_score'] = scores
    evidence_df['categories_matched'] = categories_matched_list
    evidence_df['total_patterns_matched'] = total_patterns_list
    evidence_df['matched_categories'] = matched_categories_list
    evidence_df['matched_patterns'] = matched_patterns_list

    # Filter by threshold
    # Score >= threshold ensures 2+ category matches (due to formula: categories*10 + patterns)
    mask = evidence_df['relevance_score'] >= threshold
    filtered_df = evidence_df[mask].copy()

    # Sort by score descending
    filtered_df = filtered_df.sort_values('relevance_score', ascending=False)

    print(f"\n✓ Filtered {len(filtered_df)}/{len(evidence_df)} pieces (score ≥{threshold})")

    return filtered_df, evidence_df

def generate_scoring_report(filtered_df, all_df, vocabulary, threshold, output_path, brand, sprint):
    """Generate scoring report with statistics."""

    total_evidence = len(all_df)
    passed_threshold = len(filtered_df)
    filtered_out = total_evidence - passed_threshold
    pass_rate = (passed_threshold / total_evidence * 100) if total_evidence > 0 else 0

    # Calculate stats
    if len(filtered_df) > 0:
        min_score = filtered_df['relevance_score'].min()
        max_score = filtered_df['relevance_score'].max()
        mean_score = filtered_df['relevance_score'].mean()
        median_score = filtered_df['relevance_score'].median()
    else:
        min_score = max_score = mean_score = median_score = 0

    # Category match counts
    category_counts = {}
    for categories_str in filtered_df['matched_categories']:
        for category in categories_str.split(';'):
            if category:
                category_counts[category] = category_counts.get(category, 0) + 1

    # Sort categories by count
    top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)

    # Pattern match counts (across all filtered evidence)
    pattern_counts = {}
    for patterns_json in filtered_df['matched_patterns']:
        patterns_dict = json.loads(patterns_json)
        for category, patterns in patterns_dict.items():
            for pattern in patterns:
                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

    # Sort patterns by count
    top_patterns = sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:20]

    # Generate report
    report = f"""BRAND-FIT SCORING REPORT
{'='*80}
Brand: {brand}
Sprint: {sprint}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

VOCABULARY STATS:
{'-'*80}
Total categories: {len(vocabulary['categories'])}
Total patterns: {sum(len(cat['patterns']) for cat in vocabulary['categories'].values())}

EVIDENCE STATS:
{'-'*80}
Total evidence pieces: {total_evidence:,}
Passed threshold (≥{threshold}): {passed_threshold:,} ({pass_rate:.1f}%)
Filtered out: {filtered_out:,} ({100-pass_rate:.1f}%)

SCORE DISTRIBUTION:
{'-'*80}
Min score: {min_score:.0f}
Max score: {max_score:.0f}
Mean score: {mean_score:.1f}
Median score: {median_score:.1f}

TOP MATCHED CATEGORIES:
{'-'*80}
"""

    for i, (category, count) in enumerate(top_categories[:10], 1):
        pct = (count / passed_threshold * 100) if passed_threshold > 0 else 0
        report += f"{i:2d}. {category}: {count:,} pieces ({pct:.1f}%)\n"

    report += f"\nTOP MATCHED PATTERNS:\n{'-'*80}\n"

    for i, (pattern, count) in enumerate(top_patterns, 1):
        report += f"{i:2d}. \"{pattern}\": {count:,} pieces\n"

    # Add TOP SCORING EVIDENCE (SAMPLE)
    report += f"\n\nTOP SCORING EVIDENCE (SAMPLE):\n{'-'*80}\n"

    top_samples = filtered_df.head(15)
    for idx, row in top_samples.iterrows():
        text_preview = str(row['text'])[:200].replace('\n', ' ')
        report += f"\nScore: {row['relevance_score']:.0f} | {row['source']} | {row['community']}\n"
        report += f"Text: {text_preview}...\n"

    report += f"\n{'='*80}\n"

    # Save report
    with open(output_path, 'w') as f:
        f.write(report)

    print(f"✓ Saved scoring report to: {output_path}")

    # Print summary
    print(f"\nSUMMARY:")
    print(f"  Total evidence: {total_evidence:,}")
    print(f"  Passed filter: {passed_threshold:,} ({pass_rate:.1f}%)")
    print(f"  Score range: {min_score:.0f} - {max_score:.0f}")
    print(f"  Top category: {top_categories[0][0] if top_categories else 'N/A'}")

async def main_async():
    parser = argparse.ArgumentParser(description='Score evidence for brand fit')
    parser.add_argument('brand', help='Brand name (e.g., mybrand)')
    parser.add_argument('sprint', help='Sprint folder name (e.g., 01_weight-loss-men-dads)')
    parser.add_argument('--threshold', type=int, default=15, help='Minimum score threshold (default: 15)')
    parser.add_argument('--skip-vocab', action='store_true', help='Skip vocabulary generation if exists')
    parser.add_argument('--regenerate-vocab', action='store_true', help='Force regenerate vocabulary')

    args = parser.parse_args()

    # Paths
    brand_brief_path = f"brands/{args.brand}/brand_brief.yaml"
    sprint_config_path = f"brands/{args.brand}/sprints/{args.sprint}/sprint_config.txt"
    evidence_db = db_path(args.brand)

    # Create intermediate directory
    intermediate_dir = Path(f"brands/{args.brand}/sprints/{args.sprint}/_intermediate")
    intermediate_dir.mkdir(exist_ok=True)

    vocab_output_path = intermediate_dir / "relevance_vocabulary.json"
    filtered_output_path = intermediate_dir / "evidence_filtered.csv"
    report_output_path = intermediate_dir / "scoring_report.txt"

    print("="*80)
    print("BRAND-FIT SCORER")
    print("="*80)
    print(f"Brand: {args.brand}")
    print(f"Sprint: {args.sprint}")
    print(f"Threshold: {args.threshold}")
    print()

    # STEP 1: Generate or load vocabulary
    if os.path.exists(vocab_output_path) and args.skip_vocab and not args.regenerate_vocab:
        print("Loading existing vocabulary...")
        vocabulary = load_vocabulary(vocab_output_path)
        print(f"✓ Loaded vocabulary from: {vocab_output_path}")
        total_categories = len(vocabulary['categories'])
        total_patterns = sum(len(cat['patterns']) for cat in vocabulary['categories'].values())
        print(f"  - Categories: {total_categories}")
        print(f"  - Total patterns: {total_patterns}")
    else:
        print("STEP 1: LLM Vocabulary Generation")
        print("-"*80)

        # Load inputs
        print("Loading brand brief...")
        brand_brief = load_brand_brief(brand_brief_path)

        print("Loading sprint config...")
        sprint_config = load_sprint_config(sprint_config_path)

        # Generate vocabulary
        vocabulary_data = await generate_vocabulary(brand_brief, sprint_config)

        # Save vocabulary
        save_vocabulary(vocabulary_data, args.brand, args.sprint, vocab_output_path)

        # Reload for consistency
        vocabulary = load_vocabulary(vocab_output_path)

    # STEP 2: Python scoring
    print()
    print("STEP 2: Python Scoring")
    print("-"*80)

    # Load evidence from SQLite
    print(f"Loading evidence from: {evidence_db}")
    evidence_df = get_all_evidence_df(args.brand)
    print(f"✓ Loaded {len(evidence_df):,} evidence pieces")

    # Score all evidence
    filtered_df, all_df = score_all_evidence(evidence_df, vocabulary, args.threshold)

    # Save filtered evidence
    filtered_df.to_csv(filtered_output_path, index=False)
    print(f"✓ Saved filtered evidence to: {filtered_output_path}")

    # Generate report
    print()
    print("Generating scoring report...")
    generate_scoring_report(
        filtered_df, all_df, vocabulary, args.threshold,
        report_output_path, args.brand, args.sprint
    )

    print()
    print("="*80)
    print("COMPLETE")
    print("="*80)

def main():
    asyncio.run(main_async())

if __name__ == '__main__':
    main()
