#!/usr/bin/env python3
"""
T-V001: Scrape all Khan Academy YouTube video metadata via scrapetube.

No API key required. Uses scrapetube's channel enumeration which calls
YouTube's internal browse API.

Output: data/videos/.working/khan_metadata.json
See FR-V001, CL-027.
"""

import json
import os
import sys
import time
from pathlib import Path

try:
    import scrapetube
except ImportError:
    print("ERROR: scrapetube not installed. Run: pip install scrapetube")
    sys.exit(1)

CHANNEL_URL = "https://www.youtube.com/@khanacademy"
OUTPUT_DIR = Path("data/videos/.working")
OUTPUT_FILE = OUTPUT_DIR / "khan_metadata.json"


def parse_duration(duration_text):
    """Parse duration string like '12:34' or '1:02:34' into seconds."""
    if not duration_text:
        return 0
    parts = duration_text.strip().split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 1:
            return int(parts[0])
    except ValueError:
        return 0
    return 0


def scrape_channel():
    """Enumerate all videos from the Khan Academy YouTube channel."""
    print(f"Scraping videos from {CHANNEL_URL}...")
    print("This may take 10-30 minutes for ~9,000 videos.")
    print()

    videos = []
    seen_ids = set()
    count = 0
    t0 = time.time()

    try:
        for video in scrapetube.get_channel(
            channel_url=CHANNEL_URL,
            sleep=1,  # Rate-limit: 1 second between pages
        ):
            video_id = video.get("videoId")
            if not video_id or video_id in seen_ids:
                continue
            seen_ids.add(video_id)

            # Extract title
            title_runs = video.get("title", {}).get("runs", [])
            title = title_runs[0].get("text", "") if title_runs else ""
            if not title:
                title = video.get("title", {}).get("simpleText", f"Untitled ({video_id})")

            # Extract duration
            duration_text = video.get("lengthText", {}).get("simpleText", "")
            duration_s = parse_duration(duration_text)

            # Thumbnail URL (medium quality)
            thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg"

            videos.append({
                "id": video_id,
                "title": title,
                "duration_s": duration_s,
                "thumbnail_url": thumbnail_url,
            })

            count += 1
            if count % 500 == 0:
                elapsed = time.time() - t0
                print(f"  ... {count} videos scraped ({elapsed:.0f}s elapsed)")

    except KeyboardInterrupt:
        print(f"\nInterrupted after {count} videos.")
    except Exception as exc:
        print(f"\nError after {count} videos: {exc}")
        print("Saving partial results...")

    elapsed = time.time() - t0
    print(f"\nDone: {len(videos)} unique videos in {elapsed:.0f}s")
    return videos


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    videos = scrape_channel()

    if not videos:
        print("ERROR: No videos scraped.")
        sys.exit(1)

    # Save metadata
    with open(OUTPUT_FILE, "w") as f:
        json.dump(videos, f, indent=2)
    print(f"Saved to {OUTPUT_FILE}")

    # Stats
    with_duration = [v for v in videos if v["duration_s"] > 0]
    total_hours = sum(v["duration_s"] for v in with_duration) / 3600
    print(f"\nStats:")
    print(f"  Total videos: {len(videos)}")
    print(f"  With duration: {len(with_duration)}")
    print(f"  Total content: {total_hours:.0f} hours")
    if with_duration:
        avg = sum(v["duration_s"] for v in with_duration) / len(with_duration)
        print(f"  Avg duration: {avg:.0f}s ({avg/60:.1f}min)")


if __name__ == "__main__":
    main()
