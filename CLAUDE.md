# Creative Strategy Stack — Setup & Usage Guide

This is a complete creative strategy system for DTC brands. It takes you from zero customer knowledge to a full pipeline of static ads, UGC briefs, listicles, and ongoing test batches — all grounded in real customer language.

Read `how-i-work.md` for the full philosophy and process walkthrough.

---

## Quick Setup

Run the setup script from the repo root — it handles everything:

```bash
./setup.sh
```

This will check for Node.js (install via Homebrew if missing), install npm dependencies, copy skills and commands into your Claude Code config, and prompt you for API keys.

### Manual setup (if you prefer)

<details>
<summary>Click to expand step-by-step instructions</summary>

#### 1. Prerequisites

You need **Node.js** (v18+). Check with `node --version`. If not installed:
- **macOS:** `brew install node` (install [Homebrew](https://brew.sh) first if needed)
- **Linux:** `sudo apt install nodejs npm` or use [nvm](https://github.com/nvm-sh/nvm)
- **Windows:** Download from [nodejs.org](https://nodejs.org/)

#### 2. Install skills and commands

```bash
mkdir -p ~/.claude/skills ~/.claude/commands
cp -r skills/* ~/.claude/skills/
cp -r commands/* ~/.claude/commands/
```

#### 3. Set up API keys

```bash
cp .env.example tools/ad-library/.env
cp .env.example tools/gemini-api/.env
```

Then edit both `.env` files with your actual keys:
- **GEMINI_API_KEY** — Get from Google AI Studio (https://aistudio.google.com/apikey)
- **APIFY_TOKEN** — Get from Apify (https://apify.com/) — needed for Meta Ad Library scraping

#### 4. Install tool dependencies

```bash
cd tools/ad-library && npm install && cd ../gemini-api && npm install && cd ../..
```

#### 5. (Optional) Local Transcription (MLX)

Local transcription via `tools/mlx-transcribe.py` is free and fast but requires **macOS with Apple Silicon** (M1/M2/M3/M4).

**Option A — Pinokio (easiest):** Install [Pinokio](https://pinokio.computer/) and add the "MLX Video Transcription" app. Everything is bundled.

**Option B — Manual:**
```bash
brew install ffmpeg
pip install mlx mlx-whisper numpy
```

</details>

**Don't have Apple Silicon?** No problem — use Gemini transcription instead. The `/transcribe` command will guide you to the right tool. Gemini transcription works on any platform with just an API key.

---

## What's in the Stack

### Skills (invoke with `/skill-name`)

| Skill | What it does | When to use it |
|-------|-------------|----------------|
| `/statics-briefer` | 4-gate workflow producing static ad briefs using TEEP stages, Three Selves theory, and Emotional Zones | Writing creative briefs for static ads |
| `/native-ad-creative` | Generates native ad headlines + image direction using direct response psychology | Native advertising creative (headlines + concepts) |
| `/listicle-writer` | 9-gate system where each numbered point is a sales argument | Landing page listicles |
| `/editorial-image-prompts` | Generates editorial-style image prompts that look like real content, not ads | Image generation for native placements |
| `/story-selling` | Framework for Meta ad scripts where the story earns the sale | UGC scripts, testimonial ads, video creative |
| `/critique` | Meta-skill that evaluates work against any loaded skill/framework | Quality review of any creative output |
| `/gemini-api` | Interface to Google Gemini for text, image analysis, video analysis, and image generation | Image/video analysis, AI image generation |

### Commands (invoke with `/command-name`)

| Command | What it does |
|---------|-------------|
| `/ad-library` | Batch scrape Meta Ad Library for competitor creative, download media, optional visual analysis |
| `/transcribe` | Route video/audio to local MLX (free) or Gemini API (detailed visual context) |

### Tools (backend scripts the commands call)

| Tool | Location | Purpose |
|------|----------|---------|
| Ad Library suite | `tools/ad-library/` | Scrape, download, analyze, batch process, cleanup |
| Gemini API wrapper | `tools/gemini-api/` | Universal Gemini interface (text, images, video, generation) |
| MLX Transcribe | `tools/mlx-transcribe.py` | Local video transcription (Apple Silicon only, optional) |

---

## The Workflow

The full process is documented in `how-i-work.md`. Here's the short version:

1. **Research** — Scrape reviews (brand + competitors). Run research sprints on Reddit. Extract VoC, language patterns, emotional registers.
2. **Context docs** — Write Brand Context + Product Context + Compliance Guidelines.
3. **Angle development** — Generate angle hypotheses grounded in VoC. Rank by evidence strength.
4. **Testing strategy** — Define which angles to test, in what order, and why.
5. **T001 briefs** — First test batch. Use `/statics-briefer` or `/native-ad-creative`.
6. **Read the data** — What's spending? What's clicking? What's converting?
7. **T002+ briefs** — Refinement, format expansion, channel expansion.
8. **Process log** — Document what worked, what shifted.

### Three frameworks used in every brief

- **TEEP** — Trigger, Exploration, Evaluation, Purchase (where is the buyer in their journey?)
- **Three Selves** — Actual, Ideal, Ought (which version of the buyer are we speaking to?)
- **Emotional Zones** — Valence x Intensity (what emotional state are they in, and where does the ad take them?)

---

## Key Principles

- **Nothing is based on vibes.** Every angle, headline, and emotional arc traces back to something a real customer said.
- **Reviews are the #1 data source.** Always scrape both brand AND competitor reviews.
- **Visuals go aggressive, copy stays compliant.** The image does the job the headline can't.
- **Headlines and subheadings never do the same job.** Whatever the headline covers, the subheading fills in what's missing.
- **UGC hooks must sound spoken, not written.** Read it out loud — if it sounds like a headline, rewrite it.
- **Tests are ranked by data strength, not creative preference.**
- **Briefs must not reference internal processes.** The creator gets direction. The strategy stays internal.

---

## Folder Structure for Each Brand

```
Brand Name/
├── 00 Context/
│   ├── Brand Context - [Brand].md
│   ├── Product Context - [Product].md
│   ├── Compliance Guidelines.md
│   ├── Reviews.jsonl
│   └── From Client/
├── 01 REF Images/
├── 02 Product Images/
├── YYYY-MM-DD T001 Testing Strategy
├── YYYY-MM-DD T001 Creative Briefs
├── YYYY-MM-DD T002 Creative Briefs
├── YYYY-MM-DD T003 Static Briefs
├── YYYY-MM-DD T004 UGC Creator Briefs
└── YYYY-MM-DD Listicle Draft
```

File naming: date first, always. `YYYY-MM-DD [Type] [Batch] - [Brand/Product].md`
