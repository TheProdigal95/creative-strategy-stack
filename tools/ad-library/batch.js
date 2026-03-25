#!/usr/bin/env node
/**
 * Batch scrape + download for multiple brands from a text file.
 *
 * Usage:
 *   node batch.js --file brands.txt [--output /path/to/data]
 *
 * brands.txt format (one brand per line):
 *   BrandName | https://www.facebook.com/ads/library/?...&view_all_page_id=123
 *   Another Brand | https://www.facebook.com/ads/library/?...&view_all_page_id=456
 *
 * For each brand: scrapes via Apify, downloads all media.
 * After ALL brands are done, run analysis (Gemini or MLX) separately.
 */

import axios from 'axios';
import fs from 'fs-extra';
import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, '.env') });

const APIFY_API_BASE = 'https://api.apify.com/v2';
const APIFY_ACTOR_ID = 'curious_coder~facebook-ads-library-scraper';
const APIFY_TOKEN = process.env.APIFY_TOKEN;

function parseArgs() {
  const args = process.argv.slice(2);
  const parsed = {};
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--file' && args[i + 1]) parsed.file = args[++i];
    else if (args[i] === '--output' && args[i + 1]) parsed.output = args[++i];
    else if (args[i] === '--scrape-only') parsed.scrapeOnly = true;
  }
  return parsed;
}

function slugify(name) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
}

function parseBrandsFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf-8');
  return content
    .split('\n')
    .map(line => line.trim())
    .filter(line => line && !line.startsWith('#'))
    .map(line => {
      const [name, url] = line.split('|').map(s => s.trim());
      if (!name || !url) {
        console.warn(`Skipping invalid line: ${line}`);
        return null;
      }
      return { name, url };
    })
    .filter(Boolean);
}

async function downloadFile(url, filePath) {
  const response = await axios({
    method: 'GET',
    url,
    responseType: 'stream',
    timeout: 120000,
    headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' }
  });
  const writer = fs.createWriteStream(filePath);
  response.data.pipe(writer);
  return new Promise((resolve, reject) => {
    writer.on('finish', resolve);
    writer.on('error', reject);
    response.data.on('error', reject);
  });
}

async function scrapeBrand(brand, outputDir) {
  console.log(`\n  [SCRAPE] Starting Apify for ${brand.name}...`);

  const startRes = await axios.post(
    `${APIFY_API_BASE}/acts/${APIFY_ACTOR_ID}/runs?token=${APIFY_TOKEN}`,
    {
      count: 9999,
      scrapeAdDetails: false,
      'scrapePageAds.activeStatus': 'active',
      'scrapePageAds.countryCode': 'ALL',
      urls: [{ url: brand.url }]
    },
    { headers: { 'Content-Type': 'application/json' } }
  );

  const runId = startRes.data.data.id;

  let datasetId;
  while (true) {
    await new Promise(r => setTimeout(r, 5000));
    const statusRes = await axios.get(
      `${APIFY_API_BASE}/actor-runs/${runId}?token=${APIFY_TOKEN}`
    );
    const run = statusRes.data.data;
    const elapsed = Math.floor((Date.now() - new Date(run.startedAt).getTime()) / 1000);
    process.stdout.write(`\r  Waiting... ${run.status} (${elapsed}s)    `);

    if (run.status === 'SUCCEEDED') {
      datasetId = run.defaultDatasetId;
      console.log(`\n  Scrape done!`);
      break;
    } else if (run.status === 'FAILED' || run.status === 'ABORTED') {
      throw new Error(`Apify run ${run.status}`);
    }
  }

  const dataRes = await axios.get(
    `${APIFY_API_BASE}/datasets/${datasetId}/items?token=${APIFY_TOKEN}&limit=9999`
  );
  const ads = dataRes.data;
  const jsonPath = path.join(outputDir, 'ads-raw.json');
  await fs.writeJSON(jsonPath, ads, { spaces: 2 });
  console.log(`  ${ads.length} ads saved`);
  return ads;
}

async function downloadBrandMedia(ads, outputDir) {
  const downloadsDir = path.join(outputDir, 'downloads');
  await fs.ensureDir(downloadsDir);

  let images = 0, videos = 0, failed = 0;

  for (let i = 0; i < ads.length; i++) {
    const ad = ads[i];
    const adId = String(ad.ad_archive_id || `unknown_${i}`);
    const adDir = path.join(downloadsDir, adId);
    await fs.ensureDir(adDir);

    const cards = ad.snapshot?.cards || [];
    for (let j = 0; j < cards.length; j++) {
      const card = cards[j];
      const imgUrl = card.original_image_url || card.resized_image_url;
      if (imgUrl) {
        try { await downloadFile(imgUrl, path.join(adDir, `image_${j + 1}.jpg`)); images++; }
        catch (e) { failed++; }
      }
      const vidUrl = card.video_hd_url || card.video_sd_url;
      if (vidUrl) {
        try { await downloadFile(vidUrl, path.join(adDir, `video_${j + 1}.mp4`)); videos++; }
        catch (e) { failed++; }
      }
    }

    const snapImages = ad.snapshot?.images || [];
    for (let j = 0; j < snapImages.length; j++) {
      const url = snapImages[j].original_image_url || snapImages[j].resized_image_url;
      if (url) {
        try { await downloadFile(url, path.join(adDir, `snap_image_${j + 1}.jpg`)); images++; }
        catch (e) { failed++; }
      }
    }

    const snapVideos = ad.snapshot?.videos || [];
    for (let j = 0; j < snapVideos.length; j++) {
      const url = snapVideos[j].video_url || snapVideos[j].original_video_url;
      if (url) {
        try { await downloadFile(url, path.join(adDir, `snap_video_${j + 1}.mp4`)); videos++; }
        catch (e) { failed++; }
      }
    }
  }

  console.log(`  Downloaded: ${images} images, ${videos} videos (${failed} failed)`);
}

async function main() {
  const args = parseArgs();

  if (!args.file) {
    console.error('Usage: node batch.js --file brands.txt [--output /path/to/data] [--scrape-only]');
    console.error('\nbrands.txt format (one per line):');
    console.error('  BrandName | https://www.facebook.com/ads/library/?...');
    process.exit(1);
  }

  if (!APIFY_TOKEN) {
    console.error('APIFY_TOKEN not set in .env');
    process.exit(1);
  }

  const brands = parseBrandsFile(args.file);
  const baseOutput = args.output || path.join(__dirname, 'data');

  console.log('='.repeat(60));
  console.log(`BATCH AD LIBRARY PIPELINE`);
  console.log(`Brands: ${brands.length}`);
  console.log(`Output: ${baseOutput}`);
  console.log('='.repeat(60));

  const results = [];

  for (let i = 0; i < brands.length; i++) {
    const brand = brands[i];
    const brandSlug = slugify(brand.name);
    const outputDir = path.join(baseOutput, brandSlug);
    await fs.ensureDir(outputDir);

    console.log(`\n${'─'.repeat(60)}`);
    console.log(`[${i + 1}/${brands.length}] ${brand.name}`);
    console.log(`Output: ${outputDir}`);

    try {
      const ads = await scrapeBrand(brand, outputDir);

      if (!args.scrapeOnly) {
        console.log(`  [DOWNLOAD] Fetching media...`);
        await downloadBrandMedia(ads, outputDir);
      }

      results.push({ brand: brand.name, status: 'OK', ads: ads.length, path: outputDir });
    } catch (e) {
      console.error(`  FAILED: ${e.message}`);
      results.push({ brand: brand.name, status: 'FAILED', error: e.message });
    }
  }

  console.log(`\n${'='.repeat(60)}`);
  console.log('BATCH COMPLETE');
  console.log('='.repeat(60));
  for (const r of results) {
    if (r.status === 'OK') {
      console.log(`  ✓ ${r.brand}: ${r.ads} ads → ${r.path}`);
    } else {
      console.log(`  ✗ ${r.brand}: ${r.error}`);
    }
  }
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
