#!/usr/bin/env python3
"""
Extract core concepts from level-0 Wikipedia articles using GPT-5-nano Batch API.

This script:
1. Loads wikipedia_articles.json (filtered articles from optimal rectangle)
2. Loads full article text from data/wikipedia.pkl
3. For each article, extracts 2-4 core concepts using GPT-5-nano Batch API
4. Uses prompt caching to optimize API costs
5. Processes articles in batches of 500
6. Saves checkpoints every 1000 articles
7. Outputs to level_0_concepts.json

Requirements:
- OpenAI API key in environment: OPENAI_API_KEY
- data/wikipedia.pkl (full article text)
- wikipedia_articles.json (filtered articles with coordinates)

Output schema:
{
  "metadata": {
    "level": 0,
    "total_articles": N,
    "total_concepts": M,
    "timestamp": "ISO timestamp"
  },
  "articles": [
    {
      "title": "Article title",
      "text": "Full article text",
      "excerpt": "Short excerpt",
      "concepts": ["concept1", "concept2", ...],
      "umap_x": float,
      "umap_y": float,
      "embedding_x": float,
      "embedding_y": float,
      "index": int
    }
  ]
}
"""

import json
import pickle
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from openai import OpenAI

# Add utils directory to path
sys.path.insert(0, str(Path(__file__).parent / 'utils'))
from openai_batch import batch_with_cache


# System prompt for concept extraction (cached across all requests)
SYSTEM_PROMPT = """You are an expert at extracting key concepts from Wikipedia articles for educational assessment.

For each article, identify 2-4 core concepts that:
- Are specific and well-defined
- Could be tested in multiple-choice questions
- Represent the article's main topics
- Are suitable for university-level questions

Return JSON: {"suitable": bool, "concepts": [str], "reasoning": str}

If the article is too short, too specific, or not suitable for educational questions, set suitable=false."""


def load_wikipedia_articles(articles_json_path: str = 'wikipedia_articles.json') -> List[Dict]:
    """Load filtered Wikipedia articles with coordinates."""
    print(f"Loading filtered Wikipedia articles from {articles_json_path}...")
    with open(articles_json_path, 'r') as f:
        articles = json.load(f)

    print(f"  ✓ Loaded {len(articles):,} articles")
    return articles


def load_full_text(pkl_path: str = 'data/wikipedia.pkl') -> List[Dict]:
    """Load full Wikipedia article text from pickle file."""
    print(f"Loading full article text from {pkl_path}...")
    with open(pkl_path, 'rb') as f:
        articles = pickle.load(f)

    print(f"  ✓ Loaded {len(articles):,} articles with full text")
    return articles


def merge_article_data(filtered_articles: List[Dict], full_articles: List[Dict]) -> List[Dict]:
    """Merge filtered articles with full text data."""
    print("Merging article data...")

    # Create index lookup for full articles
    full_articles_by_index = {i: article for i, article in enumerate(full_articles)}

    merged = []
    missing_count = 0

    for filtered in filtered_articles:
        index = filtered['index']

        # Get full article by index
        full_article = full_articles_by_index.get(index)

        if not full_article:
            missing_count += 1
            continue

        # Merge data
        merged_article = {
            'title': filtered['title'],
            'url': filtered['url'],
            'text': full_article.get('text', ''),
            'excerpt': filtered['excerpt'],
            'embedding_x': filtered['x'],  # Normalized [0,1] coordinates
            'embedding_y': filtered['y'],
            'umap_x': filtered['umap_x'],  # Original UMAP coordinates
            'umap_y': filtered['umap_y'],
            'index': index
        }

        merged.append(merged_article)

    print(f"  ✓ Merged {len(merged):,} articles")
    if missing_count > 0:
        print(f"  ⚠ Warning: {missing_count} articles missing from full text data")

    return merged


def create_batch_requests(articles: List[Dict], batch_size: int = 500) -> List[List[Dict]]:
    """Split articles into batches for API processing."""
    batches = []

    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]

        # Create request objects
        requests = []
        for j, article in enumerate(batch):
            custom_id = f"article_{article['index']}"

            # User prompt with article text
            user_prompt = f"""Article: "{article['title']}"

Full text:
{article['text']}

Extract 2-4 core concepts suitable for generating conceptual questions."""

            requests.append({
                'custom_id': custom_id,
                'user_prompt': user_prompt,
                'article': article  # Store for later reference
            })

        batches.append(requests)

    print(f"Created {len(batches)} batches of ~{batch_size} articles each")
    return batches


def process_batch(
    client: OpenAI,
    batch_requests: List[Dict],
    batch_num: int,
    total_batches: int
) -> Dict[str, Any]:
    """Process a single batch of articles through GPT-5-nano."""
    print()
    print("="*80)
    print(f"PROCESSING BATCH {batch_num}/{total_batches}")
    print("="*80)
    print()

    # Extract requests (without article data for API)
    api_requests = [
        {'custom_id': req['custom_id'], 'user_prompt': req['user_prompt']}
        for req in batch_requests
    ]

    # Define JSON response format
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "concept_extraction",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "suitable": {"type": "boolean"},
                    "concepts": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "reasoning": {"type": "string"}
                },
                "required": ["suitable", "concepts", "reasoning"],
                "additionalProperties": False
            }
        }
    }

    # Submit batch with caching
    results = batch_with_cache(
        client=client,
        requests=api_requests,
        system_prompt=SYSTEM_PROMPT,
        description=f"Level-0 concept extraction (batch {batch_num}/{total_batches})",
        model="gpt-5-nano",
        temperature=0.7,
        max_tokens=500,
        response_format=response_format,
        poll_interval=60,
        timeout=3600
    )

    return results


def merge_results_with_articles(
    batch_requests: List[Dict],
    results: Dict[str, Any]
) -> List[Dict]:
    """Merge API results with article data."""
    merged_articles = []

    for req in batch_requests:
        custom_id = req['custom_id']
        article = req['article']

        # Get result for this article
        result = results.get(custom_id)

        if not result:
            print(f"  ⚠ Warning: No result for {article['title']} (index {article['index']})")
            continue

        # Skip unsuitable articles
        if not result.get('suitable', False):
            print(f"  ⊘ Skipped: {article['title']} - {result.get('reasoning', 'Not suitable')}")
            continue

        # Add concepts to article
        article['concepts'] = result.get('concepts', [])
        article['reasoning'] = result.get('reasoning', '')

        merged_articles.append(article)

    return merged_articles


def save_checkpoint(
    articles: List[Dict],
    checkpoint_path: str = 'level_0_concepts_checkpoint.json'
):
    """Save checkpoint of processed articles."""
    print(f"Saving checkpoint to {checkpoint_path}...")

    checkpoint_data = {
        'metadata': {
            'level': 0,
            'total_articles': len(articles),
            'total_concepts': sum(len(a.get('concepts', [])) for a in articles),
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'in_progress'
        },
        'articles': articles
    }

    with open(checkpoint_path, 'w') as f:
        json.dump(checkpoint_data, f, indent=2)

    file_size_mb = Path(checkpoint_path).stat().st_size / (1024 * 1024)
    print(f"  ✓ Checkpoint saved ({file_size_mb:.2f} MB)")


def save_final_output(
    articles: List[Dict],
    output_path: str = 'level_0_concepts.json'
):
    """Save final output to level_0_concepts.json."""
    print()
    print(f"Saving final output to {output_path}...")

    output_data = {
        'metadata': {
            'level': 0,
            'total_articles': len(articles),
            'total_concepts': sum(len(a.get('concepts', [])) for a in articles),
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'complete'
        },
        'articles': articles
    }

    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)

    file_size_mb = Path(output_path).stat().st_size / (1024 * 1024)
    print(f"  ✓ Output saved ({file_size_mb:.2f} MB)")
    print()

    # Print statistics
    print("="*80)
    print("STATISTICS")
    print("="*80)
    print(f"Total articles: {len(articles):,}")
    print(f"Total concepts: {sum(len(a.get('concepts', [])) for a in articles):,}")
    print(f"Average concepts per article: {sum(len(a.get('concepts', [])) for a in articles) / len(articles):.2f}")
    print()

    # Show sample articles with concepts
    print("Sample articles with concepts:")
    for i, article in enumerate(articles[:5]):
        print(f"\n{i+1}. \"{article['title']}\"")
        print(f"   Concepts: {', '.join(article.get('concepts', []))}")
        print(f"   Reasoning: {article.get('reasoning', '')[:100]}...")
    print()


def main():
    """Main extraction workflow."""
    print()
    print("="*80)
    print("LEVEL-0 CONCEPT EXTRACTION WITH GPT-5-NANO")
    print("="*80)
    print()

    # Check for OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        print("ERROR: OPENAI_API_KEY environment variable not set")
        print("Please set it with: export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)

    # Initialize OpenAI client
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    print("✓ OpenAI client initialized")
    print()

    # Load data
    filtered_articles = load_wikipedia_articles('wikipedia_articles.json')
    full_articles = load_full_text('data/wikipedia.pkl')

    # Merge article data
    articles = merge_article_data(filtered_articles, full_articles)

    print()
    print(f"Total articles to process: {len(articles):,}")
    print()

    # Create batches
    batch_size = 500
    batches = create_batch_requests(articles, batch_size=batch_size)

    # Process batches
    all_processed_articles = []

    for i, batch_requests in enumerate(batches, start=1):
        print(f"\nProcessing batch {i}/{len(batches)} ({len(batch_requests)} articles)...")

        # Process batch through API
        results = process_batch(client, batch_requests, i, len(batches))

        # Merge results with article data
        processed_articles = merge_results_with_articles(batch_requests, results)
        all_processed_articles.extend(processed_articles)

        print(f"  ✓ Processed {len(processed_articles)}/{len(batch_requests)} articles from batch {i}")
        print(f"  ✓ Total processed so far: {len(all_processed_articles):,}")

        # Save checkpoint every 1000 articles
        if len(all_processed_articles) % 1000 == 0 or i == len(batches):
            save_checkpoint(all_processed_articles)

    # Save final output
    save_final_output(all_processed_articles, 'level_0_concepts.json')

    print("="*80)
    print("✓ CONCEPT EXTRACTION COMPLETE")
    print("="*80)
    print(f"Processed: {len(all_processed_articles):,} / {len(articles):,} articles")
    print(f"Output: level_0_concepts.json")
    print()


if __name__ == '__main__':
    main()
