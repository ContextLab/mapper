#!/usr/bin/env python3
"""Precompute pairwise distances between all cell centers."""

import json
import numpy as np
from scipy.spatial.distance import cdist
from pathlib import Path

def precompute_cell_distances():
    # Load cell questions
    input_file = Path('cell_questions.json')
    if not input_file.exists():
        print(f"Error: {input_file} not found")
        return

    with open(input_file) as f:
        data = json.load(f)

    # Extract cell coordinates
    cells = []
    cell_keys = []

    for cell_data in data['cells']:
        cell = cell_data['cell']
        cells.append([cell['center_x'], cell['center_y']])
        cell_keys.append(f"{cell['gx']}_{cell['gy']}")

    coords = np.array(cells)

    # Compute pairwise distances (Euclidean in normalized [0,1] space)
    print(f"Computing distances for {len(cells)} cells...")
    distances = cdist(coords, coords, metric='euclidean')

    # Create output
    output = {
        'cell_keys': cell_keys,
        'distances': distances.tolist(),
        'metadata': {
            'num_cells': len(cells),
            'metric': 'euclidean',
            'coordinate_space': 'normalized [0,1]',
            'source_file': str(input_file),
            'dimensions': list(distances.shape)
        }
    }

    output_file = Path('cell_distances.json')
    with open(output_file, 'w') as f:
        json.dump(output, f)

    file_size_mb = output_file.stat().st_size / (1024 * 1024)
    print(f"✓ Computed {len(cells)}×{len(cells)} distance matrix")
    print(f"✓ Saved to {output_file} ({file_size_mb:.2f} MB)")

    # Print statistics
    print(f"\nDistance statistics:")
    print(f"  Min: {distances.min():.4f}")
    print(f"  Max: {distances.max():.4f}")
    print(f"  Mean: {distances.mean():.4f}")
    print(f"  Median: {np.median(distances):.4f}")

if __name__ == '__main__':
    precompute_cell_distances()
