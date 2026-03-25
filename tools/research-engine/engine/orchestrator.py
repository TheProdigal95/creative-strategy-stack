#!/usr/bin/env python3
"""
Research Engine Orchestrator
Runs the complete pipeline from research direction to insights.

Usage:
    python3 engine/orchestrator.py <brand> "<research_direction>" [options]
    python3 engine/orchestrator.py <brand> --from-themes [--sprint "<name>"]
    python3 engine/orchestrator.py <brand> --from-scoring [--sprint "<name>"]

    # Parallel mode — multiple research directions at once
    python3 engine/orchestrator.py <brand> --parallel "direction 1" "direction 2" [options]

Examples:
    python3 engine/orchestrator.py mybrand "no time for exercise"
    python3 engine/orchestrator.py mybrand "back pain desk workers" --scope deep
    python3 engine/orchestrator.py mybrand --from-themes
    python3 engine/orchestrator.py mybrand --parallel "back pain" "weight loss" --scope quick
"""

import sys
import argparse
import subprocess
import asyncio
import threading
import time
import re
import os
import signal
from pathlib import Path
from datetime import datetime
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from claude_code_sdk import query, ClaudeCodeOptions
from engine.evidence_db import db_path, get_evidence_count, init_db


# Phase definitions: (name, script_path, retry_eligible)
PHASES = [
    ("Step 01: Retrieval Planner", "engine/step01_retrieval_planner.py", True),       # 0
    ("Step 02: Reddit Scraper (Stage 1)", "engine/step02_reddit_scraper.py", False),   # 1
    ("Step 02: Reddit Scraper (Stage 2)", "engine/step02_reddit_scraper.py", False),   # 2
    ("Step 03+04: Transform + Verify", "engine/step03_reddit_to_evidence.py", False),  # 3
    ("Step 05: Brand-Fit Scorer", "engine/step05_brand_fit_scorer.py", True),          # 4
    ("Step 06: Theme Discovery", "engine/step06_theme_discovery.py", True),            # 5
    ("Step 07: Persona Normalization", "engine/step07_persona_normalizer.py", True),   # 6
    ("Step 08: Evidence Matching", "engine/step08_evidence_matcher.py", False),        # 7
    ("Step 09: Insight Writer", "engine/step09_insight_writer.py", True),              # 8
    ("Step 10: VoC Analyzer", "engine/step10_voc_analyzer.py", True),                  # 9
    ("Step 12: Language Miner", "engine/step12_language_miner.py", True),              # 10
]

# Phase index for Step 12 (Language Miner) — runs concurrently after Step 05
LANG_MINER_PHASE = 10

MAX_RETRIES = 2


class OrchestrationError(Exception):
    """Custom exception for orchestration failures."""
    pass


def format_time(seconds):
    """Format seconds into human-readable time."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


def get_existing_sprints(brand_path):
    """Get list of existing sprint folders with their numbers."""
    sprints_dir = brand_path / "sprints"
    if not sprints_dir.exists():
        return []

    sprints = []
    for folder in sprints_dir.iterdir():
        if folder.is_dir():
            # Support both formats: "01 - Name" and "01_name"
            match = re.match(r'^(\d+)\s*[-_]\s*(.+)$', folder.name)
            if match:
                num = int(match.group(1))
                name = match.group(2)
                sprints.append((num, name, folder.name))

    return sorted(sprints, key=lambda x: x[0])


async def generate_sprint_folder_name(research_direction):
    """Use LLM to generate clean folder name from research direction."""
    prompt_text = f"""Generate a short, human-readable folder name for a research sprint.

Research direction: "{research_direction}"

Rules:
- Title Case (capitalize each word)
- 3-6 words maximum
- No special characters except spaces
- Capture the core topic, not every detail
- Max 50 characters

Examples:
- "weight loss for men especially dads" → "Weight Loss for Men and Dads"
- "back pain from desk jobs and sedentary work" → "Back Pain from Desk Jobs"
- "no time for exercise busy schedule" → "Time Scarcity for Busy People"

Return ONLY the folder name, nothing else."""

    folder_name = ""
    try:
        async for message in query(
            prompt=prompt_text,
            options=ClaudeCodeOptions(model="claude-haiku-4-5-20251001", max_turns=1)
        ):
            if hasattr(message, 'content'):
                for block in message.content:
                    if hasattr(block, 'text'):
                        folder_name += block.text
    except Exception as e:
        if "Unknown message type" in str(e) and folder_name:
            pass  # SDK parse warning — response already collected
        else:
            raise

    return folder_name.strip()


def validate_preflight(brand, from_scoring=False, from_themes=False, sprint_folder=None):
    """Validate all requirements before running pipeline."""
    errors = []

    # Check brand brief
    brand_brief_path = Path(f"brands/{brand}/brand_brief.yaml")
    if not brand_brief_path.exists():
        errors.append(f"Brand brief not found: {brand_brief_path}")

    # Check all required scripts
    required_scripts = [
        "engine/step01_retrieval_planner.py",
        "engine/step02_reddit_scraper.py",
        "engine/step03_reddit_to_evidence.py",
        "engine/step04_merge_evidence.py",
        "engine/step05_brand_fit_scorer.py",
        "engine/step06_theme_discovery.py",
        "engine/step07_persona_normalizer.py",
        "engine/step08_evidence_matcher.py",
        "engine/step09_insight_writer.py",
        "engine/step10_voc_analyzer.py",
        "engine/step12_language_miner.py",
    ]

    for script in required_scripts:
        if not Path(script).exists():
            errors.append(f"Required script not found: {script}")

    # Additional checks for resume modes
    if from_scoring or from_themes:
        evidence_db = db_path(brand)
        if not evidence_db.exists():
            errors.append(f"Evidence database not found: {evidence_db}")
        else:
            try:
                count = get_evidence_count(brand)
                if count == 0:
                    errors.append(f"Evidence database is empty: {evidence_db}")
            except Exception as e:
                errors.append(f"Evidence database error: {e}")

    if from_themes and sprint_folder:
        evidence_filtered = sprint_folder / "_intermediate" / "evidence_filtered.csv"
        if not evidence_filtered.exists():
            errors.append(f"Filtered evidence not found: {evidence_filtered}")

    if errors:
        print("Pre-flight validation failed:\n")
        for error in errors:
            print(f"  ✗ {error}")
        print()
        sys.exit(1)


def check_sprint_completed(sprint_folder):
    """Check if sprint has already been completed."""
    insights_final = sprint_folder / "insights_final.csv"
    if not insights_final.exists():
        return False, 0

    # Count data rows (excluding header)
    try:
        with open(insights_final) as f:
            lines = f.readlines()
            data_rows = len([l for l in lines[1:] if l.strip()])
            return data_rows > 0, data_rows
    except Exception:
        return False, 0


def read_sprint_config(sprint_folder):
    """Read research direction from sprint_config.txt."""
    config_path = sprint_folder / "sprint_config.txt"
    if not config_path.exists():
        return None, None

    with open(config_path) as f:
        content = f.read()

    research_direction = None
    scope = "standard"

    for line in content.split('\n'):
        line_lower = line.lower().strip()
        if line_lower.startswith("research direction:") or line_lower.startswith("research_direction:"):
            # Handle both "Research Direction:" and "research_direction:" formats
            research_direction = line.split(":", 1)[1].strip()
        elif line_lower.startswith("scope:"):
            scope = line.split(":", 1)[1].strip()

    return research_direction, scope


def create_run_log(sprint_folder, brand, sprint_name, research_direction, scope):
    """Initialize run log file."""
    intermediate_dir = sprint_folder / "_intermediate"
    intermediate_dir.mkdir(exist_ok=True)
    log_path = intermediate_dir / "run_log.txt"

    content = f"""RESEARCH ENGINE RUN LOG
=======================
Brand: {brand}
Sprint: {sprint_name}
Research Direction: {research_direction}
Scope: {scope}
Started: {datetime.now().isoformat()}
Completed: IN PROGRESS

EXECUTION
---------
"""

    with open(log_path, 'w') as f:
        f.write(content)

    return log_path


def append_to_log(log_path, message):
    """Append timestamped message to run log."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    with open(log_path, 'a') as f:
        f.write(f"[{timestamp}] {message}\n")


def update_log_completion(log_path, status, total_time, stats=None):
    """Update log with completion status."""
    with open(log_path, 'r') as f:
        content = f.read()

    # Replace "IN PROGRESS" with completion time
    content = content.replace(
        "Completed: IN PROGRESS",
        f"Completed: {datetime.now().isoformat()}"
    )

    # Add result section
    result = f"\n\nRESULT\n------\nStatus: {status}\nTotal time: {format_time(total_time)}\n"

    if stats:
        result += f"Evidence: {stats.get('evidence_total', 'N/A')} pieces"
        if stats.get('evidence_new'):
            result += f" ({stats['evidence_new']} new)"
        result += f"\nThemes: {stats.get('themes', 'N/A')}\n"
        result += f"Insights: {stats.get('insights', 'N/A')}\n"

    content += result

    with open(log_path, 'w') as f:
        f.write(content)


def build_phase_command(phase_idx, brand, sprint_name, research_direction, scope):
    """Build command for a specific phase."""
    python = sys.executable
    if phase_idx == 0:  # Step 01: Retrieval Planner
        return [python, "engine/step01_retrieval_planner.py", brand, sprint_name, research_direction, "--scope", scope]
    elif phase_idx == 1:  # Step 02: Stage 1
        return [python, "engine/step02_reddit_scraper.py", brand, sprint_name]
    elif phase_idx == 2:  # Step 02: Stage 2
        return [python, "engine/step02_reddit_scraper.py", brand, sprint_name, "--stage2"]
    elif phase_idx == 3:  # Step 03+04: Transform + Verify
        return [python, "engine/step03_reddit_to_evidence.py", brand, sprint_name]
    elif phase_idx == 4:  # Step 05
        return [python, "engine/step05_brand_fit_scorer.py", brand, sprint_name]
    elif phase_idx == 5:  # Step 06
        return [python, "engine/step06_theme_discovery.py", brand, sprint_name]
    elif phase_idx == 6:  # Step 07
        return [python, "engine/step07_persona_normalizer.py", brand, sprint_name]
    elif phase_idx == 7:  # Step 08
        return [python, "engine/step08_evidence_matcher.py", brand, sprint_name]
    elif phase_idx == 8:  # Step 09
        return [python, "engine/step09_insight_writer.py", brand, sprint_name]
    elif phase_idx == 9:  # Step 10
        return [python, "engine/step10_voc_analyzer.py", brand, sprint_name]
    elif phase_idx == 10:  # Step 12: Language Miner
        return [python, "engine/step12_language_miner.py", brand, sprint_name]
    else:
        raise ValueError(f"Unknown phase index: {phase_idx}")


def _run_subprocess(cmd, timeout=1800):
    """Run a subprocess with timeout. Returns (returncode, stdout, stderr, elapsed)."""
    start_time = time.time()

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,  # own process group
    )

    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        # Kill entire process group (child + grandchildren)
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except OSError:
            pass
        # Give 10s for graceful shutdown, then SIGKILL
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass
            proc.wait()

        elapsed = time.time() - start_time
        return -1, "", f"Phase timed out after {format_time(elapsed)}", elapsed

    elapsed = time.time() - start_time
    return proc.returncode, stdout, stderr, elapsed


def run_phase(phase_idx, brand, sprint_name, research_direction, scope, log_path, verbose):
    """Run a single phase with retry logic.

    Uses Popen with start_new_session=True so the child and all its
    descendants (e.g. claude CLI) run in their own process group.
    On timeout we kill the entire group — no zombie grandchildren.
    """
    phase_name, script_path, retry_eligible = PHASES[phase_idx]

    attempts = 0
    max_attempts = MAX_RETRIES + 1 if retry_eligible else 1

    while attempts < max_attempts:
        attempts += 1

        # Build command
        cmd = build_phase_command(phase_idx, brand, sprint_name, research_direction, scope)

        if verbose:
            print(f"\nExecuting: {' '.join(cmd)}")

        if attempts > 1:
            append_to_log(log_path, f"Retry {attempts-1}/{MAX_RETRIES} for {phase_name}")
        else:
            append_to_log(log_path, f"Starting {phase_name}")

        returncode, stdout, stderr, elapsed = _run_subprocess(cmd)

        if returncode == -1:
            # Timeout
            append_to_log(log_path, stderr)  # contains timeout message
            if attempts >= max_attempts:
                return elapsed, stderr
            continue  # retry

        if returncode == 0:
            # For merged Step 03+04: also run Step 04 (verify) inline
            if phase_idx == 3:
                verify_cmd = [sys.executable, "engine/step04_merge_evidence.py", brand]
                if verbose:
                    print(f"\nExecuting (verify): {' '.join(verify_cmd)}")
                v_rc, v_stdout, v_stderr, v_elapsed = _run_subprocess(verify_cmd, timeout=120)
                elapsed += v_elapsed
                if v_rc != 0:
                    error_msg = v_stderr if v_stderr else v_stdout
                    append_to_log(log_path, f"{phase_name} verify step failed")
                    append_to_log(log_path, f"Error: {error_msg[:2000]}")
                    if attempts >= max_attempts:
                        return elapsed, error_msg
                    continue  # retry

            # Success
            if attempts > 1:
                append_to_log(log_path, f"{phase_name} completed in {format_time(elapsed)} (after {attempts-1} retries)")
            else:
                append_to_log(log_path, f"{phase_name} completed in {format_time(elapsed)}")

            if verbose and stdout:
                print("\nOutput (first 50 lines):")
                lines = stdout.split('\n')[:50]
                print('\n'.join(lines))

            return elapsed, None
        else:
            # Failure
            error_msg = stderr if stderr else stdout
            append_to_log(log_path, f"{phase_name} failed (attempt {attempts}/{max_attempts})")
            append_to_log(log_path, f"Error: {error_msg[:2000]}")

            if attempts >= max_attempts:
                # Out of retries
                return elapsed, error_msg
            # Otherwise, retry

    # Should not reach here
    return 0, "Unknown error"


def get_phase_error_advice(phase_idx):
    """Get context-specific error advice based on which phase failed."""
    advice = {
        0: ("LLM error or network issue", "Just retry, usually transient"),
        1: ("Reddit rate limiting or network issue", "Wait a few minutes and retry"),
        2: ("Reddit rate limiting or network issue", "Wait a few minutes and retry"),
        3: ("No data in reddit_raw.jsonl or DB issue", "Check if scraper collected anything in sprint _intermediate/"),
        4: ("Not enough evidence passing filter", "Broaden research direction or use --scope deep"),
        5: ("LLM JSON error OR not enough filtered evidence", "Check evidence_filtered.csv row count"),
        6: ("LLM error processing personas", "Retry, usually transient"),
        7: ("themes_discovered.json malformed", "Check Phase 1A output"),
        8: ("LLM error writing insights", "Retry, usually transient"),
        9: ("LLM error analyzing VoC", "Retry, usually transient"),
        10: ("LLM error mining language patterns", "Retry, usually transient"),
    }

    return advice.get(phase_idx, ("Unknown error", "Check run_log.txt for details"))


def collect_stats(brand, sprint_folder):
    """Collect statistics for final report."""
    stats = {}

    try:
        # Evidence total from SQLite
        try:
            stats['evidence_total'] = get_evidence_count(brand)
        except Exception:
            pass

        # Themes
        insights_final = sprint_folder / "insights_final.csv"
        if insights_final.exists():
            with open(insights_final) as f:
                import csv
                reader = csv.DictReader(f)
                rows = list(reader)
                stats['insights'] = len(rows)
                # Count unique themes
                themes = set(row.get('theme', '') for row in rows)
                stats['themes'] = len(themes)

    except Exception as e:
        # Don't fail on stats collection
        pass

    return stats


def merge_voc_into_csv(sprint_folder, log_path=None):
    """Merge voc_analysis.json into insights_final.csv after concurrent Steps 09+10.

    Step 10 writes VoC results as JSON; this merges them into the CSV that Step 09 wrote.
    Safe to call even if files don't exist yet (no-op).
    """
    import pandas as pd

    voc_json_path = Path(sprint_folder) / "_intermediate" / "voc_analysis.json"
    insights_csv_path = Path(sprint_folder) / "insights_final.csv"

    if not voc_json_path.exists() or not insights_csv_path.exists():
        return

    try:
        with open(voc_json_path) as f:
            voc_data = json.load(f)
        df = pd.read_csv(insights_csv_path)

        voc_values = []
        for _, row in df.iterrows():
            insight_text = row['Insight']
            voc = voc_data.get(insight_text)
            if voc:
                parts = [f'- "{q}"' for q in voc.get('quotes', [])]
                if voc.get('general'):
                    parts.append('')
                    parts.append(f"General: {voc['general']}")
                voc_values.append('\n'.join(parts))
            else:
                voc_values.append('VoC analysis failed - check logs')

        df['VoC'] = voc_values
        df['Keep'] = ''
        df.to_csv(insights_csv_path, index=False)

        if log_path:
            append_to_log(log_path, "Merged VoC data into insights_final.csv")
    except Exception as e:
        if log_path:
            append_to_log(log_path, f"Warning: VoC merge failed: {e}")


# ── Parallel execution ──────────────────────────────────────────────

# Phase groups for parallel execution:
#   Scrape phases (0-3): Steps 01-04 — serialized due to Reddit rate limits
#   Analysis phases (4-10): Steps 05-12 — safe to run concurrently per-sprint
SCRAPE_PHASES = range(0, 4)    # Steps 01 through 03+04
ANALYSIS_PHASES = range(4, 11)  # Steps 05 through 12


async def _run_subprocess_async(cmd, timeout=1800):
    """Run a subprocess asynchronously with timeout. Returns (returncode, stdout, stderr, elapsed)."""
    start_time = time.time()

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True,  # own process group
    )

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        # Kill entire process group (child + grandchildren)
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except OSError:
            pass
        # Give 10s for graceful shutdown, then SIGKILL
        await asyncio.sleep(10)
        if proc.returncode is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass
        try:
            await proc.communicate()
        except Exception:
            pass

        elapsed = time.time() - start_time
        return -1, "", f"Phase timed out after {format_time(elapsed)}", elapsed

    elapsed = time.time() - start_time
    stdout_text = stdout.decode() if stdout else ""
    stderr_text = stderr.decode() if stderr else ""
    return proc.returncode, stdout_text, stderr_text, elapsed


async def run_phase_async(phase_idx, brand, sprint_name, research_direction, scope, log_path, verbose=False):
    """Run a single phase as an async subprocess with retry logic.

    Uses start_new_session=True so the child and all its descendants
    run in their own process group. On timeout we kill the entire group.
    """
    phase_name, script_path, retry_eligible = PHASES[phase_idx]
    max_attempts = MAX_RETRIES + 1 if retry_eligible else 1
    attempts = 0

    while attempts < max_attempts:
        attempts += 1

        cmd = build_phase_command(phase_idx, brand, sprint_name, research_direction, scope)

        if attempts > 1:
            append_to_log(log_path, f"Retry {attempts-1}/{MAX_RETRIES} for {phase_name}")
        else:
            append_to_log(log_path, f"Starting {phase_name}")

        returncode, stdout_text, stderr_text, elapsed = await _run_subprocess_async(cmd)

        if returncode == -1:
            # Timeout
            append_to_log(log_path, stderr_text)
            if attempts >= max_attempts:
                return elapsed, stderr_text
            continue

        if returncode == 0:
            # For merged Step 03+04: also run Step 04 (verify) inline
            if phase_idx == 3:
                verify_cmd = [sys.executable, "engine/step04_merge_evidence.py", brand]
                v_rc, v_stdout, v_stderr, v_elapsed = await _run_subprocess_async(verify_cmd, timeout=120)
                elapsed += v_elapsed
                if v_rc != 0:
                    error_msg = v_stderr if v_stderr else v_stdout
                    append_to_log(log_path, f"{phase_name} verify step failed")
                    append_to_log(log_path, f"Error: {error_msg[:2000]}")
                    if attempts >= max_attempts:
                        return elapsed, error_msg
                    continue  # retry

            # Success
            if attempts > 1:
                append_to_log(log_path, f"{phase_name} completed in {format_time(elapsed)} (after {attempts-1} retries)")
            else:
                append_to_log(log_path, f"{phase_name} completed in {format_time(elapsed)}")
            return elapsed, None
        else:
            error_msg = stderr_text if stderr_text else stdout_text
            append_to_log(log_path, f"{phase_name} failed (attempt {attempts}/{max_attempts})")
            append_to_log(log_path, f"Error: {error_msg[:2000]}")

            if attempts >= max_attempts:
                return elapsed, error_msg

    return 0, "Unknown error"


async def run_sprint(brand, research_direction, scope, sprint_name, sprint_folder,
                     scrape_semaphore, analysis_semaphore, verbose=False):
    """Run a full pipeline for one sprint, using semaphores to control concurrency.

    Returns: (sprint_name, success, total_time, stats, error_info)
    """
    log_path = create_run_log(sprint_folder, brand, sprint_name, research_direction, scope)
    pipeline_start = time.time()

    total_phases = len(PHASES)

    # Scrape phases — acquire scrape semaphore (serialized)
    async with scrape_semaphore:
        print(f"  [{sprint_name}] Starting scrape phases...")
        for i in SCRAPE_PHASES:
            phase_name = PHASES[i][0]
            elapsed, error = await run_phase_async(i, brand, sprint_name, research_direction, scope, log_path, verbose)

            if error:
                total_time = time.time() - pipeline_start
                update_log_completion(log_path, f"FAILED at {phase_name}", total_time)
                return (sprint_name, False, total_time, None, (i, phase_name, error))

            print(f"  [{sprint_name}] {phase_name:45} done ({format_time(elapsed)})")

    # Analysis phases — acquire analysis semaphore
    # Steps 09+10 (phases 8+9) run concurrently; Step 12 (phase 10) runs concurrently after Step 05
    STEP09 = 8
    STEP10 = 9
    STEP12 = LANG_MINER_PHASE  # 10
    concurrent_set = {STEP09, STEP10, STEP12}

    async with analysis_semaphore:
        print(f"  [{sprint_name}] Starting analysis phases...")

        # Run phases 4-7 sequentially (Steps 05-08), launch Step 12 after Step 05
        lang_miner_task = None
        for i in ANALYSIS_PHASES:
            if i in concurrent_set:
                continue

            phase_name = PHASES[i][0]
            elapsed, error = await run_phase_async(i, brand, sprint_name, research_direction, scope, log_path, verbose)

            if error:
                total_time = time.time() - pipeline_start
                update_log_completion(log_path, f"FAILED at {phase_name}", total_time)
                return (sprint_name, False, total_time, None, (i, phase_name, error))

            print(f"  [{sprint_name}] {phase_name:45} done ({format_time(elapsed)})")

            # Launch Step 12 concurrently after Step 05 (phase 4)
            if i == 4 and STEP12 in range(ANALYSIS_PHASES.start, ANALYSIS_PHASES.stop):
                lang_miner_task = asyncio.create_task(
                    run_phase_async(STEP12, brand, sprint_name, research_direction, scope, log_path, verbose)
                )

        # Run Steps 09+10 concurrently
        results_09_10 = await asyncio.gather(
            run_phase_async(STEP09, brand, sprint_name, research_direction, scope, log_path, verbose),
            run_phase_async(STEP10, brand, sprint_name, research_direction, scope, log_path, verbose),
        )

        for idx, (elapsed, error) in zip([STEP09, STEP10], results_09_10):
            phase_name = PHASES[idx][0]
            if error:
                total_time = time.time() - pipeline_start
                update_log_completion(log_path, f"FAILED at {phase_name}", total_time)
                return (sprint_name, False, total_time, None, (idx, phase_name, error))
            print(f"  [{sprint_name}] {phase_name:45} done ({format_time(elapsed)})")

        # Merge VoC data into insights_final.csv
        merge_voc_into_csv(sprint_folder, log_path)

        # Wait for Step 12 if launched
        if lang_miner_task:
            elapsed, error = await lang_miner_task
            phase_name = PHASES[STEP12][0]
            if error:
                total_time = time.time() - pipeline_start
                update_log_completion(log_path, f"FAILED at {phase_name}", total_time)
                return (sprint_name, False, total_time, None, (STEP12, phase_name, error))
            print(f"  [{sprint_name}] {phase_name:45} done ({format_time(elapsed)})")

    total_time = time.time() - pipeline_start
    stats = collect_stats(brand, sprint_folder)
    update_log_completion(log_path, "SUCCESS", total_time, stats)

    return (sprint_name, True, total_time, stats, None)


async def run_parallel(brand, directions, scope, verbose=False,
                       max_concurrent=2, scrape_concurrent=1):
    """Run multiple research directions in parallel.

    Args:
        brand: Brand name
        directions: List of research direction strings
        scope: Scraping scope
        verbose: Verbose output
        max_concurrent: Max concurrent analysis phases
        scrape_concurrent: Max concurrent scrape phases (default 1 for Reddit rate limits)
    """
    brand_path = Path(f"brands/{brand}")

    # Initialize evidence DB
    init_db(brand)

    # Validate brand
    validate_preflight(brand)

    # Create sprint folders for all directions
    existing_sprints = get_existing_sprints(brand_path)
    next_num = 1 if not existing_sprints else existing_sprints[-1][0] + 1

    sprint_configs = []
    print("Generating sprint names...")
    for i, direction in enumerate(directions):
        folder_name_part = await generate_sprint_folder_name(direction)
        sprint_name = f"{next_num + i:02d} - {folder_name_part}"
        sprint_folder = brand_path / "sprints" / sprint_name
        sprint_folder.mkdir(parents=True, exist_ok=True)
        sprint_configs.append((direction, sprint_name, sprint_folder))
        print(f"  {sprint_name}: \"{direction}\"")

    # Create semaphores
    scrape_semaphore = asyncio.Semaphore(scrape_concurrent)
    analysis_semaphore = asyncio.Semaphore(max_concurrent)

    # Print header
    print()
    print("=" * 70)
    print(f" RESEARCH ENGINE — {brand} — PARALLEL MODE")
    print(f" Sprints: {len(directions)}")
    print(f" Scope: {scope}")
    print(f" Concurrency: scrape={scrape_concurrent}, analysis={max_concurrent}")
    print("=" * 70)
    print()

    pipeline_start = time.time()

    # Launch all sprints as concurrent tasks
    tasks = []
    for direction, sprint_name, sprint_folder in sprint_configs:
        task = asyncio.create_task(
            run_sprint(
                brand, direction, scope, sprint_name, sprint_folder,
                scrape_semaphore, analysis_semaphore, verbose
            )
        )
        tasks.append(task)

    # Wait for all to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)

    total_time = time.time() - pipeline_start

    # Print results
    print()
    print("=" * 70)
    print(f" PARALLEL EXECUTION COMPLETE")
    print("=" * 70)
    print(f" Total time: {format_time(total_time)}")
    print()

    any_failed = False
    for result in results:
        if isinstance(result, Exception):
            print(f" ERROR: {result}")
            any_failed = True
            continue

        sprint_name, success, sprint_time, stats, error_info = result
        if success:
            insights = stats.get('insights', '?') if stats else '?'
            print(f" OK  {sprint_name:45} {format_time(sprint_time):>8}  ({insights} insights)")
        else:
            phase_idx, phase_name, error = error_info
            print(f" FAIL  {sprint_name:43} {format_time(sprint_time):>8}  (failed at {phase_name})")
            any_failed = True

    print()

    total_evidence = get_evidence_count(brand)
    print(f" Total evidence in DB: {total_evidence:,}")
    print("=" * 70)

    if any_failed:
        sys.exit(1)


async def main():
    parser = argparse.ArgumentParser(
        description="Research Engine Orchestrator - Run complete pipeline"
    )
    parser.add_argument('brand', help='Brand name (e.g., mybrand)')
    parser.add_argument('research_direction', nargs='*', help='Research direction(s). Multiple allowed with --parallel.')
    parser.add_argument('--scope', choices=['quick', 'standard', 'deep'], default='standard',
                        help='Thread count scope (default: standard)')
    parser.add_argument('--verbose', action='store_true', help='Show detailed progress')
    parser.add_argument('--from-scoring', action='store_true', help='Resume from Phase 2 (skip scraping)')
    parser.add_argument('--from-themes', action='store_true', help='Resume from Phase 1A (skip scraping+scoring)')
    parser.add_argument('--from-step', type=int, choices=[7, 8, 9], help='Resume from a specific step (7=Persona, 8=Evidence Match, 9=Insight Writer)')
    parser.add_argument('--sprint', help='Specific sprint to resume (default: most recent)')
    parser.add_argument('--parallel', action='store_true',
                        help='Run multiple research directions in parallel')
    parser.add_argument('--max-concurrent', type=int, default=2,
                        help='Max concurrent analysis phases in parallel mode (default: 2)')
    parser.add_argument('--scrape-concurrent', type=int, default=1,
                        help='Max concurrent scrape phases in parallel mode (default: 1)')

    args = parser.parse_args()

    # ── Parallel mode ──
    if args.parallel:
        if not args.research_direction or len(args.research_direction) < 2:
            print("Error: --parallel requires at least 2 research directions")
            print('Usage: python3 engine/orchestrator.py <brand> --parallel "direction 1" "direction 2"')
            sys.exit(1)

        await run_parallel(
            brand=args.brand,
            directions=args.research_direction,
            scope=args.scope,
            verbose=args.verbose,
            max_concurrent=args.max_concurrent,
            scrape_concurrent=args.scrape_concurrent,
        )
        return

    # ── Single sprint mode ──
    # Flatten research_direction list to single string
    research_direction_str = args.research_direction[0] if args.research_direction else None

    # Validate arguments
    resume_mode = args.from_scoring or args.from_themes or args.from_step

    if not resume_mode and not research_direction_str:
        print("Error: research_direction required for new sprints")
        print("Usage: python3 engine/orchestrator.py <brand> \"<research_direction>\"")
        sys.exit(1)

    if resume_mode and research_direction_str:
        print("Error: research_direction not needed when resuming (--from-scoring or --from-themes)")
        sys.exit(1)

    brand = args.brand
    brand_path = Path(f"brands/{brand}")

    if not brand_path.exists():
        print(f"Error: Brand folder not found: {brand_path}")
        sys.exit(1)

    # Initialize evidence DB (creates tables if needed)
    init_db(brand)

    # Pre-flight validation
    validate_preflight(brand, args.from_scoring, args.from_themes or args.from_step)

    # Determine sprint folder
    if resume_mode:
        existing_sprints = get_existing_sprints(brand_path)

        if args.sprint:
            # Find matching sprint
            sprint_folder = None
            for num, name, folder_name in existing_sprints:
                if args.sprint in folder_name:
                    sprint_folder = brand_path / "sprints" / folder_name
                    sprint_name = folder_name
                    break

            if not sprint_folder:
                print(f"Error: Sprint not found: {args.sprint}")
                print(f"Available sprints:")
                for num, name, folder_name in existing_sprints:
                    print(f"  - {folder_name}")
                sys.exit(1)
        else:
            # Use most recent
            if not existing_sprints:
                print(f"Error: No existing sprints found in {brand_path / 'sprints'}")
                sys.exit(1)

            num, name, folder_name = existing_sprints[-1]
            sprint_folder = brand_path / "sprints" / folder_name
            sprint_name = folder_name

        # Check if completed
        is_completed, insight_count = check_sprint_completed(sprint_folder)
        if is_completed:
            print(f"\n⚠️  Sprint \"{sprint_name}\" already completed with {insight_count} insights.\n")
            print("Overwriting will delete these results.")
            print("→ To preserve them, run without --from-X flags to create a new sprint.\n")
            response = input("Overwrite anyway? (y/n): ")
            if response.lower() != 'y':
                print("\nCancelled.")
                sys.exit(0)

        # Read config
        research_direction, scope = read_sprint_config(sprint_folder)
        if not research_direction:
            print(f"Error: Could not read research_direction from {sprint_folder / 'sprint_config.txt'}")
            sys.exit(1)

        # Override scope if specified
        if args.scope != 'standard':
            scope = args.scope

    else:
        # Create new sprint
        existing_sprints = get_existing_sprints(brand_path)
        next_num = 1 if not existing_sprints else existing_sprints[-1][0] + 1

        # Generate folder name with LLM
        print("Generating sprint folder name...")
        folder_name_part = await generate_sprint_folder_name(research_direction_str)
        sprint_name = f"{next_num:02d} - {folder_name_part}"
        sprint_folder = brand_path / "sprints" / sprint_name

        # Create folder
        sprint_folder.mkdir(parents=True, exist_ok=True)

        research_direction = research_direction_str
        scope = args.scope

    # Determine start phase
    # Step-to-phase mapping: step 7→phase 6, step 8→phase 7, step 9→phase 8
    STEP_TO_PHASE = {7: 6, 8: 7, 9: 8}

    if args.from_step:
        start_phase = STEP_TO_PHASE[args.from_step]
        total_phases = len(PHASES)
        step_name = PHASES[start_phase][0]
        resume_note = f"Resuming from {step_name} (--from-step {args.from_step})"
    elif args.from_themes:
        start_phase = 5  # Step 06: Theme Discovery
        total_phases = len(PHASES)
        resume_note = "Resuming from Theme Discovery (--from-themes)"
    elif args.from_scoring:
        start_phase = 4  # Step 05: Brand-Fit Scorer
        total_phases = len(PHASES)
        resume_note = "Resuming from Brand-Fit Scorer (--from-scoring)"
    else:
        start_phase = 0
        total_phases = len(PHASES)
        resume_note = None

    # Initialize run log
    log_path = create_run_log(sprint_folder, brand, sprint_name, research_direction, scope)

    if resume_note:
        append_to_log(log_path, resume_note)

    # Print header
    print("═" * 70)
    print(f" RESEARCH ENGINE — {brand}")
    print(f" Direction: \"{research_direction}\"")
    print(f" Scope: {scope}")
    if resume_note:
        print(f" {resume_note}")
    print("═" * 70)
    print()

    # Run phases
    pipeline_start = time.time()
    phase_times = []
    lang_miner_launched = False

    def handle_phase_error(i, error):
        """Print error details and exit."""
        phase_name = PHASES[i][0]
        phase_num = i + 1

        print(f"[{phase_num}/{total_phases}] {phase_name:45} ✗ failed      ")
        print()

        # Print error output
        print("═" * 70)
        print(f" ✗ FAILED at [{phase_num}/{total_phases}] {phase_name}")
        if MAX_RETRIES > 0 and PHASES[i][2]:
            print(f" (after {MAX_RETRIES} retries)")
        print("═" * 70)
        print()
        print("Error output:")
        error_lines = error.split('\n')[-20:]  # Last 20 lines
        for line in error_lines:
            print(line)
        print()

        likely_cause, recommendation = get_phase_error_advice(i)
        print("Likely causes:")
        print(f"- {likely_cause}")
        print()
        print("Recommendations:")
        print(f"→ {recommendation}")

        if i >= 5:  # Can resume from themes
            print(f"→ Re-run with: python3 engine/orchestrator.py {brand} --from-themes")
        elif i >= 4:  # Can resume from scoring
            print(f"→ Re-run with: python3 engine/orchestrator.py {brand} --from-scoring")

        print(f"→ If persistent, check run_log.txt for details")
        print()
        print(f"Sprint folder: {sprint_folder}")
        print("═" * 70)

        # Update log
        total_time = time.time() - pipeline_start
        update_log_completion(log_path, f"FAILED at {phase_name}", total_time)

        sys.exit(1)

    # Concurrent phase indices
    STEP09_PHASE = 8   # Insight Writer
    STEP10_PHASE = 9   # VoC Analyzer
    # LANG_MINER_PHASE = 10 (defined at module level)

    # Phases that run concurrently (excluded from sequential loop)
    concurrent_phases = {STEP09_PHASE, STEP10_PHASE, LANG_MINER_PHASE}
    sequential_phases = [i for i in range(start_phase, total_phases) if i not in concurrent_phases]

    # Determine which concurrent phases are in scope
    can_run_lang_miner = LANG_MINER_PHASE >= start_phase and start_phase <= 5
    can_run_09_10_concurrent = (STEP09_PHASE >= start_phase and STEP10_PHASE >= start_phase)

    # Shared state for background threads
    thread_results = {}  # phase_idx -> {'elapsed': float, 'error': str|None}

    def run_phase_background(phase_idx):
        """Run a phase in background thread."""
        elapsed, error = run_phase(phase_idx, brand, sprint_name, research_direction, scope, log_path, args.verbose)
        thread_results[phase_idx] = {'elapsed': elapsed, 'error': error}

    def print_phase_running(phase_idx, note=""):
        phase_name = PHASES[phase_idx][0]
        phase_num = phase_idx + 1
        suffix = f" ({note})" if note else ""
        print(f"[{phase_num}/{total_phases}] {phase_name:45} ⏳ running{suffix}...")

    def print_phase_done(phase_idx, elapsed, note=""):
        phase_name = PHASES[phase_idx][0]
        phase_num = phase_idx + 1
        suffix = f" ({note})" if note else ""
        print(f"[{phase_num}/{total_phases}] {phase_name:45} ✓ ({format_time(elapsed)}){suffix}")

    # --- Sequential phases (up to Step 08) ---
    lang_miner_thread = None

    for i in sequential_phases:
        phase_name = PHASES[i][0]
        phase_num = i + 1

        # Show running status
        print(f"[{phase_num}/{total_phases}] {phase_name:45} ⏳ running...", end='\r', flush=True)

        elapsed, error = run_phase(i, brand, sprint_name, research_direction, scope, log_path, args.verbose)
        phase_times.append(elapsed)

        if error:
            handle_phase_error(i, error)
        else:
            print(f"[{phase_num}/{total_phases}] {phase_name:45} ✓ ({format_time(elapsed)})")

        # After Step 05 (phase 4) completes, launch Step 12 concurrently
        if i == 4 and can_run_lang_miner and lang_miner_thread is None:
            print_phase_running(LANG_MINER_PHASE, "concurrent")
            lang_miner_thread = threading.Thread(target=run_phase_background, args=(LANG_MINER_PHASE,), daemon=True)
            lang_miner_thread.start()

    # --- Concurrent Steps 09+10 (after Step 08 completes) ---
    if can_run_09_10_concurrent:
        print_phase_running(STEP09_PHASE, "concurrent")
        print_phase_running(STEP10_PHASE, "concurrent")

        t09 = threading.Thread(target=run_phase_background, args=(STEP09_PHASE,), daemon=True)
        t10 = threading.Thread(target=run_phase_background, args=(STEP10_PHASE,), daemon=True)
        t09.start()
        t10.start()
        t09.join()
        t10.join()

        # Check results for Step 09
        r09 = thread_results.get(STEP09_PHASE, {})
        if r09.get('error'):
            handle_phase_error(STEP09_PHASE, r09['error'])
        else:
            print_phase_done(STEP09_PHASE, r09.get('elapsed', 0), "concurrent")
            phase_times.append(r09.get('elapsed', 0))

        # Check results for Step 10
        r10 = thread_results.get(STEP10_PHASE, {})
        if r10.get('error'):
            handle_phase_error(STEP10_PHASE, r10['error'])
        else:
            print_phase_done(STEP10_PHASE, r10.get('elapsed', 0), "concurrent")
            phase_times.append(r10.get('elapsed', 0))

        # Merge VoC data into insights_final.csv
        merge_voc_into_csv(sprint_folder, log_path)
    else:
        # Run Steps 09+10 sequentially if they're individually in scope
        for phase_idx in [STEP09_PHASE, STEP10_PHASE]:
            if phase_idx >= start_phase:
                phase_name = PHASES[phase_idx][0]
                phase_num = phase_idx + 1
                print(f"[{phase_num}/{total_phases}] {phase_name:45} ⏳ running...", end='\r', flush=True)
                elapsed, error = run_phase(phase_idx, brand, sprint_name, research_direction, scope, log_path, args.verbose)
                phase_times.append(elapsed)
                if error:
                    handle_phase_error(phase_idx, error)
                else:
                    print(f"[{phase_num}/{total_phases}] {phase_name:45} ✓ ({format_time(elapsed)})")

    # --- Wait for concurrent Step 12 ---
    if lang_miner_thread is not None:
        lang_miner_thread.join(timeout=1800)

        r12 = thread_results.get(LANG_MINER_PHASE, {})
        if r12.get('error'):
            handle_phase_error(LANG_MINER_PHASE, r12['error'])
        else:
            print_phase_done(LANG_MINER_PHASE, r12.get('elapsed', 0), "concurrent")
            phase_times.append(r12.get('elapsed', 0))
    elif LANG_MINER_PHASE >= start_phase and not can_run_lang_miner:
        # Fallback: run Step 12 sequentially
        phase_name = PHASES[LANG_MINER_PHASE][0]
        phase_num = LANG_MINER_PHASE + 1
        print(f"[{phase_num}/{total_phases}] {phase_name:45} ⏳ running...", end='\r', flush=True)
        elapsed, error = run_phase(LANG_MINER_PHASE, brand, sprint_name, research_direction, scope, log_path, args.verbose)
        phase_times.append(elapsed)
        if error:
            handle_phase_error(LANG_MINER_PHASE, error)
        else:
            print(f"[{phase_num}/{total_phases}] {phase_name:45} ✓ ({format_time(elapsed)})")

    # Pipeline complete
    total_time = time.time() - pipeline_start

    print()

    # Collect stats
    stats = collect_stats(brand, sprint_folder)

    # Print success message
    print("═" * 70)
    print(f" ✓ COMPLETE: {sprint_name}")
    print("═" * 70)
    print(f" Total time:     {format_time(total_time)}")

    if stats.get('evidence_total'):
        evidence_str = f"{stats['evidence_total']} pieces"
        if stats.get('evidence_new'):
            evidence_str += f" ({stats['evidence_new']} new this sprint)"
        print(f" Evidence:       {evidence_str}")

    if stats.get('themes'):
        print(f" Themes:         {stats['themes']}")

    if stats.get('insights'):
        print(f" Insights:       {stats['insights']}")

    print()
    print(f" Output: {sprint_folder / 'insights_final.csv'}")
    print("═" * 70)

    # Update log
    update_log_completion(log_path, "SUCCESS", total_time, stats)


if __name__ == "__main__":
    asyncio.run(main())
