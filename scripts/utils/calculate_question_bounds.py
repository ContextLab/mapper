#!/usr/bin/env python3
"""
Calculate adaptive heatmap bounds based on question coordinates.

This script:
1. Loads question coordinates from data/question_coordinates.pkl (if available)
   OR from questions.json as a fallback
2. Calculates bounding box from question coordinates (min/max x and y)
3. Adds 10% padding to bounds
4. Saves to data/heatmap_bounds.json for visualization

Implements Issue #8: Adaptive heatmap bounding for question-focused visualization.
"""

import json
import pickle
import os
import sys
import numpy as np
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent


def load_question_coordinates():
    """
    Load question coordinates from question_coordinates.pkl or questions.json.

    Returns:
        numpy.ndarray: Array of shape (n_questions, 2) with x, y coordinates
    """
    # Try loading from question_coordinates.pkl (Issue #7 output)
    pkl_path = PROJECT_ROOT / "data" / "question_coordinates.pkl"

    if pkl_path.exists():
        print(f"Loading question coordinates from {pkl_path}")
        with open(pkl_path, 'rb') as f:
            data = pickle.load(f)

        # Handle different possible formats
        if isinstance(data, dict):
            if 'coordinates' in data:
                coords = data['coordinates']
            elif 'question_coords' in data:
                coords = data['question_coords']
            else:
                # Assume dict with question indices as keys
                coords = np.array([data[k] for k in sorted(data.keys())])
        elif isinstance(data, (list, np.ndarray)):
            coords = np.array(data)
        else:
            raise ValueError(f"Unexpected data format in {pkl_path}: {type(data)}")

        print(f"  Loaded {len(coords)} question coordinates from pickle file")
        return np.array(coords)

    # Fallback: Load from questions.json
    json_path = PROJECT_ROOT / "questions.json"
    if not json_path.exists():
        raise FileNotFoundError(
            f"Neither {pkl_path} nor {json_path} found. "
            "Please complete Issue #7 first or ensure questions.json exists."
        )

    print(f"Loading question coordinates from {json_path}")
    with open(json_path, 'r') as f:
        questions = json.load(f)

    # Extract x, y coordinates
    coords = []
    for i, q in enumerate(questions):
        if 'x' not in q or 'y' not in q:
            raise ValueError(
                f"Question {i} missing coordinates. "
                "Please run generate_embeddings.py first."
            )
        coords.append([q['x'], q['y']])

    coords = np.array(coords)
    print(f"  Loaded {len(coords)} question coordinates from JSON file")
    return coords


def calculate_bounds_with_padding(coords, padding=0.1):
    """
    Calculate bounding box with padding.

    Args:
        coords: numpy array of shape (n, 2) with x, y coordinates
        padding: float, fraction of range to add as padding (default: 0.1 = 10%)

    Returns:
        dict with x_min, x_max, y_min, y_max, padding
    """
    if len(coords) == 0:
        raise ValueError("No coordinates provided")

    # Calculate raw bounds
    x_min = float(coords[:, 0].min())
    x_max = float(coords[:, 0].max())
    y_min = float(coords[:, 1].min())
    y_max = float(coords[:, 1].max())

    # Calculate ranges
    x_range = x_max - x_min
    y_range = y_max - y_min

    # Add padding
    x_min_padded = x_min - (padding * x_range)
    x_max_padded = x_max + (padding * x_range)
    y_min_padded = y_min - (padding * y_range)
    y_max_padded = y_max + (padding * y_range)

    bounds = {
        'x_min': x_min_padded,
        'x_max': x_max_padded,
        'y_min': y_min_padded,
        'y_max': y_max_padded,
        'padding': padding,
        'raw_bounds': {
            'x_min': x_min,
            'x_max': x_max,
            'y_min': y_min,
            'y_max': y_max
        },
        'metadata': {
            'num_questions': len(coords),
            'x_range': x_range,
            'y_range': y_range,
            'aspect_ratio': x_range / y_range if y_range > 0 else 1.0
        }
    }

    return bounds


def verify_bounds(coords, bounds):
    """
    Verify that all questions are within the calculated bounds.

    Args:
        coords: numpy array of shape (n, 2) with x, y coordinates
        bounds: dict with x_min, x_max, y_min, y_max

    Returns:
        bool: True if all questions are within bounds
    """
    x_in_bounds = (coords[:, 0] >= bounds['x_min']) & (coords[:, 0] <= bounds['x_max'])
    y_in_bounds = (coords[:, 1] >= bounds['y_min']) & (coords[:, 1] <= bounds['y_max'])
    all_in_bounds = x_in_bounds & y_in_bounds

    if not all_in_bounds.all():
        out_of_bounds = np.where(~all_in_bounds)[0]
        print(f"  WARNING: {len(out_of_bounds)} questions out of bounds: {out_of_bounds}")
        return False

    return True


def save_bounds(bounds, output_path):
    """Save bounds to JSON file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(bounds, f, indent=2)

    print(f"\n Saved bounds to {output_path}")


def main():
    """Main function to calculate and save question bounds."""
    print("="*80)
    print("CALCULATE QUESTION BOUNDS (Issue #8)")
    print("="*80)

    try:
        # Step 1: Load question coordinates
        coords = load_question_coordinates()

        # Step 2: Calculate bounds with 10% padding
        print("\nCalculating bounds with 10% padding...")
        bounds = calculate_bounds_with_padding(coords, padding=0.1)

        # Step 3: Verify bounds
        print("\nVerifying bounds...")
        all_valid = verify_bounds(coords, bounds)

        if all_valid:
            print("  All questions are within bounds")
        else:
            print("  ERROR: Some questions are out of bounds!")
            sys.exit(1)

        # Step 4: Save to data/heatmap_bounds.json
        output_path = PROJECT_ROOT / "data" / "heatmap_bounds.json"
        save_bounds(bounds, output_path)

        # Print summary
        print("\n" + "="*80)
        print("BOUNDS SUMMARY")
        print("="*80)
        print(f"\nRaw bounds (no padding):")
        print(f"  X: [{bounds['raw_bounds']['x_min']:.6f}, {bounds['raw_bounds']['x_max']:.6f}]")
        print(f"  Y: [{bounds['raw_bounds']['y_min']:.6f}, {bounds['raw_bounds']['y_max']:.6f}]")
        print(f"\nPadded bounds (10% padding):")
        print(f"  X: [{bounds['x_min']:.6f}, {bounds['x_max']:.6f}]")
        print(f"  Y: [{bounds['y_min']:.6f}, {bounds['y_max']:.6f}]")
        print(f"\nMetadata:")
        print(f"  Number of questions: {bounds['metadata']['num_questions']}")
        print(f"  X range: {bounds['metadata']['x_range']:.6f}")
        print(f"  Y range: {bounds['metadata']['y_range']:.6f}")
        print(f"  Aspect ratio: {bounds['metadata']['aspect_ratio']:.6f}")
        print(f"  Padding: {bounds['padding']*100:.0f}%")

        print("\n" + "="*80)
        print("SUCCESS")
        print("="*80)
        print(f"\nBounds file created: {output_path}")
        print("\nVerification:")
        print(f"  Min < Max (X): {bounds['x_min']} < {bounds['x_max']} = {bounds['x_min'] < bounds['x_max']}")
        print(f"  Min < Max (Y): {bounds['y_min']} < {bounds['y_max']} = {bounds['y_min'] < bounds['y_max']}")
        print(f"  All questions within bounds: {all_valid}")
        print(f"  Padding applied correctly: {bounds['padding'] == 0.1}")

    except FileNotFoundError as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        print("\nPlease complete Issue #7 first to generate question_coordinates.pkl", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
