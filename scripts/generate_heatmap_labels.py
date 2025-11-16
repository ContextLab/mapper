#!/usr/bin/env python3
"""
Generate human-readable labels for heatmap cells using GPT-OSS-20B via LM Studio.

For each cell in the heatmap grid:
1. Find k-nearest Wikipedia articles and questions in UMAP space
2. Prompt GPT-OSS-20B with titles and distances
3. Generate a brief 2-5 word label describing the concept at that cell
4. Save to heatmap_cell_labels.json
"""

import pickle
import json
import numpy as np
import requests
from pathlib import Path
from datetime import datetime


def load_articles():
    """Load Wikipedia articles with normalized coordinates from JSON"""
    print("Loading Wikipedia articles...")
    with open('wikipedia_articles.json', 'r') as f:
        articles_data = json.load(f)

    # Extract titles and normalized coordinates
    titles = [a['title'] for a in articles_data]
    coords = np.array([[a['x'], a['y']] for a in articles_data])

    print(f"  Loaded {len(titles):,} articles with normalized coords")
    print(f"  Coord range: x=[{coords[:, 0].min():.3f}, {coords[:, 0].max():.3f}], y=[{coords[:, 1].min():.3f}, {coords[:, 1].max():.3f}]")
    return titles, coords


def load_questions():
    """Load questions with normalized coordinates from JSON"""
    print("Loading questions...")
    with open('questions.json', 'r') as f:
        questions_data = json.load(f)

    # Extract texts and normalized coordinates
    texts = [q['question'] for q in questions_data]
    coords = np.array([[q['x'], q['y']] for q in questions_data])

    print(f"  Loaded {len(texts)} questions with normalized coords")
    print(f"  Coord range: x=[{coords[:, 0].min():.3f}, {coords[:, 0].max():.3f}], y=[{coords[:, 1].min():.3f}, {coords[:, 1].max():.3f}]")
    return texts, coords


def find_nearest_neighbors(cell_center, article_coords, article_titles,
                          question_coords, question_texts, k=10):
    """
    Find k-nearest articles and questions to a cell center.

    Returns combined list of (distance, type, title/text) tuples, sorted by distance.
    """
    cell_point = np.array([cell_center[0], cell_center[1]])

    # Calculate distances to all articles
    article_distances = np.sqrt(((article_coords - cell_point)**2).sum(axis=1))

    # Calculate distances to all questions
    question_distances = np.sqrt(((question_coords - cell_point)**2).sum(axis=1))

    # Get k nearest articles
    article_nearest_idx = np.argsort(article_distances)[:k]
    article_neighbors = [
        (article_distances[idx], 'article', article_titles[idx])
        for idx in article_nearest_idx
    ]

    # Get k nearest questions
    question_nearest_idx = np.argsort(question_distances)[:k]
    question_neighbors = [
        (question_distances[idx], 'question', question_texts[idx])
        for idx in question_nearest_idx
    ]

    # Combine and sort by distance
    all_neighbors = article_neighbors + question_neighbors
    all_neighbors.sort(key=lambda x: x[0])

    return all_neighbors[:k]


def generate_label_with_gpt(neighbors, cell_center, lm_studio_url="http://localhost:1234/v1/chat/completions"):
    """
    Generate a 2-5 word label for a cell using Qwen3-14B via LM Studio with structured outputs.

    Args:
        neighbors: List of (distance, type, title/text) tuples
        cell_center: (x, y) coordinates of cell center
        lm_studio_url: URL of LM Studio API endpoint

    Returns:
        dict with 'label', 'finish_reason', 'tokens_used'
    """
    # Build context from nearest neighbors
    context_lines = []
    for i, (dist, typ, text) in enumerate(neighbors):
        # Truncate long texts
        text_short = text[:80] + '...' if len(text) > 80 else text
        context_lines.append(f"  {i+1}. [{typ}] {text_short} (distance: {dist:.3f})")

    context = '\n'.join(context_lines)

    # Construct prompt - keep it simple and direct
    prompt = f"""In a 2D text embedding space, provide a human-readable label (2-5 words) for coordinate ({cell_center[0]:.3f}, {cell_center[1]:.3f}).

The nearest neighbors at this coordinate are:
{context}

Based on these neighbors, what is the best short label for this location?"""

    # Define JSON schema for structured output
    response_schema = {
        "type": "object",
        "properties": {
            "label": {
                "type": "string",
                "description": "A concise 2-5 word label describing the concept at this coordinate"
            }
        },
        "required": ["label"]
    }

    # Call LM Studio API with structured output
    try:
        response = requests.post(
            lm_studio_url,
            json={
                "model": "qwen/qwen3-14b",
                "messages": [
                    {"role": "system", "content": "You provide concise 2-5 word labels for locations in text embedding space based on their nearest neighbors."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 50,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "label_response",
                        "strict": True,
                        "schema": response_schema
                    }
                }
            },
            timeout=90
        )

        if response.status_code == 200:
            data = response.json()
            message = data['choices'][0]['message']

            # Parse JSON response
            import json
            content = message.get('content', '{}')
            parsed = json.loads(content)
            label = parsed.get('label', '').strip()

            finish_reason = data['choices'][0].get('finish_reason', 'unknown')
            tokens_used = data.get('usage', {}).get('total_tokens', 0)

            return {
                'label': label,
                'finish_reason': finish_reason,
                'tokens_used': tokens_used
            }
        else:
            print(f"  Error from LM Studio: {response.status_code}")
            return {
                'label': '',
                'finish_reason': 'error',
                'tokens_used': 0
            }

    except requests.exceptions.RequestException as e:
        print(f"  Request failed: {e}")
        return {
            'label': '',
            'finish_reason': 'error',
            'tokens_used': 0
        }
    except json.JSONDecodeError as e:
        print(f"  JSON parsing failed: {e}")
        return {
            'label': '',
            'finish_reason': 'error',
            'tokens_used': 0
        }


def generate_cell_labels(grid_size=40, k=10, max_cells=None):
    """
    Generate labels for all cells in the heatmap grid.

    Args:
        grid_size: Size of heatmap grid (default 40x40)
        k: Number of nearest neighbors to consider
        max_cells: Maximum number of cells to label (for testing)
    """
    print("="*80)
    print("HEATMAP CELL LABEL GENERATION")
    print("="*80)
    print()

    # Load data
    article_titles, article_coords = load_articles()
    question_texts, question_coords = load_questions()

    print()
    print(f"Generating labels for {grid_size}x{grid_size} grid...")
    print(f"  Using k={k} nearest neighbors")
    if max_cells:
        print(f"  Limiting to first {max_cells} cells (testing mode)")
    print()

    # Generate cell data
    cells = []
    total_cells = (grid_size - 1) * (grid_size - 1)

    if max_cells:
        total_cells = min(max_cells, total_cells)

    cell_count = 0
    for gy in range(grid_size - 1):
        for gx in range(grid_size - 1):
            if max_cells and cell_count >= max_cells:
                break

            # Calculate cell center in normalized [0, 1] coordinates
            center_x = (gx + 0.5) / (grid_size - 1)
            center_y = (gy + 0.5) / (grid_size - 1)

            print(f"Cell {cell_count + 1}/{total_cells}: ({gx}, {gy}) center=({center_x:.3f}, {center_y:.3f})")

            # Find nearest neighbors
            neighbors = find_nearest_neighbors(
                (center_x, center_y),
                article_coords,
                article_titles,
                question_coords,
                question_texts,
                k=k
            )

            # Generate label
            label_result = generate_label_with_gpt(neighbors, (center_x, center_y))

            print(f"  Generated label: \"{label_result['label']}\"")
            print(f"  Finish reason: {label_result['finish_reason']}, tokens: {label_result['tokens_used']}")
            print()

            # Store cell data
            cell_data = {
                'gx': gx,
                'gy': gy,
                'center_x': center_x,
                'center_y': center_y,
                'label': label_result['label'],
                'neighbors': [
                    {
                        'distance': float(dist),
                        'type': typ,
                        'text': text
                    }
                    for dist, typ, text in neighbors
                ],
                'label_metadata': {
                    'model': 'qwen3-14b',
                    'finish_reason': label_result['finish_reason'],
                    'tokens_used': label_result['tokens_used'],
                    'k_neighbors': k
                }
            }

            cells.append(cell_data)
            cell_count += 1

        if max_cells and cell_count >= max_cells:
            break

    return cells


def save_labels(cells, output_file='heatmap_cell_labels.json'):
    """Save cell labels to JSON file"""
    print(f"Saving labels to {output_file}...")

    output_data = {
        'metadata': {
            'grid_size': 40,
            'generated_at': datetime.now().isoformat(),
            'num_cells': len(cells),
            'method': 'qwen3-nearest-neighbors',
            'model': 'qwen3-14b'
        },
        'cells': cells
    }

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"  Saved {len(cells)} cell labels")

    # Show sample labels
    print()
    print("Sample labels:")
    for i, cell in enumerate(cells[:5]):
        print(f"  Cell ({cell['gx']}, {cell['gy']}): \"{cell['label']}\"")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Generate heatmap cell labels using GPT-OSS-20B')
    parser.add_argument('--grid-size', type=int, default=40, help='Heatmap grid size (default: 40)')
    parser.add_argument('--k', type=int, default=10, help='Number of nearest neighbors (default: 10)')
    parser.add_argument('--max-cells', type=int, default=None, help='Maximum cells to process (for testing)')
    parser.add_argument('--output', type=str, default='heatmap_cell_labels.json', help='Output file')

    args = parser.parse_args()

    # Generate labels
    cells = generate_cell_labels(
        grid_size=args.grid_size,
        k=args.k,
        max_cells=args.max_cells
    )

    # Save to file
    save_labels(cells, args.output)

    print()
    print("="*80)
    print("✓ Label generation complete")
    print("="*80)


if __name__ == '__main__':
    main()
