#!/usr/bin/env python3
"""
Merge embeddings from all GPU workers into a single file.

This script:
1. Downloads all embedding chunks from both clusters via SCP
2. Merges them into a single embeddings.pkl file
3. Verifies count and dimensions
4. Saves for UMAP processing
"""

import pickle
import json
import paramiko
import os
import sys
from pathlib import Path
from datetime import datetime
import numpy as np

def load_credentials(cluster_name):
    """Load cluster credentials from .credentials folder."""
    creds_file = Path(__file__).parent / ".credentials" / f"{cluster_name}.credentials"

    if not creds_file.exists():
        raise FileNotFoundError(f"Credentials file not found: {creds_file}")

    with open(creds_file, 'r') as f:
        creds = json.load(f)

    return creds

def download_embeddings_from_cluster(cluster_name, cluster_id, output_dir):
    """
    Download all embedding files from a cluster via SCP.

    Args:
        cluster_name: "tensor01" or "tensor02"
        cluster_id: 1 or 2
        output_dir: Local directory to save files

    Returns:
        list: Paths to downloaded files
    """
    print(f"\nDownloading from {cluster_name}...")

    creds = load_credentials(cluster_name)

    # Create SSH/SCP client
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(
            hostname=creds['address'],
            username=creds['username'],
            password=creds['password'],
            timeout=30
        )

        # Create SFTP client
        sftp = ssh.open_sftp()

        # Remote directory
        remote_dir = f"/home/{creds['username']}/mapper_embeddings/embeddings"

        # List files matching pattern
        remote_files = sftp.listdir(remote_dir)
        embedding_files = [f for f in remote_files if f.startswith(f'cluster{cluster_id}_gpu') and f.endswith('.pkl')]

        print(f"  Found {len(embedding_files)} embedding files")

        downloaded_files = []

        for remote_file in sorted(embedding_files):
            remote_path = f"{remote_dir}/{remote_file}"
            local_path = output_dir / remote_file

            print(f"  Downloading {remote_file}...", end=' ')
            sftp.get(remote_path, str(local_path))

            file_size_mb = local_path.stat().st_size / 1e6
            print(f"✓ ({file_size_mb:.2f} MB)")

            downloaded_files.append(local_path)

        sftp.close()
        ssh.close()

        return downloaded_files

    except Exception as e:
        print(f"  ✗ Error: {e}")
        ssh.close()
        return []

def merge_embeddings(embedding_files, output_file):
    """
    Merge all embedding files into a single file.

    Args:
        embedding_files: List of paths to embedding checkpoint files
        output_file: Path to save merged embeddings

    Returns:
        numpy.ndarray: Merged embeddings array
    """

    print("\n" + "="*80)
    print("MERGING EMBEDDINGS")
    print("="*80)

    # Load all chunks
    chunks = []

    for file_path in sorted(embedding_files):
        print(f"\nLoading {file_path.name}...")

        with open(file_path, 'rb') as f:
            data = pickle.load(f)

        embeddings = data['embeddings']
        start_idx = data['start_index']
        end_idx = data['end_index']
        cluster_id = data['cluster_id']
        gpu_id = data['gpu_id']

        print(f"  Cluster {cluster_id}, GPU {gpu_id}")
        print(f"  Indices: {start_idx:,} - {end_idx:,}")
        print(f"  Shape: {embeddings.shape}")
        print(f"  Items: {len(embeddings):,}")

        chunks.append({
            'embeddings': embeddings,
            'start_index': start_idx,
            'end_index': end_idx,
            'cluster_id': cluster_id,
            'gpu_id': gpu_id
        })

    # Sort by start_index to ensure correct order
    chunks.sort(key=lambda x: x['start_index'])

    print("\n" + "="*80)
    print("VERIFYING ORDER")
    print("="*80)

    # Verify continuity
    expected_idx = 0
    for chunk in chunks:
        if chunk['start_index'] != expected_idx:
            print(f"  ✗ ERROR: Gap detected!")
            print(f"    Expected index: {expected_idx}")
            print(f"    Got index: {chunk['start_index']}")
            sys.exit(1)

        expected_idx = chunk['end_index']
        print(f"  ✓ Chunk {chunk['cluster_id']}-{chunk['gpu_id']}: {chunk['start_index']:,} - {chunk['end_index']:,}")

    print(f"\n  ✓ All chunks are continuous")
    print(f"  Total items: {expected_idx:,}")

    # Concatenate embeddings
    print("\n" + "="*80)
    print("CONCATENATING")
    print("="*80)

    all_embeddings = np.concatenate([chunk['embeddings'] for chunk in chunks], axis=0)

    print(f"  Shape: {all_embeddings.shape}")
    print(f"  Items: {len(all_embeddings):,}")
    print(f"  Dimensions: {all_embeddings.shape[1]}")

    # Verify embeddings
    print("\n" + "="*80)
    print("QUALITY CHECK")
    print("="*80)

    norms = np.linalg.norm(all_embeddings, axis=1)
    print(f"\nEmbedding norms:")
    print(f"  Mean: {norms.mean():.4f}")
    print(f"  Std: {norms.std():.4f}")
    print(f"  Min: {norms.min():.4f}")
    print(f"  Max: {norms.max():.4f}")

    # Check for NaN or inf
    has_nan = np.isnan(all_embeddings).any()
    has_inf = np.isinf(all_embeddings).any()

    if has_nan or has_inf:
        print(f"  ✗ ERROR: Found NaN or Inf values!")
        print(f"    NaN: {has_nan}")
        print(f"    Inf: {has_inf}")
        sys.exit(1)

    print(f"  ✓ No NaN or Inf values")

    # Save merged embeddings
    print("\n" + "="*80)
    print("SAVING MERGED EMBEDDINGS")
    print("="*80)

    print(f"\nSaving to {output_file}...")

    with open(output_file, 'wb') as f:
        pickle.dump(all_embeddings, f)

    file_size_mb = output_file.stat().st_size / 1e6
    print(f"  ✓ Saved {len(all_embeddings):,} embeddings")
    print(f"  File size: {file_size_mb:.2f} MB")

    return all_embeddings

def main():
    """Main merge workflow."""

    print("="*80)
    print("EMBEDDING MERGE SCRIPT")
    print("="*80)
    print(f"Started: {datetime.now()}")
    print("")

    # Create output directory for downloaded chunks
    download_dir = Path(__file__).parent / "downloaded_embeddings"
    download_dir.mkdir(exist_ok=True)

    print(f"Download directory: {download_dir}")
    print("")

    # Download from both clusters
    all_files = []

    # Cluster 1
    files1 = download_embeddings_from_cluster("tensor01", 1, download_dir)
    all_files.extend(files1)

    # Cluster 2
    files2 = download_embeddings_from_cluster("tensor02", 2, download_dir)
    all_files.extend(files2)

    print(f"\nTotal files downloaded: {len(all_files)}")

    if len(all_files) != 16:
        print(f"  ✗ WARNING: Expected 16 files (2 clusters × 8 GPUs), got {len(all_files)}")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Aborted")
            sys.exit(1)

    # Merge embeddings
    output_file = Path(__file__).parent / "embeddings.pkl"
    embeddings = merge_embeddings(all_files, output_file)

    # Success
    print("\n" + "="*80)
    print("✓ MERGE COMPLETE!")
    print("="*80)
    print(f"Output file: {output_file}")
    print(f"Total embeddings: {len(embeddings):,}")
    print(f"Shape: {embeddings.shape}")
    print(f"Completed: {datetime.now()}")
    print("")
    print("Next steps:")
    print("  1. Run UMAP projection on embeddings.pkl")
    print("  2. Generate final knowledge map visualization")
    print("")

if __name__ == '__main__':
    main()
