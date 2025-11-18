#!/usr/bin/env python3
"""
Generate heatmap cell labels using GPT-5-nano Batch API.

This script:
1. Loads existing heatmap_cell_labels.json (1,521 cells in 39x39 grid)
2. For each cell, finds articles within that cell's bounds
3. Samples up to 10 articles (without replacement if more than 10)
4. Uses OpenAI Batch API with GPT-5-nano to generate semantic labels
5. Uses prompt caching for efficient batch processing
6. Saves results back to heatmap_cell_labels.json

The script uses the batch_with_cache() utility from scripts/utils/openai_batch.py
for efficient processing with prompt caching across all cells.

Usage:
    python scripts/generate_heatmap_labels_gpt5.py

Expected behavior:
- Reads heatmap_cell_labels.json for cell coordinates (39x39 grid)
- Reads wikipedia_articles.json for article details (titles, excerpts, coordinates)
- For each cell, finds articles within cell bounds [x_min, x_max] × [y_min, y_max]
- Samples up to 10 articles per cell (random sampling without replacement if >10)
- Creates batch request for all 1,521 cells
- Submits to OpenAI Batch API with prompt caching
- Polls for completion (checks every 60 seconds, no timeout)
- Updates heatmap_cell_labels.json with new labels
- Preserves cell coordinates

Output format:
- Same schema as input heatmap_cell_labels.json
- Each cell gets:
  - label: Short 2-4 word description from GPT-5-nano
  - label_metadata: Model info, reasoning, timestamp
  - articles_in_cell: List of article titles used for labeling

Error handling:
- Articles without excerpts: Skipped (not included in labeling)
- JSON parsing errors: Retry up to 3 times, then skip
- Labeling failures: Fall back to "Miscellaneous"
- Missing API key: Read from .credentials/openai.key

Cost estimate:
- ~1,521 requests × ~400 tokens avg = ~600K tokens
- With prompt caching: ~60% reduction on system prompt
- Batch API typically offers 50% discount vs real-time
"""

import json
import os
import sys
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from openai import OpenAI

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from utils.openai_batch import batch_with_cache


# System prompt for caching across all requests
SYSTEM_PROMPT = """You are an expert at creating concise, meaningful labels for clusters of related academic articles.

Given a list of article titles and excerpts, generate a SHORT (2-4 word) label that captures the main theme.

The label should be:
- Concise and descriptive
- Capturing the common theme across articles
- Suitable for a knowledge map visualization
- Academic and professional in tone

Return JSON: {"label": "short label", "reasoning": "brief explanation"}"""


def load_api_key() -> str:
    """Load OpenAI API key from credentials file."""
    creds_path = Path(__file__).parent.parent / ".credentials" / "openai.key"

    if not creds_path.exists():
        raise FileNotFoundError(
            f"API key file not found: {creds_path}\n"
            "Please create .credentials/openai.key with your OpenAI API key"
        )

    with open(creds_path, 'r') as f:
        api_key = f.read().strip()

    if not api_key:
        raise ValueError("API key file is empty")

    print(f"✓ Loaded API key from {creds_path}")
    return api_key


def load_articles(articles_path: Path) -> List[Dict[str, Any]]:
    """Load Wikipedia articles from JSON."""
    print(f"Loading articles from {articles_path}...")
    with open(articles_path, 'r') as f:
        articles = json.load(f)

    # Filter out articles without excerpts
    valid_articles = [a for a in articles if a.get('excerpt')]
    skipped = len(articles) - len(valid_articles)

    print(f"  ✓ Loaded {len(valid_articles)} articles with excerpts")
    if skipped > 0:
        print(f"  ⚠ Skipped {skipped} articles without excerpts")

    return valid_articles


def load_heatmap_cells(heatmap_path: Path) -> Dict[str, Any]:
    """Load existing heatmap cell data."""
    print(f"Loading heatmap cells from {heatmap_path}...")
    with open(heatmap_path, 'r') as f:
        data = json.load(f)

    # Determine actual grid size from cells
    max_gx = max(c['gx'] for c in data['cells'])
    max_gy = max(c['gy'] for c in data['cells'])
    actual_grid_size = max(max_gx, max_gy) + 1

    print(f"  ✓ Loaded {len(data['cells'])} cells")
    print(f"  Grid size: {actual_grid_size}x{actual_grid_size}")

    return data, actual_grid_size


def get_cell_bounds(gx: int, gy: int, grid_size: int) -> tuple:
    """
    Calculate cell bounds for a given grid cell.

    Args:
        gx: Grid x coordinate (0 to grid_size-1)
        gy: Grid y coordinate (0 to grid_size-1)
        grid_size: Total grid size (e.g., 39)

    Returns:
        (x_min, x_max, y_min, y_max) tuple
    """
    cell_width = 1.0 / grid_size
    cell_height = 1.0 / grid_size

    x_min = gx * cell_width
    x_max = (gx + 1) * cell_width
    y_min = gy * cell_height
    y_max = (gy + 1) * cell_height

    return x_min, x_max, y_min, y_max


def get_articles_in_cell(
    articles: List[Dict],
    gx: int,
    gy: int,
    grid_size: int,
    max_articles: int = 10
) -> List[Dict[str, Any]]:
    """
    Find articles within a cell's bounds and sample up to max_articles.

    Args:
        articles: List of all articles with x, y coordinates
        gx: Grid x coordinate
        gy: Grid y coordinate
        grid_size: Total grid size
        max_articles: Maximum articles to return (default: 10)

    Returns:
        List of articles within cell bounds (sampled if > max_articles)
    """
    x_min, x_max, y_min, y_max = get_cell_bounds(gx, gy, grid_size)

    # Find all articles within cell bounds
    articles_in_cell = [
        a for a in articles
        if x_min <= a['x'] < x_max and y_min <= a['y'] < y_max
    ]

    # Sample if more than max_articles
    if len(articles_in_cell) > max_articles:
        articles_in_cell = random.sample(articles_in_cell, max_articles)

    return articles_in_cell


def create_user_prompt(
    gx: int,
    gy: int,
    articles_in_cell: List[Dict[str, Any]]
) -> str:
    """
    Create user prompt for a single cell.

    Args:
        gx: Grid x coordinate
        gy: Grid y coordinate
        articles_in_cell: List of articles within this cell

    Returns:
        Formatted user prompt string
    """
    if not articles_in_cell:
        # Empty cell - request generic label
        return f"Cell coordinates: ({gx}, {gy})\n\nThis cell contains no articles.\n\nGenerate a neutral 2-4 word label like 'Empty Region' or 'Unoccupied Area'."

    prompt_lines = [
        f"Cell coordinates: ({gx}, {gy})",
        "",
        f"Articles in this cell ({len(articles_in_cell)} total):"
    ]

    for i, article in enumerate(articles_in_cell, 1):
        title = article['title']
        excerpt = article.get('excerpt', '')

        # Truncate long excerpts
        if len(excerpt) > 150:
            excerpt = excerpt[:147] + "..."

        prompt_lines.append(f'{i}. "{title}" - {excerpt}')

    prompt_lines.append("")
    prompt_lines.append("Generate a 2-4 word label for this region of the knowledge map.")

    return "\n".join(prompt_lines)


def prepare_batch_requests(
    cells: List[Dict[str, Any]],
    articles: List[Dict],
    grid_size: int
) -> tuple:
    """
    Prepare batch requests for all cells.

    Args:
        cells: List of cell data with gx, gy coordinates
        articles: List of all Wikipedia articles
        grid_size: Grid size for bounds calculation

    Returns:
        Tuple of (requests, cell_articles) where:
        - requests: List of request dicts with custom_id and user_prompt
        - cell_articles: Dict mapping custom_id to list of article titles
    """
    print(f"Preparing batch requests for {len(cells)} cells...")

    requests = []
    cell_articles = {}

    for cell in cells:
        gx = cell['gx']
        gy = cell['gy']

        # Get articles in this cell
        articles_in_cell = get_articles_in_cell(articles, gx, gy, grid_size)

        custom_id = f"cell-{gx}-{gy}"
        user_prompt = create_user_prompt(gx, gy, articles_in_cell)

        requests.append({
            'custom_id': custom_id,
            'user_prompt': user_prompt
        })

        # Store article titles for later
        cell_articles[custom_id] = [a['title'] for a in articles_in_cell]

    print(f"  ✓ Prepared {len(requests)} requests")

    # Print statistics
    article_counts = [len(articles) for articles in cell_articles.values()]
    if article_counts:
        avg_articles = sum(article_counts) / len(article_counts)
        max_articles = max(article_counts)
        min_articles = min(article_counts)
        empty_cells = sum(1 for c in article_counts if c == 0)

        print(f"  Articles per cell: avg={avg_articles:.1f}, min={min_articles}, max={max_articles}")
        print(f"  Empty cells: {empty_cells}")

    return requests, cell_articles


def update_cells_with_labels(
    cells: List[Dict[str, Any]],
    results: Dict[str, Any],
    cell_articles: Dict[str, List[str]]
) -> List[Dict[str, Any]]:
    """
    Update cell data with GPT-5-nano generated labels.

    Args:
        cells: Original cell data
        results: Dict mapping custom_id to parsed JSON response
        cell_articles: Dict mapping custom_id to article titles

    Returns:
        Updated cells with new labels and metadata
    """
    print(f"Updating {len(cells)} cells with GPT-5-nano labels...")

    updated_cells = []
    successful = 0
    failed = 0

    for cell in cells:
        gx = cell['gx']
        gy = cell['gy']
        custom_id = f"cell-{gx}-{gy}"

        # Create updated cell with existing data
        updated_cell = {
            'gx': gx,
            'gy': gy,
            'center_x': cell.get('center_x', (gx + 0.5) / 39.0),
            'center_y': cell.get('center_y', (gy + 0.5) / 39.0)
        }

        # Add articles in cell
        updated_cell['articles_in_cell'] = cell_articles.get(custom_id, [])

        # Try to get GPT-5-nano result
        if custom_id in results:
            result = results[custom_id]

            # Extract label and reasoning
            if isinstance(result, dict) and 'label' in result:
                updated_cell['label'] = result['label']
                updated_cell['label_metadata'] = {
                    'model': 'gpt-5-nano',
                    'reasoning': result.get('reasoning', ''),
                    'generated_at': datetime.now().isoformat(),
                    'num_articles': len(updated_cell['articles_in_cell'])
                }
                successful += 1
            else:
                # Fallback if result format is unexpected
                updated_cell['label'] = "Miscellaneous"
                updated_cell['label_metadata'] = {
                    'model': 'gpt-5-nano',
                    'error': 'Invalid response format',
                    'generated_at': datetime.now().isoformat(),
                    'num_articles': len(updated_cell['articles_in_cell'])
                }
                failed += 1
        else:
            # No result found - use fallback
            updated_cell['label'] = "Miscellaneous"
            updated_cell['label_metadata'] = {
                'model': 'gpt-5-nano',
                'error': 'No response received',
                'generated_at': datetime.now().isoformat(),
                'num_articles': len(updated_cell['articles_in_cell'])
            }
            failed += 1

        updated_cells.append(updated_cell)

    print(f"  ✓ Updated {successful} cells successfully")
    if failed > 0:
        print(f"  ⚠ {failed} cells used fallback label 'Miscellaneous'")

    return updated_cells


def save_heatmap_labels(
    output_path: Path,
    cells: List[Dict[str, Any]],
    grid_size: int,
    source_metadata: Dict[str, Any]
):
    """Save updated heatmap cell labels to JSON."""
    data = {
        'metadata': {
            'grid_size': grid_size,
            'generated_at': datetime.now().isoformat(),
            'num_cells': len(cells),
            'method': 'gpt-5-nano-batch-api',
            'model': 'gpt-5-nano',
            'source': 'wikipedia_articles.json',
            'previous_method': source_metadata.get('method', 'unknown'),
            'sampling': 'up to 10 articles per cell (random if >10)'
        },
        'cells': cells
    }

    print(f"Saving results to {output_path}...")
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"  ✓ Saved {len(cells)} cells to {output_path}")


def main():
    # Setup paths
    project_root = Path(__file__).parent.parent
    articles_path = project_root / "wikipedia_articles.json"
    heatmap_path = project_root / "heatmap_cell_labels.json"
    output_path = heatmap_path  # Update in place

    print("=" * 60)
    print("GPT-5-nano Heatmap Label Generation")
    print("=" * 60)
    print()

    # Load API key from credentials file
    try:
        api_key = load_api_key()
    except Exception as e:
        print(f"Error loading API key: {e}")
        sys.exit(1)

    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)

    # Load data
    articles = load_articles(articles_path)
    heatmap_data, grid_size = load_heatmap_cells(heatmap_path)

    cells = heatmap_data['cells']

    print()
    print(f"Configuration:")
    print(f"  Total cells: {len(cells)}")
    print(f"  Grid size: {grid_size}x{grid_size}")
    print(f"  Total articles: {len(articles)}")
    print(f"  Max articles per cell: 10")
    print(f"  Model: gpt-5-nano")
    print(f"  Temperature: 0.7")
    print(f"  Using prompt caching: Yes")
    print(f"  Fallback label: Miscellaneous")
    print()

    # Prepare batch requests
    requests, cell_articles = prepare_batch_requests(cells, articles, grid_size)

    # Define JSON schema for structured output
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "cell_label_response",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "label": {
                        "type": "string",
                        "description": "A concise 2-4 word label for the cell"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Brief explanation of why this label was chosen"
                    }
                },
                "required": ["label", "reasoning"],
                "additionalProperties": False
            }
        }
    }

    # Run batch with caching (no timeout - will wait indefinitely)
    print("Submitting batch to OpenAI...")
    print()

    try:
        results = batch_with_cache(
            client=client,
            requests=requests,
            system_prompt=SYSTEM_PROMPT,
            description="Heatmap cell label generation (GPT-5-nano)",
            model="gpt-5-nano",
            temperature=0.7,
            max_tokens=300,
            response_format=response_format,
            poll_interval=60,
            timeout=None  # No timeout - wait indefinitely
        )

        print()
        print(f"Batch completed: {len(results)}/{len(requests)} responses received")
        print()

        # Update cells with results
        updated_cells = update_cells_with_labels(cells, results, cell_articles)

        # Save final results
        save_heatmap_labels(
            output_path=output_path,
            cells=updated_cells,
            grid_size=grid_size,
            source_metadata=heatmap_data['metadata']
        )

        print()
        print("=" * 60)
        print("✓ Label generation complete!")
        print("=" * 60)
        print()
        print(f"Updated file: {output_path}")
        print(f"Total cells: {len(updated_cells)}")
        print(f"Grid size: {grid_size}x{grid_size}")
        print()

    except Exception as e:
        print(f"Error during batch processing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
