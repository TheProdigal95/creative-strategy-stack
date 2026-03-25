---
name: gemini-api
description: Use Google Gemini for text generation, image analysis, video analysis, and image generation
trigger: gemini, use gemini, analyze with gemini, gemini image, gemini video, generate image
---

# Gemini API Skill

Use the Gemini API for tasks Claude can't do natively: analyzing videos, generating images, or running prompts through Gemini.

## Tool Location

The Gemini API wrapper is at `tools/gemini-api/gemini-api.js` relative to the repo root.

**First-time setup:**
```bash
cd tools/gemini-api && npm install
```

Add your API key to `tools/gemini-api/.env`:
```
GEMINI_API_KEY=your_key_here
```

## Commands

### Text generation
```bash
node tools/gemini-api/gemini-api.js "your prompt here"
```

### Image analysis
```bash
node tools/gemini-api/gemini-api.js "describe what you see" --image /path/to/image.jpg
```

### Video analysis
```bash
node tools/gemini-api/gemini-api.js "describe this video in detail including all text, speech, and visual elements" --video /path/to/video.mp4
```

Supported video formats: .mp4, .mov, .avi, .webm

### Image generation (Nano Banana Pro)
```bash
node tools/gemini-api/gemini-api.js "a cat on a beach" --generate-image --output /path/to/output.png
```

### Multiple image generation
```bash
node tools/gemini-api/gemini-api.js "product shot" --generate-image --count 3 --output-dir /path/to/dir
```

### JSON output
Add `--json` flag to any text/analysis command to get structured JSON back.

### Model override
Add `--model model-name` to use a specific model. Defaults:
- Text/analysis: `gemini-2.5-pro`
- Image generation: `gemini-2.0-flash-exp-image-generation`

## When to Use

- **Video analysis**: Claude cannot process video natively. Use Gemini to analyze ad videos, extract transcripts, describe scenes, etc.
- **Image generation**: When the user needs to create images from text prompts.
- **Image analysis with Gemini specifically**: When the user asks to use Gemini for image analysis, or when you need a second opinion on an image beyond Claude's own vision.
- **Bulk media analysis**: When processing multiple images or videos in a workflow.

## Usage Notes

- Always use absolute paths for files
- For video analysis, the video is sent as base64 inline data — very large videos may hit API limits
- Image generation saves to the specified output path or generates a timestamped filename in the current directory
- Ensure your `GEMINI_API_KEY` is set in `tools/gemini-api/.env` before use
