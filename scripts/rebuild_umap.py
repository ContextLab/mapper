#!/usr/bin/env python3
"""
Rebuild UMAP Projections for Wikipedia Knowledge Map

This script rebuilds UMAP 2D projections from existing embeddings.
It should be run whenever:
  - New embeddings are generated with a different model
  - UMAP parameters need to be changed
  - The UMAP reducer becomes incompatible with current embeddings

This ensures that articles and questions exist in the same UMAP coordinate space,
preserving semantic relationships from the embedding space.

Prerequisites:
  - embeddings/wikipedia_embeddings.pkl (25,000 articles, 768-dim)
  - embeddings/question_embeddings.pkl (10 questions, 768-dim)

Outputs:
  - data/umap_reducer.pkl - Trained UMAP model for future transformations
  - data/umap_bounds.pkl - Coordinate bounds (global, articles, questions)
  - data/question_coordinates.pkl - Normalized question coordinates [0,1]
  - umap_coords.pkl - Full UMAP coordinates for all 25,010 items
  - wikipedia_articles.json - Updated article positions
  - knowledge_map.pkl - Complete knowledge map data

Usage:
  python scripts/rebuild_umap.py

Verification:
  After running, check that:
  - scripts/diagnostics/check_question_neighbors.py shows >60% neighbor overlap
  - Question nearest neighbors are semantically related
  - Articles are distributed across the map (not all clustered)
"""

import pickle
import json
import numpy as np
from pathlib import Path
import umap
from datetime import datetime


def load_embeddings():
    """Load article and question embeddings."""
    print("="*80)
    print("STEP 1: Loading Embeddings")
    print("="*80)
    print()

    # Load Wikipedia article embeddings
    print("Loading Wikipedia embeddings...")
    with open('embeddings/wikipedia_embeddings.pkl', 'rb') as f:
        wiki_data = pickle.load(f)

    wiki_embeddings = wiki_data['embeddings']
    wiki_titles = wiki_data['titles']
    wiki_urls = wiki_data['urls']

    print(f"  ✓ Loaded {len(wiki_embeddings):,} articles")
    print(f"    Shape: {wiki_embeddings.shape}")
    print(f"    Model: {wiki_data.get('model', 'unknown')}")
    print()

    # Load question embeddings
    print("Loading question embeddings...")
    with open('embeddings/question_embeddings.pkl', 'rb') as f:
        question_data = pickle.load(f)

    question_embeddings = question_data['embeddings']
    question_texts = question_data['questions']

    print(f"  ✓ Loaded {len(question_embeddings)} questions")
    print(f"    Shape: {question_embeddings.shape}")
    print(f"    Model: {question_data.get('model', 'unknown')}")
    print()

    return {
        'wiki_embeddings': wiki_embeddings,
        'wiki_titles': wiki_titles,
        'wiki_urls': wiki_urls,
        'question_embeddings': question_embeddings,
        'question_texts': question_texts
    }


def compute_umap(embeddings_data):
    """Compute UMAP projection on combined embeddings."""
    print("="*80)
    print("STEP 2: Computing UMAP Projection")
    print("="*80)
    print()

    wiki_embeddings = embeddings_data['wiki_embeddings']
    question_embeddings = embeddings_data['question_embeddings']

    # Combine embeddings (articles FIRST, then questions)
    print("Combining embeddings...")
    combined_embeddings = np.vstack([wiki_embeddings, question_embeddings])
    print(f"  Combined shape: {combined_embeddings.shape}")
    print(f"  Articles: indices 0-{len(wiki_embeddings)-1}")
    print(f"  Questions: indices {len(wiki_embeddings)}-{len(combined_embeddings)-1}")
    print()

    # Configure UMAP
    print("Configuring UMAP...")
    umap_params = {
        'n_neighbors': 15,
        'min_dist': 0.1,
        'n_components': 2,
        'metric': 'cosine',
        'random_state': 42
    }
    print(f"  Parameters: {umap_params}")
    print()

    # Fit UMAP on combined data
    print("Fitting UMAP (this may take several minutes)...")
    reducer = umap.UMAP(**umap_params)
    coords_2d = reducer.fit_transform(combined_embeddings)

    print(f"  ✓ UMAP projection complete")
    print(f"    Output shape: {coords_2d.shape}")
    print(f"    Coordinate range: x=[{coords_2d[:, 0].min():.2f}, {coords_2d[:, 0].max():.2f}]")
    print(f"                      y=[{coords_2d[:, 1].min():.2f}, {coords_2d[:, 1].max():.2f}]")
    print()

    return coords_2d, reducer


def save_umap_data(coords_2d, reducer, embeddings_data):
    """Save UMAP coordinates, bounds, and question coordinates."""
    print("="*80)
    print("STEP 3: Saving UMAP Data")
    print("="*80)
    print()

    article_count = len(embeddings_data['wiki_embeddings'])

    # Create data directory if needed
    Path('data').mkdir(exist_ok=True)

    # 1. Save full UMAP coordinates and reducer
    print("Saving full UMAP coordinates...")
    with open('umap_coords.pkl', 'wb') as f:
        pickle.dump({
            'coords_2d': coords_2d,
            'reducer': reducer,
            'timestamp': datetime.now().isoformat()
        }, f)
    print(f"  ✓ Saved to umap_coords.pkl")
    print()

    # 2. Save UMAP reducer separately
    print("Saving UMAP reducer...")
    with open('data/umap_reducer.pkl', 'wb') as f:
        pickle.dump(reducer, f)
    print(f"  ✓ Saved to data/umap_reducer.pkl")
    print()

    # 3. Compute and save bounds
    print("Computing coordinate bounds...")

    # Global bounds (all points)
    global_bounds = {
        'x_min': float(coords_2d[:, 0].min()),
        'x_max': float(coords_2d[:, 0].max()),
        'y_min': float(coords_2d[:, 1].min()),
        'y_max': float(coords_2d[:, 1].max())
    }

    # Article bounds
    article_coords = coords_2d[:article_count, :]
    article_bounds = {
        'x_min': float(article_coords[:, 0].min()),
        'x_max': float(article_coords[:, 0].max()),
        'y_min': float(article_coords[:, 1].min()),
        'y_max': float(article_coords[:, 1].max())
    }

    # Question bounds
    question_coords = coords_2d[article_count:, :]
    question_bounds = {
        'x_min': float(question_coords[:, 0].min()),
        'x_max': float(question_coords[:, 0].max()),
        'y_min': float(question_coords[:, 1].min()),
        'y_max': float(question_coords[:, 1].max())
    }

    bounds_data = {
        'global': global_bounds,
        'articles': article_bounds,
        'questions': question_bounds,
        'timestamp': datetime.now().isoformat()
    }

    with open('data/umap_bounds.pkl', 'wb') as f:
        pickle.dump(bounds_data, f)

    print(f"  ✓ Saved to data/umap_bounds.pkl")
    print(f"    Global: x=[{global_bounds['x_min']:.2f}, {global_bounds['x_max']:.2f}], "
          f"y=[{global_bounds['y_min']:.2f}, {global_bounds['y_max']:.2f}]")
    print(f"    Articles: x=[{article_bounds['x_min']:.2f}, {article_bounds['x_max']:.2f}], "
          f"y=[{article_bounds['y_min']:.2f}, {article_bounds['y_max']:.2f}]")
    print(f"    Questions: x=[{question_bounds['x_min']:.2f}, {question_bounds['x_max']:.2f}], "
          f"y=[{question_bounds['y_min']:.2f}, {question_bounds['y_max']:.2f}]")
    print()

    # 4. Save normalized question coordinates [0, 1]
    print("Saving normalized question coordinates...")

    # Normalize using global bounds
    x_range = global_bounds['x_max'] - global_bounds['x_min']
    y_range = global_bounds['y_max'] - global_bounds['y_min']

    coords_normalized = np.zeros_like(question_coords)
    coords_normalized[:, 0] = (question_coords[:, 0] - global_bounds['x_min']) / x_range
    coords_normalized[:, 1] = (question_coords[:, 1] - global_bounds['y_min']) / y_range

    question_coord_data = {
        'coordinates': coords_normalized,
        'questions': embeddings_data['question_texts'],
        'bounds_used': 'global',
        'timestamp': datetime.now().isoformat()
    }

    with open('data/question_coordinates.pkl', 'wb') as f:
        pickle.dump(question_coord_data, f)

    print(f"  ✓ Saved to data/question_coordinates.pkl")
    print(f"    Normalized to [0, 1] using global bounds")
    print()

    return article_coords, article_bounds


def export_articles_json(article_coords, article_bounds, embeddings_data):
    """Export Wikipedia articles with normalized coordinates to JSON."""
    print("="*80)
    print("STEP 4: Exporting Articles to JSON")
    print("="*80)
    print()

    print("Normalizing article coordinates...")

    # Normalize using article bounds
    x_range = article_bounds['x_max'] - article_bounds['x_min']
    y_range = article_bounds['y_max'] - article_bounds['y_min']

    coords_normalized = np.zeros_like(article_coords)
    coords_normalized[:, 0] = (article_coords[:, 0] - article_bounds['x_min']) / x_range
    coords_normalized[:, 1] = (article_coords[:, 1] - article_bounds['y_min']) / y_range

    print(f"  Normalized {len(coords_normalized):,} articles to [0, 1]")
    print()

    # Load article data
    print("Loading article text data...")
    with open('data/wikipedia.pkl', 'rb') as f:
        articles = pickle.load(f)

    # Take only first 25,000 (matching embeddings)
    articles = articles[:25000]
    print(f"  Using {len(articles):,} articles")
    print()

    # Create JSON output
    print("Creating JSON output...")
    articles_json = []

    for article, (x, y) in zip(articles, coords_normalized):
        # Create excerpt (first 100 chars)
        text = article.get('text', '')
        excerpt = ' '.join(text.split())[:100]
        if len(text) > 100:
            # Try to truncate at sentence or word boundary
            if '.' in excerpt:
                excerpt = excerpt[:excerpt.rfind('.')+1]
            elif ' ' in excerpt:
                excerpt = excerpt[:excerpt.rfind(' ')] + '...'
            else:
                excerpt = excerpt + '...'

        articles_json.append({
            'title': article.get('title', 'Untitled'),
            'url': article.get('url', ''),
            'excerpt': excerpt,
            'x': float(x),
            'y': float(y)
        })

    # Save to file
    with open('wikipedia_articles.json', 'w') as f:
        json.dump(articles_json, f, indent=2)

    print(f"  ✓ Saved to wikipedia_articles.json")
    print(f"    Exported {len(articles_json):,} articles")
    print()


def save_knowledge_map(coords_2d, embeddings_data):
    """Save complete knowledge map data."""
    print("="*80)
    print("STEP 5: Saving Knowledge Map")
    print("="*80)
    print()

    article_count = len(embeddings_data['wiki_embeddings'])

    knowledge_map_data = {
        'article_coordinates': coords_2d[:article_count, :],
        'article_titles': embeddings_data['wiki_titles'],
        'article_urls': embeddings_data['wiki_urls'],
        'question_coordinates': coords_2d[article_count:, :],
        'question_texts': embeddings_data['question_texts'],
        'timestamp': datetime.now().isoformat()
    }

    with open('knowledge_map.pkl', 'wb') as f:
        pickle.dump(knowledge_map_data, f)

    print(f"  ✓ Saved to knowledge_map.pkl")
    print()


def main():
    """Main workflow for rebuilding UMAP projections."""
    print()
    print("=" * 80)
    print("REBUILD UMAP PROJECTIONS")
    print("=" * 80)
    print(f"Started: {datetime.now()}")
    print()

    # Step 1: Load embeddings
    embeddings_data = load_embeddings()

    # Step 2: Compute UMAP
    coords_2d, reducer = compute_umap(embeddings_data)

    # Step 3: Save UMAP data
    article_coords, article_bounds = save_umap_data(coords_2d, reducer, embeddings_data)

    # Step 4: Export articles JSON
    export_articles_json(article_coords, article_bounds, embeddings_data)

    # Step 5: Save knowledge map
    save_knowledge_map(coords_2d, embeddings_data)

    # Summary
    print("=" * 80)
    print("✓ UMAP REBUILD COMPLETE")
    print("=" * 80)
    print()
    print("Files created:")
    print("  - umap_coords.pkl - Full UMAP coordinates")
    print("  - data/umap_reducer.pkl - Trained UMAP model")
    print("  - data/umap_bounds.pkl - Coordinate bounds")
    print("  - data/question_coordinates.pkl - Question coordinates")
    print("  - wikipedia_articles.json - Article data for visualization")
    print("  - knowledge_map.pkl - Complete knowledge map")
    print()
    print("Next steps:")
    print("  1. Run scripts/diagnostics/check_question_neighbors.py to verify")
    print("     - Should see >60% neighbor overlap")
    print("     - UMAP neighbors should be semantically related")
    print()
    print("  2. Check visualization at knowledge_map_heatmap.html")
    print("     - Articles should be visible")
    print("     - Questions should appear on the map")
    print()
    print(f"Completed: {datetime.now()}")
    print()


if __name__ == '__main__':
    main()
