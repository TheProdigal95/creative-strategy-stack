#!/usr/bin/env node
/**
 * Scrape a brand's Meta Ad Library via Apify.
 *
 * Usage:
 *   node scrape.js --brand "Huel" --url "https://www.facebook.com/ads/library/?...&view_all_page_id=123"
 *   node scrape.js --brand "Huel" --page-id 2281559212068421
 *   node scrape.js --brand "Huel" --url "..." --output /path/to/data
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
    if (args[i] === '--brand' && args[i + 1]) parsed.brand = args[++i];
    else if (args[i] === '--url' && args[i + 1]) parsed.url = args[++i];
    else if (args[i] === '--page-id' && args[i + 1]) parsed.pageId = args[++i];
    else if (args[i] === '--output' && args[i + 1]) parsed.output = args[++i];
  }
  return parsed;
}

function slugify(name) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
}

async function main() {
  const args = parseArgs();

  if (!args.brand) {
    console.error('Usage: node scrape.js --brand "BrandName" --url "Ad Library URL" [--output /path/to/data]');
    console.error('   or: node scrape.js --brand "BrandName" --page-id 12345 [--output /path/to/data]');
    process.exit(1);
  }

  if (!APIFY_TOKEN) {
    console.error('APIFY_TOKEN not set. Create a .env file in this directory with your Apify token.');
    process.exit(1);
  }

  // Build the Ad Library URL if only page ID was provided
  let adLibraryUrl = args.url;
  if (!adLibraryUrl && args.pageId) {
    adLibraryUrl = `https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&is_targeted_country=false&media_type=all&search_type=page&sort_data[mode]=total_impressions&sort_data[direction]=desc&view_all_page_id=${args.pageId}`;
  }

  if (!adLibraryUrl) {
    console.error('Provide either --url or --page-id');
    process.exit(1);
  }

  const brandSlug = slugify(args.brand);
  const outputDir = args.output || path.join(__dirname, 'data', brandSlug);
  await fs.ensureDir(outputDir);

  console.log('='.repeat(60));
  console.log(`AD LIBRARY SCRAPER: ${args.brand}`);
  console.log('='.repeat(60));
  console.log(`Output: ${outputDir}\n`);

  // Step 1: Start Apify scrape
  console.log('[1/3] Starting Apify scraper...');
  const startRes = await axios.post(
    `${APIFY_API_BASE}/acts/${APIFY_ACTOR_ID}/runs?token=${APIFY_TOKEN}`,
    {
      count: 9999,
      scrapeAdDetails: false,
      'scrapePageAds.activeStatus': 'active',
      'scrapePageAds.countryCode': 'ALL',
      urls: [{ url: adLibraryUrl }]
    },
    { headers: { 'Content-Type': 'application/json' } }
  );

  const runId = startRes.data.data.id;
  console.log(`  Run started: ${runId}`);

  // Step 2: Poll until done
  console.log('\n[2/3] Waiting for Apify to finish...');
  let datasetId;
  while (true) {
    await new Promise(r => setTimeout(r, 5000));
    const statusRes = await axios.get(
      `${APIFY_API_BASE}/actor-runs/${runId}?token=${APIFY_TOKEN}`
    );
    const run = statusRes.data.data;
    const elapsed = Math.floor((Date.now() - new Date(run.startedAt).getTime()) / 1000);
    process.stdout.write(`\r  Status: ${run.status} (${elapsed}s elapsed)    `);

    if (run.status === 'SUCCEEDED') {
      datasetId = run.defaultDatasetId;
      console.log('\n  Scraping complete!');
      break;
    } else if (run.status === 'FAILED' || run.status === 'ABORTED') {
      console.error(`\n  Run ${run.status}`);
      process.exit(1);
    }
  }

  // Step 3: Fetch and save results
  console.log('\n[3/3] Fetching dataset...');
  const dataRes = await axios.get(
    `${APIFY_API_BASE}/datasets/${datasetId}/items?token=${APIFY_TOKEN}&limit=9999`
  );
  const ads = dataRes.data;

  const jsonPath = path.join(outputDir, 'ads-raw.json');
  await fs.writeJSON(jsonPath, ads, { spaces: 2 });

  console.log(`\n${'='.repeat(60)}`);
  console.log(`DONE: ${ads.length} ads scraped`);
  console.log(`Raw JSON: ${jsonPath}`);
  console.log(`\nNext: node download.js --data "${outputDir}"`);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
