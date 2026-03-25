#!/usr/bin/env python3
"""
Research Engine MCP Server

Exposes the Research Engine as MCP tools so Claude Code agents can trigger
sprints without reading any files (~100 tokens overhead vs ~100K tokens).

Tools:
    - create_brand: Create a new brand from a product/brand info dump
    - run_research_sprint: Start a new research sprint as a background process
    - check_sprint_status: Check if a sprint is running/completed/failed
    - list_brands: List available brands
    - list_sprints: List sprints for a brand

Setup in .claude/settings.json or project MCP config:
    {
        "mcpServers": {
            "research-engine": {
                "command": "python3",
                "args": ["engine/mcp_server.py"],
                "cwd": "<project_root>"
            }
        }
    }

Usage:
    python3 engine/mcp_server.py
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Clear Claude Code nesting env vars so claude_code_sdk.query() works
# when this MCP server is spawned as a child of Claude Code.
os.environ.pop("CLAUDECODE", None)
os.environ.pop("CLAUDE_CODE_ENTRYPOINT", None)

import yaml
from mcp.server.fastmcp import FastMCP
from claude_code_sdk import query, ClaudeCodeOptions
from claude_code_sdk._errors import MessageParseError

logger = logging.getLogger(__name__)

# Determine project root (parent of engine/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Add project root to path so we can import evidence_db
sys.path.insert(0, str(PROJECT_ROOT))

from engine.evidence_db import get_evidence_count, load_personas, db_path

mcp = FastMCP("research-engine")

# Track running processes
_running_sprints = {}


# ---------------------------------------------------------------------------
# Brand brief generation prompt
# ---------------------------------------------------------------------------
_BRAND_BRIEF_PROMPT = """You are a direct-response strategist who distills raw product/brand
information into a structured brand brief YAML used by a research engine.

RULES:
- Output ONLY valid YAML — no markdown fences, no explanation, no commentary.
- Follow the EXACT field names and structure shown in the examples.
- brand_promise must be 3-5 words, ALL CAPS — the single strongest value prop.
- main_selling_points: 2-4 items, each with name, description, solves.
  "solves" is the CUSTOMER'S problem, not the feature.
- pain_points_solved: 3-6 strings written from customer perspective.
- target_customers: 3-6 identity-based segments (real people, specific).
- common_objections: 3-5 strings in the customer's own voice.
- product: a concise paragraph (2-4 sentences) covering what it is, price if known,
  key differentiators.

EXAMPLE 1:
brand_name: "SunCoast Greens"
brand_promise: "ONE SCOOP, FULL NUTRITION"

product: |
  $59/month daily greens powder with 40+ organic superfoods,
  probiotics, and adaptogens. Mixes into water or smoothies
  in seconds. No artificial sweeteners, third-party tested.

main_selling_points:
  - name: "40+ Superfoods in One Scoop"
    description: "Replaces handfuls of individual supplements with a single daily scoop"
    solves: "People overwhelmed by juggling 5-10 different supplements every morning"

  - name: "Actually Tastes Good"
    description: "Natural mint-citrus flavor that mixes clean — no chalky texture or fake sweetener aftertaste"
    solves: "People who tried greens powders before and couldn't stomach the taste"

  - name: "Third-Party Tested"
    description: "Every batch tested by independent labs for heavy metals, pesticides, and label accuracy"
    solves: "People who don't trust supplement brands making unverified health claims"

pain_points_solved:
  - "I take 6 different supplements every morning and I'm not even sure they're working"
  - "Every greens powder I've tried tastes like lawn clippings"
  - "I know I should eat more vegetables but I never hit my daily targets"
  - "I don't trust supplement brands — half of them don't contain what the label says"

target_customers:
  - "Health-conscious adults 25-45 who want better nutrition but don't have time to meal-prep"
  - "Busy professionals who skip breakfast or grab coffee and call it a meal"
  - "People already taking multiple supplements who want to simplify their routine"
  - "Fitness-minded people who eat well but know they still have nutritional gaps"
  - "Parents who want a quick nutrition boost they can take while getting kids ready"

common_objections:
  - "Greens powders taste terrible — I've tried them before"
  - "I'd rather just eat real vegetables"
  - "$59/month is expensive for a powder"
  - "How do I know it actually has what the label says?"

EXAMPLE 2:
brand_name: "DriftWell"
brand_promise: "DEEP SLEEP WITHOUT DRUGS"

product: |
  Natural sleep supplement combining magnesium glycinate, L-theanine,
  and apigenin in clinical doses. Two capsules before bed. No melatonin,
  no grogginess, no dependency. $45/month subscription or $55 one-time.
  90-day money-back guarantee. Ships free in the US.

main_selling_points:
  - name: "No Melatonin, No Grogginess"
    description: "Uses magnesium, L-theanine, and apigenin instead of melatonin — wakes up clear-headed, not groggy"
    solves: "People who take melatonin and feel hungover the next morning or worry about dependency"

  - name: "Clinical Doses, Not Pixie Dust"
    description: "Each ingredient at the dose used in peer-reviewed sleep studies — not trace amounts for label decoration"
    solves: "People burned by supplements that underdose ingredients to cut costs"

  - name: "90-Day Money-Back Guarantee"
    description: "Try it for a full 3 months — if sleep doesn't improve, full refund no questions asked"
    solves: "People hesitant to spend money on yet another supplement that might not work"

pain_points_solved:
  - "I fall asleep fine but wake up at 3am and can't get back to sleep"
  - "Melatonin knocks me out but I feel groggy and foggy the entire next day"
  - "I've tried every sleep supplement and nothing actually works long-term"
  - "I don't want to take prescription sleep medication but I'm desperate for better sleep"
  - "I lie in bed with my mind racing and can't shut my brain off"

target_customers:
  - "Adults 30-55 who have trouble staying asleep or falling asleep and want a non-prescription solution"
  - "People currently using melatonin who are unhappy with grogginess or worried about long-term use"
  - "High-stress professionals whose racing thoughts keep them awake at night"
  - "People who've tried prescription sleep aids and want to switch to something natural"
  - "Health-conscious consumers who research ingredients and want clinical-dose supplements"

common_objections:
  - "I've tried natural sleep supplements before and none of them worked"
  - "If it doesn't have melatonin, how can it actually help me sleep?"
  - "Is it safe to take every night long-term?"
  - "Why is this more expensive than melatonin gummies?"
  - "$45/month adds up — is it really worth it?"

---

Now transform the following info dump into a brand brief YAML.
Output ONLY the YAML. No fences, no explanation.

INFO DUMP:
{info_dump}
"""


async def _generate_brand_brief_yaml(info_dump: str, max_retries: int = 3) -> str:
    """Call LLM to transform raw info dump into brand brief YAML.

    Retries on rate-limit errors with exponential backoff.
    """
    prompt = _BRAND_BRIEF_PROMPT.format(info_dump=info_dump)

    last_error = None
    for attempt in range(max_retries):
        if attempt > 0:
            wait = 2 ** attempt  # 2s, 4s
            logger.info(f"Rate-limited, retrying in {wait}s (attempt {attempt + 1}/{max_retries})")
            await asyncio.sleep(wait)

        try:
            response_text = ""
            async for message in query(
                prompt=prompt,
                options=ClaudeCodeOptions(model="claude-sonnet-4-6", max_turns=3),
            ):
                if hasattr(message, "content"):
                    for block in message.content:
                        if hasattr(block, "text"):
                            response_text += block.text

        except Exception as e:
            if "Unknown message type" in str(e) and response_text:
                pass  # SDK parse warning — response already collected
            else:
                last_error = e
                continue

        if not response_text.strip():
            last_error = RuntimeError("LLM returned empty response")
            continue

        # Strip markdown fences if the LLM added them
        cleaned = response_text.strip()
        cleaned = re.sub(r"^```(?:ya?ml)?\s*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        return cleaned.strip()

    raise last_error or RuntimeError("Failed to generate brand brief after retries")


def _find_brand_path(brand):
    """Resolve and validate brand path."""
    brand_path = PROJECT_ROOT / "brands" / brand
    if not brand_path.exists():
        return None
    return brand_path


def _get_sprint_info(sprint_folder):
    """Get info about a sprint from its folder."""
    info = {"name": sprint_folder.name}

    # Check completion
    insights_final = sprint_folder / "insights_final.csv"
    if insights_final.exists():
        try:
            with open(insights_final) as f:
                lines = f.readlines()
                data_rows = len([l for l in lines[1:] if l.strip()])
                info["status"] = "completed"
                info["insights"] = data_rows
        except Exception:
            info["status"] = "unknown"
    else:
        info["status"] = "incomplete"

    # Read config
    config_path = sprint_folder / "sprint_config.txt"
    if config_path.exists():
        with open(config_path) as f:
            for line in f:
                if line.lower().strip().startswith("research direction:") or line.lower().strip().startswith("research_direction:"):
                    info["research_direction"] = line.split(":", 1)[1].strip()
                    break

    # Check run log
    log_path = sprint_folder / "_intermediate" / "run_log.txt"
    if log_path.exists():
        with open(log_path) as f:
            content = f.read()
            if "IN PROGRESS" in content:
                info["status"] = "running"

    return info


@mcp.tool()
async def create_brand(brand_slug: str, info_dump: str) -> str:
    """Create a new brand from a raw product/brand info dump.

    Takes unstructured product information and transforms it into a structured
    brand brief YAML, then sets up the brand directory so research sprints can
    be run immediately.

    Args:
        brand_slug: Lowercase identifier for the brand, no spaces
            (e.g., "suncoastgreens", "driftwell", "heatedblanket").
        info_dump: Raw text about the product/brand — can be a messy paste from
            a website, notes, Slack thread, or product brief. The engine will
            distill it into the required YAML structure (brand_name, brand_promise,
            product, main_selling_points, pain_points_solved, target_customers,
            common_objections).

    Returns:
        JSON with status, brand_slug, and the path to the created brand_brief.yaml
    """
    # Validate slug
    if not re.match(r"^[a-z][a-z0-9_-]*$", brand_slug):
        return json.dumps({
            "error": f"Invalid brand_slug: '{brand_slug}'. Must be lowercase, start with a letter, "
                     "and contain only letters, numbers, hyphens, or underscores."
        })

    # Check brand doesn't already exist
    brand_path = PROJECT_ROOT / "brands" / brand_slug
    if brand_path.exists() and (brand_path / "brand_brief.yaml").exists():
        return json.dumps({
            "error": f"Brand '{brand_slug}' already exists at {brand_path}. "
                     "Use a different slug or delete the existing brand first."
        })

    if not info_dump or len(info_dump.strip()) < 20:
        return json.dumps({
            "error": "info_dump is too short. Provide at least a paragraph of product/brand information."
        })

    try:
        # Generate the brand brief YAML via LLM
        brief_yaml = await _generate_brand_brief_yaml(info_dump)

        # Validate the YAML parses correctly
        parsed = yaml.safe_load(brief_yaml)
        if not isinstance(parsed, dict):
            return json.dumps({"error": "LLM returned invalid YAML structure. Please try again."})

        # Validate required fields
        required_fields = ["brand_name", "brand_promise", "product", "main_selling_points",
                           "pain_points_solved", "target_customers", "common_objections"]
        missing = [f for f in required_fields if f not in parsed]
        if missing:
            return json.dumps({
                "error": f"Generated brief is missing required fields: {missing}. Please try again with more detail in the info dump."
            })

        # Validate main_selling_points structure
        for sp in parsed.get("main_selling_points", []):
            if not all(k in sp for k in ("name", "description", "solves")):
                return json.dumps({
                    "error": "Each main_selling_point must have 'name', 'description', and 'solves'. "
                             "LLM output was malformed. Please try again."
                })

        # Create brand directory
        brand_path.mkdir(parents=True, exist_ok=True)

        # Write brand_brief.yaml
        brief_path = brand_path / "brand_brief.yaml"
        brief_path.write_text(brief_yaml + "\n", encoding="utf-8")

        return json.dumps({
            "status": "created",
            "brand_slug": brand_slug,
            "brand_brief_path": str(brief_path),
            "brand_name": parsed.get("brand_name", ""),
            "brand_promise": parsed.get("brand_promise", ""),
            "selling_points": len(parsed.get("main_selling_points", [])),
            "pain_points": len(parsed.get("pain_points_solved", [])),
            "target_segments": len(parsed.get("target_customers", [])),
            "objections": len(parsed.get("common_objections", [])),
            "message": f"Brand '{brand_slug}' created successfully. "
                       f"Run research sprints with: run_research_sprint(brand='{brand_slug}', directions=['your research direction'])"
        })

    except yaml.YAMLError as e:
        return json.dumps({"error": f"Failed to parse generated YAML: {str(e)}. Please try again."})
    except Exception as e:
        return json.dumps({"error": f"Failed to create brand: {str(e)}"})


@mcp.tool()
def run_research_sprint(brand: str, directions: list[str], scope: str = "standard") -> str:
    """Start one or more research sprints. Pass a single direction for one sprint,
    or multiple directions to run them in parallel with coordinated scraping.

    Parallel mode serializes Reddit scraping (to avoid rate limits) but runs
    analysis phases concurrently.

    Args:
        brand: Brand name (e.g., "suncoastgreens")
        directions: One or more research directions (e.g., ["daily greens supplements for energy"]
            or ["daily greens supplements for energy", "supplement fatigue in health-conscious adults"])
        scope: Scraping scope — "quick", "standard", or "deep" (default: "standard")

    Returns:
        Sprint key and status message
    """
    brand_path = _find_brand_path(brand)
    if not brand_path:
        return json.dumps({"error": f"Brand not found: {brand}. Available: {', '.join(list_brands())}"})

    if scope not in ("quick", "standard", "deep"):
        return json.dumps({"error": f"Invalid scope: {scope}. Use quick, standard, or deep."})

    if not directions:
        return json.dumps({"error": "At least one research direction is required."})

    # Build command — single vs parallel auto-detected
    if len(directions) == 1:
        cmd = [
            sys.executable, "engine/orchestrator.py",
            brand, directions[0],
            "--scope", scope,
        ]
        mode = "single"
    else:
        cmd = [
            sys.executable, "engine/orchestrator.py",
            brand, "--parallel",
        ] + directions + [
            "--scope", scope,
        ]
        mode = "parallel"

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )

        sprint_key = f"{brand}_{datetime.now().strftime('%H%M%S')}"
        _running_sprints[sprint_key] = {
            "process": proc,
            "brand": brand,
            "directions": directions,
            "mode": mode,
            "scope": scope,
            "started": datetime.now().isoformat(),
            "pid": proc.pid,
        }

        direction_summary = directions[0] if len(directions) == 1 else f"{len(directions)} directions"
        return json.dumps({
            "status": "started",
            "sprint_key": sprint_key,
            "brand": brand,
            "directions": directions,
            "mode": mode,
            "scope": scope,
            "pid": proc.pid,
            "message": f"Sprint started ({mode}) for {direction_summary}. Use check_sprint_status(brand='{brand}', sprint_key='{sprint_key}') to monitor progress.",
        })

    except Exception as e:
        return json.dumps({"error": f"Failed to start sprint: {str(e)}"})


@mcp.tool()
def check_sprint_status(brand: str, sprint_key: str = "") -> str:
    """Check the status of a research sprint.

    Args:
        brand: Brand name
        sprint_key: Sprint key returned by run_research_sprint. If empty, shows the most recent sprint.

    Returns:
        Status info including running/completed/failed, elapsed time, and summary stats
    """
    brand_path = _find_brand_path(brand)
    if not brand_path:
        return json.dumps({"error": f"Brand not found: {brand}"})

    # Check running process
    if sprint_key and sprint_key in _running_sprints:
        info = _running_sprints[sprint_key]
        proc = info["process"]
        poll = proc.poll()

        if poll is None:
            return json.dumps({
                "status": "running",
                "brand": brand,
                "directions": info["directions"],
                "mode": info["mode"],
                "started": info["started"],
                "pid": info["pid"],
            })
        else:
            # Process finished
            stdout = proc.stdout.read() if proc.stdout else ""
            last_lines = stdout.strip().split('\n')[-20:]

            return json.dumps({
                "status": "completed" if poll == 0 else "failed",
                "exit_code": poll,
                "brand": brand,
                "directions": info["directions"],
                "mode": info["mode"],
                "started": info["started"],
                "output_tail": '\n'.join(last_lines),
            })

    # Fall back to checking most recent sprint folder
    sprints_dir = brand_path / "sprints"
    if not sprints_dir.exists():
        return json.dumps({"status": "no_sprints", "brand": brand})

    sprint_folders = sorted(
        [d for d in sprints_dir.iterdir() if d.is_dir()],
        key=lambda d: d.name,
        reverse=True,
    )

    if not sprint_folders:
        return json.dumps({"status": "no_sprints", "brand": brand})

    latest = sprint_folders[0]
    info = _get_sprint_info(latest)

    # Add evidence stats
    try:
        info["evidence_total"] = get_evidence_count(brand)
    except Exception:
        pass

    return json.dumps(info)


@mcp.tool()
def list_brands() -> str:
    """List all available brands with brief info.

    Returns:
        List of brands with evidence counts and sprint counts
    """
    brands_dir = PROJECT_ROOT / "brands"
    if not brands_dir.exists():
        return json.dumps({"brands": [], "message": "No brands directory found"})

    brands = []
    for d in sorted(brands_dir.iterdir()):
        if d.is_dir() and (d / "brand_brief.yaml").exists():
            brand_info = {"name": d.name}

            # Evidence count
            try:
                brand_info["evidence_count"] = get_evidence_count(d.name)
            except Exception:
                brand_info["evidence_count"] = 0

            # Sprint count
            sprints_dir = d / "sprints"
            if sprints_dir.exists():
                brand_info["sprint_count"] = len([
                    s for s in sprints_dir.iterdir() if s.is_dir()
                ])
            else:
                brand_info["sprint_count"] = 0

            brands.append(brand_info)

    return json.dumps({"brands": brands})


@mcp.tool()
def list_sprints(brand: str) -> str:
    """List all sprints for a brand with their status.

    Args:
        brand: Brand name

    Returns:
        List of sprints with status, research direction, and insight count
    """
    brand_path = _find_brand_path(brand)
    if not brand_path:
        return json.dumps({"error": f"Brand not found: {brand}"})

    sprints_dir = brand_path / "sprints"
    if not sprints_dir.exists():
        return json.dumps({"brand": brand, "sprints": []})

    sprints = []
    for d in sorted(sprints_dir.iterdir()):
        if d.is_dir():
            info = _get_sprint_info(d)
            sprints.append(info)

    return json.dumps({"brand": brand, "sprints": sprints})


if __name__ == "__main__":
    mcp.run()
