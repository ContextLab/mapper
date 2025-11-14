import pandas as pd
from pytube import Playlist
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import pickle
import os
import re
import json
from pathlib import Path
from multiprocessing import Pool, cpu_count
from typing import List, Tuple, Optional
import time

CHANNEL_URL = 'https://www.youtube.com/@khanacademy'
OUTPUT_DIR = Path('khan_academy_data')
TRANSCRIPT_DIR = OUTPUT_DIR / 'transcripts'
METADATA_DIR = OUTPUT_DIR / 'metadata'

# Create output directories
TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
METADATA_DIR.mkdir(parents=True, exist_ok=True)

def sanitize_filename(title: str) -> str:
    """Convert video title to safe filename."""
    # Remove punctuation and convert to lowercase
    cleaned = re.sub(r'[^\w\s-]', '', title.lower())
    # Replace spaces with underscores
    cleaned = re.sub(r'[-\s]+', '_', cleaned)
    # Remove leading/trailing underscores
    cleaned = cleaned.strip('_')
    return cleaned

def get_all_playlists(channel_url: str) -> List[Tuple[str, str]]:
    """Get all playlists from a channel. Returns list of (playlist_url, playlist_name)."""
    print("Fetching channel playlists...")
    
    import requests
    from bs4 import BeautifulSoup
    
    playlists_url = f"{channel_url}/playlists"
    response = requests.get(playlists_url)
    
    # Extract playlist IDs from the page
    playlist_pattern = r'"playlistId":"([^"]+)"'
    playlist_ids = list(set(re.findall(playlist_pattern, response.text)))
    
    playlists = []
    for playlist_id in playlist_ids:
        playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
        try:
            p = Playlist(playlist_url)
            playlist_name = p.title
            playlists.append((playlist_url, playlist_name))
            print(f"  Found: {playlist_name}")
        except Exception as e:
            print(f"  Error loading playlist {playlist_id}: {e}")
    
    return playlists

def get_all_videos_from_playlists(playlists: List[Tuple[str, str]]) -> List[Tuple[str, str, str, str]]:
    """
    Get all videos from all playlists.
    Returns list of (playlist_name, video_id, video_title, video_url).
    """
    all_videos = []
    
    for playlist_url, playlist_name in playlists:
        print(f"\nScanning playlist: {playlist_name}")
        try:
            playlist = Playlist(playlist_url)
            for video_url in playlist.video_urls:
                video_id = video_url.split('v=')[-1].split('&')[0]
                all_videos.append((playlist_name, video_id, None, video_url))
            print(f"  Found {len(playlist.video_urls)} videos")
        except Exception as e:
            print(f"  Error loading playlist: {e}")
    
    return all_videos

def video_already_processed(filename_base: str) -> bool:
    """Check if video has already been processed."""
    transcript_file = TRANSCRIPT_DIR / f"{filename_base}.tsv"
    metadata_file = METADATA_DIR / f"{filename_base}.json"
    return transcript_file.exists() and metadata_file.exists()

def process_single_video(video_data: Tuple[str, str, str, str]) -> Optional[str]:
    """
    Process a single video: get transcript and save files.
    Returns filename_base if successful, None otherwise.
    """
    playlist_name, video_id, video_title, video_url = video_data
    
    # Get video title if not provided
    if not video_title:
        try:
            from pytube import YouTube
            yt = YouTube(video_url)
            video_title = yt.title
        except Exception as e:
            print(f"  Error getting title for {video_id}: {e}")
            video_title = f"video_{video_id}"
    
    # Create filename
    filename_base = sanitize_filename(video_title)
    
    # Skip if already processed
    if video_already_processed(filename_base):
        return filename_base
    
    # Get transcript
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
    except (TranscriptsDisabled, NoTranscriptFound):
        print(f"  ✗ {video_title} (no transcript)")
        return None
    except Exception as e:
        print(f"  ✗ {video_title} (error: {e})")
        return None
    
    # Save transcript as TSV
    transcript_file = TRANSCRIPT_DIR / f"{filename_base}.tsv"
    with open(transcript_file, 'w', encoding='utf-8') as f:
        f.write("start\tend\ttext\n")
        for entry in transcript:
            start = round(entry['start'], 1)
            end = round(entry['start'] + entry['duration'], 1)
            text = entry['text'].replace('\t', ' ').replace('\n', ' ')
            f.write(f"{start}\t{end}\t{text}\n")
    
    # Save metadata as JSON
    metadata = {
        'playlist_name': playlist_name,
        'video_name': video_title,
        'video_url': video_url,
        'video_id': video_id
    }
    metadata_file = METADATA_DIR / f"{filename_base}.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"  ✓ {video_title}")
    return filename_base

def process_videos_parallel(videos: List[Tuple[str, str, str, str]], num_workers: int = None):
    """Process videos in parallel."""
    if num_workers is None:
        num_workers = max(1, cpu_count() - 1)
    
    print(f"\nProcessing {len(videos)} videos using {num_workers} workers...")
    
    with Pool(num_workers) as pool:
        results = pool.map(process_single_video, videos)
    
    successful = sum(1 for r in results if r is not None)
    print(f"\nProcessed {successful} videos successfully")

def merge_to_dataframe() -> pd.DataFrame:
    """Merge all saved files into final DataFrame format."""
    print("\nMerging all data into DataFrame...")
    
    data = []
    
    # Get all metadata files
    metadata_files = list(METADATA_DIR.glob("*.json"))
    
    for metadata_file in metadata_files:
        filename_base = metadata_file.stem
        transcript_file = TRANSCRIPT_DIR / f"{filename_base}.tsv"
        
        if not transcript_file.exists():
            continue
        
        # Load metadata
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Load transcript
        df_transcript = pd.read_csv(transcript_file, sep='\t')
        
        # Convert to required format
        transcript_lines = df_transcript['text'].tolist()
        timestamps = list(zip(df_transcript['start'], df_transcript['end']))
        
        data.append({
            'playlist_name': metadata['playlist_name'],
            'video_name': metadata['video_name'],
            'video_url': metadata['video_url'],
            'transcript': transcript_lines,
            'line_timestamps': timestamps
        })
    
    df = pd.DataFrame(data)
    print(f"Created DataFrame with {len(df)} videos")
    
    return df

def main():
    """Main execution function."""
    # Step 1: Get all playlists
    print("="*60)
    print("STEP 1: Discovering playlists")
    print("="*60)
    playlists = get_all_playlists(CHANNEL_URL)
    print(f"\nFound {len(playlists)} playlists")
    
    # Step 2: Get all videos from all playlists
    print("\n" + "="*60)
    print("STEP 2: Collecting video list")
    print("="*60)
    all_videos = get_all_videos_from_playlists(playlists)
    print(f"\nTotal videos found: {len(all_videos)}")
    
    # Check how many are already processed
    already_processed = sum(1 for v in all_videos if video_already_processed(sanitize_filename(v[3].split('v=')[-1])))
    print(f"Already processed: {already_processed}")
    print(f"To process: {len(all_videos) - already_processed}")
    
    # Step 3: Process videos in parallel
    print("\n" + "="*60)
    print("STEP 3: Processing videos")
    print("="*60)
    process_videos_parallel(all_videos)
    
    # Step 4: Merge into final DataFrame
    print("\n" + "="*60)
    print("STEP 4: Creating final dataset")
    print("="*60)
    df = merge_to_dataframe()
    
    # Save to pickle
    output_file = OUTPUT_DIR / 'khan_academy_transcripts.pkl'
    with open(output_file, 'wb') as f:
        pickle.dump(df, f)
    
    print(f"\n{'='*60}")
    print(f"Complete!")
    print(f"Total videos with transcripts: {len(df)}")
    print(f"Saved to: {output_file}")
    print(f"Individual files in: {OUTPUT_DIR}")
    print(f"{'='*60}")
    
    return df

if __name__ == "__main__":
    # Install required packages:
    # pip install pytube youtube-transcript-api pandas beautifulsoup4 requests
    
    df = main()
    print("\nDataFrame preview:")
    print(df.head())