# Research Engine

## What This Is

A marketing research pipeline that scrapes Reddit, filters evidence by brand relevance, and generates structured insights with voice-of-customer analysis. The pipeline is fully automated — one command runs all 12 steps.

## First-Time Setup

If the user just got this project, they need:
1. Python 3.10+ installed
2. `pip3 install -r requirements.txt`
3. Claude Code CLI authenticated (they're already using it if they're reading this)

That's it. No API keys in the code, no env files to configure.

## Brand Setup (IMPORTANT — read this carefully)

When a user wants to add a new brand, set up a brand, or says something like "I want to try this with [brand name]", follow this workflow:

### Step 1: Get the brand name

Ask the user for a short lowercase brand name to use as the folder name (e.g., `suncoastgreens`, `acmewidgets`, `heatedblanket`). No spaces, no special characters.

### Step 2: Ask for brand information

Ask them to paste whatever they have about the brand. Tell them explicitly:

> Paste whatever you have on the brand — a product page, a pitch deck dump, raw notes, a brief, a URL, anything. Any format works. I'll extract what I need from it.

They do NOT need to know the YAML format. Accept any messy input.

### Step 3: Create the brand folder and brand_brief.yaml

From whatever they pasted, extract and create `brands/<brandname>/brand_brief.yaml` with this exact structure:

```yaml
brand_name: "The Brand Name"
brand_promise: "CORE VALUE PROP IN 3-5 WORDS ALL CAPS"

product: |
  Clear description of the product. Price if known. Key features.
  What it physically is and what it does.

main_selling_points:
  - name: "Short Feature Name"
    description: "What this feature does for the customer"
    solves: "The specific customer problem this addresses"
  # Include 2-4 selling points

pain_points_solved:
  - "Customer problem the product solves — written from their perspective"
  # Include 3-6 pain points

target_customers:
  - "Description of an audience segment"
  # Include 3-6 target segments

common_objections:
  - "A reason someone might not buy — written in their voice"
  # Include 3-5 objections
```

Guidelines for filling this out from messy input:
- **brand_promise**: Distill to the single strongest value prop, 3-5 words, ALL CAPS. This becomes a section in every insight the engine writes.
- **main_selling_points**: Each needs all three sub-fields (`name`, `description`, `solves`). The `solves` field is critical — it must describe the CUSTOMER'S problem, not the feature.
- **pain_points_solved**: Write these from the customer's perspective. "People quit X because Y" not "Our product fixes Y".
- **target_customers**: Describe real people. "Men over 40 who want to lose belly fat" not "Health-conscious consumers".
- **common_objections**: Write these in the customer's voice. "This seems too expensive" not "Price sensitivity".

If the user's input is missing key info (like they didn't mention the price, or there are no clear objections), ask a follow-up question for just the missing pieces. Don't guess on things that matter.

### Step 4: Create the folder

```bash
mkdir -p brands/<brandname>
```

Then write the `brand_brief.yaml` file.

### Step 5: Confirm and prompt for research

Show the user a summary of what was created and tell them they're ready to go. Then ask:

> Your brand is set up. What do you want to research? Give me a research direction — describe the specific audience and topic you want to explore.
>
> Good examples:
> - "back pain from desk jobs and sedentary work"
> - "weight loss for men over 40 who are busy dads"
> - "new moms struggling to find time for self-care"
> - "people who quit gym memberships and want home alternatives"

### Step 6: Run the pipeline

Once they give a research direction:

```bash
python3 engine/orchestrator.py <brandname> "their research direction"
```

This takes 7-25 minutes. Let them know it's running and what to expect.

## How to Run (for returning users)

### Single sprint (standard)

```bash
python3 engine/orchestrator.py <brand> "research direction"
```

Options:
- `--scope quick|standard|deep` — controls scraping volume (default: standard)
- `--from-scoring` — resume from Step 05 (skip scraping)
- `--from-themes` — resume from Step 06 (skip scraping + scoring)
- `--sprint "name"` — target a specific sprint when resuming

### Parallel sprints (multiple directions at once)

```bash
python3 engine/orchestrator.py <brand> --parallel \
    "back pain from desk jobs" \
    "weight loss for busy dads" \
    "time scarcity for professionals" \
    --scope quick
```

Options for parallel mode:
- `--max-concurrent N` — max concurrent analysis phases (default: 2)
- `--scrape-concurrent N` — max concurrent scrape phases (default: 1, for Reddit rate limits)

Parallel mode serializes scraping (to avoid Reddit rate limits) but runs analysis phases concurrently. Evidence is safely stored in SQLite with WAL mode — no data loss from concurrent writes.

## Project Layout

- `engine/orchestrator.py` — Entry point, runs all steps (single or parallel)
- `engine/evidence_db.py` — SQLite evidence store (concurrent-safe)
- `engine/mcp_server.py` — MCP server for agent-driven workflows
- `engine/migrate_to_sqlite.py` — Migration from CSV/JSON to SQLite
- `engine/step01-12_*.py` — Individual pipeline steps
- `brands/<name>/brand_brief.yaml` — Brand configuration
- `brands/<name>/evidence.db` — SQLite database (evidence + personas)
- `brands/<name>/sprints/<sprint>/insights_final.csv` — Main output (open in spreadsheet)
- `brands/<name>/sprints/<sprint>/language_report.json` — Language analysis output
- `brands/<name>/sprints/<sprint>/_intermediate/` — Internal working files

## Key Technical Details

- All LLM calls use `claude_code_sdk` (authenticates through local Claude Code CLI)
- Reddit scraping uses the public JSON API (no Reddit API key needed)
- Evidence stored in SQLite with WAL mode (concurrent-safe across parallel sprints)
- Dependencies: pandas, requests, pyyaml, claude-code-sdk, mcp
- Use `python3`, not `python`
- Evidence accumulates at the brand level across sprints — INSERT OR IGNORE deduplicates automatically

## Pipeline Steps (in execution order)

1. **Retrieval Planner** — LLM discovers subreddits and search queries
2. **Reddit Scraper** — Two-stage scraping (test then scale). Stage 2 has early-exit once enough candidates found.
3. **Transform + Verify** (03+04 merged) — JSONL to SQLite evidence rows, then DB health check inline
4. **Brand-Fit Scorer** — LLM vocabulary + Python scoring to filter evidence
5. **Theme Discovery** — LLM identifies themes and draft insights. *Step 12 (Language Miner) launches concurrently from here.*
6. **Persona Normalizer** — Normalizes personas to consistent identity-based names
7. **Evidence Matcher** — Python counts evidence per insight
8. **Insight Writer + VoC Analyzer** (09+10 concurrent) — Run simultaneously after Step 08. Step 09 writes insights; Step 10 extracts quotes & tone from `themes_discovered.json`. VoC data merged into `insights_final.csv` after both complete. LLM batches within each step also run concurrently (max 3).
9. **Language Miner** — Quantitative n-gram analysis + LLM language categorization (concurrent with Steps 06-10, completes independently)
10. **VoC Curator** — Manual tool (NOT in orchestrator): curates quotes to SQLite (`evidence.db`). Use `--export-json` to export `voc_master.json`.

## MCP Server (for agent-driven workflows)

The MCP server lets Claude Code agents trigger sprints without reading any files. Instead of a sub-agent loading 15+ files to figure out the right command (~100K tokens overhead), it calls a single tool (~100 tokens).

### Setup

Add to project-level `.claude/settings.json`:

```json
{
  "mcpServers": {
    "research-engine": {
      "command": "python3",
      "args": ["engine/mcp_server.py"],
      "cwd": "/path/to/creative-strategy-stack/tools/research-engine"
    }
  }
}
```

This is already configured in the project-level `.claude/settings.json`.

### Available tools

- `run_research_sprint(brand, directions, scope?)` — Start one or more sprints. Pass a single direction for one sprint, or multiple to run them in parallel with coordinated scraping.
- `check_sprint_status(brand, sprint_key?)` — Returns status and summary stats
- `list_brands()` — Lists available brands with evidence/sprint counts
- `list_sprints(brand)` — Lists all sprints with status

### When to use MCP tools (IMPORTANT for agents)

**Always prefer MCP tools over Bash for research engine operations.** These tools exist so agents don't need to read files or figure out CLI commands (~100 tokens vs ~100K).

- When asked to "run a research sprint" → use `run_research_sprint`, not `python3 engine/orchestrator.py`
- For multiple directions, pass them all in one `run_research_sprint` call — the tool auto-detects single vs parallel mode and coordinates scraping to avoid Reddit rate limits
- To monitor a running sprint → use `check_sprint_status`
- To discover what brands exist → use `list_brands`
- To see what sprints have been run → use `list_sprints`
- Only fall back to Bash for operations not covered by the tools (e.g., `--from-scoring` resume, VoC Curator)

## Evidence Database

Evidence is stored in `brands/<brand>/evidence.db` (SQLite, WAL mode).

### Migration from CSV

If you have existing `evidence_master.csv` or `personas.json` files, migrate them:

```bash
python3 engine/migrate_to_sqlite.py <brand>    # Single brand
python3 engine/migrate_to_sqlite.py --all       # All brands
```

Original files are preserved as backup.

### Utilities

```bash
python3 engine/evidence_db.py <brand> --stats    # Print DB statistics
python3 engine/evidence_db.py <brand> --export   # Export to CSV
```

## When Modifying Code

- Steps that use LLM follow a consistent pattern: build prompt, call `query()` from claude_code_sdk, parse response
- The orchestrator's `PHASES` list, `build_phase_command()`, and concurrent phase sets (`concurrent_phases` in the main loop) must be updated together when adding steps
- Steps 09+10 run concurrently — Step 10 reads `themes_discovered.json` (not `insights_final.csv`), writes `voc_analysis.json`, then orchestrator merges VoC into CSV
- Step 12 (Language Miner) runs concurrently after Step 05 — it only reads `evidence_filtered.csv` and `sprint_config.txt`
- LLM batch processing in Steps 09 and 10 uses `asyncio.gather()` + `Semaphore(3)` for concurrent batches
- Evidence schema is 12 fields (see step03 for the canonical schema)
- Persona names must be identity-based ("Busy Dads") not problem-based ("Pain Blocked")
- Shared state is in SQLite (`evidence.db`) — no more CSV merging or JSON file locking
- Scrape output goes to sprint-level `_intermediate/` directory, not brand-level `evidence/raw/`
