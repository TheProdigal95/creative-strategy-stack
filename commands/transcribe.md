# Transcribe Video or Audio

Transcribe a video or audio file. Route between MLX (local, fast) and Gemini (API, detailed) based on what's needed.

## When to use which

**Use MLX (local)** when:
- You only need the spoken words (speech-to-text)
- Transcribing interviews, podcasts, talks, or any audio-first content
- The visuals don't matter for the analysis
- Batch transcribing multiple files
- Cost matters (MLX is free, runs locally)

**Use Gemini** when:
- You need visual context: what's on screen, captions, text overlays, scene descriptions
- Transcribing ads or video content where visuals ARE the content
- You need a structured script breakdown (timestamp | visual | voiceover | captions)
- The user explicitly asks for detailed/visual transcription

## MLX Transcription (local)

**Tool location:** `~/.claude/tools/mlx-transcribe.py`

**Run with:**
```bash
python3 ~/.claude/tools/mlx-transcribe.py /path/to/video.mp4
```

**For a folder of videos:**
```bash
python3 ~/.claude/tools/mlx-transcribe.py /path/to/folder/ --output /path/to/output/
```

**Models available** (use `--model`):
- `turbo` (default) — fast, good quality, best general choice
- `large` — highest accuracy, slower
- `small` — fastest, lower quality
- `small-en` — English-only, fast
- `distil` — good balance of speed/quality

**Language:** Default is English. Use `--language es` for Spanish, etc.

**Output:** Creates markdown files named `Transcript - [filename].md` in the same directory (or --output directory).

**Environment:** Uses Pinokio's MLX environment at `~/pinokio/api/mlx-video-transcription.git/app/env`. The ffmpeg binary is at `~/pinokio/bin/miniconda/bin/ffmpeg`. Both must be installed via Pinokio.

## Gemini Transcription (API)

**Tool location:** `~/.claude/tools/gemini-api/gemini-api.js`

**For speech-to-text only:**
```bash
node ~/.claude/tools/gemini-api/gemini-api.js "Transcribe this video. Output clean text with paragraph breaks." --video /path/to/video.mp4
```

**For detailed visual + audio breakdown:**
```bash
node ~/.claude/tools/gemini-api/gemini-api.js "Please watch the attached video, and convert it into a script with 1 column for the visual action that's happening, 1 column for the voiceover that's happening, and 1 column for the on-screen captions. Format as a markdown table with columns: | Timestamp | Visual Action | Voiceover | On-Screen Captions | Be thorough and capture every scene transition, every spoken word, and every text overlay." --video /path/to/video.mp4
```

**For batch transcription via Gemini File Manager API** (uploads to Gemini servers, better for large files):
```bash
node ~/.claude/tools/gemini-api/transcribe-videos.js
```
Note: This script has hardcoded paths. Modify the source/destination paths in the script before running.

## Default behavior

If the user says "transcribe this" without specifying detail level:
- Single video file → use MLX with turbo model
- If they mention "visuals," "captions," "on-screen text," "ad breakdown" → use Gemini
- If they mention "batch" or give a folder → use MLX

Always save the output as a markdown file. Use the video filename to create the transcript filename.
