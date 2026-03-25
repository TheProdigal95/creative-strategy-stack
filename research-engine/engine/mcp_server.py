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
brand_name: "Pure Plank"
brand_promise: "3-MIN MICRO-COMMITMENT"

product: |
  $149 cushioned planking board with ergonomic handles,
  built-in timer, and phone holder. Designed to make planking
  comfortable and trackable.

main_selling_points:
  - name: "Comfort Hack"
    description: "Cushioned padding + non-slip handles removes elbow pain and slipping"
    solves: "People quit planking at 10-15 seconds due to discomfort"

  - name: "3 Minutes, No Excuses"
    description: "Only 3 minutes daily kills the time objection"
    solves: "People think they don't have time for exercise"

  - name: "Living Proof Founders"
    description: "Adam Copeland (Edge) + Jay Reso (Christian Cage), both 51, returned to peak shape after injuries"
    solves: "Skepticism that older/injured people can benefit"

pain_points_solved:
  - "People quit planking due to elbow/wrist discomfort on hard floors"
  - "People believe they don't have time for exercise"
  - "People think they're too old or injured to start"
  - "People try planks, plateau at 15-60 seconds, and give up"

target_customers:
  - "Busy adults who want core strength but can't commit to gym"
  - "Men/dads who want to lose belly fat"
  - "People who've tried and quit exercise programs"
  - "Office workers with back pain"
  - "People 40+ who think they're past their fitness prime"

common_objections:
  - "Planks don't burn belly fat"
  - "I can just plank on the floor for free"
  - "3 minutes can't do anything meaningful"
  - "I'm too heavy/old/injured to plank"

EXAMPLE 2:
brand_name: "WeightRx"
brand_promise: "AFFORDABLE GLP-1 DELIVERED FAST"

product: |
  Compounded GLP-1 weight loss medications (semaglutide + B12 and tirzepatide)
  delivered to your door within 48 hours. 100% online telehealth — same-day
  doctor visits and prescriptions. Semaglutide starts at $99/mo, tirzepatide
  at $83/mo. No insurance needed, no long-term contracts, cancel anytime.
  Ships FedEx overnight on ice from licensed U.S. compounding pharmacies.
  30-day money-back guarantee.

main_selling_points:
  - name: "Lowest Price in Market"
    description: "Semaglutide at $99/mo and tirzepatide at $83/mo — saving over $1,000/mo vs brand-name Wegovy or Zepbound"
    solves: "People who want GLP-1 medication but can't afford $1,300-1,600/mo for brand-name drugs and don't have insurance coverage"

  - name: "48-Hour Delivery"
    description: "Same-day doctor visit, same-day prescription, medication at your door within 48 hours via FedEx overnight"
    solves: "People frustrated by long wait times, pharmacy trips, appointment backlogs, and 5-7 day shipping from other telehealth providers"

  - name: "30-Day Money-Back Guarantee"
    description: "Results in 30 days or full refund — rare risk-reversal in telehealth weight loss"
    solves: "People hesitant to spend money on something they're not sure will work for them"

  - name: "Easy Switcher Transfer"
    description: "Accepts patients already on semaglutide or tirzepatide at any dose from other providers — no restart required"
    solves: "People unhappy with their current GLP-1 provider who don't want the hassle of starting over or losing their current dose"

pain_points_solved:
  - "I want to try GLP-1 medication but it costs over $1,000 a month and my insurance won't cover it"
  - "I've been trying to get an appointment for weeks and my pharmacy keeps saying it's on backorder"
  - "I'm paying $300-400/month at my current provider and the service is terrible — slow responses, shipping delays, can't reach anyone"
  - "I've tried every diet, every app, every program — nothing sticks and I'm exhausted from trying"
  - "I want to switch from semaglutide to tirzepatide because I've plateaued or the side effects are too much"
  - "I don't want to deal with insurance pre-authorizations, prior auths, or step therapy requirements"

target_customers:
  - "Women 30-55 who've heard about GLP-1s through social media or friends and want an affordable way to start"
  - "People already on semaglutide from Hims, Hers, Ro, or other providers who are frustrated with price, service, or results"
  - "People who want to switch from semaglutide to tirzepatide for better results or fewer side effects"
  - "Diet-fatigued people who've tried everything — keto, Noom, Weight Watchers, intermittent fasting — and are ready for medical intervention"
  - "People with pre-diabetes, high A1C, high cholesterol, or other weight-related health scares who need to lose weight now"
  - "Budget-conscious deal seekers who compare prices and want the most medication for their money"

common_objections:
  - "Compounded medication isn't the same as the real thing — is it safe?"
  - "This price seems too good to be true — what's the catch?"
  - "I don't trust online telehealth — will I actually talk to a real doctor?"
  - "What happens when I stop taking it — won't I just gain it all back?"
  - "I've heard horror stories about side effects like nausea and vomiting"

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
            (e.g., "pureplank", "weightrx", "heatedblanket").
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
        brand: Brand name (e.g., "pureplank")
        directions: One or more research directions (e.g., ["back pain from desk jobs"]
            or ["back pain from desk jobs", "weight loss for busy dads"])
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
