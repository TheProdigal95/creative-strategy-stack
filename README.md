# Creative Strategy Stack

A complete creative strategy system for DTC brands, built around Claude Code.

Takes you from "new brand, zero creative" to a full pipeline of static ads, UGC video briefs, listicles, and ongoing test batches — all grounded in real customer language, not assumptions.

## Quick Start

```bash
git clone https://github.com/TheProdigal95/creative-strategy-stack.git
cd creative-strategy-stack
./setup.sh
```

The setup script handles everything: installs dependencies, copies skills into Claude Code, configures the Research Engine, and prompts for API keys.

## What's Inside

### AI Skills (7)

Structured workflows invoked from Claude Code with `/skill-name`:

| Skill | What it does |
|-------|-------------|
| `statics-briefer` | Static ad briefs using TEEP stages + Three Selves + Emotional Zones |
| `native-ad-creative` | Native ad headlines + image direction via direct response psychology |
| `listicle-writer` | Research-driven listicle landing pages (9-gate workflow) |
| `editorial-image-prompts` | Editorial-style image prompts that look like content, not ads |
| `story-selling` | Meta ad scripts where the story earns the sale |
| `critique` | Evaluate any creative work against a chosen skill/framework |
| `gemini-api` | Google Gemini for text generation, image/video analysis, image generation |

### Research Engine

A 12-step Python pipeline that scrapes Reddit, extracts evidence, discovers themes, scores brand fit, and mines language patterns. Runs as an MCP server — use it directly from Claude Code, no separate commands needed.

- `create_brand` — Set up a new brand from a product info dump
- `run_research_sprint` — Run Reddit research sprints (7-25 min each)
- `check_sprint_status` — Monitor sprint progress
- `list_brands` / `list_sprints` — Browse existing data

**Auth:** Uses your Claude Code session — no separate API key needed.

### Reddit Scraper (Lightweight)

A faster, lower-token alternative to the full Research Engine. Use when you need to quickly pull posts and comments from specific Reddit threads or subreddits without running the full 12-step analysis pipeline. Requires an Apify token.

### Commands (2)

| Command | What it does |
|---------|-------------|
| `/ad-library` | Batch scrape Meta Ad Library for competitor creative, download media, optional Gemini visual analysis |
| `/transcribe` | Route video/audio to local MLX (free, Apple Silicon) or Gemini API (any platform) |

### Backend Tools

| Tool | Purpose |
|------|---------|
| Ad Library suite | Scrape, download, analyze, batch process, cleanup Meta Ad Library data |
| Gemini API wrapper | Universal Gemini interface (text, images, video, generation) |
| MLX Transcribe | Free local video transcription (Apple Silicon only) |

## Three Frameworks in Every Brief

| Framework | What it decides |
|-----------|----------------|
| **TEEP** (Trigger, Exploration, Evaluation, Purchase) | Where the buyer is in their journey |
| **Three Selves** (Actual, Ideal, Ought) | Which version of the buyer we're speaking to |
| **Emotional Zones** (Valence x Intensity) | The emotional arc from current state to target state |

## Requirements

- [Claude Code](https://claude.ai/code) (CLI)
- Node.js v18+ (setup script installs via Homebrew if missing)
- Python 3.10+ (setup script installs if missing)
- Google Gemini API key — [Get one here](https://aistudio.google.com/apikey)
- Apify account — [Sign up here](https://apify.com/) (for Meta Ad Library + Reddit scraping)
- (Optional) Apple Silicon Mac for free local MLX transcription
