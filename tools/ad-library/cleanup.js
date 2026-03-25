#!/usr/bin/env node
/**
 * Clean up downloaded media to free disk space.
 * Keeps ads-raw.json and analysis/ files. Deletes downloads/ (images + videos).
 *
 * Usage:
 *   node cleanup.js --data /path/to/brand-data          # clean one brand
 *   node cleanup.js --data /path/to/data --all           # clean all brands in data dir
 */

import fs from 'fs-extra';
import path from 'path';

function parseArgs() {
  const args = process.argv.slice(2);
  const parsed = {};
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--data' && args[i + 1]) parsed.data = args[++i];
    else if (args[i] === '--all') parsed.all = true;
  }
  return parsed;
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

async function getDirSize(dirPath) {
  let size = 0;
  if (!await fs.pathExists(dirPath)) return 0;
  const files = await fs.readdir(dirPath, { recursive: true });
  for (const file of files) {
    try {
      const stats = await fs.stat(path.join(dirPath, file));
      if (stats.isFile()) size += stats.size;
    } catch (e) { /* skip */ }
  }
  return size;
}

async function cleanBrand(brandDir) {
  const downloadsDir = path.join(brandDir, 'downloads');
  if (!await fs.pathExists(downloadsDir)) {
    console.log(`  No downloads/ to clean in ${path.basename(brandDir)}`);
    return 0;
  }

  const size = await getDirSize(downloadsDir);
  await fs.remove(downloadsDir);
  console.log(`  Cleaned ${path.basename(brandDir)}: freed ${formatSize(size)}`);
  return size;
}

async function main() {
  const args = parseArgs();

  if (!args.data) {
    console.error('Usage: node cleanup.js --data /path/to/brand-data [--all]');
    process.exit(1);
  }

  let totalFreed = 0;

  if (args.all) {
    const entries = await fs.readdir(args.data, { withFileTypes: true });
    const dirs = entries.filter(e => e.isDirectory());
    console.log(`Cleaning media for ${dirs.length} brands...\n`);
    for (const dir of dirs) {
      totalFreed += await cleanBrand(path.join(args.data, dir.name));
    }
  } else {
    totalFreed = await cleanBrand(args.data);
  }

  console.log(`\nTotal freed: ${formatSize(totalFreed)}`);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
