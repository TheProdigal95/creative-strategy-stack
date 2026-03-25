#!/usr/bin/env python3
"""
Insight Writer - Step 09 of Research Engine

Uses LLM to write full Notes section and determine Valence, Intensity, Self.

Usage:
    python3 engine/step09_insight_writer.py mybrand 01_weight-loss-men-dads
    python3 engine/step09_insight_writer.py mybrand 01_weight-loss-men-dads --verbose
"""

import os
import sys
import json
import yaml
import argparse
import asyncio
import re
import pandas as pd
from pathlib import Path
from datetime import datetime
from claude_code_sdk import query, ClaudeCodeOptions

def load_themes(json_path):
    """Load themes_discovered.json from sprint folder."""
    with open(json_path, 'r') as f:
        return json.load(f)

def load_brand_brief(yaml_path):
    """Load brand brief YAML file."""
    with open(yaml_path, 'r') as f:
        return yaml.safe_load(f)

def build_system_instructions(brand_name, brand_promise):
    """Build static system instructions for insight analysis (cached across batches)."""

    return f"""You are writing insight analysis for {brand_name}.

BRAND PROMISE: {brand_promise}

YOUR TASK: For each insight below, generate the missing fields that complete the analysis.

OUTPUT DEFINITIONS:

VALENCE (Emotional Polarity of the Insight)

Valence answers: What emotional state is the customer in when they express this insight?

This is BINARY — every insight is either Positive or Negative.

- NEGATIVE: The customer is describing a problem, frustration, fear, limitation, or pain point. They are in a "push away from" state. Emotions: fear, frustration, anxiety, anger, disappointment, shame.

- POSITIVE: The customer is describing a desire, hope, aspiration, or want. They are in a "pull toward" state. Emotions: hope, excitement, pride, anticipation, longing.

If an insight seems to contain both, determine which is MORE PREVALENT and assign that. There is no "Mixed" option.

How to determine: Read the belief_statement and best_quotes. Is this person primarily describing something that feels BAD (problem they have) or something that feels GOOD (thing they want)? The insight tells you where they ARE emotionally.

---

INTENSITY (Emotional Charge of the Insight)

Intensity answers: How deeply is this emotion felt? How acute is the customer truth?

Scale 1-5:

1 = Mild. Passing thought, minor irritation, slight preference. Low stakes.
    Negative examples: "My coffee gets cold too fast." "Gym parking is annoying."
    Positive examples: "It would be nice to be more organized." "I kind of want to try yoga sometime."

2 = Moderate-low. Noticeable frustration or interest, but not pressing or urgent.
    Negative examples: "I wish I had more energy." "Commuting to the gym is a hassle."
    Positive examples: "I'd like to feel a bit healthier." "It would be cool to have visible abs."

3 = Moderate. Clear emotional weight. The person thinks about this regularly.
    Negative examples: "I can never stick with workout programs." "I'm tired of starting over every January."
    Positive examples: "I want to feel confident in photos." "I really want to keep up with my kids."

4 = High. Strong emotional charge. This affects their self-image or daily life significantly.
    Negative examples: "I'm embarrassed to take my shirt off at the pool." "I feel like I'm failing at staying healthy."
    Positive examples: "I want my kids to see me as strong and capable." "I want to feel proud of my body again."

5 = Acute. Existential, identity-level, or deeply painful/desired. High stakes.
    Negative examples: "I'm terrified my kids will watch me die young." "I've completely given up on ever being fit."
    Positive examples: "I want to finally prove everyone wrong about me." "I want to become the person I always knew I could be."

How to determine: Read the best_quotes. What language are people using? Mild language ("it would be nice", "kind of annoying") = low intensity. Strong language ("terrified", "exhausted", "desperate", "finally", "prove everyone wrong") = high intensity. Consider the stakes — is this about convenience or identity?

---

SELF (Which Psychological Version the Insight Activates)

Based on Self-Discrepancy Theory: customers exist as three psychological versions simultaneously. The insight reveals which version is "speaking."

IDEAL SELF — "Who I want to become"
- Time orientation: Future
- Core drive: Aspiration, dreams, transformation, potential
- The customer is expressing a vision of a better version of themselves
- Language patterns (or similar phrasing): "I want to become...", "I wish I could...", "Someday I'll...", "What if I finally...", "I dream of...", "I could be...", "I want to get back to..."
- Emotional flavor: Hope, longing, possibility, inspiration
- Example insights: "Dads want to feel confident taking their shirt off at the pool" (vision of transformed self), "I want to get back to who I was before kids" (aspiration for future state)

ACTUAL SELF — "Who I already am"
- Time orientation: Present
- Core drive: Validation, identity consistency, belonging
- The customer is expressing something about their current identity that they want acknowledged or maintained
- Language patterns (or similar phrasing): "I'm the kind of person who...", "I already...", "That's just who I am...", "I've always been...", "This fits my lifestyle...", "I'm not a... person", "I know what works for me"
- Emotional flavor: Pride, self-acceptance, identity protection, belonging
- Example insights: "I'm not a gym person and never will be" (identity statement), "I already know what works for my body" (validation of current self)

OUGHT SELF — "Who I should be"
- Time orientation: Obligation (past promises, external standards, responsibilities)
- Core drive: Duty, responsibility, meeting expectations, avoiding guilt
- The customer is expressing pressure from internal standards or external expectations
- Language patterns (or similar phrasing): "I should...", "I'm supposed to...", "I need to for my kids/family...", "What kind of father/mother would...", "I owe it to...", "People expect me to...", "I have a responsibility to...", "I can't let them down"
- Emotional flavor: Guilt, duty, pressure, responsibility, obligation
- Example insights: "I should be healthier for my kids" (obligation), "As a dad, I need to be able to keep up with them" (role-based duty), "I've let myself go and I shouldn't have" (internal standard not met)

How to determine: Read the belief_statement and best_quotes. Ask:
- Is this person painting a picture of who they COULD become? → Ideal Self
- Is this person asserting or protecting who they ALREADY are? → Actual Self
- Is this person invoking duty, standards, or what they SHOULD do/be? → Ought Self

Important nuance: The same TOPIC can activate different selves depending on how it's framed.
- "I want to be a fit dad" → Ideal (aspiration)
- "I'm a hands-on dad, I just need more energy" → Actual (identity + enhancement)
- "I should be healthier for my kids" → Ought (duty)

Look at the FRAMING in the evidence, not just the topic.

---

FOR EACH INSIGHT, GENERATE:

1. **reframe**: The cognitive shift that challenges the belief (1-2 sentences). This reframes their limiting belief or objection into an empowering perspective.

2. **brand_promise_application**: How "{brand_promise}" specifically applies to their situation (1-2 sentences). Make it concrete and personal to this persona.

3. **bridge**: Rewrite the bridge_rationale following the BRIDGE rules (MAX 20 words, active verbs, visual, concrete)

4. **valence**: Either "Positive" or "Negative" (pick the most prevalent emotional state)

5. **intensity**: Integer from 1-5 based on emotional charge in the quotes

6. **self**: Either "Ideal", "Actual", or "Ought" based on which psychological version is activated

---

WRITING RULES (CRITICAL - FOLLOW EXACTLY):

**REFRAME rules:**
- MAX 25 words total (usually two short sentences)
- First sentence: Challenge the belief with an unexpected inversion. Use pattern "X isn't Y, it's Z" or similar contrast.
- Second sentence: Tie to the solution concept (time commitment), NOT the product.
- Use contractions (it's, you'll, that's, doesn't)
- Use dashes for contrast: "rehab, not risk" / "partners, not substitutes"
- NEVER mention product features — that comes in Bridge
- Declarative voice — state truth, don't explain it

**BRAND PROMISE APPLICATION rules:**
- MAX 20 words
- Include a SPECIFIC scenario from this persona's life (use persona field to tailor)
- Dad personas: reference kids, naps, screen time, before they wake, soccer practice, bedtime routine
- Worker personas: reference morning coffee, commute, lunch break, before meetings
- Make the time commitment feel effortless for THEIR specific situation
- Use "you/your" — speak TO them, not ABOUT them

**BRIDGE rules:**
- MAX 20 words
- ONE sentence only
- Show the product IN ACTION with active verbs: "waits", "gives", "keeps", "eliminates", "tracks", "proves"
- Visual and concrete — reader should picture it happening
- Use "you/your" — speak TO them ("gives you a win" not "gives users a win")
- Connect to a SPECIFIC product feature from the bridge_rationale

**BANNED PHRASES (never use these):**
- "specifically designed to"
- "directly addresses"
- "directly removes"
- "selling point"
- "this barrier"
- "eliminates the barrier"
- "the antidote to"
- "is designed to"
- "letting you focus on"
- Any phrase that sounds like a strategist describing copy rather than the copy itself

**VOICE:**
- Write like a creative who has internalized the customer, not a strategist explaining insights
- Punchy and direct, not explanatory
- Confident declarations, not hedged suggestions
- Use second person (you/your) throughout

---

OUTPUT FORMAT (JSON):

{{
  "insights": [
    {{
      "insight_number": 1,
      "reframe": "The cognitive reframe here...",
      "brand_promise_application": "How the brand promise applies...",
      "bridge": "Rewritten bridge following BRIDGE rules...",
      "valence": "Negative",
      "intensity": 4,
      "self": "Ought"
    }},
    {{
      "insight_number": 2,
      "reframe": "...",
      "brand_promise_application": "...",
      "bridge": "...",
      "valence": "Positive",
      "intensity": 3,
      "self": "Ideal"
    }}
  ]
}}

CRITICAL INSTRUCTIONS:
- Generate analysis for ALL insights provided in the user message
- insight_number must match the insight's position in the list (1, 2, 3, etc.)
- valence must be exactly "Positive" or "Negative"
- intensity must be integer 1-5
- self must be exactly "Ideal", "Actual", or "Ought"
- reframe and brand_promise_application should be 1-2 sentences each
- Reframe must be MAX 25 words. Brand promise application must be MAX 20 words. Bridge must be MAX 20 words. COUNT YOUR WORDS.

IMPORTANT: Output ONLY the JSON object. No preamble, no explanation. Start with the opening brace {{."""


def build_batch_data(insights_batch):
    """Build the variable per-batch data prompt (insight details only)."""

    prompt = "INSIGHTS TO ANALYZE:\n"

    for i, insight_data in enumerate(insights_batch, 1):
        prompt += f"\n--- INSIGHT {i} ---\n\n"
        prompt += f"Insight: {insight_data['insight']}\n"
        prompt += f"Insight Type: {insight_data['insight_type']}\n"
        prompt += f"Belief Statement: {insight_data['belief_statement']}\n"
        prompt += f"Bridge Rationale (rewrite this): {insight_data['bridge_rationale']}\n"
        prompt += f"Persona: {insight_data['persona_normalized']}\n"

        # Include best quotes (truncated)
        best_quotes = insight_data.get('best_quotes', [])
        if best_quotes:
            prompt += f"\nBest Quotes from Evidence:\n"
            for j, quote in enumerate(best_quotes[:3], 1):
                text = quote.get('text', '')[:200]
                prompt += f"{j}. \"{text}...\"\n"

        prompt += "\n"

    return prompt

def parse_analysis_json(response_text):
    """Parse JSON response from Claude."""
    # Try to extract JSON from markdown code blocks if present
    json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
    if json_match:
        response_text = json_match.group(1)

    # Extract JSON object
    if not response_text.strip().startswith('{'):
        start = response_text.find('{')
        end = response_text.rfind('}')
        if start != -1 and end != -1 and end > start:
            response_text = response_text[start:end+1]

    return json.loads(response_text)

async def analyze_insights_batch(insights_batch, brand_name, brand_promise, verbose=False):
    """Call Claude to analyze a batch of insights.

    Uses system_prompt for static instructions (cached after first call)
    and prompt for variable per-batch data only.
    """

    instructions = build_system_instructions(brand_name, brand_promise)
    data_prompt = build_batch_data(insights_batch)

    if verbose:
        print("\n" + "="*80)
        print("SYSTEM PROMPT (cached across batches):")
        print("="*80)
        print(instructions[:500] + "\n... [truncated]")
        print("="*80)
        print("USER PROMPT (batch data):")
        print("="*80)
        print(data_prompt)
        print("="*80 + "\n")

    response_text = ""
    try:
        async for message in query(
            prompt=data_prompt,
            options=ClaudeCodeOptions(model="claude-opus-4-6", system_prompt=instructions, max_turns=3)
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
    analysis_data = parse_analysis_json(response_text)

    return analysis_data

def assemble_notes(insight, analysis, brand_name, brand_promise):
    """Assemble the Notes field in the required format."""

    belief = insight.get('belief_statement', '')
    reframe = analysis.get('reframe', '')
    brand_promise_app = analysis.get('brand_promise_application', '')
    bridge = analysis.get('bridge', insight.get('bridge_rationale', ''))

    notes = f"BELIEF: {belief} "
    notes += f"REFRAME: {reframe} "
    notes += f"{brand_promise}: {brand_promise_app} "
    notes += f"{brand_name.upper()} BRIDGE: {bridge}"

    return notes

async def process_all_insights(themes_data, brand_name, brand_promise, batch_size=7, verbose=False, max_concurrent=3):
    """Process all insights in batches, running up to max_concurrent LLM calls concurrently."""

    print(f"\nProcessing insights with Claude (batch size: {batch_size}, concurrency: {max_concurrent})...")

    # Flatten all insights
    all_insights = []
    for theme in themes_data.get('themes', []):
        for insight in theme.get('insights', []):
            all_insights.append({
                'theme_name': theme.get('theme_name'),
                'insight_obj': insight
            })

    total_insights = len(all_insights)

    # Build all batches upfront
    batches = []
    for batch_start in range(0, total_insights, batch_size):
        batch_end = min(batch_start + batch_size, total_insights)
        batch = all_insights[batch_start:batch_end]
        batches.append((batch_start, batch_end, batch))

    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_batch(batch_start, batch_end, batch):
        async with semaphore:
            print(f"  Processing insights {batch_start + 1}-{batch_end} of {total_insights}...")

            # Prepare batch data
            batch_data = []
            for item in batch:
                insight = item['insight_obj']
                batch_data.append({
                    'insight': insight.get('insight', ''),
                    'insight_type': insight.get('insight_type', ''),
                    'belief_statement': insight.get('belief_statement', ''),
                    'bridge_rationale': insight.get('bridge_rationale', ''),
                    'persona_normalized': insight.get('persona_normalized', ''),
                    'best_quotes': insight.get('best_quotes', [])
                })

            # Analyze batch
            analysis_results = await analyze_insights_batch(batch_data, brand_name, brand_promise, verbose)

            return batch, analysis_results

    # Run all batches concurrently (limited by semaphore)
    tasks = [process_batch(bs, be, b) for bs, be, b in batches]
    results = await asyncio.gather(*tasks)

    # Apply results in order after all complete
    processed = 0
    for batch, analysis_results in results:
        for i, analysis in enumerate(analysis_results.get('insights', [])):
            insight_obj = batch[i]['insight_obj']

            # Assemble Notes field
            notes = assemble_notes(insight_obj, analysis, brand_name, brand_promise)

            # Add new fields
            insight_obj['notes'] = notes
            insight_obj['valence'] = analysis.get('valence', 'Negative')
            insight_obj['intensity'] = analysis.get('intensity', 3)
            insight_obj['self'] = analysis.get('self', 'Ideal')

            # Store reframe and brand_promise_application separately for reference
            insight_obj['_reframe'] = analysis.get('reframe', '')
            insight_obj['_brand_promise_application'] = analysis.get('brand_promise_application', '')

        processed += len(batch)

    print(f"  Completed {processed} insights")

    return themes_data

def save_themes(themes_data, output_path):
    """Save updated themes with notes and analysis."""

    # Remove temporary fields before saving
    for theme in themes_data.get('themes', []):
        for insight in theme.get('insights', []):
            if '_reframe' in insight:
                del insight['_reframe']
            if '_brand_promise_application' in insight:
                del insight['_brand_promise_application']

    with open(output_path, 'w') as f:
        json.dump(themes_data, f, indent=2)

    print(f"✓ Saved complete insights to: {output_path}")

def snake_to_title(snake_str):
    """Convert snake_case to Title Case with spaces."""
    if not snake_str:
        return ''
    return ' '.join(word.capitalize() for word in snake_str.split('_'))

def save_final_csv(themes_data, output_dir):
    """Save final CSV with flattened insights."""

    rows = []

    for theme in themes_data.get('themes', []):
        theme_name = theme.get('theme_name', '')

        for insight in theme.get('insights', []):
            # Handle sources - join if list
            sources = insight.get('sources', [])
            if isinstance(sources, list):
                sources_str = ';'.join(sources)
            else:
                sources_str = str(sources) if sources else ''

            # Handle top_communities - join if list
            top_communities = insight.get('top_communities', [])
            if isinstance(top_communities, list):
                communities_str = ';'.join(top_communities)
            else:
                communities_str = str(top_communities) if top_communities else ''

            row = {
                'Insight': insight.get('insight', ''),
                'Insight Type': insight.get('insight_type', ''),
                'Theme': theme_name,
                'Persona': snake_to_title(insight.get('persona_normalized', '')),
                'Angle': insight.get('angle', ''),
                'Notes': insight.get('notes', ''),
                'Valence': insight.get('valence', ''),
                'Intensity': insight.get('intensity', ''),
                'Self': insight.get('self', ''),
                'Evidence Count': insight.get('evidence_count', 0),
                'Source': sources_str,
                'Top Communities': communities_str,
                'Status': 'New'
            }
            rows.append(row)

    # Create DataFrame with exact column order
    columns = [
        'Insight', 'Insight Type', 'Theme', 'Persona', 'Angle', 'Notes',
        'Valence', 'Intensity', 'Self', 'Evidence Count', 'Source',
        'Top Communities', 'Status'
    ]
    df = pd.DataFrame(rows, columns=columns)

    # Save to CSV
    output_path = os.path.join(output_dir, 'insights_final.csv')
    df.to_csv(output_path, index=False)

    print(f"✓ Saved final CSV: {output_path}")

def print_summary(themes_data):
    """Print summary statistics."""

    print("\n" + "="*80)
    print("INSIGHT WRITING SUMMARY")
    print("="*80)

    total_insights = 0
    valence_counts = {'Positive': 0, 'Negative': 0}
    intensity_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    self_counts = {'Ideal': 0, 'Actual': 0, 'Ought': 0}

    for theme in themes_data.get('themes', []):
        for insight in theme.get('insights', []):
            total_insights += 1

            valence = insight.get('valence', 'Negative')
            valence_counts[valence] = valence_counts.get(valence, 0) + 1

            intensity = insight.get('intensity', 3)
            intensity_counts[intensity] = intensity_counts.get(intensity, 0) + 1

            self_type = insight.get('self', 'Ideal')
            self_counts[self_type] = self_counts.get(self_type, 0) + 1

    print(f"\nTotal insights analyzed: {total_insights}")

    print(f"\nValence distribution:")
    for valence, count in sorted(valence_counts.items()):
        pct = (count / total_insights * 100) if total_insights > 0 else 0
        print(f"  {valence}: {count} ({pct:.1f}%)")

    print(f"\nIntensity distribution:")
    for intensity in sorted(intensity_counts.keys()):
        count = intensity_counts[intensity]
        pct = (count / total_insights * 100) if total_insights > 0 else 0
        print(f"  Level {intensity}: {count} ({pct:.1f}%)")

    print(f"\nSelf distribution:")
    for self_type, count in sorted(self_counts.items()):
        pct = (count / total_insights * 100) if total_insights > 0 else 0
        print(f"  {self_type}: {count} ({pct:.1f}%)")

    print("\n" + "="*80)

async def main_async():
    parser = argparse.ArgumentParser(description='Write full insight analysis using LLM')
    parser.add_argument('brand', help='Brand name (e.g., mybrand)')
    parser.add_argument('sprint', help='Sprint folder name (e.g., 01_weight-loss-men-dads)')
    parser.add_argument('--batch-size', type=int, default=7,
                       help='Number of insights to process per LLM call (default: 7)')
    parser.add_argument('--verbose', action='store_true',
                       help='Print full LLM prompt before sending')

    args = parser.parse_args()

    # Paths
    intermediate_dir = f"brands/{args.brand}/sprints/{args.sprint}/_intermediate"
    themes_path = f"{intermediate_dir}/themes_discovered.json"
    output_path = f"{intermediate_dir}/insights_complete.json"
    brand_brief_path = f"brands/{args.brand}/brand_brief.yaml"

    print("="*80)
    print("INSIGHT WRITER - PHASE 1C")
    print("="*80)
    print(f"Brand: {args.brand}")
    print(f"Sprint: {args.sprint}")
    print()

    # Load inputs
    print("Loading data...")
    themes_data = load_themes(themes_path)
    brand_brief = load_brand_brief(brand_brief_path)

    brand_name = brand_brief.get('brand_name', 'Unknown Brand')
    brand_promise = brand_brief.get('brand_promise', 'Unknown Promise')

    print(f"  Brand: {brand_name}")
    print(f"  Promise: {brand_promise}")

    # Process all insights
    updated_themes = await process_all_insights(
        themes_data,
        brand_name,
        brand_promise,
        batch_size=args.batch_size,
        verbose=args.verbose
    )

    # Save output
    print("\nSaving results...")
    save_themes(updated_themes, output_path)

    # Save final CSV
    output_dir = f"brands/{args.brand}/sprints/{args.sprint}"
    save_final_csv(updated_themes, output_dir)

    # Print summary
    print_summary(updated_themes)

    print("\n" + "="*80)
    print("COMPLETE")
    print("="*80)

def main():
    asyncio.run(main_async())

if __name__ == '__main__':
    main()
