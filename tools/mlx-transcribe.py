#!/usr/bin/env python3
"""
Batch video transcription using MLX Whisper (local, no API needed).
Uses Pinokio's MLX environment.

Usage:
  python3 mlx-transcribe.py /path/to/video.mp4
  python3 mlx-transcribe.py /path/to/folder/ --output /path/to/output/
  python3 mlx-transcribe.py /path/to/folder/ --model turbo
"""

import sys
import os
import subprocess
import pathlib
import argparse
import numpy as np

# Add Pinokio's MLX env to path
PINOKIO_ENV = pathlib.Path.home() / "pinokio/api/mlx-video-transcription.git/app/env"
FFMPEG = str(pathlib.Path.home() / "pinokio/bin/miniconda/bin/ffmpeg")

sys.path.insert(0, str(PINOKIO_ENV / "lib/python3.11/site-packages"))

import mlx.core as mx
import mlx_whisper

MODELS = {
    "tiny": "mlx-community/whisper-tiny-mlx-q4",
    "small": "mlx-community/whisper-small-mlx-fp32",
    "small-en": "mlx-community/whisper-small.en-mlx-q4",
    "large": "mlx-community/whisper-large-v3-mlx",
    "distil": "mlx-community/distil-whisper-large-v3",
    "turbo": "mlx-community/whisper-large-v3-turbo",
}

def extract_audio(video_path):
    """Extract audio from video using ffmpeg, return as numpy array."""
    command = [
        FFMPEG, "-i", str(video_path),
        "-f", "s16le", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1", "-"
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    audio_data, _ = process.communicate()
    audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
    return mx.array(audio_array)

def transcribe_video(video_path, model_name="turbo", language="en"):
    """Transcribe a video file and return the text."""
    print(f"  Extracting audio...")
    audio = extract_audio(video_path)

    print(f"  Transcribing with {model_name}...")
    model_path = MODELS.get(model_name, model_name)
    results = mlx_whisper.transcribe(
        audio,
        path_or_hf_repo=model_path,
        fp16=False,
        verbose=False,
        language=language,
    )
    return results["text"]

def clean_filename(name):
    """Convert video filename to a clean transcript name."""
    name = pathlib.Path(name).stem
    # Remove common prefixes
    for prefix in ["undefined - ", "undefined-"]:
        if name.startswith(prefix):
            name = name[len(prefix):]
    # Remove numbering prefixes like "002 - "
    import re
    name = re.sub(r'^\d+\s*-\s*', '', name)
    return f"Transcript - {name}.md"

def main():
    parser = argparse.ArgumentParser(description="Batch transcribe videos using MLX Whisper")
    parser.add_argument("input", help="Video file or directory of videos")
    parser.add_argument("--output", "-o", help="Output directory (default: same as input)")
    parser.add_argument("--model", "-m", default="turbo",
                        choices=list(MODELS.keys()),
                        help="Whisper model to use (default: turbo)")
    parser.add_argument("--language", "-l", default="en", help="Language code (default: en)")
    args = parser.parse_args()

    input_path = pathlib.Path(args.input)
    video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

    if input_path.is_file():
        videos = [input_path]
        output_dir = pathlib.Path(args.output) if args.output else input_path.parent
    elif input_path.is_dir():
        videos = sorted([f for f in input_path.iterdir() if f.suffix.lower() in video_extensions])
        output_dir = pathlib.Path(args.output) if args.output else input_path
    else:
        print(f"Error: {input_path} not found")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Found {len(videos)} video(s) to transcribe")
    print(f"Model: {args.model}")
    print(f"Output: {output_dir}\n")

    for i, video in enumerate(videos, 1):
        print(f"[{i}/{len(videos)}] {video.name}")
        try:
            text = transcribe_video(video, args.model, args.language)
            out_name = clean_filename(video.name)
            out_path = output_dir / out_name
            out_path.write_text(text, encoding="utf-8")
            print(f"  Saved: {out_path.name}\n")
        except Exception as e:
            print(f"  Error: {e}\n")

    print("Done!")

if __name__ == "__main__":
    main()
