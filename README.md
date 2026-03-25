# Creative Strategy Stack

A complete creative strategy system for DTC brands, built around Claude Code.

Takes you from "new brand, zero creative" to a full pipeline of static ads, UGC video briefs, listicles, and ongoing test batches — all grounded in real customer language, not assumptions.

## What's Inside

**7 AI Skills** — Structured workflows for static ad briefs, native ad creative, listicles, editorial image prompts, story-selling scripts, copy critique, and Gemini API integration.

**2 Commands** — Meta Ad Library scraping/analysis and video transcription (local or cloud).

**Backend Tools** — Node.js scripts for ad scraping, media downloading, Gemini analysis, and local MLX transcription.

**Process Documentation** — The complete research-to-brief methodology with real examples.

## The System in One Sentence

**Customer research (reviews + Reddit + competitor reviews + customer calls) becomes structured VoC data, which becomes angle hypotheses ranked by evidence strength, which become creative briefs with strategic frameworks baked in, which become the ads you design.**

## Three Frameworks in Every Brief

| Framework | What it decides |
|-----------|----------------|
| **TEEP** (Trigger, Exploration, Evaluation, Purchase) | Where the buyer is in their journey |
| **Three Selves** (Actual, Ideal, Ought) | Which version of the buyer we're speaking to |
| **Emotional Zones** (Valence x Intensity) | The emotional arc from current state to target state |

## Getting Started

1. Clone this repo
2. Open the folder in Claude Code
3. The `CLAUDE.md` will auto-load with full setup instructions
4. Copy skills and commands into your `~/.claude/` directory
5. Add your API keys (Gemini + Apify)
6. Read `how-i-work.md` for the full process walkthrough

## Requirements

- [Claude Code](https://claude.ai/code) (CLI)
- Node.js (for ad library tools)
- Google Gemini API key (for image/video analysis and generation)
- Apify account (for Meta Ad Library scraping)
- (Optional) Pinokio with MLX Video Transcription for free local transcription

## Skills Overview

| Skill | Purpose |
|-------|---------|
| `statics-briefer` | Static ad briefs using TEEP + Three Selves + Emotional Zones |
| `native-ad-creative` | Native ad headlines + image direction via direct response psychology |
| `listicle-writer` | Research-driven listicle landing pages (9-gate workflow) |
| `editorial-image-prompts` | Editorial-style image prompts that look like content, not ads |
| `story-selling` | Meta ad scripts where the story earns the sale |
| `critique` | Evaluate any work against a chosen skill/framework |
| `gemini-api` | Google Gemini for text, image analysis, video analysis, image generation |

## License

Private. Shared by invitation only.
