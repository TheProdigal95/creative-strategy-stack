#!/usr/bin/env python3
"""
Theme Discovery - Step 06 of Research Engine

Analyzes filtered evidence to identify bridgeable themes.

Usage:
    python3 engine/step06_theme_discovery.py mybrand 01_weight-loss-men-dads
    python3 engine/step06_theme_discovery.py mybrand 01_weight-loss-men-dads --sample-size 300
    python3 engine/step06_theme_discovery.py mybrand 01_weight-loss-men-dads --verbose
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

def sample_evidence(csv_path, sample_size=300, seed=42):
    """Load filtered evidence and sample using stratified strategy.

    Allocation:
      - Top 40% by relevance_score (highest signal, always included)
      - 30% community-diverse (proportional across subreddits)
      - 30% random from remainder (serendipity factor)
    """
    print(f"Loading evidence from: {csv_path}")
    df = pd.read_csv(csv_path)
    df['relevance_score'] = pd.to_numeric(df.get('relevance_score', 0), errors='coerce').fillna(0)

    total_evidence = len(df)
    print(f"Total filtered evidence: {total_evidence:,} pieces")

    if total_evidence <= sample_size:
        sample_df = df
        print(f"Using all {total_evidence} pieces (less than requested {sample_size})")
    else:
        top_n = int(sample_size * 0.4)
        community_n = int(sample_size * 0.3)
        random_n = sample_size - top_n - community_n

        selected_indices = set()

        # 1. Top 40% by relevance score
        sorted_df = df.sort_values('relevance_score', ascending=False)
        top_indices = sorted_df.head(top_n).index.tolist()
        selected_indices.update(top_indices)

        # 2. 30% community-diverse (proportional sampling across subreddits)
        remaining = df[~df.index.isin(selected_indices)]
        if 'community' in remaining.columns and len(remaining) > 0:
            community_counts = remaining['community'].value_counts()
            total_remaining = len(remaining)
            community_selected = []
            for comm, count in community_counts.items():
                # Proportional allocation per community
                alloc = max(1, int(round(community_n * count / total_remaining)))
                comm_rows = remaining[remaining['community'] == comm]
                # Take highest-scoring within each community
                comm_sample = comm_rows.sort_values('relevance_score', ascending=False).head(alloc)
                community_selected.extend(comm_sample.index.tolist())
            # Trim to budget if over-allocated
            community_selected = community_selected[:community_n]
            selected_indices.update(community_selected)

        # 3. 30% random from remainder
        remaining = df[~df.index.isin(selected_indices)]
        if len(remaining) > 0:
            actual_random_n = min(random_n, len(remaining))
            random_sample = remaining.sample(n=actual_random_n, random_state=seed)
            selected_indices.update(random_sample.index.tolist())

        sample_df = df.loc[sorted(selected_indices)]
        print(f"Stratified sample: {top_n} top-scored + {community_n} community-diverse + {random_n} random = {len(sample_df)} pieces (seed={seed})")

    # Extract evidence_id and text
    evidence_pieces = []
    for _, row in sample_df.iterrows():
        evidence_pieces.append({
            'evidence_id': row['evidence_id'],
            'text': str(row['text']) if pd.notna(row['text']) else ""
        })

    return evidence_pieces, total_evidence

def build_theme_discovery_prompt(brand_brief, sprint_config, evidence_pieces):
    """Build prompt asking Claude to identify themes and insights within them."""

    prompt = f"""You are analyzing market research evidence to identify THEMES and INSIGHTS.

THIS SPRINT'S RESEARCH DIRECTION (this is your PRIMARY constraint — every theme and insight MUST be relevant to this):
"{sprint_config['research_direction']}"
"""
    if sprint_config.get('focus_areas'):
        prompt += "\nFOCUS AREAS:\n"
        for fa in sprint_config['focus_areas']:
            prompt += f"- {fa}\n"

    prompt += f"""
EVERY theme you generate must be directly relevant to the research direction above.
Do NOT generate themes about the broader brand audience — ONLY about this specific research angle.
If the evidence contains content that doesn't match the research direction (wrong audience, wrong topic, wrong tone), SKIP IT.

PRODUCT CONTEXT (for understanding what the product is — NOT for expanding scope):
Brand: {brand_brief['brand_name']}
Product: {brand_brief['product']}

Key selling points (use these for bridge_rationale):
"""
    for sp in brand_brief.get('main_selling_points', []):
        prompt += f"- {sp['name']}: {sp['description']}\n"
        prompt += f"  Solves: {sp['solves']}\n"

    prompt += f"""
The product context tells you WHAT the product does so you can create bridgeable insights.
But the RESEARCH DIRECTION determines WHO you're looking for and WHAT themes to cover.

DIRECTION COMPLIANCE RULES:
1. If the research direction mentions a specific AUDIENCE (e.g., "men over 40"), only generate insights about that audience. Skip evidence from people who don't match.
2. If the research direction mentions a specific TOPIC (e.g., "weight loss, dad bods"), only generate themes about those topics. Don't generate themes about unrelated topics like desk posture or gym equipment unless the direction mentions them.
3. If the research direction mentions a specific TONE or STYLE (e.g., "witty", "humorous"), prioritize evidence that shows that tone. Capture the language and humor patterns, not just the topics.
4. ASK YOURSELF FOR EACH THEME: "Does this theme directly serve the research direction?" If no, don't include it.

YOUR TASK:

Analyze the evidence below to identify THEMES and INSIGHTS that are relevant to the RESEARCH DIRECTION.

STEP 1: IDENTIFY THEMES
Themes are specific topics that the audience in the research direction discusses. Each theme must be relevant to the direction.

STEP 2: WITHIN EACH THEME, IDENTIFY INSIGHTS
Insights are specific beliefs, frictions, desires, objections, or misconceptions that:
- Appear multiple times in the evidence (not one-off comments)
- Can be BRIDGED to this product's value propositions
- Are SPECIFIC and actionable

WHAT IS A BRIDGEABLE INSIGHT?

An insight you can connect to how the product solves it or enables it.

GOOD insight examples:
✓ "Many dads believe the dad bod is inevitable once kids arrive" (Belief Shift)
✓ "Men quit planking within 15 seconds due to elbow pain on hard floors" (Friction)
✓ "Busy professionals want workouts that fit morning routines under 10 minutes" (Desire)
✓ "Men dismiss 3-minute workouts as 'too short' to build real strength" (Objection)

BAD insight examples:
✗ "People discuss exercise" - Too vague
✗ "People prefer running" - Not bridgeable to planking product
✗ "Want to be healthy" - Too broad, not specific

INSIGHT TYPES (Psychological Mechanisms):

Each insight should be tagged with ONE of these types:
- Belief Shift: A limiting belief that needs reframing
- Objection: A reason they think the product won't work for them
- Desire: What they want to achieve or feel
- Misconception: Factually incorrect understanding
- Friction: A barrier preventing action
- Motivation: Why they want to change

PERSONA ASSIGNMENT:
Each insight should identify WHO is expressing this belief/desire/objection. Look at the evidence examples - what do they reveal about the person's life situation? Are they parents? Office workers? Older adults? Gym-avoiders? The persona should capture the specific subset of people most likely to hold this insight, not just broad demographics.

REQUIREMENTS FOR EACH INSIGHT:

1. **insight**: Clear statement of what people believe/feel/want (1 sentence)

2. **insight_type**: One of the psychological mechanisms above

3. **angle**: A punchy 1-3 word label that sounds like an ad campaign name
   - Should INSTANTLY communicate the core idea — you read it and immediately get it
   - Should sound like an ad campaign name, not an academic label
   - Punchy and memorable

   GOOD angle examples:
   ✓ "Dad Bod Reset" - immediately conjures reclaiming your body
   ✓ "15-Second Quit" - instantly know it's about giving up quickly
   ✓ "Sideline Dad" - picture the dad watching, not playing
   ✓ "Newborn Chaos" - captures the life stage perfectly
   ✓ "Someday Trap" - you get the procrastination instantly
   ✓ "Injury Comeback" - clear narrative in two words

   BAD angle examples:
   ✗ "Last Off" - vague, requires explanation
   ✗ "Thin My Life" - awkward, unclear
   ✗ "Hour or Nothing" - sounds clinical, not punchy
   ✗ "Exercise Motivation Deficit" - academic label, not campaign name

4. **belief_statement**: How people express this in their own voice (direct quote style, 1 sentence)

5. **bridge_rationale**: How this connects to product selling points
   - MUST reference specific selling point(s) by name
   - Explain HOW the product addresses this insight
   - Be specific, not generic

6. **matching_patterns**: 6-15 short phrases (1-3 WORDS each) to find more evidence
   - CRITICAL: Each pattern must be 1-3 words maximum
   - Use flexible, commonly-used phrases
   - Include variations (synonyms, related terms)
   - Good patterns: "no time", "elbow pain", "gave up", "dad bod", "quick workout"
   - Bad patterns: "I don't have time in the morning", "elbow pain on hard floors"

7. **evidence_examples**: 2-3 actual quotes from the evidence below that illustrate this insight
   - Must be actual quotes from the evidence (include evidence_id in brackets)

8. **persona_raw**: Who is the person expressing this insight? Describe them in a short phrase (3-8 words) based on what the evidence reveals about their life situation, constraints, or identity. Examples: "fathers with no time for gym", "office workers with chronic back pain", "men over 40 doubting their fitness potential", "beginners intimidated by gym culture". Don't use generic descriptions like "men who want to lose weight" — be specific about what makes this group distinct.

DO NOT CAP THE NUMBER OF THEMES OR INSIGHTS
Find what's actually in the evidence. Some themes may have 1 insight, others may have 10.

EVIDENCE SAMPLE ({len(evidence_pieces)} pieces):

"""

    # Add evidence samples
    for i, piece in enumerate(evidence_pieces, 1):
        # Truncate very long text
        text = piece['text'][:800] if len(piece['text']) > 800 else piece['text']
        prompt += f"\n[{piece['evidence_id']}] \"{text}\"\n"

    prompt += """

OUTPUT FORMAT (JSON):

{
  "themes": [
    {
      "theme_name": "Dad Bod",
      "theme_description": "Beliefs and feelings about belly fat and body changes after becoming a father",
      "insights": [
        {
          "insight": "Many dads believe the dad bod is inevitable once kids arrive",
          "insight_type": "Belief Shift",
          "angle": "Dad Bod Reset",
          "belief_statement": "Having kids means gaining a belly - it's just what happens to dads",
          "bridge_rationale": "The '3 Minutes, No Excuses' selling point addresses this by fitting chaotic dad schedules (kids nap, before they wake). The founders' comeback story at 51 proves the dad bod isn't inevitable.",
          "matching_patterns": [
            "dad bod", "inevitable", "since kids", "what happens", "price of fatherhood",
            "kids arrived", "became a dad", "after kids", "fatherhood"
          ],
          "evidence_examples": [
            "[evidence_123] I accepted the dad bod was just what happens when you have kids",
            "[evidence_456] Everyone told me belly fat is the price of fatherhood"
          ],
          "persona_raw": "fathers with no time for gym"
        },
        {
          "insight": "Dads want to feel confident taking their shirt off at the pool/beach",
          "insight_type": "Desire",
          "angle": "Pool Confidence",
          "belief_statement": "I want to take my shirt off at the pool without feeling self-conscious",
          "bridge_rationale": "The 'Visible Core Strength' selling point addresses this desire - planks build the abs that create confidence. The timer tracks measurable progress toward this goal.",
          "matching_patterns": [
            "shirt off", "pool", "beach", "self conscious", "embarrassed",
            "shirtless", "take off shirt", "feel confident", "look good"
          ],
          "evidence_examples": [
            "[evidence_789] I haven't taken my shirt off at the pool in 3 years",
            "[evidence_234] Beach season makes me anxious about my belly"
          ],
          "persona_raw": "fathers wanting confidence at pool/beach"
        }
      ]
    },
    {
      "theme_name": "Time Scarcity",
      "theme_description": "Beliefs about not having enough time for exercise or fitness",
      "insights": [
        {
          "insight": "Busy professionals believe 'real' workouts require 60+ minutes at a gym",
          "insight_type": "Objection",
          "angle": "All-or-Nothing Trap",
          "belief_statement": "If I can't get to the gym for an hour, why bother with anything?",
          "bridge_rationale": "The '3 Minutes, No Excuses' selling point directly challenges this - 3 minutes done daily beats 60 minutes done monthly. No commute, no setup.",
          "matching_patterns": [
            "no time", "too busy", "real workout", "gym hour", "60 minutes",
            "don't have time", "can't commit", "full workout"
          ],
          "evidence_examples": [
            "[evidence_567] Real workouts need at least an hour, I just can't commit to that",
            "[evidence_890] If I can't do it properly at the gym, what's the point?"
          ],
          "persona_raw": "busy professionals with no gym time"
        }
      ]
    }
  ]
}

RULES:
- Find ALL themes present in the evidence — do NOT limit yourself to a specific number
- Each theme should contain ALL relevant insights you find (some themes may have 1 insight, others 10+)
- Every insight MUST be bridgeable to the product (reference specific selling points)
- Each insight must have an angle (1-3 word punchy campaign label)
- Each insight must have a persona_raw (3-8 word description of who holds this belief)
- Matching patterns must be 1-3 words each
- Evidence examples must be actual quotes from the evidence above (include evidence_id in brackets)
- Each insight gets its own matching_patterns (these are used to count evidence in Phase 1B)

OUTPUT RULES (follow these EXACTLY):
- Do NOT wrap the JSON in markdown code fences (no ```)
- Do NOT add any text, explanation, or commentary before or after the JSON
- The FIRST character of your response MUST be {
- The LAST character of your response MUST be }
- Output ONLY the raw JSON object
"""

    return prompt

def parse_themes_json(response_text):
    """Parse JSON response from Claude using brace-depth matching.

    Finds the first '{' and walks forward tracking brace depth,
    respecting JSON string literals (skips braces inside "...").
    Stops at depth 0 — any trailing text is ignored.
    """
    # Strip markdown code fences if present (with or without language tag)
    json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response_text, re.DOTALL)
    if json_match:
        response_text = json_match.group(1)

    # Find the first opening brace
    start = response_text.find('{')
    if start == -1:
        raise json.JSONDecodeError("No opening brace found in response", response_text, 0)

    # Walk forward with brace-depth counting, respecting string literals
    depth = 0
    in_string = False
    i = start
    while i < len(response_text):
        ch = response_text[i]

        if in_string:
            if ch == '\\':
                i += 2  # skip escaped character
                continue
            if ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return json.loads(response_text[start:i + 1])

        i += 1

    raise json.JSONDecodeError(
        f"Unbalanced braces — reached end of response at depth {depth}",
        response_text[start:start + 200],
        len(response_text)
    )

INSIGHT_REQUIRED_STR_FIELDS = [
    'insight', 'insight_type', 'angle', 'belief_statement',
    'bridge_rationale', 'persona_raw',
]
INSIGHT_REQUIRED_LIST_FIELDS = ['matching_patterns', 'evidence_examples']

def validate_themes_structure(data):
    """Validate parsed JSON has the expected theme/insight structure.

    Returns (is_valid: bool, errors: list[str]).
    """
    errors = []

    if not isinstance(data, dict):
        return False, ["Root is not a dict"]

    if 'themes' not in data:
        return False, ["Missing 'themes' key at root"]

    themes = data['themes']
    if not isinstance(themes, list) or len(themes) == 0:
        return False, ["'themes' must be a non-empty list"]

    for ti, theme in enumerate(themes):
        prefix = f"themes[{ti}]"

        if not isinstance(theme, dict):
            errors.append(f"{prefix}: not a dict")
            continue

        for field in ('theme_name', 'theme_description'):
            if field not in theme or not isinstance(theme[field], str):
                errors.append(f"{prefix}: missing or non-string '{field}'")

        insights = theme.get('insights')
        if not isinstance(insights, list):
            errors.append(f"{prefix}: missing or non-list 'insights'")
            continue

        for ii, ins in enumerate(insights):
            ipfx = f"{prefix}.insights[{ii}]"
            if not isinstance(ins, dict):
                errors.append(f"{ipfx}: not a dict")
                continue

            for field in INSIGHT_REQUIRED_STR_FIELDS:
                if field not in ins or not isinstance(ins[field], str):
                    errors.append(f"{ipfx}: missing or non-string '{field}'")

            for field in INSIGHT_REQUIRED_LIST_FIELDS:
                val = ins.get(field)
                if not isinstance(val, list):
                    errors.append(f"{ipfx}: missing or non-list '{field}'")
                elif field == 'matching_patterns' and len(val) == 0:
                    errors.append(f"{ipfx}: 'matching_patterns' is empty")

    return (len(errors) == 0, errors)


MAX_INTERNAL_RETRIES = 2  # so 3 total attempts

async def discover_themes(brand_brief, sprint_config, evidence_pieces, verbose=False):
    """Call Claude to discover bridgeable themes with internal retry on parse/validation errors."""
    print("\nDiscovering bridgeable themes with Claude...")

    prompt = build_theme_discovery_prompt(brand_brief, sprint_config, evidence_pieces)

    if verbose:
        print("\n" + "="*80)
        print("FULL LLM PROMPT:")
        print("="*80)
        print(prompt)
        print("="*80 + "\n")

    last_error = None

    for attempt in range(1, MAX_INTERNAL_RETRIES + 2):  # 1..3
        current_prompt = prompt
        if attempt > 1:
            error_feedback = f"\n\nRETRY (attempt {attempt}/{MAX_INTERNAL_RETRIES + 1}) — YOUR PREVIOUS RESPONSE FAILED.\nError: {last_error}\n\nPlease output ONLY a valid JSON object. No markdown fences, no text before or after. The first character must be {{ and the last must be }}."
            current_prompt = prompt + error_feedback
            print(f"  Retry {attempt}/{MAX_INTERNAL_RETRIES + 1} — previous error: {last_error}")

        response_text = ""
        try:
            async for message in query(
                prompt=current_prompt,
                options=ClaudeCodeOptions(model="claude-opus-4-6", max_turns=3)
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

        # Parse JSON
        try:
            themes_data = parse_themes_json(response_text)
        except json.JSONDecodeError as e:
            last_error = f"JSON parse error: {e}"
            print(f"  ✗ Attempt {attempt}: {last_error}")
            if attempt <= MAX_INTERNAL_RETRIES:
                continue
            raise

        # Validate structure
        is_valid, validation_errors = validate_themes_structure(themes_data)
        if not is_valid:
            capped = validation_errors[:5]
            last_error = "Structural validation failed: " + "; ".join(capped)
            if len(validation_errors) > 5:
                last_error += f" (and {len(validation_errors) - 5} more)"
            print(f"  ✗ Attempt {attempt}: {last_error}")
            if attempt <= MAX_INTERNAL_RETRIES:
                continue
            raise ValueError(last_error)

        # Success
        if attempt > 1:
            print(f"  ✓ Attempt {attempt} succeeded")
        return themes_data

def save_themes(themes_data, brand, sprint, output_path, sample_size, total_evidence):
    """Save discovered themes as JSON."""
    themes = themes_data.get('themes', [])

    # Count total insights across all themes
    total_insights = sum(len(theme.get('insights', [])) for theme in themes)

    # Count total patterns across all insights
    total_patterns = 0
    for theme in themes:
        for insight in theme.get('insights', []):
            total_patterns += len(insight.get('matching_patterns', []))

    output = {
        "generated_for": {
            "brand": brand,
            "sprint": sprint,
            "timestamp": datetime.now().isoformat(),
            "evidence_sample_size": sample_size,
            "evidence_total": total_evidence
        },
        "themes": themes,
        "statistics": {
            "total_themes": len(themes),
            "total_insights": total_insights,
            "avg_insights_per_theme": total_insights / max(len(themes), 1),
            "avg_patterns_per_insight": total_patterns / max(total_insights, 1)
        }
    }

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"✓ Saved themes to: {output_path}")

    # Print stats
    stats = output['statistics']
    print(f"  - Themes discovered: {stats['total_themes']}")
    print(f"  - Insights discovered: {stats['total_insights']}")
    print(f"  - Avg insights per theme: {stats['avg_insights_per_theme']:.1f}")
    print(f"  - Avg patterns per insight: {stats['avg_patterns_per_insight']:.1f}")

def generate_theme_report(themes_data, sample_size, total_evidence, output_path, brand, sprint):
    """Generate human-readable report."""

    themes = themes_data.get('themes', [])
    total_insights = sum(len(theme.get('insights', [])) for theme in themes)

    report = f"""THEME DISCOVERY REPORT
{'='*80}
Brand: {brand}
Sprint: {sprint}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

EVIDENCE ANALYSIS:
{'-'*80}
Evidence sample size: {sample_size} pieces (from {total_evidence:,} filtered)
Sampling method: Stratified (40% top-scored, 30% community-diverse, 30% random, seed=42)

THEMES DISCOVERED: {len(themes)}
INSIGHTS DISCOVERED: {total_insights}
{'-'*80}
"""

    # Theme overview
    for i, theme in enumerate(themes, 1):
        insights = theme.get('insights', [])
        report += f"\n{i:2d}. {theme['theme_name']} ({len(insights)} insights)\n"
        report += f"    \"{theme['theme_description']}\"\n"
        for j, insight in enumerate(insights, 1):
            report += f"    {i}.{j} [{insight['insight_type']}] {insight['angle']}: {insight['insight'][:60]}...\n"

    # Detailed insights for first 3 themes
    report += f"\n\nDETAILED INSIGHTS (First 3 Themes):\n{'='*80}\n"

    sample_count = min(3, len(themes))
    for i in range(sample_count):
        theme = themes[i]
        report += f"\n--- THEME {i+1}: {theme['theme_name']} ---\n"
        report += f"{theme['theme_description']}\n"
        report += f"\n{len(theme.get('insights', []))} insights:\n"

        for j, insight in enumerate(theme.get('insights', []), 1):
            report += f"\n  {i+1}.{j} {insight['angle']}\n"
            report += f"  Insight Type: {insight['insight_type']}\n"
            report += f"  Insight: {insight['insight']}\n"
            report += f"  Belief: \"{insight['belief_statement']}\"\n"
            report += f"  Bridge: {insight['bridge_rationale'][:100]}...\n"
            report += f"  Patterns ({len(insight['matching_patterns'])}): {', '.join(insight['matching_patterns'][:8])}...\n"
            report += f"  Evidence examples: {len(insight['evidence_examples'])}\n"

        report += "\n" + "-"*80 + "\n"

    report += "\n" + "="*80 + "\n"

    with open(output_path, 'w') as f:
        f.write(report)

    print(f"✓ Saved report to: {output_path}")

async def main_async():
    parser = argparse.ArgumentParser(description='Discover bridgeable themes from filtered evidence')
    parser.add_argument('brand', help='Brand name (e.g., mybrand)')
    parser.add_argument('sprint', help='Sprint folder name (e.g., 01_weight-loss-men-dads)')
    parser.add_argument('--sample-size', type=int, default=300,
                       help='Number of evidence pieces to sample (default: 300)')
    parser.add_argument('--skip-if-exists', action='store_true',
                       help='Skip theme discovery if themes file already exists')
    parser.add_argument('--regenerate', action='store_true',
                       help='Force regenerate themes even if file exists')
    parser.add_argument('--verbose', action='store_true',
                       help='Print full LLM prompt before sending')

    args = parser.parse_args()

    # Paths
    brand_brief_path = f"brands/{args.brand}/brand_brief.yaml"
    sprint_config_path = f"brands/{args.brand}/sprints/{args.sprint}/sprint_config.txt"
    intermediate_dir = Path(f"brands/{args.brand}/sprints/{args.sprint}/_intermediate")
    evidence_path = intermediate_dir / "evidence_filtered.csv"

    themes_output_path = intermediate_dir / "themes_discovered.json"
    report_output_path = intermediate_dir / "theme_discovery_report.txt"

    print("="*80)
    print("THEME DISCOVERY - PHASE 1A")
    print("="*80)
    print(f"Brand: {args.brand}")
    print(f"Sprint: {args.sprint}")
    print(f"Sample size: {args.sample_size}")
    print()

    # Check if themes already exist
    if os.path.exists(themes_output_path) and args.skip_if_exists and not args.regenerate:
        print(f"Themes already exist at: {themes_output_path}")
        print("Use --regenerate to force regeneration")
        return

    # Load inputs
    print("Loading brand brief...")
    brand_brief = load_brand_brief(brand_brief_path)

    print("Loading sprint config...")
    sprint_config = load_sprint_config(sprint_config_path)

    # Sample evidence
    evidence_pieces, total_evidence = sample_evidence(
        evidence_path,
        sample_size=args.sample_size
    )

    # Discover themes
    themes_data = await discover_themes(
        brand_brief,
        sprint_config,
        evidence_pieces,
        verbose=args.verbose
    )

    print("\nProcessing results...")

    # Save outputs
    save_themes(
        themes_data,
        args.brand,
        args.sprint,
        themes_output_path,
        len(evidence_pieces),
        total_evidence
    )

    generate_theme_report(
        themes_data,
        len(evidence_pieces),
        total_evidence,
        report_output_path,
        args.brand,
        args.sprint
    )

    print()
    print("="*80)
    print("COMPLETE")
    print("="*80)

def main():
    asyncio.run(main_async())

if __name__ == '__main__':
    main()
