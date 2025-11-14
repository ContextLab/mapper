#!/usr/bin/env python3
"""
Verify cell labels by sampling grid coordinates and checking if they make sense
relative to nearby questions.
"""

import json
import numpy as np
from collections import defaultdict

def load_data():
    """Load questions and cell labels."""
    with open('questions.json') as f:
        questions = json.load(f)

    with open('heatmap_cell_labels.json') as f:
        cell_labels = json.load(f)

    return questions, cell_labels

def find_nearest_questions(cell_x, cell_y, questions, k=3):
    """Find k nearest questions to a cell coordinate."""
    distances = []
    for i, q in enumerate(questions):
        dx = q['x'] - cell_x
        dy = q['y'] - cell_y
        dist = np.sqrt(dx*dx + dy*dy)
        distances.append((dist, i, q))

    distances.sort()
    return distances[:k]

def sample_grid_cells(grid_size=40, sample_every=4):
    """Sample grid cells by taking every Nth cell."""
    sampled_cells = []
    for i in range(0, grid_size, sample_every):
        for j in range(0, grid_size, sample_every):
            # Normalize to [0, 1] range (matching generate_cell_labels.py logic)
            x = (i + 0.5) / grid_size
            y = (j + 0.5) / grid_size
            sampled_cells.append((i, j, x, y))
    return sampled_cells

def main():
    print("=" * 80)
    print("Cell Label Verification")
    print("=" * 80)
    print()

    # Load data
    questions, cell_labels_data = load_data()

    # Convert cell labels to dict for easy lookup
    cell_labels = {}
    for cell in cell_labels_data['cells']:
        key = (cell['gx'], cell['gy'])
        cell_labels[key] = cell['label']

    print(f"Loaded {len(questions)} questions")
    print(f"Loaded {len(cell_labels)} cell labels")
    print()

    # Generate cell labels for 40x40 grid if not already done
    grid_size = cell_labels_data['metadata']['grid_size']
    if grid_size != 40:
        print(f"⚠️  Warning: Cell labels were generated for {grid_size}x{grid_size} grid, not 40x40")
        print("   Run: python generate_cell_labels.py --grid-size 40")
        print()
        grid_size = 40
        print("   Proceeding with verification using existing labels...")
        print()

    # Sample every 4th cell
    sampled_cells = sample_grid_cells(grid_size=grid_size, sample_every=4)
    print(f"Sampled {len(sampled_cells)} cells (every 4th cell in {grid_size}x{grid_size} grid)")
    print()

    # Verify each sampled cell
    print("=" * 80)
    print("Verification Results")
    print("=" * 80)
    print()

    verification_results = []

    for grid_x, grid_y, cell_x, cell_y in sampled_cells:
        # Get cell label
        label = cell_labels.get((grid_x, grid_y), "NOT FOUND")

        # Find nearest questions
        nearest = find_nearest_questions(cell_x, cell_y, questions, k=3)

        result = {
            'grid_coords': (grid_x, grid_y),
            'norm_coords': (cell_x, cell_y),
            'label': label,
            'nearest_questions': [
                {
                    'distance': dist,
                    'question': q['question'][:80] + ('...' if len(q['question']) > 80 else '')
                }
                for dist, idx, q in nearest
            ]
        }
        verification_results.append(result)

    # Display results in groups of 10 for readability
    for i, result in enumerate(verification_results):
        if i > 0 and i % 10 == 0:
            print()
            print("-" * 80)
            print()

        print(f"Cell ({result['grid_coords'][0]:2d}, {result['grid_coords'][1]:2d}) "
              f"@ ({result['norm_coords'][0]:.3f}, {result['norm_coords'][1]:.3f})")
        print(f"  Label: \"{result['label']}\"")
        print(f"  Nearest questions:")
        for j, nq in enumerate(result['nearest_questions'], 1):
            print(f"    {j}. [{nq['distance']:.3f}] {nq['question']}")
        print()

    # Summary statistics
    print()
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Total cells verified: {len(verification_results)}")
    print(f"Cells with labels: {sum(1 for r in verification_results if r['label'] and r['label'] != 'NOT FOUND')}")
    print(f"Empty labels: {sum(1 for r in verification_results if not r['label'] or r['label'].strip() == '')}")
    print(f"Not found: {sum(1 for r in verification_results if r['label'] == 'NOT FOUND')}")

    # Group by label to check uniqueness
    label_counts = defaultdict(int)
    for r in verification_results:
        if r['label'] and r['label'] != 'NOT FOUND':
            label_counts[r['label']] += 1

    print(f"Unique labels: {len(label_counts)}")

    # Show most common labels
    if label_counts:
        print()
        print("Most common labels:")
        for label, count in sorted(label_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  \"{label}\": {count} cells")

if __name__ == '__main__':
    main()
