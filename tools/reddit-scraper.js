#!/usr/bin/env node

/**
 * Reddit Scraper using Apify
 *
 * Lightweight Reddit Scraper using Apify
 *
 * A fast, low-token alternative to the full Research Engine. Use this when you
 * need to quickly pull posts and comments from specific Reddit threads or
 * subreddits without running the full 12-step analysis pipeline.
 *
 * Usage:
 *   node tools/reddit-scraper.js <reddit_url> [maxComments] [maxPosts]
 *
 * Examples:
 *   node tools/reddit-scraper.js "https://www.reddit.com/r/dogs/comments/xyz123/my_post/"
 *   node tools/reddit-scraper.js "https://www.reddit.com/r/dogs/comments/xyz123/my_post/" 20
 *   node tools/reddit-scraper.js "https://www.reddit.com/r/dogs/comments/xyz123/my_post/" 20 5
 *
 * Environment:
 *   Requires APIFY_TOKEN in tools/ad-library/.env (same key used by the ad library tools)
 *
 * Output:
 *   Saves results to reddit-scrape-[timestamp].json in current directory
 */

import https from 'https';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load .env from ad-library directory (shares the same APIFY_TOKEN)
try {
    const envPaths = [
        path.join(__dirname, 'ad-library', '.env'),  // tools/ad-library/.env
        path.join(__dirname, '.env'),                  // tools/.env
    ];
    for (const envPath of envPaths) {
        if (fs.existsSync(envPath)) {
            const envContent = fs.readFileSync(envPath, 'utf8');
            envContent.split('\n').forEach(line => {
                const [key, ...valueParts] = line.split('=');
                if (key && valueParts.length) {
                    process.env[key.trim()] = valueParts.join('=').trim();
                }
            });
            break;
        }
    }
} catch (e) {
    // .env not found, continue
}

const APIFY_TOKEN = process.env.APIFY_TOKEN || process.env.APIFY_API_TOKEN;

if (!APIFY_TOKEN) {
    console.error('Error: APIFY_TOKEN not found.');
    console.error('Add it to tools/ad-library/.env (same file used by the ad library tools).');
    process.exit(1);
}

function makeRequest(options, postData = null) {
    return new Promise((resolve, reject) => {
        const req = https.request(options, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                try {
                    resolve({ status: res.statusCode, data: JSON.parse(data) });
                } catch (e) {
                    resolve({ status: res.statusCode, data: data });
                }
            });
        });
        req.on('error', reject);
        if (postData) req.write(postData);
        req.end();
    });
}

async function startScrape(redditUrl, maxComments = 10, maxPosts = 10) {
    const body = {
        debugMode: false,
        ignoreStartUrls: false,
        includeNSFW: true,
        maxComments: maxComments,
        maxCommunitiesCount: 2,
        maxItems: 50,
        maxPostCount: maxPosts,
        maxUserCount: 2,
        proxy: {
            useApifyProxy: true,
            apifyProxyGroups: ["RESIDENTIAL"]
        },
        scrollTimeout: 40,
        searchComments: false,
        searchCommunities: false,
        searchPosts: true,
        searchUsers: false,
        skipComments: false,
        skipCommunity: false,
        skipUserPosts: false,
        sort: "new",
        startUrls: [{ url: redditUrl }]
    };

    const postData = JSON.stringify(body);

    const options = {
        hostname: 'api.apify.com',
        port: 443,
        path: `/v2/acts/trudax~reddit-scraper-lite/runs?token=${APIFY_TOKEN}`,
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Content-Length': Buffer.byteLength(postData)
        }
    };

    console.log('Starting Reddit scrape...');
    console.log(`URL: ${redditUrl}`);
    console.log(`Max comments: ${maxComments}, Max posts: ${maxPosts}`);

    const response = await makeRequest(options, postData);

    if (response.status !== 201) {
        throw new Error(`Failed to start scrape: ${response.status} - ${JSON.stringify(response.data)}`);
    }

    return response.data;
}

async function waitForCompletion(runId) {
    const options = {
        hostname: 'api.apify.com',
        port: 443,
        path: `/v2/actor-runs/${runId}?token=${APIFY_TOKEN}`,
        method: 'GET'
    };

    console.log('\nWaiting for scrape to complete...');

    let attempts = 0;
    const maxAttempts = 60; // 5 minutes max wait

    while (attempts < maxAttempts) {
        const response = await makeRequest(options);
        const status = response.data?.data?.status;

        process.stdout.write(`\rStatus: ${status} (${attempts + 1}/${maxAttempts})`);

        if (status === 'SUCCEEDED') {
            console.log('\nScrape completed successfully!');
            return response.data.data;
        }

        if (status === 'FAILED' || status === 'ABORTED' || status === 'TIMED-OUT') {
            throw new Error(`Scrape failed with status: ${status}`);
        }

        await new Promise(resolve => setTimeout(resolve, 5000)); // Wait 5 seconds
        attempts++;
    }

    throw new Error('Timeout waiting for scrape to complete');
}

async function getResults(datasetId) {
    const options = {
        hostname: 'api.apify.com',
        port: 443,
        path: `/v2/datasets/${datasetId}/items?token=${APIFY_TOKEN}`,
        method: 'GET'
    };

    console.log('Fetching results...');
    const response = await makeRequest(options);
    return response.data;
}

function formatResults(results) {
    if (!Array.isArray(results)) {
        return results;
    }

    const formatted = {
        summary: {
            totalItems: results.length,
            posts: results.filter(r => r.dataType === 'post').length,
            comments: results.filter(r => r.dataType === 'comment').length
        },
        posts: [],
        comments: []
    };

    results.forEach(item => {
        if (item.dataType === 'post') {
            formatted.posts.push({
                title: item.title,
                author: item.username,
                subreddit: item.communityName,
                url: item.url,
                score: item.numberOfUpvotes,
                numComments: item.numberOfComments,
                createdAt: item.createdAt,
                body: item.body || item.text || ''
            });
        } else if (item.dataType === 'comment') {
            formatted.comments.push({
                author: item.username,
                body: item.body || item.text || '',
                score: item.numberOfUpvotes,
                createdAt: item.createdAt,
                postTitle: item.postTitle || '',
                url: item.url
            });
        }
    });

    return formatted;
}

async function scrapeReddit(redditUrl, maxComments = 10, maxPosts = 10) {
    try {
        // Start the scrape
        const runData = await startScrape(redditUrl, maxComments, maxPosts);
        const runId = runData.data.id;
        console.log(`Run ID: ${runId}`);

        // Wait for completion
        const completedRun = await waitForCompletion(runId);
        const datasetId = completedRun.defaultDatasetId;

        // Get results
        const results = await getResults(datasetId);
        const formatted = formatResults(results);

        // Save to file
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
        const outputFile = `reddit-scrape-${timestamp}.json`;
        fs.writeFileSync(outputFile, JSON.stringify(formatted, null, 2));
        console.log(`\nResults saved to: ${outputFile}`);

        // Print summary
        console.log('\n=== SUMMARY ===');
        console.log(`Total items: ${formatted.summary.totalItems}`);
        console.log(`Posts: ${formatted.summary.posts}`);
        console.log(`Comments: ${formatted.summary.comments}`);

        if (formatted.posts.length > 0) {
            console.log('\n=== POST ===');
            const post = formatted.posts[0];
            console.log(`Title: ${post.title}`);
            console.log(`Author: ${post.author}`);
            console.log(`Subreddit: r/${post.subreddit}`);
            console.log(`Score: ${post.score} | Comments: ${post.numComments}`);
            if (post.body) {
                console.log(`\nBody:\n${post.body.slice(0, 500)}${post.body.length > 500 ? '...' : ''}`);
            }
        }

        if (formatted.comments.length > 0) {
            console.log('\n=== TOP COMMENTS ===');
            formatted.comments.slice(0, 5).forEach((comment, i) => {
                console.log(`\n[${i + 1}] u/${comment.author} (${comment.score} upvotes)`);
                console.log(comment.body.slice(0, 300) + (comment.body.length > 300 ? '...' : ''));
            });
        }

        return formatted;

    } catch (error) {
        console.error('Error:', error.message);
        process.exit(1);
    }
}

// CLI execution
const args = process.argv.slice(2);

if (args.length === 0) {
    console.log(`
Reddit Scraper (Lightweight) — Quick Reddit scraping via Apify

Usage:
  node tools/reddit-scraper.js <reddit_url> [maxComments] [maxPosts]

Examples:
  node tools/reddit-scraper.js "https://www.reddit.com/r/dogs/comments/xyz123/my_post/"
  node tools/reddit-scraper.js "https://www.reddit.com/r/dogs/comments/xyz123/my_post/" 20
  node tools/reddit-scraper.js "https://www.reddit.com/r/dogs/comments/xyz123/my_post/" 20 5

Arguments:
  reddit_url   - The Reddit post or subreddit URL to scrape
  maxComments  - Maximum comments to fetch (default: 10)
  maxPosts     - Maximum posts to fetch (default: 10)

Note: Uses the same APIFY_TOKEN from tools/ad-library/.env
    `);
    process.exit(0);
}

const url = args[0];
const maxComments = parseInt(args[1]) || 10;
const maxPosts = parseInt(args[2]) || 10;

scrapeReddit(url, maxComments, maxPosts);

export { scrapeReddit };
