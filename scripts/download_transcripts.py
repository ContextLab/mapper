#!/usr/bin/env python3
"""
T-V002: Download English transcripts for all scraped Khan Academy videos.

Rate-limits to 5 requests/second with exponential backoff on 429 errors.
Checkpoints progress every 500 videos. Excludes videos with no English
transcript or transcripts shorter than 100 words.

Input:  data/videos/.working/khan_metadata.json
Output: data/videos/.working/transcripts/{video_id}.txt
See FR-V002, CL-021, CL-022, CL-033.
"""

import json
import os
import sys
import time
from pathlib import Path

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    print("ERROR: youtube-transcript-api not installed.")
    print("Run: pip install youtube-transcript-api")
    sys.exit(1)

METADATA_FILE = Path("data/videos/.working/khan_metadata.json")
TRANSCRIPT_DIR = Path("data/videos/.working/transcripts")
CHECKPOINT_FILE = Path("data/videos/.working/transcript_checkpoint.json")

MIN_WORDS = 100
RATE_LIMIT_DELAY = 0.2  # 5 requests/second
MAX_RETRIES = 3
CHECKPOINT_INTERVAL = 500


def download_transcript(video_id):
    """Download English transcript, return text or None."""
    ytt_api = YouTubeTranscriptApi()
    transcript = ytt_api.fetch(video_id, languages=["en"])
    text = " ".join(snippet.text for snippet in transcript)
    return text


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
        json.dump({"processed": list(processed_ids)}, f)


def main():
    if not METADATA_FILE.exists():
        print(f"ERROR: {METADATA_FILE} not found.")
        print("Run scrape_khan_videos.py first.")
        sys.exit(1)

    with open(METADATA_FILE) as f:
        videos = json.load(f)

    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)

    processed = load_checkpoint()
    remaining = [v for v in videos if v["id"] not in processed]

    print(f"Total videos: {len(videos)}")
    print(f"Already processed: {len(processed)}")
    print(f"Remaining: {len(remaining)}")
    print()

    succeeded = 0
    skipped_no_transcript = 0
    skipped_too_short = 0
    errors = 0
    t0 = time.time()

    for i, video in enumerate(remaining):
        video_id = video["id"]
        output_path = TRANSCRIPT_DIR / f"{video_id}.txt"

        # Skip if transcript file already exists
        if output_path.exists():
            processed.add(video_id)
            continue

        retry_delay = 1.0
        text = None

        for attempt in range(MAX_RETRIES):
            try:
                text = download_transcript(video_id)
                break
            except Exception as exc:
                exc_str = str(exc)
                if "429" in exc_str or "Too Many Requests" in exc_str:
                    # Rate limited — exponential backoff
                    print(f"  Rate limited on {video_id}, waiting {retry_delay:.0f}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                elif "No transcript" in exc_str or "disabled" in exc_str.lower():
                    # No transcript available
                    text = None
                    break
                else:
                    if attempt == MAX_RETRIES - 1:
                        text = None
                    else:
                        time.sleep(retry_delay)
                        retry_delay *= 2

        processed.add(video_id)

        if text is None:
            skipped_no_transcript += 1
        elif len(text.split()) < MIN_WORDS:
            skipped_too_short += 1
        else:
            with open(output_path, "w") as f:
                f.write(text)
            succeeded += 1

        # Rate limit
        time.sleep(RATE_LIMIT_DELAY)

        # Progress reporting
        total_done = len(processed)
        if total_done % CHECKPOINT_INTERVAL == 0:
            save_checkpoint(processed)
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (len(remaining) - i - 1) / rate if rate > 0 else 0
            print(
                f"  Checkpoint: {total_done}/{len(videos)} processed, "
                f"{succeeded} transcripts saved, "
                f"{elapsed:.0f}s elapsed, ETA {eta:.0f}s"
            )

        if (i + 1) % 100 == 0:
            elapsed = time.time() - t0
            print(
                f"  ... {i + 1}/{len(remaining)}: "
                f"{succeeded} ok, {skipped_no_transcript} no-transcript, "
                f"{skipped_too_short} too-short, {errors} errors "
                f"({elapsed:.0f}s)"
            )

    # Final checkpoint
    save_checkpoint(processed)

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.0f}s")
    print(f"  Transcripts saved: {succeeded}")
    print(f"  No English transcript: {skipped_no_transcript}")
    print(f"  Too short (<{MIN_WORDS} words): {skipped_too_short}")
    print(f"  Errors: {errors}")

    # Count total transcript files
    transcript_count = len(list(TRANSCRIPT_DIR.glob("*.txt")))
    print(f"  Total transcript files on disk: {transcript_count}")


if __name__ == "__main__":
    main()
