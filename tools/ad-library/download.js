#!/usr/bin/env node
/**
 * Download all media (images + videos) from scraped ad library data.
 *
 * Usage:
 *   node download.js --data /path/to/brand-data
 *
 * Expects ads-raw.json in the data directory.
 * Creates downloads/ subdirectory with media organized by ad ID.
 */

import axios from 'axios';
import fs from 'fs-extra';
import path from 'path';

function parseArgs() {
  const args = process.argv.slice(2);
  const parsed = {};
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--data' && args[i + 1]) parsed.data = args[++i];
  }
  return parsed;
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

async function main() {
  const args = parseArgs();

  if (!args.data) {
    console.error('Usage: node download.js --data /path/to/brand-data');
    process.exit(1);
  }

  const dataDir = args.data;
  const jsonPath = path.join(dataDir, 'ads-raw.json');

  if (!await fs.pathExists(jsonPath)) {
    console.error(`No ads-raw.json found in ${dataDir}. Run scrape.js first.`);
    process.exit(1);
  }

  const ads = await fs.readJSON(jsonPath);
  const downloadsDir = path.join(dataDir, 'downloads');
  await fs.ensureDir(downloadsDir);

  console.log(`Downloading media for ${ads.length} ads...\n`);

  let images = 0, videos = 0, failed = 0;

  for (let i = 0; i < ads.length; i++) {
    const ad = ads[i];
    const adId = String(ad.ad_archive_id || `unknown_${i}`);
    const adDir = path.join(downloadsDir, adId);
    await fs.ensureDir(adDir);

    // Download from cards (carousel ads)
    const cards = ad.snapshot?.cards || [];
    for (let j = 0; j < cards.length; j++) {
      const card = cards[j];
      const imgUrl = card.original_image_url || card.resized_image_url;
      if (imgUrl) {
        try {
          await downloadFile(imgUrl, path.join(adDir, `image_${j + 1}.jpg`));
          images++;
        } catch (e) { failed++; }
      }
      const vidUrl = card.video_hd_url || card.video_sd_url;
      if (vidUrl) {
        try {
          await downloadFile(vidUrl, path.join(adDir, `video_${j + 1}.mp4`));
          videos++;
        } catch (e) { failed++; }
      }
    }

    // Snapshot-level images
    const snapImages = ad.snapshot?.images || [];
    for (let j = 0; j < snapImages.length; j++) {
      const url = snapImages[j].original_image_url || snapImages[j].resized_image_url;
      if (url) {
        try {
          await downloadFile(url, path.join(adDir, `snap_image_${j + 1}.jpg`));
          images++;
        } catch (e) { failed++; }
      }
    }

    // Snapshot-level videos
    const snapVideos = ad.snapshot?.videos || [];
    for (let j = 0; j < snapVideos.length; j++) {
      const url = snapVideos[j].video_url || snapVideos[j].original_video_url;
      if (url) {
        try {
          await downloadFile(url, path.join(adDir, `snap_video_${j + 1}.mp4`));
          videos++;
        } catch (e) { failed++; }
      }
    }

    if ((i + 1) % 10 === 0 || i === ads.length - 1) {
      console.log(`  ${i + 1}/${ads.length} ads | ${images} images | ${videos} videos | ${failed} failed`);
    }
  }

  console.log(`\nDONE: ${images} images, ${videos} videos downloaded (${failed} failed)`);
  console.log(`Media at: ${downloadsDir}/`);
  console.log(`\nNext: node analyze.js --data "${dataDir}"`);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
