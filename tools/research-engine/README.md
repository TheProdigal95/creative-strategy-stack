# Research Engine

A pipeline that scrapes Reddit, collects real user conversations, and generates structured marketing insights with voice-of-customer analysis. Give it a brand brief and a research direction, get back actionable insights backed by evidence.

Built for marketing strategists who need to understand how their target audience actually talks, thinks, and feels — before writing a single line of copy.

## What It Does

```
Brand Brief + Research Direction
        |
        v
   Scrape Reddit (auto-discovers subreddits + search queries)
        |
        v
   Score & Filter Evidence (keeps only brand-relevant pieces)
        |
        v
   Discover Themes + Write Insights (LLM-powered analysis)
        |
        v
   Voice of Customer Analysis (real quotes, tone, language patterns)
        |
        v
   Outputs:
     - insights_final.csv    (structured insights with evidence backing)
     - language_report.json  (how the audience actually talks)
```

A typical run takes 7-25 minutes depending on scope and produces 20-40 insights from thousands of Reddit conversations.

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** (for installing Claude Code CLI)
- **Claude Code CLI** — this is how the pipeline makes LLM calls
- Either a **Claude Max/Pro subscription** or an **Anthropic API key**

## Setup

### 1. Install dependencies

```bash
cd "Research Engine"
pip3 install -r requirements.txt
```

### 2. Install and authenticate Claude Code

The pipeline uses Claude's SDK for all LLM calls. There are no API keys in the code — it authenticates through your local Claude Code CLI.

```bash
# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Authenticate (opens browser for OAuth login)
claude
```

If you prefer using an Anthropic API key instead of a subscription:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Verify it works

```bash
python3 -c "from claude_code_sdk import query; print('SDK ready')"
```

## Quick Start

### The easy way (recommended): Use Claude Code

If you're already in Claude Code, just tell it what brand you want to research:

> "I want to set up a brand called [name]"

Claude Code will ask you to paste whatever info you have on the brand — a product page, pitch deck, raw notes, anything. It will automatically create the brand folder and config file in the right format. Then it'll ask for your research direction and run the pipeline.

You don't need to know the YAML format or the folder structure. Just paste your brand info and go.

### The manual way: Create a brand brief yourself

The brand brief tells the engine what product you're researching for. Create a YAML file:

```bash
mkdir -p brands/mybrand
```

Then create `brands/mybrand/brand_brief.yaml`. Here's a real example to follow:

```yaml
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
```

**What each field does:**

| Field | Purpose | Tip |
|-------|---------|-----|
| `brand_name` | Your product/company name | Used in insight copy |
| `brand_promise` | The core value prop in 3-5 words | Becomes a section in every insight |
| `product` | What the product is, price, key features | Helps the engine write product bridges |
| `main_selling_points` | 2-4 key features with what they solve | Each needs `name`, `description`, `solves` |
| `pain_points_solved` | Problems your product addresses | Written from the customer's perspective |
| `target_customers` | Who buys this | Drives persona discovery |
| `common_objections` | Why people don't buy | Becomes objection-type insights |

### Step 2: Run the pipeline

```bash
python3 engine/orchestrator.py mybrand "your research direction"
```

**The research direction** is the specific angle you want to explore. It should describe the audience + topic in natural language. The engine uses this to find the right Reddit conversations.

Good research directions (specific, describes real people + their situation):
```
"back pain from desk jobs and sedentary work"
"weight loss for men over 40 who are busy dads"
"witty humorous language men over 40 use when talking about dad bods"
"people who quit gym memberships and want home alternatives"
"new moms struggling to find time for self-care"
```

Bad research directions (too vague or too broad):
```
"fitness"                    # Way too broad
"people who buy things"      # Not specific enough
"marketing insights"         # That's what the tool produces, not what to research
```

### Step 3: Check output

After the run completes, your results are in:

```
brands/mybrand/sprints/01 - Sprint Name/
  insights_final.csv      <-- Main deliverable (open in any spreadsheet app)
  language_report.json    <-- How the audience talks (for copywriters)
  sprint_config.txt       <-- What was researched
  _intermediate/          <-- Internal working files (ignore unless debugging)
```

### What an insight looks like

Here's a real example from an actual run:

| Field | Value |
|-------|-------|
| **Insight** | Men over 40 use humor to mask genuine desperation about getting back in shape after years of neglect |
| **Insight Type** | Motivation |
| **Theme** | The Comeback Narrative |
| **Persona** | Former Athletes |
| **Angle** | Rock Bottom Rally |
| **Notes** | BELIEF: I used to be in shape, then life happened — now I'm starting from zero and laughing so I don't cry. REFRAME: Starting from zero isn't a setback... |
| **Valence** | Negative |
| **Intensity** | 4 |
| **Self** | Ideal |
| **Evidence Count** | 52 |
| **VoC** | "As a 41 year old, injuries, and things just taking longer and being harder than they used to be are my biggest challenges..." |

Each run typically produces 20-40 insights like this, each backed by real evidence counts and authentic quotes.

## Running Multiple Sprints

Each run creates a new "sprint" — a separate research angle for the same brand. Evidence accumulates across sprints (the engine gets smarter over time).

```bash
# Sprint 1: Research one angle
python3 engine/orchestrator.py mybrand "back pain from desk jobs"

# Sprint 2: Different angle, same brand
python3 engine/orchestrator.py mybrand "time scarcity for busy parents"

# Sprint 3: Yet another angle
python3 engine/orchestrator.py mybrand "skepticism about home fitness equipment"
```

Sprints are numbered automatically: `01 - Back Pain from Desk Jobs`, `02 - Time Scarcity for Busy Parents`, etc.

## Scope Options

Control how much Reddit data to scrape:

| Scope | Runtime | Best for |
|-------|---------|----------|
| `--scope quick` | ~7 min | Testing, quick exploration |
| `--scope standard` | ~15 min | Default, good balance |
| `--scope deep` | ~25 min | Maximum evidence collection |

```bash
python3 engine/orchestrator.py mybrand "direction" --scope quick
```

## Error Recovery

If the pipeline fails partway through, resume without re-scraping:

```bash
# Resume from scoring (skip scraping)
python3 engine/orchestrator.py mybrand --from-scoring

# Resume from theme discovery (skip scraping + scoring)
python3 engine/orchestrator.py mybrand --from-themes

# Resume a specific sprint
python3 engine/orchestrator.py mybrand --from-themes --sprint "03 - Sprint Name"
```

## Pipeline Steps

| Step | Name | What It Does | Method |
|------|------|-------------|--------|
| 01 | Retrieval Planner | Discovers subreddits + search queries for the research direction | LLM |
| 02 | Reddit Scraper | Scrapes threads (two-stage: test then scale) | Reddit JSON API |
| 03 | Transform to CSV | Converts raw JSONL to structured evidence CSV | Python |
| 04 | Merge Evidence | Deduplicates and merges into master evidence file | Python |
| 05 | Brand-Fit Scorer | Filters evidence to brand-relevant pieces using LLM-generated vocabulary | Hybrid |
| 06 | Theme Discovery | Identifies themes and draft insights from filtered evidence | LLM |
| 07 | Persona Normalizer | Normalizes audience personas to a consistent ledger | LLM |
| 08 | Evidence Matcher | Counts evidence matches per insight | Python |
| 09 | Insight Writer | Writes full insight notes with reframes and brand connections | LLM |
| 10 | VoC Analyzer | Extracts authentic quotes and tone analysis per insight | LLM |
| 12 | Language Miner | Produces structured language report (phrases, tone, copywriter gold) | Hybrid |

Step 11 (VoC Curator) is a manual tool, not part of the automatic pipeline — see below.

## Output Reference

### insights_final.csv

| Column | Description |
|--------|-------------|
| Insight | The core finding |
| Insight Type | Psychological mechanism: Belief Shift, Objection, Desire, Friction, Misconception, or Motivation |
| Theme | Topic being discussed (e.g., "The Comeback Narrative", "Time as Currency") |
| Persona | Target audience segment — identity-based (e.g., "Busy Dads", "Desk Workers", "Former Athletes") |
| Angle | Specific entry point for this insight |
| Notes | Full context: Belief, Reframe, Brand Promise Application, Product Bridge |
| Valence | Negative (pain/frustration) or Positive (desire/aspiration) |
| Intensity | 1-5 scale of emotional weight (1=mild, 5=existential) |
| Self | Ideal (who I want to be), Actual (who I am), or Ought (who I should be) |
| Evidence Count | Number of real Reddit posts/comments supporting this insight |
| Source | Data source (reddit) |
| Top Communities | Subreddits where evidence came from |
| Status | New |
| VoC | Authentic quotes + tone analysis from real conversations |
| Keep | Empty — mark Y to curate into voc_master.json with Step 11 |

### language_report.json

Structured report of how the audience actually talks:

- **language_categories** — Clustered language patterns (e.g., "Self-Deprecating Body Terms", "Discipline vs Motivation")
- **tone_profile** — Dominant tones, how they express pain vs desire, register (humorous/clinical/emotional/mixed)
- **top_phrases** — Most frequent phrases with real frequency counts from n-gram analysis
- **copywriter_gold** — The absolute best phrases, quotes, and metaphors for direct use in copy
- **quantitative_summary** — Raw n-gram frequency data extracted from all evidence

## Manual Tools

### VoC Curator (Step 11)

After reviewing `insights_final.csv` in a spreadsheet, mark rows you want to keep with `Y` in the Keep column, save, then run:

```bash
python3 engine/step11_voc_curator.py mybrand "01 - Sprint Name"
```

This stores curated quotes into `brands/mybrand/voc_master.json` organized by Theme and Persona. Useful for building a library of authentic voice-of-customer language across multiple sprints.

### Running Individual Steps

For debugging or re-running a specific step:

```bash
python3 engine/step05_brand_fit_scorer.py mybrand "sprint-name"
python3 engine/step06_theme_discovery.py mybrand "sprint-name"
python3 engine/step12_language_miner.py mybrand "sprint-name"
```

## Project Structure

```
Research Engine/
├── engine/
│   ├── orchestrator.py             # Entry point — runs the full pipeline
│   ├── step01_retrieval_planner.py
│   ├── step02_reddit_scraper.py
│   ├── step03_reddit_to_evidence.py
│   ├── step04_merge_evidence.py
│   ├── step05_brand_fit_scorer.py
│   ├── step06_theme_discovery.py
│   ├── step07_persona_normalizer.py
│   ├── step08_evidence_matcher.py
│   ├── step09_insight_writer.py
│   ├── step10_voc_analyzer.py
│   ├── step11_voc_curator.py       # Manual (not in orchestrator)
│   ├── step12_language_miner.py
│   └── config/
│       ├── insight_format_example.csv
│       └── subreddit_cache.json
├── brands/                         # Your brand data lives here
│   └── <brand-name>/
│       ├── brand_brief.yaml        # Brand context (you create this)
│       ├── personas.json           # Auto-generated, grows across sprints
│       ├── voc_master.json         # Curated VoC data (from Step 11)
│       ├── evidence/
│       │   ├── evidence_master.csv # Accumulates across all sprints
│       │   └── raw/
│       └── sprints/
│           └── 01 - Sprint Name/
│               ├── insights_final.csv
│               ├── language_report.json
│               ├── sprint_config.txt
│               └── _intermediate/
├── requirements.txt
├── CLAUDE.md                       # Instructions for Claude Code
└── README.md
```

## Design Decisions

- **Brand-agnostic**: Works for any brand. Nothing is hardcoded to a specific product. Just create a new brand_brief.yaml and go.
- **Evidence accumulates**: The master evidence file grows across sprints and is never overwritten. More sprints = richer evidence base.
- **Hybrid architecture**: Python handles scale (scoring thousands of evidence pieces). LLM handles intelligence (theme discovery, insight writing, voice analysis).
- **File hygiene**: User-facing outputs in the sprint root. Internal working files in `_intermediate/`.
- **No API keys in code**: Authentication is handled entirely by your local Claude Code installation.
