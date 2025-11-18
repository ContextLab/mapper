#!/usr/bin/env python3
"""
Generate level-0 questions from concepts using GPT-5-nano Batch API.

This script:
1. Loads level_0_concepts.json (concepts extracted from Wikipedia articles)
2. For each concept in each article, generates 1 multiple-choice question
3. Uses OpenAI Batch API with prompt caching for cost efficiency
4. Groups questions by heatmap cell (using article coordinates)
5. Saves to cell_questions_level_0.json

Cost estimation:
- ~25K articles × 2 concepts/article × 4K tokens/request = ~200M tokens input
- With prompt caching (90% savings): ~20M tokens effective
- GPT-5-nano input: $0.05/1M tokens → ~$1.00
- GPT-5-nano output: $0.40/1M tokens × ~5M tokens → ~$2.00
- Total: ~$3.00

Expected time: 1-2 hours (batch processing + waiting)
"""

import json
import pickle
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from scripts.utils.api_utils import create_openai_client
from scripts.utils.openai_batch import batch_with_cache


# System prompt for question generation (cached across all requests)
SYSTEM_PROMPT = """You are an expert at creating high-quality conceptual multiple-choice questions.

Given a concept and source article, generate ONE question that:
- Tests understanding of relationships, implications, or applications
- Is thought-provoking and requires conceptual understanding
- NOT simple factual recall
- Has 4 plausible options with one clearly correct answer
- Suitable for university-level students

Return JSON: {"question": str, "options": [str, str, str, str], "correct_answer": str, "correct_index": int, "reasoning": str}
"""


def load_level_0_concepts(concepts_file: str = 'level_0_concepts.json') -> List[Dict[str, Any]]:
    """
    Load level-0 concepts from JSON file.

    Expected schema:
    [
      {
        "cell_gx": int,
        "cell_gy": int,
        "level": 0,
        "articles": [
          {
            "title": str,
            "text": str,
            "excerpt": str,
            "concepts": [str, str, ...],
            "umap_x": float,
            "umap_y": float,
            "embedding_x": float,
            "embedding_y": float
          }
        ]
      }
    ]

    Args:
        concepts_file: Path to level_0_concepts.json

    Returns:
        List of cell concept data
    """
    print(f"Loading level-0 concepts from {concepts_file}...")

    with open(concepts_file, 'r') as f:
        data = json.load(f)

    # Handle both list and dict formats
    if isinstance(data, dict):
        cells = data.get('cells', [])
        metadata = data.get('metadata', {})
        print(f"  Metadata: {metadata}")
    else:
        cells = data

    print(f"  Loaded {len(cells)} cells")

    # Count total articles and concepts
    total_articles = sum(len(cell.get('articles', [])) for cell in cells)
    total_concepts = sum(
        sum(len(article.get('concepts', [])) for article in cell.get('articles', []))
        for cell in cells
    )

    print(f"  Total articles: {total_articles}")
    print(f"  Total concepts: {total_concepts}")
    print()

    return cells


def load_cell_labels(labels_file: str = 'heatmap_cell_labels.json') -> Dict[tuple, str]:
    """
    Load cell labels for adding to output.

    Returns:
        Dict mapping (gx, gy) -> cell label
    """
    print(f"Loading cell labels from {labels_file}...")

    with open(labels_file, 'r') as f:
        data = json.load(f)

    labels = {}
    for cell in data['cells']:
        key = (cell['gx'], cell['gy'])
        labels[key] = cell.get('label', '')

    print(f"  Loaded {len(labels)} cell labels")
    print()

    return labels


def create_question_requests(
    cells: List[Dict[str, Any]],
    batch_size: int = 500
) -> List[List[Dict[str, Any]]]:
    """
    Create batch requests for question generation.

    For each concept in each article, creates a request with:
    - custom_id: Unique identifier (cell_gx_gy_article_concept_index)
    - user_prompt: Concept, article title, and full text

    Args:
        cells: List of cell concept data
        batch_size: Maximum requests per batch (default: 500)

    Returns:
        List of batches, where each batch is a list of request dicts
    """
    print("Creating question generation requests...")

    all_requests = []

    for cell in cells:
        cell_gx = cell['cell_gx']
        cell_gy = cell['cell_gy']

        for article in cell.get('articles', []):
            article_title = article['title']
            article_text = article.get('text', article.get('excerpt', ''))

            # Truncate very long articles to fit in context
            if len(article_text) > 8000:
                article_text = article_text[:8000] + '...'

            for i, concept in enumerate(article.get('concepts', [])):
                # Create unique request ID
                custom_id = f"cell_{cell_gx}_{cell_gy}_{article_title.replace(' ', '_')}_{i}"

                # Create user prompt
                user_prompt = f"""Concept: "{concept}"

Source article: "{article_title}"
Full text:
{article_text}

Generate one conceptual multiple-choice question about this concept."""

                # Store metadata for later reconstruction
                request = {
                    'custom_id': custom_id,
                    'user_prompt': user_prompt,
                    'metadata': {
                        'cell_gx': cell_gx,
                        'cell_gy': cell_gy,
                        'article_title': article_title,
                        'concept': concept,
                        'embedding_x': article.get('embedding_x'),
                        'embedding_y': article.get('embedding_y'),
                        'umap_x': article.get('umap_x'),
                        'umap_y': article.get('umap_y')
                    }
                }

                all_requests.append(request)

    print(f"  Created {len(all_requests)} requests")

    # Split into batches
    batches = []
    for i in range(0, len(all_requests), batch_size):
        batch = all_requests[i:i + batch_size]
        batches.append(batch)

    print(f"  Split into {len(batches)} batches of up to {batch_size} requests")
    print()

    return batches


def process_batch(
    client,
    batch: List[Dict[str, Any]],
    batch_num: int,
    total_batches: int
) -> Dict[str, Any]:
    """
    Process one batch of question generation requests.

    Args:
        client: OpenAI client
        batch: List of request dicts
        batch_num: Current batch number (for logging)
        total_batches: Total number of batches

    Returns:
        Dict mapping custom_id -> question data
    """
    print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} requests)...")
    print("="*80)

    # Define JSON schema for structured output
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "conceptual_question",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question text"
                    },
                    "options": {
                        "type": "array",
                        "description": "Four answer options",
                        "items": {"type": "string"},
                        "minItems": 4,
                        "maxItems": 4
                    },
                    "correct_answer": {
                        "type": "string",
                        "description": "The correct answer text"
                    },
                    "correct_index": {
                        "type": "integer",
                        "description": "Index of correct answer (0-3)",
                        "minimum": 0,
                        "maximum": 3
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Brief explanation of why this question tests the concept"
                    }
                },
                "required": ["question", "options", "correct_answer", "correct_index", "reasoning"],
                "additionalProperties": False
            }
        }
    }

    # Submit batch with caching
    results = batch_with_cache(
        client=client,
        requests=batch,
        system_prompt=SYSTEM_PROMPT,
        description=f"Level-0 questions batch {batch_num}/{total_batches}",
        model="gpt-5-nano",
        temperature=0.7,
        max_tokens=500,
        response_format=response_format,
        poll_interval=60,  # Check every minute
        timeout=3600  # 1 hour timeout
    )

    print()
    print(f"✓ Batch {batch_num}/{total_batches} complete: {len(results)} results")
    print("="*80)
    print()

    return results


def group_questions_by_cell(
    all_results: Dict[str, Any],
    batches: List[List[Dict[str, Any]]],
    cell_labels: Dict[tuple, str]
) -> List[Dict[str, Any]]:
    """
    Group generated questions by heatmap cell.

    Args:
        all_results: Dict mapping custom_id -> question data
        batches: Original batches (for metadata reconstruction)
        cell_labels: Dict mapping (gx, gy) -> cell label

    Returns:
        List of cell question data
    """
    print("Grouping questions by cell...")

    # Create metadata lookup from batches
    metadata_lookup = {}
    for batch in batches:
        for request in batch:
            metadata_lookup[request['custom_id']] = request['metadata']

    # Group by cell
    cells = {}

    for custom_id, question_data in all_results.items():
        metadata = metadata_lookup.get(custom_id)
        if not metadata:
            print(f"  ⚠ Warning: No metadata found for {custom_id}")
            continue

        cell_key = (metadata['cell_gx'], metadata['cell_gy'])

        if cell_key not in cells:
            cells[cell_key] = {
                'cell': {
                    'gx': metadata['cell_gx'],
                    'gy': metadata['cell_gy'],
                    'label': cell_labels.get(cell_key, '')
                },
                'questions': []
            }

        # Build question record
        question = {
            'question': question_data.get('question', ''),
            'options': question_data.get('options', []),
            'correct_answer': question_data.get('correct_answer', ''),
            'correct_index': question_data.get('correct_index', 0),
            'source_article': metadata['article_title'],
            'concepts_tested': [metadata['concept']],
            'level': 0,
            'embedding_x': metadata['embedding_x'],
            'embedding_y': metadata['embedding_y'],
            'umap_x': metadata['umap_x'],
            'umap_y': metadata['umap_y']
        }

        cells[cell_key]['questions'].append(question)

    # Convert to list and sort by cell coordinates
    cell_list = list(cells.values())
    cell_list.sort(key=lambda c: (c['cell']['gx'], c['cell']['gy']))

    print(f"  Grouped into {len(cell_list)} cells")

    # Show distribution
    questions_per_cell = [len(c['questions']) for c in cell_list]
    print(f"  Questions per cell: min={min(questions_per_cell)}, max={max(questions_per_cell)}, avg={sum(questions_per_cell)/len(questions_per_cell):.1f}")
    print()

    return cell_list


def save_questions(
    cells: List[Dict[str, Any]],
    output_file: str = 'cell_questions_level_0.json'
) -> None:
    """
    Save grouped questions to JSON file.

    Args:
        cells: List of cell question data
        output_file: Output file path
    """
    print(f"Saving questions to {output_file}...")

    total_cells = len(cells)
    total_questions = sum(len(c['questions']) for c in cells)

    output_data = {
        'metadata': {
            'level': 0,
            'total_cells': total_cells,
            'total_questions': total_questions,
            'status': 'completed',
            'timestamp': datetime.now().isoformat(),
            'model': 'gpt-5-nano',
            'method': 'concept-based-batched'
        },
        'cells': cells
    }

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"  ✓ Saved {total_cells} cells with {total_questions} questions")
    print()


def main():
    parser = argparse.ArgumentParser(
        description='Generate level-0 questions from concepts using GPT-5-nano Batch API'
    )
    parser.add_argument(
        '--concepts',
        type=str,
        default='level_0_concepts.json',
        help='Input concepts file (default: level_0_concepts.json)'
    )
    parser.add_argument(
        '--labels',
        type=str,
        default='heatmap_cell_labels.json',
        help='Cell labels file (default: heatmap_cell_labels.json)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='cell_questions_level_0.json',
        help='Output file (default: cell_questions_level_0.json)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=500,
        help='Batch size for API requests (default: 500)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Create requests but do not submit to API'
    )

    args = parser.parse_args()

    print()
    print("="*80)
    print("LEVEL-0 QUESTION GENERATION (GPT-5-nano Batch API)")
    print("="*80)
    print()

    # Load input data
    cells = load_level_0_concepts(args.concepts)
    cell_labels = load_cell_labels(args.labels)

    # Create batches
    batches = create_question_requests(cells, batch_size=args.batch_size)

    if args.dry_run:
        print("DRY RUN: Skipping API submission")
        print(f"Would submit {len(batches)} batches with {sum(len(b) for b in batches)} total requests")
        return

    # Create OpenAI client
    client = create_openai_client()

    # Process batches
    all_results = {}

    for i, batch in enumerate(batches, start=1):
        batch_results = process_batch(
            client=client,
            batch=batch,
            batch_num=i,
            total_batches=len(batches)
        )

        all_results.update(batch_results)

        print(f"Progress: {len(all_results)}/{sum(len(b) for b in batches)} questions generated")
        print()

    # Group by cell
    cell_questions = group_questions_by_cell(all_results, batches, cell_labels)

    # Save output
    save_questions(cell_questions, args.output)

    print()
    print("="*80)
    print("✓ LEVEL-0 QUESTION GENERATION COMPLETE")
    print("="*80)
    print(f"Output: {args.output}")
    print()


if __name__ == '__main__':
    main()
