# Creative Strategy Stack

A complete creative strategy system for DTC brands, built around Claude Code.

Takes you from "new brand, zero creative" to a full pipeline of static ads, UGC video briefs, listicles, and ongoing test batches — all grounded in real customer language, not assumptions.

Everything here is built around one idea: **the customer's own language is the best source material for ads.** The tools research how real people talk about their problems — scraping Reddit, pulling reviews, mining forums — and the skills turn that language into strategic creative briefs with psychological frameworks baked in. No angle, headline, or emotional arc comes from guessing. It all traces back to something a real customer said.

---

## Setup

This is a shared workspace in Claude Code. To get started:

1. Install [Claude Code](https://claude.ai/code) if you haven't already
2. Clone this repo and open it in Claude Code:

```bash
git clone https://github.com/TheProdigal95/creative-strategy-stack.git
cd creative-strategy-stack
claude
```

3. Once inside Claude Code, tell it:

> "Run ./setup.sh and walk me through the setup. I need help getting everything installed and configured."

Claude will run the setup script, install all dependencies, and prompt you for the API keys you need. It handles everything from there.

## What to try first

Once you're in Claude Code, try these to get a feel for the system:

**Research a new brand:**
> "Create a brand called pure-plank. Here's the product info: [paste product description, website copy, or messy notes]"

Claude sets up the brand and you can immediately run research sprints on it.

**Run a Reddit research sprint:**
> "Run a research sprint for pure-plank on 'back pain from desk jobs'"

This kicks off the 12-step Research Engine. It scrapes Reddit, extracts evidence, discovers themes, and comes back 7-25 minutes later with structured insights and customer language.

**Write static ad briefs:**
> "/statics-briefer" then provide your angles and voice of customer data

The skill walks you through 4 gates — stage, format, headlines, designer guidance — using three psychological frameworks to shape every brief.

**Pull competitor ads:**
> "/ad-library" then paste a Meta Ad Library URL

Scrapes all active ads for a brand, downloads the media, and optionally analyzes every creative with Gemini.

**Generate editorial images:**
> "/editorial-image-prompts" then describe what you need

Builds image prompts that produce visuals looking like magazine content, not ads.

**Quick Reddit scrape (lightweight):**
> "Scrape this Reddit thread: [URL]"

Uses the lightweight scraper — faster and cheaper than the full Research Engine, gives you raw posts and comments.

## What's inside

```
creative-strategy-stack/
├── CLAUDE.md                     # Auto-loaded context — setup guide + workflow reference
├── setup.sh                      # One-command installer
├── .env.example                  # API key template
│
├── skills/                       # AI workflows (copied to ~/.claude/skills/ during setup)
│   ├── statics-briefer/          # Static ad briefs — TEEP + Three Selves + Emotional Zones
│   ├── native-ad-creative/       # Native ad headlines + image direction
│   ├── listicle-writer/          # Research-driven listicle landing pages
│   ├── editorial-image-prompts/  # Editorial-style image generation prompts
│   ├── story-selling/            # Meta ad scripts where the story earns the sale
│   ├── critique/                 # Score any work against a chosen framework
│   └── gemini-api/               # Google Gemini for images, video, text
│
├── commands/                     # Claude Code commands (copied to ~/.claude/commands/)
│   ├── ad-library.md             # Meta Ad Library scraping pipeline
│   └── transcribe.md             # Video/audio transcription routing
│
├── tools/                        # Backend scripts the skills and commands call
│   ├── ad-library/               # Scrape, download, analyze, batch, cleanup
│   ├── gemini-api/               # Universal Gemini API wrapper
│   ├── reddit-scraper.js         # Lightweight Reddit scraping (fast, low-token)
│   └── mlx-transcribe.py         # Local video transcription (Apple Silicon only)
│
└── research-engine/              # 12-step Reddit research pipeline + MCP server
    ├── engine/                   # The pipeline steps
    ├── brands/                   # Your brand data (created as you work, not shared)
    └── requirements.txt          # Python dependencies
```

## The tools in plain English

### Research

**Research Engine** — You give it a brand and a direction ("gut health for backyard chickens"). It goes to Reddit, finds every relevant conversation, extracts the evidence, scores it against your brand, groups it into themes, and comes back with 20-40 structured insights plus a report on how the audience actually talks. Takes 7-25 minutes. No API key needed — it runs on your Claude Code session.

**Reddit Scraper** — A much simpler version. Give it a Reddit URL, get back the posts and comments as structured data. Takes seconds. Use this when you already know which threads matter and just need the text.

**Ad Library** — Scrapes Meta's Ad Library for any brand's active ads. Can process 10-20 brands in a batch. Downloads all the images and videos, and optionally runs Gemini visual analysis on every creative to break down messaging angles, visual patterns, and scripts.

### Creative

**Statics Briefer** — The most complex skill. Produces creative briefs for static ads using three psychological frameworks simultaneously:

| Framework | What it decides |
|-----------|----------------|
| **TEEP** (Trigger, Exploration, Evaluation, Purchase) | Where the buyer is in their journey |
| **Three Selves** (Actual, Ideal, Ought) | Which version of the buyer we're speaking to |
| **Emotional Zones** (Valence x Intensity) | What emotional state they're in and where the ad takes them |

It walks you through 4 gates with approval at each step. The output is a complete brief a designer can execute — strategy notes, image directions, headlines grouped by psychological type, subheadings, and compliance guardrails.

**Native Ad Creative** — Headlines and image direction for native advertising. Uses 7 psychological angles (curiosity gap, enemy framing, authority, social proof, contrarian, fear + discovery, identity filtering). Philosophy: copy sells, design gets in the way.

**Listicle Writer** — 9-gate workflow that produces landing page listicles where each numbered point is a sales argument, not just education. Built around a unifying theme with research at every step.

**Story-Selling** — Framework for writing Meta ad scripts where the story earns the sale. Covers how to find the "one row" in a transformation, curiosity gaps, contrast, and how to bring the product in without killing trust.

**Editorial Image Prompts** — Generates image prompts that produce visuals looking like they belong in magazines or journals, not ad creative. 9 style options, 7-layer prompt architecture.

**Critique** — A meta-skill. Pick any other skill or framework, and this one evaluates work against it. Scores each dimension 1-10 with specific feedback and fixes.

### Utility

**Gemini API** — Google Gemini for things Claude can't do natively: video analysis, image generation, image analysis. Works as both a skill and a CLI tool.

**Transcribe** — Routes video/audio to either local MLX (free, Apple Silicon) or Gemini (any platform). Use MLX for speech-to-text, Gemini when you need visual context like on-screen captions.

## Requirements

- [Claude Code](https://claude.ai/code) (CLI) — the environment everything runs in
- macOS, Linux, or WSL (Claude Code requirement)
- Google Gemini API key — [get one here](https://aistudio.google.com/apikey) (free tier available)
- Apify account — [sign up here](https://apify.com/) (for Ad Library + Reddit scraping)
- (Optional) Apple Silicon Mac for free local video transcription

Node.js, Python, Homebrew, and all other dependencies are handled by `setup.sh`.

## Contributing

Main is protected — nobody pushes directly to it. To make changes:

```bash
git checkout -b your-name/what-you-changed
# make your changes
git add -A && git commit -m "what you did"
git push -u origin your-name/what-you-changed
```

Then open a pull request on GitHub. Changes go into main after review and approval.

## Roadmap

This is a working system that's actively evolving. Known areas for improvement:

- **`statics-briefer` needs updating** — The frameworks are solid, but the gate flow needs to be brought in line with the latest process.
- **UGC briefing skill** — Story-selling covers the philosophy, but there's no dedicated skill yet for the full UGC creator package (hooks, b-roll shot lists, emotional arc checks).
- **Review scraping** — Currently manual. A tool for pulling and organizing brand + competitor reviews would close the loop on research.
- **Testing strategy skill** — The process for ranking angles by data strength isn't encoded as a skill yet.
