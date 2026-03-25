# Ad Library Pull & Analysis

Pull a brand's entire Meta Ad Library, download all media, and analyze every creative. This is the full pipeline used for competitive ad audits and PVP research.

## Prerequisites

**First-time setup:**
```bash
cd tools/ad-library && npm install
cd tools/gemini-api && npm install
```

**API keys:** Copy `.env.example` to each tool directory and add your keys:
```bash
cp .env.example tools/ad-library/.env
cp .env.example tools/gemini-api/.env
```

Then edit both `.env` files with your actual keys:
```
APIFY_TOKEN=your_token
GEMINI_API_KEY=your_key
```

## Batch processing (10-20 brands at once)

When the user pastes multiple Ad Library URLs, create a `brands.txt` file and run batch mode.

### Step 1: Create the brands file

Write a `brands.txt` file with one brand per line, pipe-separated:
```
BrandName | https://www.facebook.com/ads/library/?...&view_all_page_id=123
Another Brand | https://www.facebook.com/ads/library/?...&view_all_page_id=456
```

Lines starting with `#` are ignored. Save this file anywhere convenient (e.g., in the sprint folder).

### Step 2: Run the batch

```bash
node tools/ad-library/batch.js --file /path/to/brands.txt
```

Optional: specify output directory:
```bash
node tools/ad-library/batch.js --file /path/to/brands.txt --output /path/to/data
```

Scrape-only mode (skip media download, useful when you only need the ad copy/headlines from JSON):
```bash
node tools/ad-library/batch.js --file /path/to/brands.txt --scrape-only
```

**Default output:** `tools/ad-library/data/[brand-slug]/` for each brand.

**What it does:** For each brand sequentially: scrapes via Apify (2-10 min), downloads all media. Reports results at the end.

## Single brand processing

For a single brand, use the individual scripts:

```bash
# Scrape
node tools/ad-library/scrape.js --brand "BrandName" --url "AD_LIBRARY_URL"

# Download media
node tools/ad-library/download.js --data tools/ad-library/data/brand-slug

# Analyze with Gemini (full visual analysis — use for deep dives, not for every PVP)
node tools/ad-library/analyze.js --data tools/ad-library/data/brand-slug
```

**How to get the Ad Library URL:**
1. Go to https://www.facebook.com/ads/library/
2. Search for the brand name
3. Click on their page
4. Copy the full URL from the browser bar — it should contain `view_all_page_id=...`

## Choosing the right analysis depth

### Lean analysis (for PVP work — messaging focused)

For PVP sprints where you're mapping messaging angles across 10-20 brands, you do NOT need full Gemini analysis of every creative. The ad copy and headlines are already in `ads-raw.json`.

**Workflow:**
1. Scrape all brands (batch mode, or `--scrape-only` to skip media download)
2. Read `ads-raw.json` for each brand — the `snapshot.cards[].body` field has ad copy, `snapshot.cards[].title` has headlines, `snapshot.cards[].cta_text` has CTAs
3. Categorize the ad copy by messaging angle (see Messaging Analysis Framework below)
4. For video ads where you want the voiceover, download the videos and transcribe them:
   ```bash
   # Local transcription (requires Apple Silicon + MLX — see tools/mlx-transcribe.py)
   python3 tools/mlx-transcribe.py /path/to/brand-data/downloads/ --output /path/to/transcripts/

   # OR use Gemini transcription (works anywhere, requires API key)
   node tools/gemini-api/gemini-api.js "Transcribe this video" --video /path/to/video.mp4
   ```
5. Clean up media when done

**This approach is free (no Gemini costs) and fast.** Use it for the niche-level mapping.

### Deep analysis (for full audits)

For deep competitive audits or when preparing a Tier 1 Strategy Sprint deliverable, run the full Gemini analysis:

1. Scrape + download
2. Run `analyze.js` for full visual + script breakdowns
3. This gives you image text overlays, video scripts, visual patterns
4. Clean up media when done

## Messaging Analysis Framework

When analyzing ads for messaging angles (whether from JSON ad copy or full creative analysis), categorize by:

**Primary angle** — What's the main claim or benefit?
- Product feature (ingredient, technology, formula)
- Outcome/result (weight loss, muscle gain, clear skin)
- Convenience (time savings, ease of use)
- Price/value (cost per serving, discount)
- Social proof (reviews, testimonials, before/after)
- Identity/belonging (lifestyle, community, values)
- Fear/risk (what happens if you don't act)
- Comparison (us vs. them, old way vs. new way)

**Emotional territory** — What feeling does it target?
- Aspiration (who you could become)
- Pain/frustration (current suffering)
- Fear (what you might lose)
- Belonging (being part of something)
- Pride (what you've achieved)
- Relief (the problem going away)

**What to look for across a niche:**
- Which angles do ALL brands cluster on? (messaging poverty territory)
- Which angles does NO brand touch? (potential whitespace)
- Which angles have strong customer language support but no ad coverage? (proven demand, no supply)
- Which brands have the narrowest angle diversity? (prime PVP targets)

**Flexibility:** These categories are starting points, not rigid taxonomy. Every niche will surface its own patterns. Add categories that fit. Merge ones that overlap. The goal is to see the landscape clearly, not to fill in a template.

## Storage cleanup

Media files (images + videos) are the storage hog. After you've analyzed what you need, clean them up.

**Clean one brand:**
```bash
node tools/ad-library/cleanup.js --data tools/ad-library/data/brand-slug
```

**Clean all brands:**
```bash
node tools/ad-library/cleanup.js --data tools/ad-library/data --all
```

This deletes the `downloads/` folder (media) but keeps `ads-raw.json` (ad copy, structured data) and `analysis/` (Gemini analysis markdown files). Those are small and worth keeping for reference.

**When to clean up:**
- After batch PVP work: clean up all brands once you've mapped the messaging landscape
- After deep analysis: clean up once the Ad Library Breakdown doc is written
- Rule of thumb: if you've extracted what you need into documents, the media can go

## Tips

- Batch scraping 20 brands takes roughly 40-120 minutes total (Apify processes sequentially)
- For PVP work, `--scrape-only` mode is usually enough — the JSON has all the messaging data
- Download media only for brands where you need visual/video analysis
- MLX transcription of video voiceovers is free and local — use it instead of Gemini for messaging-focused work
- If MLX isn't available (no Apple Silicon or no Pinokio), Gemini transcription works as a drop-in replacement
- If any step gets interrupted, it's safe to re-run — scrape creates new data, download overwrites, analyze resumes
