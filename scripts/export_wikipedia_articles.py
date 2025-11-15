#!/usr/bin/env python3
"""
Export Wikipedia articles with 2D coordinates for visualization.

This script:
1. Loads Wikipedia articles from data/wikipedia.pkl
2. Loads embeddings from embeddings/wikipedia_embeddings.pkl
3. Projects embeddings to 2D using UMAP reducer from data/umap_reducer.pkl
4. Filters articles to those within bounds from data/umap_bounds.pkl
5. Exports to JSON with coordinates, titles, URLs, and excerpts (100 chars)

Output: wikipedia_articles.json
"""

import pickle
import json
import numpy as np
from pathlib import Path


def load_wikipedia_data():
    """Load Wikipedia articles from data/wikipedia.pkl"""
    print("Loading Wikipedia articles...")
    with open('data/wikipedia.pkl', 'rb') as f:
        articles = pickle.load(f)
    print(f"  Loaded {len(articles):,} articles")
    return articles


def load_embeddings():
    """Load Wikipedia embeddings"""
    print("Loading embeddings...")
    with open('embeddings/wikipedia_embeddings.pkl', 'rb') as f:
        data = pickle.load(f)

    embeddings = data['embeddings']
    print(f"  Loaded embeddings: shape {embeddings.shape}")

    # Verify we have the right number of embeddings
    assert len(embeddings) == 25000, f"Expected 25000 embeddings, got {len(embeddings)}"

    return embeddings


def load_umap_reducer():
    """Load UMAP reducer from data/umap_reducer.pkl"""
    print("Loading UMAP reducer...")
    with open('data/umap_reducer.pkl', 'rb') as f:
        reducer = pickle.load(f)
    print(f"  Loaded UMAP reducer: {type(reducer)}")
    return reducer


def load_bounds():
    """Load heatmap bounds from data/umap_bounds.pkl"""
    print("Loading bounds...")
    with open('data/umap_bounds.pkl', 'rb') as f:
        bounds_data = pickle.load(f)

    # Extract article bounds (full range)
    bounds = bounds_data['articles']
    print(f"  Article bounds: x=[{bounds['x_min']:.2f}, {bounds['x_max']:.2f}], y=[{bounds['y_min']:.2f}, {bounds['y_max']:.2f}]")
    return bounds


def project_embeddings(embeddings, reducer):
    """Project embeddings to 2D using UMAP reducer"""
    print("Projecting embeddings to 2D...")
    coords_2d = reducer.transform(embeddings)
    print(f"  Projected coordinates: shape {coords_2d.shape}")
    return coords_2d


def filter_by_bounds(articles, coords_2d, bounds):
    """Collect all articles with their coordinates"""
    print("Processing articles with coordinates...")

    # Collect all articles with their coordinates
    all_articles = []

    for i, (article, coord) in enumerate(zip(articles, coords_2d)):
        x, y = coord
        all_articles.append((article, x, y))

    print(f"  Total articles: {len(all_articles):,}")
    return all_articles


def normalize_coordinates(filtered_articles, bounds):
    """Normalize coordinates to [0, 1] range using full article bounds"""
    print("Normalizing coordinates to [0, 1] using full article bounds...")

    x_min = bounds['x_min']
    x_max = bounds['x_max']
    y_min = bounds['y_min']
    y_max = bounds['y_max']

    normalized = []

    for article, x, y in filtered_articles:
        # Normalize to [0, 1] based on full article bounds
        x_norm = (x - x_min) / (x_max - x_min)
        y_norm = (y - y_min) / (y_max - y_min)

        normalized.append((article, x_norm, y_norm))

    print(f"  Normalized {len(normalized):,} articles to [0, 1] range")

    return normalized


def create_excerpt(text, max_length=100):
    """Create a short excerpt from article text"""
    if not text:
        return ""

    # Clean text (remove extra whitespace)
    text = ' '.join(text.split())

    # Truncate to max_length characters
    if len(text) <= max_length:
        return text

    # Try to truncate at sentence boundary
    excerpt = text[:max_length]
    last_period = excerpt.rfind('.')
    last_space = excerpt.rfind(' ')

    if last_period > max_length * 0.7:  # If we have a sentence ending in the last 30%
        return excerpt[:last_period + 1]
    elif last_space > 0:  # Otherwise truncate at last word
        return excerpt[:last_space] + '...'
    else:
        return excerpt + '...'


def export_to_json(normalized_articles, output_path='wikipedia_articles.json'):
    """Export articles to JSON format for visualization"""
    print(f"Exporting to {output_path}...")

    articles_json = []
    for article, x, y in normalized_articles:
        articles_json.append({
            'title': article.get('title', 'Untitled'),
            'url': article.get('url', ''),
            'excerpt': create_excerpt(article.get('text', ''), max_length=100),
            'x': float(x),
            'y': float(y)
        })

    with open(output_path, 'w') as f:
        json.dump(articles_json, f, indent=2)

    print(f"  Exported {len(articles_json):,} articles")
    print(f"\nSample articles:")
    for i, article in enumerate(articles_json[:3]):
        print(f"  {i+1}. {article['title']}")
        print(f"     Position: ({article['x']:.3f}, {article['y']:.3f})")
        print(f"     Excerpt: {article['excerpt'][:60]}...")

    return output_path


def main():
    print("="*80)
    print("Wikipedia Articles Export Script")
    print("="*80)
    print()

    # Load data
    articles = load_wikipedia_data()
    embeddings = load_embeddings()
    reducer = load_umap_reducer()
    bounds = load_bounds()

    # We only have embeddings for the first 25000 articles
    articles = articles[:25000]
    print(f"\nUsing first {len(articles):,} articles (matching embeddings)")

    # Project to 2D
    coords_2d = project_embeddings(embeddings, reducer)

    # Filter by bounds
    filtered = filter_by_bounds(articles, coords_2d, bounds)

    # Normalize coordinates
    normalized = normalize_coordinates(filtered, bounds)

    # Export to JSON
    output_path = export_to_json(normalized)

    print()
    print("="*80)
    print(f"✓ Successfully exported {len(normalized):,} articles to {output_path}")
    print("="*80)


if __name__ == '__main__':
    main()
