#!/usr/bin/env python3
"""
Retrieval Planner - Phase 3 of Research Engine

Generates scrape_config.json from research direction using hybrid discovery:
- Cached subreddit knowledge
- Reddit API search
- Web search fallback
- LLM planning

Usage:
    python3 step01_retrieval_planner.py <brand> <sprint> "<research_direction>"
    python3 step01_retrieval_planner.py <brand> <sprint> "<research_direction>" --scope deep
    python3 step01_retrieval_planner.py <brand> <sprint> "<research_direction>" --refresh-cache

Examples:
    python3 step01_retrieval_planner.py pureplank 02_busy-dads "weight loss for busy dads"
    python3 step01_retrieval_planner.py pureplank 02_busy-dads "weight loss for busy dads" --scope deep
"""

import json
import re
import sys
import argparse
import asyncio
import time
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import quote_plus

import yaml
import requests
from claude_code_sdk import query, ClaudeCodeOptions


def load_brand_brief(yaml_path):
    """Load brand brief YAML file."""
    with open(yaml_path, 'r') as f:
        return yaml.safe_load(f)


def format_brand_brief_for_prompt(brand_brief: dict) -> str:
    """Format brand brief dict as readable text for LLM prompt."""
    formatted = f"BRAND: {brand_brief['brand_name']}\n\n"
    formatted += f"PRODUCT:\n{brand_brief['product']}\n\n"

    formatted += "MAIN SELLING POINTS:\n"
    for sp in brand_brief.get('main_selling_points', []):
        formatted += f"- {sp['name']}: {sp['description']}\n"
        formatted += f"  Solves: {sp['solves']}\n"

    formatted += "\nPAIN POINTS SOLVED:\n"
    for pp in brand_brief.get('pain_points_solved', []):
        formatted += f"- {pp}\n"

    formatted += "\nTARGET CUSTOMERS:\n"
    for tc in brand_brief.get('target_customers', []):
        formatted += f"- {tc}\n"

    return formatted.strip()


# Scope configurations
SCOPE_CONFIGS = {
    "quick": {"stage1": 10, "stage2": 25},
    "standard": {"stage1": 15, "stage2": 50},
    "deep": {"stage1": 20, "stage2": 100},
}

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
CACHE_MAX_AGE_DAYS = 30


async def extract_topics_llm(research_direction: str, cache: dict) -> list[str]:
    """Use LLM to extract relevant topic categories from research direction."""
    # Get available topics from cache
    available_topics = sorted(cache.keys())

    if not available_topics:
        print("Warning: No topics in cache, returning empty list")
        return []

    prompt = f"""Given this research direction: "{research_direction}"

Which of these topic categories are relevant? Pick ALL that apply.

Available topics:
{', '.join(available_topics)}

Return ONLY a JSON array of matching topics, nothing else.
Example: ["health", "fitness", "workplace"]

IMPORTANT: Output ONLY the JSON array. Start with [.
"""

    print("  Using LLM to extract topics...")

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

    # Parse JSON array
    try:
        # Try to extract JSON from markdown code blocks if present
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(1)

        # Extract JSON array
        if not response_text.strip().startswith('['):
            start = response_text.find('[')
            end = response_text.rfind(']')
            if start != -1 and end != -1 and end > start:
                response_text = response_text[start:end+1]

        topics = json.loads(response_text)

        # Validate topics are in cache
        valid_topics = [t for t in topics if t in available_topics]

        return sorted(valid_topics)

    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse LLM topic extraction: {e}")
        print(f"Response: {response_text[:200]}")
        return []


def load_subreddit_cache(cache_path: Path) -> dict:
    """Load subreddit cache from JSON."""
    if not cache_path.exists():
        return {}

    with open(cache_path) as f:
        return json.load(f)


def save_subreddit_cache(cache_path: Path, cache: dict):
    """Save subreddit cache to JSON."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, 'w') as f:
        json.dump(cache, f, indent=2)


def is_cache_fresh(topic_data: dict, max_age_days: int = CACHE_MAX_AGE_DAYS) -> bool:
    """Check if cache entry is fresh."""
    if "last_updated" not in topic_data:
        return False

    last_updated = datetime.fromisoformat(topic_data["last_updated"])
    age = datetime.now() - last_updated
    return age.days < max_age_days


def discover_subreddits_from_cache(topics: list[str], cache: dict) -> tuple[list[str], dict]:
    """Get subreddits from cache for given topics."""
    candidates = []
    cache_info = {}

    for topic in topics:
        if topic in cache:
            topic_data = cache[topic]
            subreddits = topic_data.get("subreddits", [])
            candidates.extend(subreddits)

            is_fresh = is_cache_fresh(topic_data)
            cache_info[topic] = {
                "found": True,
                "count": len(subreddits),
                "fresh": is_fresh,
                "source": topic_data.get("source", "unknown"),
            }
        else:
            cache_info[topic] = {"found": False, "count": 0, "fresh": False}

    return list(set(candidates)), cache_info


async def extract_reddit_search_keywords_llm(research_direction: str, brand_brief_data: dict) -> list[str]:
    """Use LLM to extract niche-relevant Reddit search keywords from direction + brand context."""
    target_customers = brand_brief_data.get('target_customers', [])[:2]
    product = brand_brief_data.get('product', '')[:200]

    prompt = f"""Extract 3-5 short Reddit search phrases for this research task.

PRODUCT: {product}

TARGET AUDIENCE:
{chr(10).join(f'- {tc}' for tc in target_customers)}

RESEARCH DIRECTION: "{research_direction}"

Return search phrases that will find subreddits where the target audience is active.
Focus on the NICHE, HOBBY, or PRODUCT CATEGORY — not on any emotional language in the direction.
Emotional language like "guilt", "anxiety", "fear" describes what people feel within their hobby —
do NOT extract those as search terms.

Return ONLY a JSON array of short phrases (2-5 words each).
Example for a backyard chicken brand: ["backyard chickens worms", "chicken keeper dewormer", "natural poultry care"]
Example for a fitness brand: ["home workout routine", "weight loss meal prep", "dad bod fitness"]

IMPORTANT: Output ONLY the JSON array. Start with [.
"""

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
            pass
        else:
            raise

    try:
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(1)
        if not response_text.strip().startswith('['):
            start = response_text.find('[')
            end = response_text.rfind(']')
            if start != -1 and end != -1 and end > start:
                response_text = response_text[start:end+1]
        keywords = json.loads(response_text)
        print(f"    LLM-extracted keywords: {keywords}")
        return keywords[:5]
    except (json.JSONDecodeError, Exception) as e:
        print(f"    Warning: keyword extraction failed ({e}), falling back to direction")
        return [research_direction]


async def discover_subreddits_from_reddit_api(research_direction: str, brand_brief_data: dict) -> list[str]:
    """Discover subreddits using Reddit's search API with LLM-extracted niche keywords."""
    print("\n  Layer B: Reddit API discovery...")

    keywords = await extract_reddit_search_keywords_llm(research_direction, brand_brief_data)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    candidates = []

    for keyword in keywords:
        try:
            time.sleep(2)  # Rate limiting

            encoded = quote_plus(keyword)
            url = f"https://www.reddit.com/subreddits/search.json?q={encoded}&limit=10"

            print(f"    Searching: '{keyword}'...", end=" ")

            response = session.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                children = data.get("data", {}).get("children", [])

                for child in children:
                    subreddit_data = child.get("data", {})
                    name = subreddit_data.get("display_name")
                    if name:
                        candidates.append(name)

                print(f"found {len(children)} subreddits")
            else:
                print(f"failed (status {response.status_code})")

        except Exception as e:
            print(f"error: {e}")

    unique_candidates = list(set(candidates))
    print(f"    Total unique from API: {len(unique_candidates)}")

    return unique_candidates


def discover_subreddits_from_web_search(topics: list[str]) -> dict:
    """Discover subreddits using web search for topics needing refresh."""
    print("\n  Layer C: Web search discovery...")

    # Note: This would use WebSearch tool, but since we're in a script context
    # without direct tool access, we'll return empty and rely on Reddit API + cache
    # In a real implementation, this would make web search queries

    print("    (Skipping web search - relying on cache + Reddit API)")
    return {}


def build_planning_prompt(brand_brief: str, brand_brief_data: dict, research_direction: str, candidate_subreddits: list[str]) -> str:
    """Build LLM prompt for scrape config planning."""
    target_customers = brand_brief_data.get('target_customers', [])[:3]
    community_constraint = '\n'.join(f"  - {tc}" for tc in target_customers)

    prompt = f"""You are planning Reddit research for a brand.

BRAND BRIEF:
{brand_brief}

RESEARCH DIRECTION:
"{research_direction}"

CANDIDATE SUBREDDITS ({len(candidate_subreddits)} available):
{', '.join(candidate_subreddits)}

YOUR TASK:
Generate a Reddit scraping configuration optimized for this research direction.

REQUIREMENTS:

1. **subreddits** (5-8 total):
   COMMUNITY CONSTRAINT — apply this before all other rules:
   This brand's customers are:
{community_constraint}
   You MUST select ONLY subreddits where these specific people are active in their hobby or interest context.
   If a candidate subreddit serves human medical patients, general health/anxiety, mental health, or any
   audience NOT described above — reject it. This applies even when the research direction contains
   emotional language like "guilt", "anxiety", "fear", or "failed". That language describes how the
   target audience feels within their hobby — it does NOT mean they belong to a medical community.
   - Pick the MOST RELEVANT subreddits from the candidates that pass the community constraint above
   - Prioritize communities with active discussions about the research topic
   - Mix general and niche communities for diversity

2. **search_queries** (10-15 total):
   - Generate search queries using PROBLEM-CENTRIC language
   - Focus on pain points, barriers, struggles, questions
   - Use natural language people actually search for
   - Examples: "can't lose weight busy schedule", "dad bod exercise at home", "too tired to workout"

3. **theme_keywords** (15-20 total):
   - Keywords for filtering thread relevance
   - Include problem words, solution words, demographic words
   - Lowercase, no duplicates

4. **high_signal_keywords** (20-30 total):
   - Emotional and friction markers for comment filtering
   - Pain words: hurt, sore, struggle, failed, quit
   - Emotion words: frustrated, tired, worried, hopeful
   - Action words: tried, stopped, can't, won't

OUTPUT FORMAT (JSON only, no explanation):

{{
  "subreddits": ["subreddit1", "subreddit2", ...],
  "search_queries": ["query 1", "query 2", ...],
  "theme_keywords": ["keyword1", "keyword2", ...],
  "high_signal_keywords": ["keyword1", "keyword2", ...]
}}

IMPORTANT: Output ONLY the JSON object. Start with the opening brace {{.
"""

    return prompt


def parse_llm_json(response_text: str) -> dict:
    """Parse JSON from LLM response."""
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


async def plan_with_llm(brand_brief: str, brand_brief_data: dict, research_direction: str, candidate_subreddits: list[str], verbose: bool = False) -> dict:
    """Use LLM to generate scrape config."""
    print("\nSTEP 3: LLM Planning")
    print("-" * 60)

    prompt = build_planning_prompt(brand_brief, brand_brief_data, research_direction, candidate_subreddits)

    if verbose:
        print("\nFull LLM Prompt:")
        print("=" * 60)
        print(prompt)
        print("=" * 60)

    print("Querying Claude for scrape config...")

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

    # Parse JSON with retry
    try:
        config = parse_llm_json(response_text)
        print("✓ LLM planning complete")
        return config
    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse LLM response: {e}")
        print("Retrying...")

        # Retry once
        response_text = ""
        try:
            async for message in query(
                prompt=prompt + "\n\nREMINDER: Output ONLY valid JSON, no explanation.",
                options=ClaudeCodeOptions(model="claude-sonnet-4-6", max_turns=3)
            ):
                if hasattr(message, 'content'):
                    for block in message.content:
                        if hasattr(block, 'text'):
                            response_text += block.text
        except Exception as e2:
            if "Unknown message type" in str(e2) and response_text:
                pass
            else:
                raise

        try:
            config = parse_llm_json(response_text)
            print("✓ LLM planning complete (retry succeeded)")
            return config
        except json.JSONDecodeError as e2:
            print(f"ERROR: Failed to parse LLM response after retry: {e2}")
            print("Response text:")
            print(response_text[:500])
            sys.exit(1)


def assemble_config(research_direction: str, scope: str, llm_output: dict) -> dict:
    """Assemble final scrape config."""
    scope_params = SCOPE_CONFIGS[scope]

    config = {
        "research_direction": research_direction,
        "scope": scope,
        "generated_at": datetime.now().isoformat(),
        "subreddits": llm_output["subreddits"],
        "search_queries": llm_output["search_queries"],
        "theme_keywords": llm_output["theme_keywords"],
        "high_signal_keywords": llm_output["high_signal_keywords"],
        "min_comments": 15,
        "max_threads_stage1": scope_params["stage1"],
        "max_threads_stage2": scope_params["stage2"],
        "max_comments_per_thread": 80,
    }

    return config


def save_outputs(brand: str, sprint: str, config: dict):
    """Save scrape config and sprint info."""
    # Create sprint folder
    sprint_dir = Path(f"brands/{brand}/sprints/{sprint}")
    sprint_dir.mkdir(parents=True, exist_ok=True)
    intermediate_dir = sprint_dir / "_intermediate"
    intermediate_dir.mkdir(exist_ok=True)

    # Save scrape_config.json
    config_path = intermediate_dir / "scrape_config.json"
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"\n✓ Saved: {config_path}")

    # Save sprint_config.txt
    info_path = sprint_dir / "sprint_config.txt"
    with open(info_path, 'w') as f:
        f.write(f"Research Direction: {config['research_direction']}\n")
        f.write(f"Scope: {config['scope']}\n")
        f.write(f"Generated: {config['generated_at']}\n")
        f.write(f"\nSubreddits ({len(config['subreddits'])}):\n")
        for sub in config['subreddits']:
            f.write(f"  - r/{sub}\n")
        f.write(f"\nSearch Queries ({len(config['search_queries'])}):\n")
        for query in config['search_queries']:
            f.write(f"  - {query}\n")
    print(f"✓ Saved: {info_path}")


async def main_async():
    parser = argparse.ArgumentParser(description='Generate scrape config from research direction')
    parser.add_argument('brand', help='Brand name (e.g., pureplank)')
    parser.add_argument('sprint', help='Sprint folder name (e.g., 02_busy-dads)')
    parser.add_argument('research_direction', help='Research direction in quotes')
    parser.add_argument('--scope', choices=['quick', 'standard', 'deep'], default='standard',
                       help='Scope of scraping (default: standard)')
    parser.add_argument('--refresh-cache', action='store_true',
                       help='Force refresh of subreddit cache')
    parser.add_argument('--verbose', action='store_true',
                       help='Print full LLM prompt')

    args = parser.parse_args()

    print("=" * 80)
    print("RETRIEVAL PLANNER - PHASE 3")
    print("=" * 80)
    print(f"Brand: {args.brand}")
    print(f"Sprint: {args.sprint}")
    print(f"Research Direction: \"{args.research_direction}\"")
    print(f"Scope: {args.scope}")
    print()

    # Load brand brief
    brief_path = Path(f"brands/{args.brand}/brand_brief.yaml")
    if not brief_path.exists():
        print(f"ERROR: Brand brief not found: {brief_path}")
        sys.exit(1)

    brand_brief_data = load_brand_brief(brief_path)
    brand_brief = format_brand_brief_for_prompt(brand_brief_data)

    # Load cache first (needed for topic extraction)
    cache_path = Path("engine/config/subreddit_cache.json")
    cache = load_subreddit_cache(cache_path)

    # STEP 1: Extract topics
    print("STEP 1: Topic Extraction (LLM)")
    print("-" * 60)
    topics = await extract_topics_llm(args.research_direction, cache)
    print(f"Extracted topics: {', '.join(topics)}")

    # STEP 2: Subreddit Discovery
    print("\nSTEP 2: Subreddit Discovery (Hybrid)")
    print("-" * 60)

    all_candidates = []

    # Layer A: Cache lookup
    print("  Layer A: Cache lookup...")
    cache_candidates, cache_info = discover_subreddits_from_cache(topics, cache)
    all_candidates.extend(cache_candidates)

    for topic, info in cache_info.items():
        if info["found"]:
            freshness = "fresh" if info["fresh"] else "stale"
            print(f"    {topic}: {info['count']} subreddits ({freshness}, source: {info['source']})")
        else:
            print(f"    {topic}: not in cache")

    print(f"    Total from cache: {len(cache_candidates)}")

    # Layer B: Reddit API
    api_candidates = await discover_subreddits_from_reddit_api(args.research_direction, brand_brief_data)
    all_candidates.extend(api_candidates)

    # Layer C: Web search (if refresh needed or cache missing)
    needs_refresh = args.refresh_cache or any(
        not info["found"] or not info["fresh"]
        for info in cache_info.values()
    )

    if needs_refresh:
        # Placeholder for web search - would use WebSearch tool
        print("\n  Layer C: Would use web search here (not implemented in script mode)")

    # Deduplicate
    unique_candidates = list(set(all_candidates))
    print(f"\n  Total unique candidates: {len(unique_candidates)}")

    if len(unique_candidates) == 0:
        print("\nERROR: No subreddit candidates found. Try:")
        print("  1. Adding topics to engine/config/subreddit_cache.json")
        print("  2. Checking internet connection for Reddit API")
        sys.exit(1)

    # STEP 3: LLM Planning
    llm_output = await plan_with_llm(brand_brief, brand_brief_data, args.research_direction, unique_candidates, args.verbose)

    print(f"  Selected subreddits: {len(llm_output['subreddits'])}")
    print(f"  Generated queries: {len(llm_output['search_queries'])}")
    print(f"  Theme keywords: {len(llm_output['theme_keywords'])}")
    print(f"  High-signal keywords: {len(llm_output['high_signal_keywords'])}")

    # STEP 4: Assemble config
    print("\nSTEP 4: Assembling Config")
    print("-" * 60)
    config = assemble_config(args.research_direction, args.scope, llm_output)
    print(f"  Stage 1: {config['max_threads_stage1']} threads")
    print(f"  Stage 2: {config['max_threads_stage2']} threads")
    print(f"  Min comments: {config['min_comments']}")

    # STEP 5: Save outputs
    print("\nSTEP 5: Saving Outputs")
    print("-" * 60)
    save_outputs(args.brand, args.sprint, config)

    print("\n" + "=" * 80)
    print("COMPLETE")
    print("=" * 80)
    print(f"\nNext steps:")
    print(f"  1. python3 engine/step02_reddit_scraper.py {args.brand} {args.sprint}")
    print(f"  2. python3 engine/step02_reddit_scraper.py {args.brand} {args.sprint} --stage2")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
