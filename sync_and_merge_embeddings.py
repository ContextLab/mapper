#!/usr/bin/env python3
"""
Sync embedding files from remote clusters and merge into a single local file.

This script provides two main functions:
1. SYNC: Download embedding checkpoint files from remote clusters using SFTP
2. MERGE: Combine all downloaded embeddings into a single merged file

Pipeline:
    cluster*_gpu*.pkl files (remote)
        ↓ (scp/sftp)
    embeddings/cluster*_gpu*.pkl (local)
        ↓ (merge)
    embeddings/wikipedia_merged.pkl

Important: The workers compute embeddings for 250,010 items (250k articles + 10 questions).
This script only includes the first 250,000 embeddings (articles) in the merged output.

Usage:
    python sync_and_merge_embeddings.py              # Sync and merge
    python sync_and_merge_embeddings.py --sync-only  # Only sync files
    python sync_and_merge_embeddings.py --merge-only # Only merge existing files
    python sync_and_merge_embeddings.py --clusters "tensor01 tensor02"  # Specify clusters
"""

import pickle
import json
import os
import sys
import argparse
import subprocess
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import numpy as np


# ============================================================================
# CREDENTIAL MANAGEMENT
# ============================================================================

def load_credentials(cluster_name: str) -> Dict:
    """
    Load cluster credentials from .credentials folder.

    Args:
        cluster_name: "tensor01" or "tensor02" or other cluster name

    Returns:
        Dictionary with keys: address, username, password

    Raises:
        FileNotFoundError: If credentials file not found
        json.JSONDecodeError: If credentials file is not valid JSON
    """
    creds_file = Path(__file__).parent / ".credentials" / f"{cluster_name}.credentials"

    if not creds_file.exists():
        raise FileNotFoundError(
            f"Credentials file not found: {creds_file}\n"
            f"Expected format: {{'address': 'hostname', 'username': 'user', 'password': 'pass'}}"
        )

    with open(creds_file, 'r') as f:
        creds = json.load(f)

    # Validate required fields
    required_fields = ['address', 'username', 'password']
    for field in required_fields:
        if field not in creds:
            raise ValueError(f"Missing required field '{field}' in {creds_file}")

    return creds


# ============================================================================
# SYNC OPERATIONS
# ============================================================================

def extract_chunk_info(filename: str) -> Optional[Dict]:
    """
    Extract metadata from checkpoint filename.

    Expected format: cluster{cluster_id}_gpu{gpu_id}.pkl
    Example: cluster1_gpu0.pkl -> {'cluster_id': 1, 'gpu_id': 0}

    Args:
        filename: Checkpoint filename

    Returns:
        Dictionary with cluster_id and gpu_id, or None if format doesn't match
    """
    match = re.match(r'cluster(\d+)_gpu(\d+)\.pkl', filename)
    if match:
        return {
            'cluster_id': int(match.group(1)),
            'gpu_id': int(match.group(2))
        }
    return None


def sync_from_cluster(
    cluster_name: str,
    output_dir: Path,
    use_sshpass: bool = False
) -> Tuple[List[Path], List[str]]:
    """
    Sync embedding files from a remote cluster using SFTP/SCP.

    Args:
        cluster_name: "tensor01", "tensor02", etc.
        output_dir: Local directory to save downloaded files
        use_sshpass: If True, use sshpass for authentication (default: paramiko)

    Returns:
        Tuple of (list of downloaded file paths, list of warnings/errors)
    """
    print(f"\n{'='*80}")
    print(f"SYNCING FROM {cluster_name.upper()}")
    print(f"{'='*80}")

    try:
        creds = load_credentials(cluster_name)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        error_msg = f"Error loading credentials: {e}"
        print(f"✗ {error_msg}")
        return [], [error_msg]

    address = creds['address']
    username = creds['username']
    password = creds['password']

    # Create output directory if needed
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}")

    # Remote directory path
    remote_dir = f"/home/{username}/mapper_embeddings/embeddings"
    print(f"Remote directory: {remote_dir}\n")

    downloaded_files = []
    warnings = []

    # Try to list remote files using scp/sftp
    try:
        if use_sshpass:
            # Use sshpass with scp (simpler but less flexible)
            result = sync_via_sshpass(
                address, username, password, remote_dir, output_dir
            )
            downloaded_files = result['files']
            warnings = result['warnings']
        else:
            # Use paramiko SFTP (preferred)
            result = sync_via_paramiko(
                address, username, password, remote_dir, output_dir
            )
            downloaded_files = result['files']
            warnings = result['warnings']

    except Exception as e:
        error_msg = f"Failed to sync from {cluster_name}: {e}"
        print(f"✗ {error_msg}")
        return [], [error_msg]

    # Summary
    print(f"\n✓ Downloaded {len(downloaded_files)} files from {cluster_name}")
    if warnings:
        for warning in warnings:
            print(f"⚠ {warning}")

    return downloaded_files, warnings


def sync_via_paramiko(
    address: str,
    username: str,
    password: str,
    remote_dir: str,
    output_dir: Path
) -> Dict:
    """
    Sync files using paramiko SFTP (preferred method).

    Args:
        address: Remote host address
        username: Remote username
        password: Remote password
        remote_dir: Remote directory path
        output_dir: Local output directory

    Returns:
        Dict with 'files' (list of downloaded paths) and 'warnings' (list of messages)
    """
    import paramiko
    from paramiko.ssh_exception import SSHException, AuthException

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    downloaded_files = []
    warnings = []

    try:
        print(f"Connecting to {address}...")
        ssh.connect(
            hostname=address,
            username=username,
            password=password,
            timeout=30
        )
        print(f"✓ Connected")

        # Open SFTP channel
        sftp = ssh.open_sftp()

        # List remote files
        print(f"Listing files in {remote_dir}...")
        try:
            remote_files = sftp.listdir(remote_dir)
        except FileNotFoundError:
            error_msg = f"Remote directory not found: {remote_dir}"
            warnings.append(error_msg)
            sftp.close()
            ssh.close()
            return {'files': [], 'warnings': warnings}

        # Filter for embedding files
        embedding_files = [
            f for f in remote_files
            if re.match(r'cluster\d+_gpu\d+\.pkl', f)
        ]
        embedding_files.sort()

        if not embedding_files:
            warnings.append("No embedding files found matching pattern 'cluster*_gpu*.pkl'")

        print(f"Found {len(embedding_files)} embedding files\n")

        # Download each file
        for idx, remote_file in enumerate(embedding_files, 1):
            remote_path = f"{remote_dir}/{remote_file}"
            local_path = output_dir / remote_file

            # Show download progress
            print(f"  [{idx}/{len(embedding_files)}] {remote_file}...", end=' ', flush=True)

            try:
                sftp.get(remote_path, str(local_path))

                # Get file size
                file_size_mb = local_path.stat().st_size / 1e6
                print(f"✓ ({file_size_mb:.2f} MB)")

                downloaded_files.append(local_path)

            except Exception as e:
                print(f"✗ Error: {e}")
                warnings.append(f"Failed to download {remote_file}: {e}")

        sftp.close()
        ssh.close()

    except AuthException as e:
        error_msg = f"Authentication failed: {e}"
        warnings.append(error_msg)
    except SSHException as e:
        error_msg = f"SSH connection failed: {e}"
        warnings.append(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        warnings.append(error_msg)
    finally:
        try:
            ssh.close()
        except:
            pass

    return {'files': downloaded_files, 'warnings': warnings}


def sync_via_sshpass(
    address: str,
    username: str,
    password: str,
    remote_dir: str,
    output_dir: Path
) -> Dict:
    """
    Sync files using sshpass command-line tool.

    Requires 'sshpass' to be installed: brew install sshpass (macOS) or apt install sshpass (Linux)

    Args:
        address: Remote host address
        username: Remote username
        password: Remote password
        remote_dir: Remote directory path
        output_dir: Local output directory

    Returns:
        Dict with 'files' (list of downloaded paths) and 'warnings' (list of messages)
    """
    import shlex

    downloaded_files = []
    warnings = []

    # Check if sshpass is available
    result = subprocess.run(['which', 'sshpass'], capture_output=True)
    if result.returncode != 0:
        warnings.append("sshpass not found. Install with: brew install sshpass")
        return {'files': [], 'warnings': warnings}

    print(f"Connecting to {address}...")

    # List remote files
    list_cmd = f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no {username}@{address} ls -1 {remote_dir}"

    try:
        result = subprocess.run(
            list_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            error_msg = f"Failed to list remote files: {result.stderr}"
            warnings.append(error_msg)
            return {'files': [], 'warnings': warnings}

        # Parse file list
        remote_files = [
            f.strip() for f in result.stdout.split('\n')
            if re.match(r'cluster\d+_gpu\d+\.pkl', f.strip())
        ]
        remote_files.sort()

        if not remote_files:
            warnings.append("No embedding files found matching pattern 'cluster*_gpu*.pkl'")

        print(f"Found {len(remote_files)} embedding files\n")

        # Download each file
        for idx, remote_file in enumerate(remote_files, 1):
            remote_path = f"{username}@{address}:{remote_dir}/{remote_file}"
            local_path = output_dir / remote_file

            print(f"  [{idx}/{len(remote_files)}] {remote_file}...", end=' ', flush=True)

            download_cmd = f"sshpass -p '{password}' scp -o StrictHostKeyChecking=no {remote_path} {local_path}"

            try:
                result = subprocess.run(
                    download_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300
                )

                if result.returncode != 0:
                    print(f"✗ Error: {result.stderr}")
                    warnings.append(f"Failed to download {remote_file}: {result.stderr}")
                    continue

                # Get file size
                file_size_mb = local_path.stat().st_size / 1e6
                print(f"✓ ({file_size_mb:.2f} MB)")
                downloaded_files.append(local_path)

            except subprocess.TimeoutExpired:
                print(f"✗ Timeout")
                warnings.append(f"Download timeout for {remote_file}")

    except subprocess.TimeoutExpired:
        error_msg = "Timeout listing remote files"
        warnings.append(error_msg)
    except Exception as e:
        error_msg = f"Error during sync: {e}"
        warnings.append(error_msg)

    return {'files': downloaded_files, 'warnings': warnings}


# ============================================================================
# MERGE OPERATIONS
# ============================================================================

def load_wikipedia_articles() -> List[Dict]:
    """
    Load article metadata from wikipedia.pkl.

    The file contains a list of 250,000 Wikipedia article dictionaries with:
    - id: Wikipedia article ID
    - title: Article title
    - url: Wikipedia URL
    - text: Article text

    Returns:
        List of article dictionaries (250,000 items)

    Raises:
        FileNotFoundError: If wikipedia.pkl not found
    """
    wiki_file = Path(__file__).parent / "wikipedia.pkl"

    if not wiki_file.exists():
        raise FileNotFoundError(
            f"Wikipedia articles file not found: {wiki_file}\n"
            f"Expected 250,000 Wikipedia articles"
        )

    print("Loading Wikipedia articles...")
    with open(wiki_file, 'rb') as f:
        articles = pickle.load(f)

    if not isinstance(articles, list):
        raise ValueError(f"Expected list, got {type(articles)}")

    if len(articles) != 250000:
        raise ValueError(
            f"Expected 250,000 articles, got {len(articles)}"
        )

    print(f"✓ Loaded {len(articles):,} Wikipedia articles")
    return articles


def load_checkpoint(filepath: Path) -> Dict:
    """
    Load a single checkpoint file and extract metadata.

    Expected checkpoint structure:
    {
        'embeddings': np.ndarray of shape (N, 768),
        'start_index': int,
        'end_index': int,
        'cluster_id': int,
        'gpu_id': int,
        ...
    }

    Args:
        filepath: Path to checkpoint .pkl file

    Returns:
        Dictionary with checkpoint data

    Raises:
        FileNotFoundError: If file doesn't exist
        pickle.UnpicklingError: If file is not a valid pickle
        ValueError: If required fields are missing
    """
    if not filepath.exists():
        raise FileNotFoundError(f"Checkpoint file not found: {filepath}")

    with open(filepath, 'rb') as f:
        data = pickle.load(f)

    # Validate required fields
    required_fields = ['embeddings', 'start_index', 'end_index', 'cluster_id', 'gpu_id']
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field '{field}' in {filepath.name}")

    embeddings = data['embeddings']
    if not isinstance(embeddings, np.ndarray):
        raise ValueError(f"'embeddings' must be numpy array, got {type(embeddings)}")

    return data


def verify_embedding_quality(embeddings: np.ndarray) -> Dict:
    """
    Perform quality checks on embeddings array.

    Args:
        embeddings: Numpy array of shape (N, D)

    Returns:
        Dictionary with quality metrics
    """
    norms = np.linalg.norm(embeddings, axis=1)

    metrics = {
        'shape': embeddings.shape,
        'dtype': embeddings.dtype,
        'min_norm': float(norms.min()),
        'max_norm': float(norms.max()),
        'mean_norm': float(norms.mean()),
        'std_norm': float(norms.std()),
        'has_nan': bool(np.isnan(embeddings).any()),
        'has_inf': bool(np.isinf(embeddings).any()),
    }

    return metrics


def merge_embeddings(
    embedding_files: List[Path],
    output_file: Path,
    articles: List[Dict],
    embedding_dim: int = 768,
    num_articles: int = 250000,
    model_name: str = 'google/embeddinggemma-300m'
) -> bool:
    """
    Merge all checkpoint files into a single embedding file.

    Process:
    1. Load all checkpoint files
    2. Sort by start_index to ensure correct order
    3. Verify no gaps or overlaps in index ranges
    4. Extract article titles from wikipedia.pkl
    5. Concatenate embeddings (only first 250,000, excluding 10 question embeddings)
    6. Perform quality checks
    7. Save merged file with metadata

    Args:
        embedding_files: List of checkpoint file paths to merge
        output_file: Path to save merged embeddings.pkl
        articles: List of article dictionaries from wikipedia.pkl
        embedding_dim: Expected embedding dimension (default 768)
        num_articles: Number of articles to include (default 250,000)
        model_name: Name of embedding model (for metadata)

    Returns:
        True if merge successful, False otherwise
    """
    print(f"\n{'='*80}")
    print("MERGING EMBEDDINGS")
    print(f"{'='*80}")

    if not embedding_files:
        print("✗ No embedding files to merge")
        return False

    # ========== LOAD CHECKPOINTS ==========
    print(f"\nLoading {len(embedding_files)} checkpoint files...\n")

    chunks = []

    for idx, filepath in enumerate(sorted(embedding_files), 1):
        print(f"  [{idx}/{len(embedding_files)}] {filepath.name}...", end=' ')

        try:
            data = load_checkpoint(filepath)

            embeddings = data['embeddings']
            start_idx = data['start_index']
            end_idx = data['end_index']
            cluster_id = data['cluster_id']
            gpu_id = data['gpu_id']

            num_items = len(embeddings)
            expected_items = end_idx - start_idx

            if num_items != expected_items:
                print(f"✗ Size mismatch")
                print(f"    Expected {expected_items} items, got {num_items}")
                return False

            print(f"✓ ({num_items:,} items, dim={embeddings.shape[1]})")

            chunks.append({
                'embeddings': embeddings,
                'start_index': start_idx,
                'end_index': end_idx,
                'cluster_id': cluster_id,
                'gpu_id': gpu_id,
                'filepath': filepath.name
            })

        except Exception as e:
            print(f"✗ Error: {e}")
            return False

    # ========== VERIFY ORDER ==========
    print(f"\n{'='*80}")
    print("VERIFYING INDEX RANGES")
    print(f"{'='*80}\n")

    # Sort by start_index
    chunks.sort(key=lambda x: x['start_index'])

    # Check for gaps and overlaps
    expected_idx = 0
    total_items = 0

    for chunk in chunks:
        start = chunk['start_index']
        end = chunk['end_index']
        size = end - start

        # Check for gap
        if start != expected_idx:
            print(f"✗ ERROR: Gap detected!")
            print(f"  Expected index: {expected_idx}")
            print(f"  Got index: {start}")
            return False

        # Check for overlap
        if end < start:
            print(f"✗ ERROR: Invalid index range!")
            print(f"  Start: {start}, End: {end}")
            return False

        print(f"  ✓ Cluster {chunk['cluster_id']}, GPU {chunk['gpu_id']}: "
              f"{start:,} - {end:,} ({size:,} items)")

        expected_idx = end
        total_items += size

    print(f"\n  ✓ No gaps or overlaps")
    print(f"  ✓ Total items across all chunks: {total_items:,}")

    # ========== CONCATENATE ==========
    print(f"\n{'='*80}")
    print("CONCATENATING EMBEDDINGS")
    print(f"{'='*80}\n")

    all_embeddings = np.concatenate([chunk['embeddings'] for chunk in chunks], axis=0)

    print(f"  Shape: {all_embeddings.shape}")
    print(f"  Items: {len(all_embeddings):,}")
    print(f"  Dimensions: {all_embeddings.shape[1]}")

    # Extract only article embeddings (exclude last 10 for questions)
    if len(all_embeddings) > num_articles:
        print(f"\n  Extracting first {num_articles:,} items (articles only, excluding questions)...")
        article_embeddings = all_embeddings[:num_articles]
        excluded_items = len(all_embeddings) - num_articles

        print(f"  ✓ Excluded {excluded_items} question embeddings")

        all_embeddings = article_embeddings

    # Verify dimension matches
    if all_embeddings.shape[1] != embedding_dim:
        print(f"✗ ERROR: Embedding dimension mismatch!")
        print(f"  Expected: {embedding_dim}")
        print(f"  Got: {all_embeddings.shape[1]}")
        return False

    # ========== QUALITY CHECKS ==========
    print(f"\n{'='*80}")
    print("QUALITY CHECKS")
    print(f"{'='*80}\n")

    metrics = verify_embedding_quality(all_embeddings)

    print(f"  Shape: {metrics['shape']}")
    print(f"  Dtype: {metrics['dtype']}")
    print(f"  Embedding norms:")
    print(f"    Mean: {metrics['mean_norm']:.4f}")
    print(f"    Std: {metrics['std_norm']:.4f}")
    print(f"    Min: {metrics['min_norm']:.4f}")
    print(f"    Max: {metrics['max_norm']:.4f}")

    if metrics['has_nan'] or metrics['has_inf']:
        print(f"\n  ✗ ERROR: Found NaN or Inf values!")
        print(f"    NaN: {metrics['has_nan']}")
        print(f"    Inf: {metrics['has_inf']}")
        return False

    print(f"  ✓ No NaN or Inf values")

    # Verify article count matches
    if len(all_embeddings) != num_articles:
        print(f"\n  ✗ ERROR: Item count mismatch!")
        print(f"    Expected: {num_articles:,}")
        print(f"    Got: {len(all_embeddings):,}")
        return False

    if len(articles) != num_articles:
        print(f"\n  ✗ ERROR: Article count mismatch!")
        print(f"    Expected: {num_articles:,}")
        print(f"    Got: {len(articles):,}")
        return False

    print(f"  ✓ Embedding count matches article count")

    # ========== PREPARE ARTICLE LIST ==========
    print(f"\n{'='*80}")
    print("PREPARING ARTICLE METADATA")
    print(f"{'='*80}\n")

    # Extract article titles (include full metadata for reference)
    article_titles = []
    for article in articles:
        article_titles.append({
            'title': article.get('title', ''),
            'id': article.get('id', ''),
            'url': article.get('url', '')
        })

    print(f"  ✓ Extracted {len(article_titles):,} article titles")

    # ========== SAVE MERGED FILE ==========
    print(f"\n{'='*80}")
    print("SAVING MERGED EMBEDDINGS")
    print(f"{'='*80}\n")

    print(f"Saving to {output_file}...")

    # Create output directory if needed
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Prepare output data
    output_data = {
        'embeddings': all_embeddings,
        'articles': article_titles,
        'total_articles': len(article_titles),
        'embedding_dim': embedding_dim,
        'model': model_name,
        'timestamp': datetime.now().isoformat(),
        'shape': all_embeddings.shape,
        'quality_metrics': metrics,
        'chunk_info': [
            {
                'cluster_id': chunk['cluster_id'],
                'gpu_id': chunk['gpu_id'],
                'start_index': chunk['start_index'],
                'end_index': chunk['end_index'],
                'filepath': chunk['filepath']
            }
            for chunk in chunks
        ]
    }

    # Save to pickle
    try:
        with open(output_file, 'wb') as f:
            pickle.dump(output_data, f)

        file_size_mb = output_file.stat().st_size / 1e6
        print(f"  ✓ Saved {len(article_titles):,} article embeddings")
        print(f"  File size: {file_size_mb:.2f} MB")
        print(f"  Timestamp: {output_data['timestamp']}")

        return True

    except Exception as e:
        print(f"  ✗ Error saving file: {e}")
        return False


# ============================================================================
# MAIN WORKFLOW
# ============================================================================

def main():
    """Main entry point for sync/merge workflow."""

    parser = argparse.ArgumentParser(
        description="Sync embedding files from remote clusters and merge into single file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sync and merge (default)
  python sync_and_merge_embeddings.py

  # Only sync files, don't merge
  python sync_and_merge_embeddings.py --sync-only

  # Only merge existing local files, don't sync
  python sync_and_merge_embeddings.py --merge-only

  # Specify which clusters to sync from
  python sync_and_merge_embeddings.py --clusters "tensor01 tensor02"

  # Sync only from tensor01
  python sync_and_merge_embeddings.py --clusters "tensor01" --sync-only
        """
    )

    parser.add_argument(
        '--sync-only',
        action='store_true',
        help='Only sync files from clusters, do not merge'
    )

    parser.add_argument(
        '--merge-only',
        action='store_true',
        help='Only merge existing local files, do not sync'
    )

    parser.add_argument(
        '--clusters',
        default='tensor01 tensor02',
        help='Space-separated list of clusters to sync from (default: "tensor01 tensor02")'
    )

    parser.add_argument(
        '--output',
        default='embeddings/wikipedia_merged.pkl',
        help='Output file path for merged embeddings (default: embeddings/wikipedia_merged.pkl)'
    )

    args = parser.parse_args()

    # ========== HEADER ==========
    print(f"\n{'='*80}")
    print("EMBEDDING SYNC & MERGE")
    print(f"{'='*80}")
    print(f"Started: {datetime.now()}")
    print(f"Working directory: {Path.cwd()}")
    print("")

    # Create embeddings directory
    embeddings_dir = Path(__file__).parent / "embeddings"
    embeddings_dir.mkdir(exist_ok=True)
    print(f"Embeddings directory: {embeddings_dir}\n")

    output_file = Path(__file__).parent / args.output
    downloaded_files = []

    # ========== SYNC PHASE ==========
    if not args.merge_only:
        print(f"{'='*80}")
        print("SYNC PHASE")
        print(f"{'='*80}\n")

        cluster_list = args.clusters.split()
        all_warnings = []

        for cluster_name in cluster_list:
            files, warnings = sync_from_cluster(
                cluster_name,
                embeddings_dir,
                use_sshpass=False  # Use paramiko by default
            )
            downloaded_files.extend(files)
            all_warnings.extend(warnings)

        print(f"\n{'='*80}")
        print("SYNC SUMMARY")
        print(f"{'='*80}")
        print(f"Total files downloaded: {len(downloaded_files)}")

        if all_warnings:
            print(f"Warnings ({len(all_warnings)}):")
            for warning in all_warnings:
                print(f"  ⚠ {warning}")

        if args.sync_only:
            print(f"\n✓ SYNC COMPLETE (merge skipped)")
            print(f"Downloaded files: {embeddings_dir}")
            return 0

    else:
        # Collect existing local files
        print(f"{'='*80}")
        print("LOADING EXISTING FILES")
        print(f"{'='*80}\n")

        local_files = sorted(embeddings_dir.glob("cluster*_gpu*.pkl"))
        if local_files:
            downloaded_files = local_files
            print(f"Found {len(downloaded_files)} local embedding files\n")
        else:
            print(f"✗ No embedding files found in {embeddings_dir}")
            return 1

    # ========== MERGE PHASE ==========
    print(f"\n{'='*80}")
    print("MERGE PHASE")
    print(f"{'='*80}\n")

    # Load articles metadata
    try:
        articles = load_wikipedia_articles()
    except (FileNotFoundError, ValueError, pickle.UnpicklingError) as e:
        print(f"✗ Error loading articles: {e}")
        return 1

    # Perform merge
    success = merge_embeddings(
        embedding_files=downloaded_files,
        output_file=output_file,
        articles=articles,
        embedding_dim=768,
        num_articles=250000,
        model_name='google/embeddinggemma-300m'
    )

    # ========== FINAL SUMMARY ==========
    print(f"\n{'='*80}")
    if success:
        print("✓ MERGE COMPLETE!")
    else:
        print("✗ MERGE FAILED!")
    print(f"{'='*80}")

    if success:
        print(f"\nOutput file: {output_file}")
        file_size_mb = output_file.stat().st_size / 1e6
        print(f"File size: {file_size_mb:.2f} MB")
        print(f"Completed: {datetime.now()}")
        print(f"\nNext steps:")
        print(f"  1. Generate UMAP projections using the merged embeddings")
        print(f"  2. Create knowledge map visualization")
        return 0
    else:
        print(f"\nMerge failed. Check errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
