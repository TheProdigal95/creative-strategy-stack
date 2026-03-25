#!/usr/bin/env node
/**
 * Analyze downloaded ad media with Gemini (images + videos).
 *
 * Usage:
 *   node analyze.js --data /path/to/brand-data
 *
 * Expects ads-raw.json and downloads/ in the data directory.
 * Creates analysis/ subdirectory with per-ad markdown analysis files.
 * Resume-capable: skips ads that already have analysis files.
 */

import fs from 'fs-extra';
import path from 'path';
import { fileURLToPath } from 'url';
import { GoogleGenerativeAI } from '@google/generative-ai';
import dotenv from 'dotenv';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, '.env') });

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
const model = genAI.getGenerativeModel({ model: 'gemini-2.5-flash' });

const VIDEO_PROMPT = `Please watch the attached video, and convert it into a script with 1 column for the visual action that's happening, 1 column for the voiceover that's happening, and 1 column for the on-screen captions.

Format as a markdown table with columns: | Timestamp | Visual Action | Voiceover | On-Screen Captions |

Be thorough and capture every scene transition, every spoken word, and every text overlay.`;

const IMAGE_PROMPT = `Analyze this Facebook ad image in detail:

1. **Visual Description**: What's in the image (product, people, setting, layout)
2. **All Text**: Every piece of text visible in the image (headlines, body copy, CTAs, fine print)
3. **Design Elements**: Colors, fonts, composition, visual hierarchy
4. **Ad Format**: Is this a single image, carousel card, story format, etc.
5. **Key Message**: What is this ad trying to communicate in one sentence`;

function parseArgs() {
  const args = process.argv.slice(2);
  const parsed = {};
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--data' && args[i + 1]) parsed.data = args[++i];
  }
  return parsed;
}

async function analyzeMedia(mediaPath, prompt, adText) {
  const data = await fs.readFile(mediaPath);
  const base64 = data.toString('base64');
  const ext = path.extname(mediaPath).toLowerCase();

  let mimeType;
  if (['.mp4', '.mov'].includes(ext)) mimeType = ext === '.mov' ? 'video/quicktime' : 'video/mp4';
  else if (ext === '.png') mimeType = 'image/png';
  else mimeType = 'image/jpeg';

  const fullPrompt = adText
    ? `${prompt}\n\nAD COPY:\n${adText}`
    : prompt;

  const result = await model.generateContent([
    fullPrompt,
    { inlineData: { data: base64, mimeType } }
  ]);

  return result.response.text();
}

async function main() {
  const args = parseArgs();

  if (!args.data) {
    console.error('Usage: node analyze.js --data /path/to/brand-data');
    process.exit(1);
  }

  if (!process.env.GEMINI_API_KEY) {
    console.error('GEMINI_API_KEY not set. Create a .env file in this directory.');
    process.exit(1);
  }

  const dataDir = args.data;
  const jsonPath = path.join(dataDir, 'ads-raw.json');
  const downloadsDir = path.join(dataDir, 'downloads');
  const analysisDir = path.join(dataDir, 'analysis');

  if (!await fs.pathExists(jsonPath)) {
    console.error(`No ads-raw.json found in ${dataDir}. Run scrape.js first.`);
    process.exit(1);
  }

  const ads = await fs.readJSON(jsonPath);
  await fs.ensureDir(analysisDir);

  // Resume capability: check what's already done
  const existing = new Set(
    (await fs.readdir(analysisDir))
      .filter(f => f.endsWith('_analysis.md'))
      .map(f => f.replace('_analysis.md', ''))
  );

  console.log(`Analyzing ${ads.length} ads with Gemini...`);
  console.log(`Already analyzed: ${existing.size}\n`);

  let analyzed = 0, skipped = 0, failed = 0;

  for (let i = 0; i < ads.length; i++) {
    const ad = ads[i];
    const adId = String(ad.ad_archive_id || `unknown_${i}`);
    const adDir = path.join(downloadsDir, adId);

    if (existing.has(adId)) {
      skipped++;
      continue;
    }

    const files = await fs.pathExists(adDir) ? await fs.readdir(adDir) : [];
    const videoFile = files.find(f => f.endsWith('.mp4'));
    const imageFile = files.find(f => f.endsWith('.jpg') || f.endsWith('.png'));

    if (!videoFile && !imageFile) {
      skipped++;
      continue;
    }

    const adText = ad.snapshot?.cards?.[0]?.body || '';
    const isVideo = !!videoFile;
    const mediaPath = path.join(adDir, videoFile || imageFile);

    // Skip large videos (Gemini limit)
    const stats = await fs.stat(mediaPath);
    const sizeMB = stats.size / (1024 * 1024);
    if (sizeMB > 50) {
      console.log(`  [SKIP] ${adId} - too large (${sizeMB.toFixed(1)}MB)`);
      skipped++;
      continue;
    }

    try {
      const prompt = isVideo ? VIDEO_PROMPT : IMAGE_PROMPT;
      const analysis = await analyzeMedia(mediaPath, prompt, adText);

      const card = ad.snapshot?.cards?.[0] || {};
      const content = `# Ad Analysis: ${adId}

**Page:** ${ad.page_name || 'Unknown'}
**Ad Library URL:** ${ad.ad_library_url || `https://www.facebook.com/ads/library/?id=${adId}`}
**Type:** ${isVideo ? 'Video' : 'Image'}
**Start Date:** ${ad.start_date_formatted || ad.start_date || 'N/A'}
**Status:** ${ad.is_active ? 'Active' : 'Inactive'}
**CTA:** ${card.cta_text || 'N/A'}
**Landing Page:** ${card.link_url || 'N/A'}
**Headline:** ${card.title || 'N/A'}

## Ad Copy
${adText || 'N/A'}

---

## ${isVideo ? 'Video Script Breakdown' : 'Image Analysis'}

${analysis}
`;

      await fs.writeFile(path.join(analysisDir, `${adId}_analysis.md`), content);
      analyzed++;

      console.log(`  [${analyzed + skipped + failed}/${ads.length}] ${adId} - ${isVideo ? 'VIDEO' : 'IMAGE'} (${sizeMB.toFixed(1)}MB) - OK`);

      await new Promise(r => setTimeout(r, 1500));

    } catch (e) {
      failed++;
      console.log(`  [${analyzed + skipped + failed}/${ads.length}] ${adId} - FAILED: ${e.message.substring(0, 100)}`);
      await new Promise(r => setTimeout(r, 5000));
    }
  }

  console.log(`\n${'='.repeat(60)}`);
  console.log(`DONE: ${analyzed} analyzed | ${skipped} skipped | ${failed} failed`);
  console.log(`Analysis files: ${analysisDir}/`);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
