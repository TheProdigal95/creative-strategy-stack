# Transcribe Video or Audio

Transcribe a video or audio file. Route between MLX (local, fast) and Gemini (API, detailed) based on what's needed.

## When to use which

**Use MLX (local)** when:
- You only need the spoken words (speech-to-text)
- Transcribing interviews, podcasts, talks, or any audio-first content
- The visuals don't matter for the analysis
- Batch transcribing multiple files
- Cost matters (MLX is free, runs locally)
- **Requires:** macOS with Apple Silicon (M1+). See MLX section below for setup.

**Use Gemini** when:
- You need visual context: what's on screen, captions, text overlays, scene descriptions
- Transcribing ads or video content where visuals ARE the content
- You need a structured script breakdown (timestamp | visual | voiceover | captions)
- The user explicitly asks for detailed/visual transcription
- MLX is not available (no Apple Silicon, no Pinokio)
- **Requires:** Gemini API key only. Works on any platform.

## MLX Transcription (local, Apple Silicon only)

**Tool location:** `tools/mlx-transcribe.py`

**Setup options:**
- **Option A (Pinokio):** Install [Pinokio](https://pinokio.computer/) and add the "MLX Video Transcription" app. This bundles everything automatically.
- **Option B (Manual):** Install dependencies yourself:
  ```bash
  brew install ffmpeg
  pip install mlx mlx-whisper numpy
  ```

**Run with:**
```bash
python3 tools/mlx-transcribe.py /path/to/video.mp4
```

**For a folder of videos:**
```bash
python3 tools/mlx-transcribe.py /path/to/folder/ --output /path/to/output/
```

**Models available** (use `--model`):
- `turbo` (default) — fast, good quality, best general choice
- `large` — highest accuracy, slower
- `small` — fastest, lower quality
- `small-en` — English-only, fast
- `distil` — good balance of speed/quality

**Language:** Default is English. Use `--language es` for Spanish, etc.

**Output:** Creates markdown files named `Transcript - [filename].md` in the same directory (or --output directory).

## Gemini Transcription (API, any platform)

**Tool location:** `tools/gemini-api/gemini-api.js`

**Setup:**
```bash
cd tools/gemini-api && npm install
```
Then add your `GEMINI_API_KEY` to `tools/gemini-api/.env`.

**For speech-to-text only:**
```bash
node tools/gemini-api/gemini-api.js "Transcribe this video. Output clean text with paragraph breaks." --video /path/to/video.mp4
```

**For detailed visual + audio breakdown:**
```bash
node tools/gemini-api/gemini-api.js "Please watch the attached video, and convert it into a script with 1 column for the visual action that's happening, 1 column for the voiceover that's happening, and 1 column for the on-screen captions. Format as a markdown table with columns: | Timestamp | Visual Action | Voiceover | On-Screen Captions | Be thorough and capture every scene transition, every spoken word, and every text overlay." --video /path/to/video.mp4
```

## Default behavior

If the user says "transcribe this" without specifying detail level:
- Single video file → use MLX with turbo model (if available), otherwise Gemini
- If they mention "visuals," "captions," "on-screen text," "ad breakdown" → use Gemini
- If they mention "batch" or give a folder → use MLX (if available), otherwise loop Gemini

Always save the output as a markdown file. Use the video filename to create the transcript filename.
