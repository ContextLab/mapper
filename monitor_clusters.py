#!/usr/bin/env python3
"""
Monitor distributed embedding generation across both clusters.

This script:
1. SSHs to both tensor01 and tensor02
2. Checks progress.json on each cluster
3. Reports combined status
4. Estimates time remaining
"""

import json
import paramiko
import time
import sys
from datetime import datetime, timedelta
from pathlib import Path

def load_credentials(cluster_name):
    """Load cluster credentials from .credentials folder."""
    creds_file = Path(__file__).parent / ".credentials" / f"{cluster_name}.credentials"

    if not creds_file.exists():
        raise FileNotFoundError(f"Credentials file not found: {creds_file}")

    with open(creds_file, 'r') as f:
        creds = json.load(f)

    return creds

def get_cluster_progress(cluster_name):
    """
    SSH to cluster and retrieve progress.json.

    Returns:
        dict: Progress data, or None if not available
    """
    try:
        creds = load_credentials(cluster_name)

        # Create SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect
        ssh.connect(
            hostname=creds['address'],
            username=creds['username'],
            password=creds['password'],
            timeout=10
        )

        # Read progress file
        progress_path = "~/mapper_embeddings/embeddings/progress.json"
        stdin, stdout, stderr = ssh.exec_command(f"cat {progress_path}")

        output = stdout.read().decode()
        error = stderr.read().decode()

        ssh.close()

        if error and "No such file" in error:
            return None

        if output:
            return json.loads(output)

        return None

    except Exception as e:
        print(f"  ✗ Error connecting to {cluster_name}: {e}")
        return None

def format_time(seconds):
    """Format seconds into human-readable time."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.2f}h"

def monitor_clusters(interval=30, max_checks=None):
    """
    Monitor both clusters and report progress.

    Args:
        interval: Seconds between checks (default 30)
        max_checks: Maximum number of checks, or None for infinite
    """

    TOTAL_ITEMS = 250_010
    EXPECTED_WORKERS = 16  # 2 clusters × 8 GPUs

    print("="*80)
    print("CLUSTER MONITORING")
    print("="*80)
    print(f"Target: {TOTAL_ITEMS:,} items")
    print(f"Expected workers: {EXPECTED_WORKERS}")
    print(f"Check interval: {interval}s")
    print("")

    check_count = 0
    start_time = time.time()

    while True:
        check_count += 1

        if max_checks and check_count > max_checks:
            print("\nReached maximum checks, exiting.")
            break

        print(f"{'='*80}")
        print(f"Check #{check_count} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        print("")

        # Get progress from both clusters
        cluster1_progress = get_cluster_progress("tensor01")
        cluster2_progress = get_cluster_progress("tensor02")

        # Process cluster 1
        print("Cluster 1 (tensor01):")
        if cluster1_progress:
            summary = cluster1_progress.get('_summary', {})
            workers = summary.get('total_workers_completed', 0)
            items = summary.get('total_items_processed', 0)
            percent = summary.get('percent_complete', 0)
            print(f"  Workers: {workers}/8")
            print(f"  Items: {items:,}/{TOTAL_ITEMS//2:,} ({percent:.1f}%)")

            # Show worker details
            for key, value in cluster1_progress.items():
                if key.startswith('cluster') and isinstance(value, dict):
                    rate = value.get('rate', 0)
                    items_done = value.get('items_processed', 0)
                    print(f"  - {key}: {items_done:,} items @ {rate:.1f} items/sec")
        else:
            print("  ✗ No progress data available")
        print("")

        # Process cluster 2
        print("Cluster 2 (tensor02):")
        if cluster2_progress:
            summary = cluster2_progress.get('_summary', {})
            workers = summary.get('total_workers_completed', 0)
            items = summary.get('total_items_processed', 0)
            percent = summary.get('percent_complete', 0)
            print(f"  Workers: {workers}/8")
            print(f"  Items: {items:,}/{TOTAL_ITEMS//2:,} ({percent:.1f}%)")

            # Show worker details
            for key, value in cluster2_progress.items():
                if key.startswith('cluster') and isinstance(value, dict):
                    rate = value.get('rate', 0)
                    items_done = value.get('items_processed', 0)
                    print(f"  - {key}: {items_done:,} items @ {rate:.1f} items/sec")
        else:
            print("  ✗ No progress data available")
        print("")

        # Combined summary
        print("Combined Progress:")

        total_workers = 0
        total_items = 0
        total_rate = 0

        if cluster1_progress:
            summary = cluster1_progress.get('_summary', {})
            total_workers += summary.get('total_workers_completed', 0)
            total_items += summary.get('total_items_processed', 0)

            # Sum rates
            for key, value in cluster1_progress.items():
                if key.startswith('cluster') and isinstance(value, dict):
                    total_rate += value.get('rate', 0)

        if cluster2_progress:
            summary = cluster2_progress.get('_summary', {})
            total_workers += summary.get('total_workers_completed', 0)
            total_items += summary.get('total_items_processed', 0)

            # Sum rates
            for key, value in cluster2_progress.items():
                if key.startswith('cluster') and isinstance(value, dict):
                    total_rate += value.get('rate', 0)

        if total_items > 0:
            percent_complete = (total_items / TOTAL_ITEMS) * 100
            remaining_items = TOTAL_ITEMS - total_items

            print(f"  Workers completed: {total_workers}/{EXPECTED_WORKERS}")
            print(f"  Total items: {total_items:,}/{TOTAL_ITEMS:,} ({percent_complete:.1f}%)")

            if total_rate > 0:
                print(f"  Combined rate: {total_rate:.1f} items/sec")

                # Estimate time remaining
                if remaining_items > 0:
                    eta_seconds = remaining_items / total_rate
                    eta_time = datetime.now() + timedelta(seconds=eta_seconds)
                    print(f"  ETA: {format_time(eta_seconds)} (at {eta_time.strftime('%H:%M:%S')})")

            # Check if complete
            if total_workers >= EXPECTED_WORKERS:
                print("")
                print("="*80)
                print("✓ ALL WORKERS COMPLETE!")
                print("="*80)
                elapsed = time.time() - start_time
                print(f"Total monitoring time: {format_time(elapsed)}")
                print("")
                print("Next steps:")
                print("  1. Run merge_embeddings.py to download and combine results")
                print("  2. Continue with UMAP projection")
                break
        else:
            print("  No progress data available from any cluster")

        print("")
        print(f"Next check in {interval}s...")
        print("")

        time.sleep(interval)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Monitor distributed embedding generation')
    parser.add_argument('--interval', type=int, default=30,
                        help='Seconds between checks (default: 30)')
    parser.add_argument('--max-checks', type=int, default=None,
                        help='Maximum number of checks (default: unlimited)')

    args = parser.parse_args()

    try:
        monitor_clusters(interval=args.interval, max_checks=args.max_checks)
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")
        sys.exit(0)
