#!/usr/bin/env python3
"""
Persona Normalizer - Step 07 of Research Engine

Normalizes raw persona descriptions into consistent canonical labels.

Usage:
    python3 engine/step07_persona_normalizer.py mybrand 01_weight-loss-men-dads
    python3 engine/step07_persona_normalizer.py mybrand 01_weight-loss-men-dads --verbose
"""

import os
import sys
import json
import argparse
import asyncio
import re
from pathlib import Path
from datetime import datetime
from claude_code_sdk import query, ClaudeCodeOptions

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.evidence_db import load_personas, upsert_personas, init_db

def load_themes(json_path):
    """Load themes_discovered.json from sprint folder."""
    with open(json_path, 'r') as f:
        return json.load(f)

def load_personas_ledger(brand):
    """Load personas from evidence.db. Return empty dict if none exist."""
    return load_personas(brand)

def extract_raw_personas(themes_data):
    """Extract all unique persona_raw values from themes."""
    raw_personas = set()
    for theme in themes_data.get('themes', []):
        for insight in theme.get('insights', []):
            persona_raw = insight.get('persona_raw')
            if persona_raw:
                raw_personas.add(persona_raw)
    return sorted(list(raw_personas))

def build_normalization_prompt(raw_personas, existing_ledger):
    """Build prompt asking Claude to normalize personas."""

    existing_personas = existing_ledger.get('personas', [])

    prompt = f"""You are normalizing persona descriptions into consistent canonical labels.

TASK: Map raw persona descriptions to normalized canonical labels. Either use existing personas from the ledger, or propose new ones.

EXISTING PERSONAS IN LEDGER ({len(existing_personas)}):
"""

    if existing_personas:
        for p in existing_personas:
            prompt += f"\n- {p['id']}: {p['label']}"
            prompt += f"\n  Description: {p['description']}"
    else:
        prompt += "\n(None yet - this is the first sprint)\n"

    prompt += f"""

RAW PERSONAS FROM THIS SPRINT ({len(raw_personas)}):
"""

    for i, raw in enumerate(raw_personas, 1):
        prompt += f"\n{i:2d}. \"{raw}\""

    prompt += """

YOUR TASK:

1. GROUP similar raw personas that describe the same type of person
2. For each group, either:
   - MAP to existing ledger persona if it fits
   - PROPOSE new persona if meaningfully distinct

CRITICAL INSTRUCTIONS:
- Be AGGRESSIVE about clustering — if two raw personas describe essentially the same life situation, map to same label
- Only create new persona if meaningfully distinct from existing ones
- Use existing ledger personas when they fit
- A persona should capture a specific life situation, constraint, or identity — not just demographics

EXAMPLE CLUSTERING:
- "fathers who accept dad bod as inevitable" + "dads embarrassed at the pool" → Same persona? Could be, if both are dads struggling with body image. Map to "self_conscious_dads"
- "beginners who experience elbow wrist pain" + "floor plankers frustrated with discomfort" → Same persona? YES → Map to "pain_blocked" or "floor_pain_sufferers"
- "people with all-or-nothing thinking" + "people who quit after one missed day" → Same persona? YES → Map to "perfectionists" or "all_or_nothing"

FOR EACH NEW PERSONA, PROVIDE:
- id: Short snake_case identifier (2-3 words max). Should sound like natural market segments, not clinical labels.
- label: Human-readable name (2-3 words max, Title Case)
- description: 1-2 sentences explaining who this person is
- justification: Why existing personas don't fit (if creating new)

PERSONA NAMING RULES (CRITICAL):

A PERSONA describes WHO someone IS — their identity, life stage, situation, or personality type.
A PERSONA does NOT describe what barrier they're facing or what state they're in. That belongs in the insight.

The test: "These are [persona]" should sound natural.
✓ "These are busy dads" — identity
✓ "These are desk workers" — occupation
✓ "These are men over 40" — demographic
✓ "These are perfectionists" — personality type
✓ "These are home exercisers" — lifestyle
✓ "These are fitness beginners" — life stage
✓ "These are beer belly dads" — identity + situation

✗ "These are pain blocked" — that's a barrier, not a person
✗ "These are early plateaus" — that's a stage in their journey, not who they are
✗ "These are desk pain" — that's a symptom, not a person
✗ "These are age doubters" — that's a mindset about one thing, not an identity
✗ "These are duration skeptics" — that's a belief, not a person

GOOD persona names (WHO they are):
✓ "busy_dads" — life situation
✓ "men_over_40" — demographic
✓ "desk_workers" — occupation
✓ "fitness_beginners" — life stage
✓ "gym_avoiders" — lifestyle choice (this IS part of their identity)
✓ "perfectionists" — personality type
✓ "former_athletes" — identity
✓ "new_fathers" — life stage
✓ "beer_belly_dads" — identity + physical situation

BAD persona names (barrier/state, not identity):
✗ "pain_blocked" — barrier
✗ "desk_pain" — symptom
✗ "early_plateaus" — journey stage
✗ "age_doubters" — temporary mindset
✗ "duration_skeptics" — belief about one thing
✗ "quick_quitters" — behavior pattern
✗ "form_confused" — temporary state
✗ "confidence_seekers" — goal, not identity

If you can't determine WHO the person is from the raw persona, default to a broad but real segment like "fitness_beginners", "busy_professionals", "men_over_40", "dads", etc.

OUTPUT FORMAT (JSON):

{
  "mappings": {
    "beginners who experience elbow wrist pain": "pain_blocked",
    "floor plankers frustrated with discomfort": "pain_blocked",
    "people with all-or-nothing thinking patterns": "perfectionists",
    "people who quit after one missed day": "perfectionists"
  },
  "new_personas": [
    {
      "id": "busy_dads",
      "label": "Busy Dads",
      "description": "Fathers juggling work and family who struggle to find time for fitness.",
      "justification": "Life stage and identity, not just a barrier."
    },
    {
      "id": "men_over_40",
      "label": "Men Over 40",
      "description": "Men past 40 who are skeptical about fitness results at their age.",
      "justification": "Demographic identity, not just age-related doubt."
    }
  ]
}

IMPORTANT: Output ONLY the JSON object. No preamble, no explanation. Start with the opening brace {.
"""

    return prompt

def parse_normalization_json(response_text):
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

async def normalize_personas(raw_personas, existing_ledger, verbose=False):
    """Call Claude to normalize personas."""
    print("\nNormalizing personas with Claude...")

    prompt = build_normalization_prompt(raw_personas, existing_ledger)

    if verbose:
        print("\n" + "="*80)
        print("FULL LLM PROMPT:")
        print("="*80)
        print(prompt)
        print("="*80 + "\n")

    response_text = ""
    try:
        async for message in query(
            prompt=prompt,
            options=ClaudeCodeOptions(model="claude-haiku-4-5-20251001", max_turns=3)
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
    normalization_data = parse_normalization_json(response_text)

    return normalization_data

def update_themes_with_normalized_personas(themes_data, mappings):
    """Add persona_normalized field to each insight."""
    for theme in themes_data.get('themes', []):
        for insight in theme.get('insights', []):
            raw_persona = insight.get('persona_raw')
            if raw_persona and raw_persona in mappings:
                insight['persona_normalized'] = mappings[raw_persona]

    return themes_data

def update_personas_ledger(existing_ledger, new_personas, sprint_name, mappings):
    """Update personas ledger with new personas and counts."""
    # Get existing personas as dict by id
    personas_by_id = {p['id']: p for p in existing_ledger.get('personas', [])}

    # Add new personas
    for new_persona in new_personas:
        if new_persona['id'] not in personas_by_id:
            personas_by_id[new_persona['id']] = {
                'id': new_persona['id'],
                'label': new_persona['label'],
                'description': new_persona['description'],
                'justification': new_persona['justification'],
                'first_seen_sprint': sprint_name,
                'insight_count': 0
            }

    # Count insights per persona from mappings
    persona_counts = {}
    for raw_persona, normalized_id in mappings.items():
        persona_counts[normalized_id] = persona_counts.get(normalized_id, 0) + 1

    # Update counts
    for persona_id, count in persona_counts.items():
        if persona_id in personas_by_id:
            personas_by_id[persona_id]['insight_count'] = personas_by_id[persona_id].get('insight_count', 0) + count

    # Convert back to list
    updated_ledger = {
        'last_updated': datetime.now().isoformat(),
        'personas': sorted(personas_by_id.values(), key=lambda x: x['id'])
    }

    return updated_ledger

def save_themes(themes_data, output_path):
    """Save updated themes with persona_normalized."""
    with open(output_path, 'w') as f:
        json.dump(themes_data, f, indent=2)
    print(f"✓ Updated themes with normalized personas: {output_path}")

def save_personas_ledger(ledger_data, output_path):
    """Save updated personas ledger."""
    with open(output_path, 'w') as f:
        json.dump(ledger_data, f, indent=2)
    print(f"✓ Updated personas ledger: {output_path}")

def print_summary_report(raw_personas, mappings, new_personas, updated_ledger):
    """Print summary report."""
    print("\n" + "="*80)
    print("PERSONA NORMALIZATION SUMMARY")
    print("="*80)

    print(f"\nRaw personas processed: {len(raw_personas)}")
    print(f"Unique normalized personas: {len(set(mappings.values()))}")
    print(f"New personas created: {len(new_personas)}")
    print(f"Total personas in ledger: {len(updated_ledger['personas'])}")

    # Show clustering stats
    normalized_counts = {}
    for normalized_id in mappings.values():
        normalized_counts[normalized_id] = normalized_counts.get(normalized_id, 0) + 1

    print(f"\n{'-'*80}")
    print("CLUSTERING RESULTS:")
    print(f"{'-'*80}")

    # Find personas in ledger by id
    personas_by_id = {p['id']: p for p in updated_ledger['personas']}

    for normalized_id, count in sorted(normalized_counts.items(), key=lambda x: -x[1]):
        persona = personas_by_id.get(normalized_id, {})
        label = persona.get('label', normalized_id)
        print(f"{count:2d} raw personas → {normalized_id} ({label})")

    if new_personas:
        print(f"\n{'-'*80}")
        print("NEW PERSONAS CREATED:")
        print(f"{'-'*80}")
        for p in new_personas:
            print(f"\n{p['id']} - {p['label']}")
            print(f"  {p['description']}")
            print(f"  Justification: {p['justification']}")

    print("\n" + "="*80)

async def main_async():
    parser = argparse.ArgumentParser(description='Normalize raw persona descriptions')
    parser.add_argument('brand', help='Brand name (e.g., mybrand)')
    parser.add_argument('sprint', help='Sprint folder name (e.g., 01_weight-loss-men-dads)')
    parser.add_argument('--verbose', action='store_true',
                       help='Print full LLM prompt before sending')

    args = parser.parse_args()

    # Paths
    themes_path = f"brands/{args.brand}/sprints/{args.sprint}/_intermediate/themes_discovered.json"

    print("="*80)
    print("PERSONA NORMALIZER - PHASE 1A-N")
    print("="*80)
    print(f"Brand: {args.brand}")
    print(f"Sprint: {args.sprint}")
    print()

    # Initialize DB (ensures tables exist)
    init_db(args.brand)

    # Load inputs
    print("Loading themes...")
    themes_data = load_themes(themes_path)

    print("Loading personas ledger from evidence.db...")
    existing_ledger = load_personas_ledger(args.brand)
    existing_count = len(existing_ledger.get('personas', []))
    print(f"  Existing personas in ledger: {existing_count}")

    # Extract raw personas
    raw_personas = extract_raw_personas(themes_data)
    print(f"  Raw personas in this sprint: {len(raw_personas)}")

    # Normalize personas
    normalization_data = await normalize_personas(
        raw_personas,
        existing_ledger,
        verbose=args.verbose
    )

    print("\nProcessing results...")

    mappings = normalization_data.get('mappings', {})
    new_personas = normalization_data.get('new_personas', [])

    # Update themes with normalized personas
    updated_themes = update_themes_with_normalized_personas(themes_data, mappings)

    # Update personas ledger
    updated_ledger = update_personas_ledger(
        existing_ledger,
        new_personas,
        args.sprint,
        mappings
    )

    # Save outputs
    save_themes(updated_themes, themes_path)
    upsert_personas(args.brand, updated_ledger)
    print(f"✓ Updated personas in evidence.db")

    # Print report
    print_summary_report(raw_personas, mappings, new_personas, updated_ledger)

    print("\n" + "="*80)
    print("COMPLETE")
    print("="*80)

def main():
    asyncio.run(main_async())

if __name__ == '__main__':
    main()
