/**
 * ============================================================================
 * GEMINI API - Universal Google Gemini Interface
 * ============================================================================
 *
 * A flexible utility for interacting with Google's Gemini API.
 * Supports text generation, image analysis, video analysis, image generation,
 * and multimodal prompts.
 *
 * CAPABILITIES:
 *   - Text generation and chat
 *   - Image analysis (pass images for description, extraction, etc.)
 *   - Video analysis (pass videos for scene breakdown, transcription, etc.)
 *   - Image generation (Nano Banana Pro - gemini-3-pro-image-preview)
 *   - Multimodal prompts (combine text + images + video)
 *
 * USAGE:
 *   As module:
 *     import { generate, analyzeImage, analyzeVideo, generateImage } from './gemini-api.js';
 *
 *   As CLI:
 *     node gemini-api.js "your prompt here"
 *     node gemini-api.js "describe this" --image path/to/image.jpg
 *     node gemini-api.js "analyze this video" --video path/to/video.mp4
 *     node gemini-api.js "a cat on a beach" --generate-image --output cat.png
 *
 * REQUIRES:
 *   npm install @google/generative-ai fs-extra dotenv
 *   GEMINI_API_KEY in .env
 *
 * ============================================================================
 */

import { GoogleGenerativeAI } from '@google/generative-ai';
import fs from 'fs-extra';
import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load environment variables
dotenv.config({ path: path.join(__dirname, '.env') });

// ============================================================================
// GEMINI CLIENT
// ============================================================================

let genAI = null;

function getClient() {
  if (!genAI && process.env.GEMINI_API_KEY) {
    genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
  }
  if (!genAI) {
    throw new Error('GEMINI_API_KEY not set. Add it to your .env file.');
  }
  return genAI;
}

/**
 * Get a Gemini model instance
 * @param {string} modelName - Model to use (default: gemini-2.5-pro)
 */
function getModel(modelName = 'gemini-2.5-pro') {
  return getClient().getGenerativeModel({ model: modelName });
}

// ============================================================================
// CORE GENERATION
// ============================================================================

/**
 * Generate content with Gemini (text, images, video, or combination)
 * @param {string} prompt - Text prompt
 * @param {Object} options - Optional media and settings
 * @param {string} options.imagePath - Path to image file
 * @param {string} options.videoPath - Path to video file
 * @param {string} options.model - Model name (default: gemini-2.5-pro)
 * @returns {Promise<string>} Generated text response
 */
export async function generate(prompt, options = {}) {
  const model = getModel(options.model);
  const contentParts = [prompt];

  // Add video if provided
  if (options.videoPath && await fs.pathExists(options.videoPath)) {
    const videoData = await fs.readFile(options.videoPath);
    const ext = path.extname(options.videoPath).toLowerCase();
    const mimeType = ext === '.mov' ? 'video/quicktime' :
                     ext === '.avi' ? 'video/x-msvideo' :
                     ext === '.webm' ? 'video/webm' :
                     'video/mp4';
    contentParts.push({
      inlineData: {
        data: videoData.toString('base64'),
        mimeType
      }
    });
  }

  // Add image if provided
  if (options.imagePath && await fs.pathExists(options.imagePath)) {
    const imageData = await fs.readFile(options.imagePath);
    const ext = path.extname(options.imagePath).toLowerCase();
    const mimeType = ext === '.png' ? 'image/png' :
                     ext === '.gif' ? 'image/gif' :
                     ext === '.webp' ? 'image/webp' :
                     'image/jpeg';
    contentParts.push({
      inlineData: {
        data: imageData.toString('base64'),
        mimeType
      }
    });
  }

  const result = await model.generateContent(contentParts);
  const response = await result.response;
  return response.text();
}

/**
 * Generate with JSON output (parses response as JSON)
 * @param {string} prompt - Prompt that requests JSON output
 * @param {Object} options - Same as generate()
 * @returns {Promise<Object>} Parsed JSON response
 */
export async function generateJSON(prompt, options = {}) {
  const fullPrompt = `${prompt}\n\nReturn ONLY valid JSON, no markdown formatting or code blocks.`;
  const text = await generate(fullPrompt, options);

  // Clean up markdown if present
  let cleaned = text.trim();
  if (cleaned.startsWith('```json')) {
    cleaned = cleaned.replace(/```json\n?/g, '').replace(/```\n?$/g, '');
  } else if (cleaned.startsWith('```')) {
    cleaned = cleaned.replace(/```\n?/g, '');
  }

  return JSON.parse(cleaned);
}

// ============================================================================
// CONVENIENCE METHODS
// ============================================================================

/**
 * Analyze an image with a prompt
 * @param {string} imagePath - Path to image
 * @param {string} prompt - What to analyze (default: describe the image)
 * @returns {Promise<string>} Analysis result
 */
export async function analyzeImage(imagePath, prompt = 'Describe this image in detail.') {
  return generate(prompt, { imagePath });
}

/**
 * Analyze a video with a prompt
 * @param {string} videoPath - Path to video
 * @param {string} prompt - What to analyze (default: describe the video)
 * @returns {Promise<string>} Analysis result
 */
export async function analyzeVideo(videoPath, prompt = 'Describe this video in detail, including key scenes and any text or speech.') {
  return generate(prompt, { videoPath });
}

/**
 * Extract text from an image (OCR)
 * @param {string} imagePath - Path to image
 * @returns {Promise<string>} Extracted text
 */
export async function extractText(imagePath) {
  return generate('Extract and return all text visible in this image. Return only the extracted text, nothing else.', { imagePath });
}

/**
 * Transcribe speech from a video
 * @param {string} videoPath - Path to video
 * @returns {Promise<string>} Transcription
 */
export async function transcribe(videoPath) {
  return generate('Transcribe all spoken words in this video. Return only the transcription, nothing else.', { videoPath });
}

/**
 * Simple text generation (no media)
 * @param {string} prompt - Text prompt
 * @returns {Promise<string>} Generated response
 */
export async function text(prompt) {
  return generate(prompt);
}

// ============================================================================
// IMAGE GENERATION (Nano Banana Pro)
// ============================================================================

/**
 * Generate an image from a text prompt using Nano Banana Pro
 * @param {string} prompt - Text description of the image to generate
 * @param {Object} options - Generation options
 * @param {string} options.outputPath - Path to save the generated image
 * @param {string} options.model - Model name (default: gemini-2.0-flash-exp-image-generation)
 * @returns {Promise<{imagePath: string, text: string|null}>} Path to saved image and any text response
 */
export async function generateImage(prompt, options = {}) {
  const modelName = options.model || 'gemini-2.0-flash-exp-image-generation';
  const model = getClient().getGenerativeModel({
    model: modelName,
    generationConfig: {
      responseModalities: ['Text', 'Image']
    }
  });

  const result = await model.generateContent(prompt);
  const response = await result.response;

  let imagePath = null;
  let textResponse = null;

  // Process response parts
  for (const part of response.candidates[0].content.parts) {
    if (part.text) {
      textResponse = part.text;
    } else if (part.inlineData) {
      // Extract and save image
      const imageData = part.inlineData.data;
      const mimeType = part.inlineData.mimeType || 'image/png';
      const ext = mimeType.includes('jpeg') ? '.jpg' :
                  mimeType.includes('webp') ? '.webp' : '.png';

      // Determine output path
      if (options.outputPath) {
        imagePath = options.outputPath;
      } else {
        // Generate a default filename
        const timestamp = Date.now();
        imagePath = `generated-image-${timestamp}${ext}`;
      }

      // Save the image
      const buffer = Buffer.from(imageData, 'base64');
      await fs.writeFile(imagePath, buffer);
    }
  }

  return { imagePath, text: textResponse };
}

/**
 * Generate multiple images from a prompt
 * @param {string} prompt - Text description
 * @param {number} count - Number of images to generate
 * @param {string} outputDir - Directory to save images
 * @param {string} filenamePrefix - Prefix for filenames
 * @returns {Promise<Array<{imagePath: string, text: string|null}>>} Array of results
 */
export async function generateImages(prompt, count, outputDir, filenamePrefix = 'image') {
  await fs.ensureDir(outputDir);

  const results = [];
  for (let i = 1; i <= count; i++) {
    const outputPath = path.join(outputDir, `${filenamePrefix}-${i}.png`);
    console.log(`Generating image ${i}/${count}...`);

    try {
      const result = await generateImage(prompt, { outputPath });
      results.push(result);
      console.log(`  Saved: ${result.imagePath}`);
    } catch (error) {
      console.error(`  Error generating image ${i}: ${error.message}`);
      results.push({ imagePath: null, text: null, error: error.message });
    }
  }

  return results;
}

// ============================================================================
// CLI
// ============================================================================

async function main() {
  const args = process.argv.slice(2);

  if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
    console.log(`
Gemini API - Universal Google Gemini Interface

Usage:
  node gemini-api.js "your prompt"
  node gemini-api.js "describe this" --image path/to/image.jpg
  node gemini-api.js "analyze this" --video path/to/video.mp4
  node gemini-api.js "a sunset over mountains" --generate-image --output sunset.png

Options:
  --image <path>      Include an image in the prompt (for analysis)
  --video <path>      Include a video in the prompt (for analysis)
  --generate-image    Generate an image from the prompt (Nano Banana Pro)
  --output <path>     Output path for generated image (default: generated-image-{timestamp}.png)
  --count <n>         Generate multiple images (use with --generate-image and --output-dir)
  --output-dir <dir>  Directory for multiple images (use with --count)
  --json              Parse response as JSON
  --model <name>      Use specific model (default: gemini-2.5-pro for text, gemini-2.0-flash-exp-image-generation for images)

Examples:
  node gemini-api.js "Write a haiku about coding"
  node gemini-api.js "What's in this image?" --image photo.jpg
  node gemini-api.js "Summarize this video" --video clip.mp4
  node gemini-api.js "a cat wearing sunglasses" --generate-image --output cat.png
  node gemini-api.js "product photography of nasal inhaler" --generate-image --count 3 --output-dir ./images

Environment:
  GEMINI_API_KEY   Required - Your Gemini API key (in .env file)
`);
    process.exit(0);
  }

  // Parse arguments
  let prompt = '';
  let imagePath = null;
  let videoPath = null;
  let jsonOutput = false;
  let model = null;
  let generateImageMode = false;
  let outputPath = null;
  let outputDir = null;
  let count = 1;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--image' && args[i + 1]) {
      imagePath = args[++i];
    } else if (args[i] === '--video' && args[i + 1]) {
      videoPath = args[++i];
    } else if (args[i] === '--json') {
      jsonOutput = true;
    } else if (args[i] === '--model' && args[i + 1]) {
      model = args[++i];
    } else if (args[i] === '--generate-image') {
      generateImageMode = true;
    } else if (args[i] === '--output' && args[i + 1]) {
      outputPath = args[++i];
    } else if (args[i] === '--output-dir' && args[i + 1]) {
      outputDir = args[++i];
    } else if (args[i] === '--count' && args[i + 1]) {
      count = parseInt(args[++i], 10);
    } else if (!args[i].startsWith('--')) {
      prompt = args[i];
    }
  }

  if (!prompt) {
    console.error('Error: No prompt provided');
    process.exit(1);
  }

  if (!process.env.GEMINI_API_KEY) {
    console.error('Error: GEMINI_API_KEY not set in environment');
    process.exit(1);
  }

  try {
    // Image generation mode
    if (generateImageMode) {
      console.log('Generating image(s)...\n');

      if (count > 1 && outputDir) {
        // Multiple images
        const results = await generateImages(prompt, count, outputDir);
        console.log(`\nGenerated ${results.filter(r => r.imagePath).length}/${count} images`);
      } else {
        // Single image
        const options = {};
        if (outputPath) options.outputPath = outputPath;
        if (model) options.model = model;

        const result = await generateImage(prompt, options);
        console.log(`Image saved: ${result.imagePath}`);
        if (result.text) {
          console.log(`Response: ${result.text}`);
        }
      }
      return;
    }

    // Text/analysis mode
    console.log('Generating...\n');

    const options = { model: model || 'gemini-2.5-pro' };
    if (imagePath) options.imagePath = imagePath;
    if (videoPath) options.videoPath = videoPath;

    let result;
    if (jsonOutput) {
      result = await generateJSON(prompt, options);
      console.log(JSON.stringify(result, null, 2));
    } else {
      result = await generate(prompt, options);
      console.log(result);
    }
  } catch (error) {
    console.error('Error:', error.message);
    process.exit(1);
  }
}

// Run CLI if executed directly
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main();
}
