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
    """Load Wikipedia article metadata from embeddings file (correct ordering)"""
    print("Loading Wikipedia article metadata...")
    with open('embeddings/wikipedia_embeddings.pkl', 'rb') as f:
        data = pickle.load(f)

    # Extract article metadata - these are in the SAME ORDER as embeddings
    articles = []
    for i in range(len(data['titles'])):
        articles.append({
            'title': data['titles'][i],
            'url': data['urls'][i],
            'index': data['indices'][i],  # Original index in full dataset
            'text': ''  # No text in embeddings file
        })

    print(f"  Loaded {len(articles):,} articles")
    embeddings = data['embeddings']
    print(f"  Embeddings shape: {embeddings.shape}")

    return articles, embeddings


def load_umap_reducer():
    """Load UMAP reducer from data/umap_reducer.pkl"""
    print("Loading UMAP reducer...")
    with open('data/umap_reducer.pkl', 'rb') as f:
        reducer = pickle.load(f)
    print(f"  Loaded UMAP reducer: {type(reducer)}")
    return reducer


def load_bounds():
    """Load article bounds from data/umap_bounds.pkl"""
    print("Loading article bounds...")
    with open('data/umap_bounds.pkl', 'rb') as f:
        bounds_data = pickle.load(f)

    # Extract only article bounds (we'll calculate question bounds dynamically)
    article_bounds = bounds_data['articles']

    print(f"  Article bounds: x=[{article_bounds['x_min']:.2f}, {article_bounds['x_max']:.2f}], y=[{article_bounds['y_min']:.2f}, {article_bounds['y_max']:.2f}]")

    return article_bounds


def load_question_embeddings():
    """Load question embeddings"""
    print("Loading question embeddings...")
    with open('embeddings/question_embeddings.pkl', 'rb') as f:
        q_data = pickle.load(f)
    print(f"  Loaded {len(q_data['questions'])} questions")
    return q_data


def compute_question_bounds(question_coords):
    """Compute actual question bounding box from projected coordinates"""
    q_x_min = question_coords[:, 0].min()
    q_x_max = question_coords[:, 0].max()
    q_y_min = question_coords[:, 1].min()
    q_y_max = question_coords[:, 1].max()

    question_bounds = {
        'x_min': q_x_min,
        'x_max': q_x_max,
        'y_min': q_y_min,
        'y_max': q_y_max
    }

    print(f"  Question bounds (actual): x=[{q_x_min:.3f}, {q_x_max:.3f}], y=[{q_y_min:.3f}, {q_y_max:.3f}]")

    return question_bounds


def project_embeddings(embeddings, reducer):
    """Project embeddings to 2D using UMAP reducer"""
    print("Projecting embeddings to 2D...")
    coords_2d = reducer.transform(embeddings)
    print(f"  Projected coordinates: shape {coords_2d.shape}")
    return coords_2d


def filter_by_bounds(articles, coords_2d, question_bounds, padding=0.5):
    """Filter articles to only those within the question bounding box (with padding)"""
    print(f"Filtering articles within question bounding box (with {padding*100:.0f}% padding)...")

    # Calculate padded bounding box
    q_x_min, q_x_max = question_bounds['x_min'], question_bounds['x_max']
    q_y_min, q_y_max = question_bounds['y_min'], question_bounds['y_max']

    x_range = q_x_max - q_x_min
    y_range = q_y_max - q_y_min

    bbox_x_min = q_x_min - padding * x_range
    bbox_x_max = q_x_max + padding * x_range
    bbox_y_min = q_y_min - padding * y_range
    bbox_y_max = q_y_max + padding * y_range

    print(f"  Question bbox: x=[{bbox_x_min:.3f}, {bbox_x_max:.3f}], y=[{bbox_y_min:.3f}, {bbox_y_max:.3f}]")

    # Filter articles within bounding box
    filtered_articles = []

    for i, (article, coord) in enumerate(zip(articles, coords_2d)):
        x, y = coord
        if bbox_x_min <= x <= bbox_x_max and bbox_y_min <= y <= bbox_y_max:
            filtered_articles.append((article, x, y))

    print(f"  Filtered: {len(filtered_articles):,} / {len(articles):,} articles ({len(filtered_articles)/len(articles)*100:.1f}%)")
    return filtered_articles


def normalize_coordinates(filtered_articles, question_bounds, padding=0.5):
    """Normalize coordinates to [0, 1] range using padded question bounding box"""
    print(f"Normalizing coordinates to [0, 1] using padded question bbox...")

    # Calculate padded bounding box (same as used for filtering)
    q_x_min, q_x_max = question_bounds['x_min'], question_bounds['x_max']
    q_y_min, q_y_max = question_bounds['y_min'], question_bounds['y_max']

    x_range = q_x_max - q_x_min
    y_range = q_y_max - q_y_min

    bbox_x_min = q_x_min - padding * x_range
    bbox_x_max = q_x_max + padding * x_range
    bbox_y_min = q_y_min - padding * y_range
    bbox_y_max = q_y_max + padding * y_range

    normalized = []

    for article, x, y in filtered_articles:
        # Normalize to [0, 1] based on padded question bbox
        x_norm = (x - bbox_x_min) / (bbox_x_max - bbox_x_min)
        y_norm = (y - bbox_y_min) / (bbox_y_max - bbox_y_min)

        normalized.append((article, x_norm, y_norm))

    print(f"  Normalized {len(normalized):,} articles to [0, 1] range")
    print(f"  Bbox used: x=[{bbox_x_min:.3f}, {bbox_x_max:.3f}], y=[{bbox_y_min:.3f}, {bbox_y_max:.3f}]")

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


def normalize_question_coordinates(question_coords, question_bounds, padding=0.5):
    """Normalize question coordinates using the same padded bounding box as articles"""
    print(f"\nNormalizing question coordinates...")

    # Calculate padded bounding box (same as used for articles)
    q_x_min, q_x_max = question_bounds['x_min'], question_bounds['x_max']
    q_y_min, q_y_max = question_bounds['y_min'], question_bounds['y_max']

    x_range = q_x_max - q_x_min
    y_range = q_y_max - q_y_min

    bbox_x_min = q_x_min - padding * x_range
    bbox_x_max = q_x_max + padding * x_range
    bbox_y_min = q_y_min - padding * y_range
    bbox_y_max = q_y_max + padding * y_range

    normalized = []
    for coord in question_coords:
        x, y = coord
        x_norm = (x - bbox_x_min) / (bbox_x_max - bbox_x_min)
        y_norm = (y - bbox_y_min) / (bbox_y_max - bbox_y_min)
        normalized.append((x_norm, y_norm))

    print(f"  Normalized {len(normalized)} questions")
    return np.array(normalized)


def export_to_json(normalized_articles, normalized_questions, question_texts,
                   article_output='wikipedia_articles.json',
                   question_output='question_coordinates.json'):
    """Export articles and questions to JSON format for visualization"""
    print(f"\nExporting articles to {article_output}...")

    articles_json = []
    for article, x, y in normalized_articles:
        articles_json.append({
            'title': article.get('title', 'Untitled'),
            'url': article.get('url', ''),
            'excerpt': create_excerpt(article.get('text', ''), max_length=100),
            'x': float(x),
            'y': float(y)
        })

    with open(article_output, 'w') as f:
        json.dump(articles_json, f, indent=2)

    print(f"  Exported {len(articles_json):,} articles")
    print(f"\nSample articles:")
    for i, article in enumerate(articles_json[:3]):
        print(f"  {i+1}. {article['title']}")
        print(f"     Position: ({article['x']:.3f}, {article['y']:.3f})")
        print(f"     Excerpt: {article['excerpt'][:60]}...")

    # Export questions to question_coordinates.json
    print(f"\nExporting questions to {question_output}...")
    questions_json = []
    for i, (coord, text) in enumerate(zip(normalized_questions, question_texts)):
        questions_json.append({
            'id': i,
            'text': text,
            'x': float(coord[0]),
            'y': float(coord[1])
        })

    with open(question_output, 'w') as f:
        json.dump(questions_json, f, indent=2)

    print(f"  Exported {len(questions_json)} questions")
    print(f"\nSample questions:")
    for i, q in enumerate(questions_json[:3]):
        print(f"  {i+1}. {q['text'][:60]}...")
        print(f"     Position: ({q['x']:.3f}, {q['y']:.3f})")

    # Update questions.json (used by visualization)
    print(f"\nUpdating questions.json with new coordinates...")
    try:
        with open('questions.json', 'r') as f:
            questions_main = json.load(f)

        # Update x, y coordinates
        for i, q in enumerate(questions_main):
            q['x'] = float(normalized_questions[i][0])
            q['y'] = float(normalized_questions[i][1])

        with open('questions.json', 'w') as f:
            json.dump(questions_main, f, indent=2)

        print(f"  Updated questions.json with normalized coordinates")
    except FileNotFoundError:
        print(f"  Warning: questions.json not found - skipping update")

    return article_output, question_output


def main():
    print("="*80)
    print("Wikipedia Articles Export Script")
    print("="*80)
    print()

    # Load data (articles and embeddings in correct order)
    articles, embeddings = load_wikipedia_data()
    reducer = load_umap_reducer()
    article_bounds = load_bounds()

    # Load question embeddings and compute actual question bounds
    q_data = load_question_embeddings()
    question_embeddings = q_data['embeddings']

    print("\nProjecting question embeddings to UMAP space...")
    question_coords = reducer.transform(question_embeddings)
    print(f"  Question UMAP coords: {question_coords.shape}")

    question_bounds = compute_question_bounds(question_coords)

    # Articles and embeddings are already aligned
    print(f"\nUsing {len(articles):,} articles with {len(embeddings):,} embeddings")

    # Project to 2D
    coords_2d = project_embeddings(embeddings, reducer)

    # Filter by question bounding box (with 50% padding for better visualization)
    padding = 0.5
    filtered = filter_by_bounds(articles, coords_2d, question_bounds, padding=padding)

    # Normalize coordinates using padded question bounding box
    normalized_articles = normalize_coordinates(filtered, question_bounds, padding=padding)

    # Normalize question coordinates using same bounding box
    normalized_questions = normalize_question_coordinates(question_coords, question_bounds, padding=padding)

    # Export to JSON
    article_output, question_output = export_to_json(
        normalized_articles,
        normalized_questions,
        q_data['questions']
    )

    print()
    print("="*80)
    print(f"✓ Successfully exported {len(normalized_articles):,} articles to {article_output}")
    print(f"✓ Successfully exported {len(normalized_questions)} questions to {question_output}")
    print("="*80)


if __name__ == '__main__':
    main()
