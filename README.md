# Creative Strategy Stack

A complete creative strategy system for DTC brands, built around Claude Code.

Takes you from "new brand, zero creative" to a full pipeline of static ads, UGC video briefs, listicles, and ongoing test batches — all grounded in real customer language, not assumptions.

## Quick Start

```bash
git clone https://github.com/TheProdigal95/creative-strategy-stack.git
cd creative-strategy-stack
./setup.sh
```

The setup script handles everything: checks for Node.js and Python (installs them if missing), installs all dependencies, copies skills and commands into your Claude Code config, wires up the Research Engine as an MCP server, and prompts you for API keys. After that, open the folder in Claude Code and the `CLAUDE.md` loads automatically with the full reference.

## What's Inside

### Research

Two tools for gathering customer language — one deep, one fast.

**Research Engine** — A 12-step Python pipeline that scrapes Reddit, extracts evidence, discovers themes, scores brand fit, and mines language patterns. Runs as an MCP server inside Claude Code. You tell it a brand and a research direction ("gut health for backyard chickens"), it comes back 7-25 minutes later with 20-40 structured insights, evidence counts, VoC quotes, and a language report showing how the audience actually talks. Uses your Claude Code session for auth — no separate API key.

**Reddit Scraper (Lightweight)** — A single Node.js script that pulls posts and comments from specific Reddit threads or subreddits via Apify. Much faster, uses far fewer tokens, but gives you raw data instead of structured analysis. Use this when you already know which threads matter and just need the text.

### Creative Skills

Seven structured AI workflows, each invoked from Claude Code with `/skill-name`:

| Skill | When to use it |
|-------|----------------|
| `/statics-briefer` | Writing creative briefs for static ads. Uses three psychological frameworks simultaneously — see below. |
| `/native-ad-creative` | Native advertising headlines + image direction. Direct response psychology with 7 angle types. |
| `/listicle-writer` | Landing page listicles where each numbered point is a sales argument. 9-gate workflow from research to imagery. |
| `/editorial-image-prompts` | Image generation prompts that produce editorial-quality visuals — images that look like magazine content, not ads. |
| `/story-selling` | Meta ad scripts (UGC, testimonials) where the story earns the sale. Covers curiosity gaps, contrast, and product integration. |
| `/critique` | Evaluate any creative output against a chosen skill or framework. Scores each dimension 1-10 with specific fixes. |
| `/gemini-api` | Google Gemini for video analysis, image generation, image analysis, and text generation. |

### Competitive Intelligence

| Tool | What it does |
|------|-------------|
| `/ad-library` | Batch scrape Meta Ad Library for 10-20 brands at once. Downloads media, optional Gemini visual analysis for full creative breakdowns. |
| `/transcribe` | Transcribe video/audio — routes to local MLX (free, Apple Silicon) or Gemini API (any platform, detailed visual context). |

## Three Frameworks in Every Static Brief

The `/statics-briefer` skill makes three simultaneous strategic decisions for each ad. These aren't separate tools — they work together to determine the tone, pressure, and emotional arc.

| Framework | What it decides | Example |
|-----------|----------------|---------|
| **TEEP** (Trigger, Exploration, Evaluation, Purchase) | Where the buyer is in their journey | Trigger = something just happened. Evaluation = she's comparing products. |
| **Three Selves** (Actual, Ideal, Ought) | Which version of the buyer we're speaking to | Ought = "you should." Actual = "you're not wrong." Ideal = "the person who..." |
| **Emotional Zones** (Valence x Intensity) | What emotional state the buyer is in, and where the ad takes them | Zone 3 (quiet frustration) → Zone 1 (calm relief) |

The ratio of Selves and the emotional journey are deliberate strategic decisions per brief, not random choices. The skill guides you through this at each gate.

## Requirements

- [Claude Code](https://claude.ai/code) (CLI)
- Node.js v18+ (setup script installs via Homebrew if missing)
- Python 3.10+ (setup script installs if missing)
- Google Gemini API key — [Get one here](https://aistudio.google.com/apikey)
- Apify account — [Sign up here](https://apify.com/) (for Meta Ad Library + Reddit scraping)
- (Optional) Apple Silicon Mac for free local MLX transcription

## Roadmap

This is a working system that's actively evolving. Known areas for improvement:

- **`statics-briefer` needs updating** — The skill encodes an earlier version of the workflow. The frameworks (TEEP, Three Selves, Emotional Zones) are solid, but the gate flow and some execution details need to be brought in line with the latest process. If you're using it and something feels off, that's why.
- **UGC briefing skill** — Story-selling covers the philosophy, but there's no dedicated skill yet for the full UGC creator package workflow (hooks, b-roll shot lists, emotional arc checks).
- **Review scraping** — Currently manual. A structured skill or tool for pulling and organizing brand + competitor reviews would close the loop on the research side.
- **Testing strategy skill** — The process for ranking angles by data strength and writing testing strategies is documented but not yet encoded as a skill.
