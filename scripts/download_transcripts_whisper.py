#!/usr/bin/env python3
"""
T-V002 (revised): Download and transcribe Khan Academy video audio via Whisper.

Bypasses YouTube transcript API IP bans by:
  1. Downloading audio via yt-dlp (uses different endpoints)
  2. Transcribing locally with OpenAI Whisper (small.en on MPS/Metal)

Rate-limits to 0.5s between downloads.
Checkpoints progress every 100 videos.
Excludes transcripts shorter than 100 words.

Input:  data/videos/.working/khan_metadata.json
Output: data/videos/.working/transcripts/{video_id}.txt

Usage:
    python scripts/download_transcripts_whisper.py [--model small.en] [--batch 500] [--start 0]
"""

import json
import os
import sys
import time
import subprocess
import tempfile
import argparse
from pathlib import Path

# Defer whisper import until needed (heavy)
whisper = None

METADATA_FILE = Path("data/videos/.working/khan_metadata.json")
TRANSCRIPT_DIR = Path("data/videos/.working/transcripts")
AUDIO_CACHE_DIR = Path("data/videos/.working/audio_cache")
CHECKPOINT_FILE = Path("data/videos/.working/transcript_checkpoint.json")
ERROR_LOG_FILE = Path("data/videos/.working/transcript_errors.json")

MIN_WORDS = 100
RATE_LIMIT_DELAY = 0.5  # 0.5s between downloads (was 0.2)
MAX_DOWNLOAD_RETRIES = 2
CHECKPOINT_INTERVAL = 100


def download_audio(video_id, output_dir):
    """Download audio via yt-dlp. Returns path to audio file or None."""
    output_path = output_dir / f"{video_id}.mp4"

    if output_path.exists():
        return output_path

    # Try downloading with yt-dlp — format 18 is usually available (360p mp4 with audio)
    # Fall back to any available format with audio
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "-f", "18/bestaudio/worst",
        "--no-playlist",
        "--no-warnings",
        "--quiet",
        "--no-progress",
        "-o", str(output_path),
        f"https://www.youtube.com/watch?v={video_id}",
    ]

    for attempt in range(MAX_DOWNLOAD_RETRIES):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0 and output_path.exists():
                return output_path

            stderr = result.stderr.lower()

            # Detect IP ban / 403 — abort early
            if "403" in stderr or "forbidden" in stderr:
                print(f"  *** HTTP 403 Forbidden for {video_id} — likely IP banned")
                return "IP_BLOCKED"

            if "blocked" in stderr or "ip" in stderr:
                print(f"  *** Possible IP block for {video_id}: {result.stderr[:200]}")
                return "IP_BLOCKED"

            if attempt < MAX_DOWNLOAD_RETRIES - 1:
                time.sleep(2 ** attempt)

        except subprocess.TimeoutExpired:
            print(f"  Download timeout for {video_id} (attempt {attempt + 1})")
            if attempt < MAX_DOWNLOAD_RETRIES - 1:
                time.sleep(2)

    return None


def transcribe_audio(audio_path, model):
    """Transcribe audio file with Whisper. Returns text or None."""
    try:
        result = model.transcribe(str(audio_path), language="en")
        return result["text"].strip()
    except Exception as exc:
        print(f"  Whisper error: {exc}")
        return None


def load_checkpoint():
    """Load set of already-processed video IDs."""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            data = json.load(f)
        return set(data.get("processed", []))
    return set()


def save_checkpoint(processed_ids):
    """Save processed video IDs to checkpoint file."""
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump({"processed": sorted(processed_ids)}, f)


def load_errors():
    """Load error log."""
    if ERROR_LOG_FILE.exists():
        with open(ERROR_LOG_FILE) as f:
            return json.load(f)
    return {}


def save_errors(errors):
    """Save error log."""
    with open(ERROR_LOG_FILE, "w") as f:
        json.dump(errors, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Download and transcribe Khan Academy videos")
    parser.add_argument("--model", default="small.en", help="Whisper model name (default: small.en)")
    parser.add_argument("--batch", type=int, default=0, help="Process N videos then stop (0 = all)")
    parser.add_argument("--start", type=int, default=0, help="Start from Nth unprocessed video")
    parser.add_argument("--keep-audio", action="store_true", help="Keep downloaded audio files")
    parser.add_argument("--test", type=int, default=0, help="Quick test: process N videos then stop")
    args = parser.parse_args()

    if not METADATA_FILE.exists():
        print(f"ERROR: {METADATA_FILE} not found.")
        print("Run scrape_khan_videos.py first.")
        sys.exit(1)

    with open(METADATA_FILE) as f:
        videos = json.load(f)

    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Load Whisper model
    global whisper
    import whisper as _whisper
    whisper = _whisper

    print(f"Loading Whisper model '{args.model}'...")
    t_load = time.time()
    model = whisper.load_model(args.model)
    print(f"Model loaded in {time.time() - t_load:.1f}s")
    print()

    processed = load_checkpoint()
    errors = load_errors()
    remaining = [v for v in videos if v["id"] not in processed]

    # Apply start offset
    if args.start > 0:
        remaining = remaining[args.start:]

    # Apply batch limit
    if args.batch > 0:
        remaining = remaining[:args.batch]

    # Apply test limit
    if args.test > 0:
        remaining = remaining[:args.test]

    print(f"Total videos: {len(videos)}")
    print(f"Already processed: {len(processed)}")
    print(f"Remaining in this run: {len(remaining)}")
    print(f"Existing transcripts on disk: {len(list(TRANSCRIPT_DIR.glob('*.txt')))}")
    print()

    succeeded = 0
    skipped_no_audio = 0
    skipped_too_short = 0
    skipped_whisper_fail = 0
    ip_blocked = 0
    t0 = time.time()
    consecutive_blocks = 0

    for i, video in enumerate(remaining):
        video_id = video["id"]
        title = video.get("title", video_id)[:60]
        output_path = TRANSCRIPT_DIR / f"{video_id}.txt"

        # Skip if transcript file already exists
        if output_path.exists():
            processed.add(video_id)
            continue

        # Step 1: Download audio
        audio_path = download_audio(video_id, AUDIO_CACHE_DIR)

        if audio_path == "IP_BLOCKED":
            ip_blocked += 1
            consecutive_blocks += 1
            errors[video_id] = "ip_blocked"

            if consecutive_blocks >= 3:
                print(f"\n*** 3 consecutive IP blocks — aborting. Reconnect to VPN and retry.")
                print(f"*** Progress saved. Resume with: --start {i}")
                save_checkpoint(processed)
                save_errors(errors)
                sys.exit(2)

            time.sleep(RATE_LIMIT_DELAY)
            continue

        if audio_path is None:
            skipped_no_audio += 1
            processed.add(video_id)
            errors[video_id] = "download_failed"
            time.sleep(RATE_LIMIT_DELAY)
            continue

        consecutive_blocks = 0  # Reset on successful download

        # Step 2: Transcribe with Whisper
        text = transcribe_audio(audio_path, model)

        if text is None:
            skipped_whisper_fail += 1
            processed.add(video_id)
            errors[video_id] = "whisper_failed"
        elif len(text.split()) < MIN_WORDS:
            skipped_too_short += 1
            processed.add(video_id)
        else:
            with open(output_path, "w") as f:
                f.write(text)
            succeeded += 1
            processed.add(video_id)

        # Clean up audio if not keeping
        if not args.keep_audio and audio_path and audio_path.exists():
            audio_path.unlink()

        # Rate limit between downloads
        time.sleep(RATE_LIMIT_DELAY)

        # Progress reporting
        if (i + 1) % 10 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta_s = (len(remaining) - i - 1) / rate if rate > 0 else 0
            eta_m = eta_s / 60
            print(
                f"  [{i + 1}/{len(remaining)}] "
                f"{succeeded} ok, {skipped_no_audio} no-audio, "
                f"{skipped_too_short} short, {skipped_whisper_fail} whisper-fail, "
                f"{ip_blocked} blocked | "
                f"{elapsed:.0f}s elapsed, ETA {eta_m:.0f}m"
            )

        # Checkpoint
        if (i + 1) % CHECKPOINT_INTERVAL == 0:
            save_checkpoint(processed)
            save_errors(errors)
            print(f"  *** Checkpoint saved ({len(processed)} processed)")

    # Final checkpoint
    save_checkpoint(processed)
    save_errors(errors)

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.0f}s ({elapsed / 60:.1f}m)")
    print(f"  Transcripts saved: {succeeded}")
    print(f"  No audio available: {skipped_no_audio}")
    print(f"  Too short (<{MIN_WORDS} words): {skipped_too_short}")
    print(f"  Whisper failures: {skipped_whisper_fail}")
    print(f"  IP blocked: {ip_blocked}")
    print(f"  Total transcript files on disk: {len(list(TRANSCRIPT_DIR.glob('*.txt')))}")

    if ip_blocked > 0:
        print(f"\n  WARNING: {ip_blocked} videos blocked by IP ban.")
        print(f"  Connect to VPN for a fresh IP and re-run.")


if __name__ == "__main__":
    main()
