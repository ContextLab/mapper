#!/usr/bin/env python3
"""
Spot check cell labels by testing specific cells:
1. Cells near each question
2. Cells between different questions
3. Cells on the periphery
"""

import json
import numpy as np
import subprocess
import sys

def load_questions():
    """Load questions from JSON."""
    with open('questions.json') as f:
        return json.load(f)

def normalize_to_grid(x, y, grid_size=40):
    """Convert normalized [0, 1] coordinates to grid coordinates."""
    gx = int(x * grid_size)
    gy = int(y * grid_size)
    # Clamp to valid range
    gx = max(0, min(grid_size - 1, gx))
    gy = max(0, min(grid_size - 1, gy))
    return gx, gy

def denormalize_grid(gx, gy, grid_size=40):
    """Convert grid coordinates back to normalized [0, 1] coordinates (center of cell)."""
    x = (gx + 0.5) / grid_size
    y = (gy + 0.5) / grid_size
    return x, y

def find_cell_near_question(question, grid_size=40):
    """Find grid cell nearest to a question."""
    return normalize_to_grid(question['x'], question['y'], grid_size)

def find_cell_between_questions(q1, q2, grid_size=40):
    """Find grid cell at midpoint between two questions."""
    mid_x = (q1['x'] + q2['x']) / 2
    mid_y = (q1['y'] + q2['y']) / 2
    return normalize_to_grid(mid_x, mid_y, grid_size)

def find_peripheral_cells(questions, grid_size=40):
    """Find cells on the periphery (corners and edges)."""
    # Get bounds of questions
    x_coords = [q['x'] for q in questions]
    y_coords = [q['y'] for q in questions]

    x_min, x_max = min(x_coords), max(x_coords)
    y_min, y_max = min(y_coords), max(y_coords)

    # Sample peripheral cells
    periphery = []

    # Corners (in normalized space, outside question cluster)
    corners = [
        (0.0, 0.0),   # Bottom-left
        (1.0, 0.0),   # Bottom-right
        (0.0, 1.0),   # Top-left
        (1.0, 1.0),   # Top-right
    ]

    for x, y in corners:
        gx, gy = normalize_to_grid(x, y, grid_size)
        periphery.append(('corner', gx, gy, x, y))

    # Edge midpoints
    edges = [
        (0.5, 0.0),   # Bottom center
        (0.5, 1.0),   # Top center
        (0.0, 0.5),   # Left center
        (1.0, 0.5),   # Right center
    ]

    for x, y in edges:
        gx, gy = normalize_to_grid(x, y, grid_size)
        periphery.append(('edge', gx, gy, x, y))

    return periphery

def generate_single_cell_label(gx, gy, grid_size=40, verbose=False):
    """Generate label for a single cell by running generate_cell_labels.py."""
    # This would require modifying generate_cell_labels.py to support single-cell mode
    # For now, we'll generate a small grid and extract the cell
    # This is inefficient but works for spot checking

    import os
    import pickle
    from generate_cell_labels import (
        load_questions,
        load_umap_model,
        load_umap_bounds,
        invert_umap_coordinates,
        validate_embedding,
        repair_embedding,
        recover_tokens_from_embedding,
        generate_label_from_tokens
    )

    # Load data
    questions = load_questions('questions.json')
    reducer = load_umap_model('data/umap_reducer.pkl')
    bounds = load_umap_bounds('data/umap_bounds.pkl')

    # Convert grid coords to normalized coords
    x_norm, y_norm = denormalize_grid(gx, gy, grid_size)

    # Invert UMAP coordinates to get embedding
    embedding, quality_score_umap = invert_umap_coordinates(x_norm, y_norm, reducer, bounds)

    if verbose:
        print(f"  Normalized coords: ({x_norm:.3f}, {y_norm:.3f})")
        print(f"  UMAP quality score: {quality_score_umap:.3f}")

    # Validate and repair embedding
    reference_embeddings = np.array([q['embedding_full'] for q in questions])
    is_valid, diagnostics = validate_embedding(embedding, reference_embeddings)

    if verbose:
        print(f"  Is valid: {is_valid}")
        if 'norm' in diagnostics:
            print(f"  Norm: {diagnostics['norm']:.3f}")
        if 'max_cosine_similarity' in diagnostics:
            print(f"  Max cosine similarity: {diagnostics['max_cosine_similarity']:.3f}")

    if not is_valid:
        if verbose:
            print(f"  Invalid embedding - repairing...")
        embedding, repair_log = repair_embedding(embedding, reference_embeddings, quality_score_umap)
        if verbose and repair_log:
            for log_entry in repair_log:
                print(f"    {log_entry}")

    # Recover tokens
    tokens, metadata = recover_tokens_from_embedding(
        embedding,
        model_name='sentence-transformers/gtr-t5-base'
    )

    if verbose and tokens:
        print(f"  Recovered {len(tokens)} tokens via vec2text")

    # Generate label (note: LM Studio may not be running, so label might be empty)
    label = generate_label_from_tokens(tokens, existing_labels=None, token_metadata=metadata)

    return {
        'grid_coords': (gx, gy),
        'norm_coords': (x_norm, y_norm),
        'quality_score': quality_score_umap,
        'is_valid': is_valid,
        'diagnostics': diagnostics,
        'tokens': tokens[:5],  # Top 5 tokens
        'label': label,
        'metadata': metadata
    }

def distance(q1, q2):
    """Calculate Euclidean distance between two questions."""
    dx = q1['x'] - q2['x']
    dy = q1['y'] - q2['y']
    return np.sqrt(dx*dx + dy*dy)

def main():
    print("=" * 80)
    print("Cell Label Spot Check")
    print("=" * 80)
    print()

    # Load questions
    questions = load_questions()
    print(f"Loaded {len(questions)} questions")
    print()

    grid_size = 40
    spot_checks = []

    # 1. Cells near each question
    print("=" * 80)
    print("PHASE 1: Cells Near Questions")
    print("=" * 80)
    print()

    for i, q in enumerate(questions):
        print(f"Question {i+1}/{len(questions)}: {q['question'][:60]}...")
        print(f"  Position: ({q['x']:.3f}, {q['y']:.3f})")

        gx, gy = find_cell_near_question(q, grid_size)
        print(f"  Nearest cell: ({gx}, {gy})")

        result = generate_single_cell_label(gx, gy, grid_size, verbose=True)
        spot_checks.append({
            'type': 'near_question',
            'question_idx': i,
            'question_text': q['question'],
            **result
        })

        print(f"  Recovered tokens: {result['tokens'][:3]}")
        print(f"  Label: \"{result['label']}\"")
        print()

    # 2. Cells between questions
    print("=" * 80)
    print("PHASE 2: Cells Between Questions")
    print("=" * 80)
    print()

    # Find pairs of questions that are relatively close
    pairs = []
    for i in range(len(questions)):
        for j in range(i+1, len(questions)):
            dist = distance(questions[i], questions[j])
            pairs.append((dist, i, j))

    # Take closest 3 pairs
    pairs.sort()
    for dist, i, j in pairs[:3]:
        q1, q2 = questions[i], questions[j]
        print(f"Between Q{i+1} and Q{j+1} (distance: {dist:.3f})")
        print(f"  Q{i+1}: {q1['question'][:60]}...")
        print(f"  Q{j+1}: {q2['question'][:60]}...")

        gx, gy = find_cell_between_questions(q1, q2, grid_size)
        print(f"  Midpoint cell: ({gx}, {gy})")

        result = generate_single_cell_label(gx, gy, grid_size, verbose=True)
        spot_checks.append({
            'type': 'between_questions',
            'question_idx1': i,
            'question_idx2': j,
            'question1_text': q1['question'],
            'question2_text': q2['question'],
            **result
        })

        print(f"  Recovered tokens: {result['tokens'][:3]}")
        print(f"  Label: \"{result['label']}\"")
        print()

    # 3. Peripheral cells
    print("=" * 80)
    print("PHASE 3: Peripheral Cells")
    print("=" * 80)
    print()

    peripheral_cells = find_peripheral_cells(questions, grid_size)
    for cell_type, gx, gy, x_norm, y_norm in peripheral_cells:
        print(f"Peripheral cell ({cell_type}): ({gx}, {gy}) @ ({x_norm:.3f}, {y_norm:.3f})")

        result = generate_single_cell_label(gx, gy, grid_size, verbose=True)
        spot_checks.append({
            'type': f'periphery_{cell_type}',
            **result
        })

        print(f"  Recovered tokens: {result['tokens'][:3]}")
        print(f"  Label: \"{result['label']}\"")
        print()

    # Summary
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Total spot checks: {len(spot_checks)}")
    print()

    # Quality distribution
    quality_scores = [sc['quality_score'] for sc in spot_checks]
    print(f"Quality scores:")
    print(f"  Min: {min(quality_scores):.3f}")
    print(f"  Max: {max(quality_scores):.3f}")
    print(f"  Mean: {np.mean(quality_scores):.3f}")
    print(f"  Median: {np.median(quality_scores):.3f}")
    print()

    # Label analysis
    labels_present = sum(1 for sc in spot_checks if sc['label'] and sc['label'].strip())
    print(f"Labels generated: {labels_present}/{len(spot_checks)}")
    if labels_present == 0:
        print("  ⚠️  Note: LM Studio may not be running, so labels are empty")
    print()

    # Save results
    with open('spot_check_results.json', 'w') as f:
        json.dump(spot_checks, f, indent=2)
    print("Results saved to spot_check_results.json")

if __name__ == '__main__':
    main()
