#!/usr/bin/env python3
"""
Export Wikipedia articles with 2D coordinates for visualization.

This script:
1. Loads optimal rectangle bounds from optimal_rectangle.json
2. Loads Wikipedia article data from data/wikipedia.pkl
3. Loads UMAP coordinates from umap_coords.pkl
4. Filters articles to those within optimal rectangle bounds
5. Normalizes coordinates to [0, 1] within the optimal rectangle
6. Exports to wikipedia_articles.json with titles, URLs, and excerpts

Output: wikipedia_articles.json
"""

import pickle
import json
from pathlib import Path


def load_optimal_rectangle():
    """Load optimal rectangle bounds from optimal_rectangle.json"""
    print("Loading optimal rectangle bounds...")
    with open('optimal_rectangle.json', 'r') as f:
        data = json.load(f)

    bounds = data['optimal_rectangle']['bounds']
    metrics = data['metrics']

    print(f"  Optimal rectangle:")
    print(f"    Coverage: {metrics['coverage_percent']:.2f}%")
    print(f"    Area: {data['optimal_rectangle']['area']:.2f} UMAP units²")
    print(f"    Expected articles: {metrics['num_articles']:,}")
    print(f"    Bounds: X=[{bounds['x_min']:.2f}, {bounds['x_max']:.2f}], "
          f"Y=[{bounds['y_min']:.2f}, {bounds['y_max']:.2f}]")
    print()

    return bounds


def load_wikipedia_articles():
    """Load Wikipedia article data from data/wikipedia.pkl"""
    print("Loading Wikipedia article data...")
    with open('data/wikipedia.pkl', 'rb') as f:
        articles = pickle.load(f)

    print(f"  Loaded {len(articles):,} Wikipedia articles")
    print(f"  First article: \"{articles[0]['title']}\"")
    print()

    return articles


def load_umap_coordinates():
    """Load UMAP coordinates from umap_coords.pkl"""
    print("Loading UMAP coordinates...")
    with open('umap_coords.pkl', 'rb') as f:
        data = pickle.load(f)

    coords = data['coords_2d'][:250000]  # First 250K are Wikipedia articles

    print(f"  Loaded {len(coords):,} article coordinates")
    print(f"  UMAP space: X=[{coords[:, 0].min():.2f}, {coords[:, 0].max():.2f}], "
          f"Y=[{coords[:, 1].min():.2f}, {coords[:, 1].max():.2f}]")
    print()

    return coords


def filter_by_bounds(articles, coords, bounds):
    """Filter articles to only those within optimal rectangle bounds"""
    print(f"Filtering articles within optimal rectangle...")

    x_min = bounds['x_min']
    x_max = bounds['x_max']
    y_min = bounds['y_min']
    y_max = bounds['y_max']

    print(f"  Rectangle: X=[{x_min:.2f}, {x_max:.2f}], Y=[{y_min:.2f}, {y_max:.2f}]")

    filtered_articles = []

    for i, (article, coord) in enumerate(zip(articles, coords)):
        x, y = coord
        if x_min <= x <= x_max and y_min <= y <= y_max:
            filtered_articles.append({
                'article': article,
                'umap_x': float(x),
                'umap_y': float(y),
                'index': i
            })

    print(f"  Filtered: {len(filtered_articles):,} / {len(articles):,} articles "
          f"({len(filtered_articles)/len(articles)*100:.1f}%)")
    print()

    return filtered_articles


def normalize_coordinates(filtered_articles, bounds):
    """Normalize coordinates to [0, 1] range within optimal rectangle"""
    print(f"Normalizing coordinates to [0, 1]...")

    x_min = bounds['x_min']
    x_max = bounds['x_max']
    y_min = bounds['y_min']
    y_max = bounds['y_max']

    width = x_max - x_min
    height = y_max - y_min

    normalized = []

    for item in filtered_articles:
        # Normalize to [0, 1] based on rectangle bounds
        x_norm = (item['umap_x'] - x_min) / width
        y_norm = (item['umap_y'] - y_min) / height

        normalized.append({
            'article': item['article'],
            'x': float(x_norm),
            'y': float(y_norm),
            'umap_x': item['umap_x'],
            'umap_y': item['umap_y'],
            'index': item['index']
        })

    print(f"  Normalized {len(normalized):,} articles")
    print(f"  X range: [{min(n['x'] for n in normalized):.4f}, {max(n['x'] for n in normalized):.4f}]")
    print(f"  Y range: [{min(n['y'] for n in normalized):.4f}, {max(n['y'] for n in normalized):.4f}]")
    print()

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


def export_to_json(normalized_articles, output_file='wikipedia_articles.json'):
    """Export articles to JSON format for visualization"""
    print(f"Exporting to {output_file}...")

    articles_json = []
    for item in normalized_articles:
        article = item['article']
        articles_json.append({
            'title': article.get('title', 'Untitled'),
            'url': article.get('url', ''),
            'excerpt': create_excerpt(article.get('text', ''), max_length=100),
            'x': item['x'],
            'y': item['y'],
            'umap_x': item['umap_x'],
            'umap_y': item['umap_y'],
            'index': item['index']
        })

    with open(output_file, 'w') as f:
        json.dump(articles_json, f, indent=2)

    file_size_mb = Path(output_file).stat().st_size / (1024 * 1024)
    print(f"  ✓ Exported {len(articles_json):,} articles")
    print(f"  File size: {file_size_mb:.2f} MB")
    print()

    # Show sample articles
    print("Sample articles:")
    for i, article in enumerate(articles_json[:5]):
        print(f"  {i+1}. \"{article['title']}\"")
        print(f"     Position: ({article['x']:.4f}, {article['y']:.4f})")
        print(f"     UMAP: ({article['umap_x']:.2f}, {article['umap_y']:.2f})")
        if article['excerpt']:
            print(f"     Excerpt: {article['excerpt'][:60]}...")
        print()

    return output_file


def main():
    print()
    print("="*80)
    print("WIKIPEDIA ARTICLES EXPORT (OPTIMAL RECTANGLE)")
    print("="*80)
    print()

    # Load optimal rectangle bounds
    bounds = load_optimal_rectangle()

    # Load Wikipedia article data
    articles = load_wikipedia_articles()

    # Load UMAP coordinates
    coords = load_umap_coordinates()

    # Verify data consistency
    if len(articles) != len(coords):
        print(f"⚠ WARNING: Article count ({len(articles):,}) != "
              f"Coordinate count ({len(coords):,})")
        min_len = min(len(articles), len(coords))
        print(f"  Using first {min_len:,} entries")
        articles = articles[:min_len]
        coords = coords[:min_len]
        print()

    # Filter by optimal rectangle bounds
    filtered = filter_by_bounds(articles, coords, bounds)

    # Normalize coordinates to [0, 1]
    normalized = normalize_coordinates(filtered, bounds)

    # Export to JSON
    output_file = export_to_json(normalized)

    print("="*80)
    print("✓ EXPORT COMPLETE")
    print("="*80)
    print(f"Output: {output_file}")
    print(f"Articles exported: {len(normalized):,}")
    print(f"Coverage rectangle: X=[{bounds['x_min']:.2f}, {bounds['x_max']:.2f}], "
          f"Y=[{bounds['y_min']:.2f}, {bounds['y_max']:.2f}]")
    print()


if __name__ == '__main__':
    main()
