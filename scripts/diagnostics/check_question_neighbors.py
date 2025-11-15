#!/usr/bin/env python3
"""
Diagnostic script to check question-article alignment in embedding and UMAP spaces.

For each question, finds:
1. 5 nearest articles in high-dimensional embedding space (768-dim)
2. 5 nearest articles in UMAP space (2-dim)

This helps diagnose if embeddings/UMAP are working correctly.
"""

import pickle
import json
import numpy as np
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances


def load_question_embeddings():
    """Load question embeddings"""
    print("Loading question embeddings...")
    with open('embeddings/question_embeddings.pkl', 'rb') as f:
        q_data = pickle.load(f)
    print(f"  Loaded {len(q_data['questions'])} questions")
    return q_data


def load_article_embeddings():
    """Load article embeddings"""
    print("Loading article embeddings...")
    with open('embeddings/wikipedia_embeddings.pkl', 'rb') as f:
        a_data = pickle.load(f)
    print(f"  Loaded {len(a_data['embeddings'])} articles")
    return a_data


def load_umap_reducer():
    """Load UMAP reducer"""
    print("Loading UMAP reducer...")
    with open('data/umap_reducer.pkl', 'rb') as f:
        reducer = pickle.load(f)
    print(f"  Loaded UMAP reducer")
    return reducer


def find_nearest_in_embedding_space(question_emb, article_embs, article_titles, k=5):
    """Find k nearest articles to question in embedding space using cosine similarity"""
    # Reshape for cosine_similarity
    question_emb = question_emb.reshape(1, -1)

    # Compute cosine similarities
    similarities = cosine_similarity(question_emb, article_embs)[0]

    # Get top k indices
    top_k_indices = np.argsort(similarities)[-k:][::-1]

    results = []
    for idx in top_k_indices:
        results.append({
            'index': int(idx),
            'title': article_titles[idx],
            'similarity': float(similarities[idx])
        })

    return results


def find_nearest_in_umap_space(question_coord, article_coords, article_titles, k=5):
    """Find k nearest articles to question in UMAP space using Euclidean distance"""
    # Reshape for distance calculation
    question_coord = question_coord.reshape(1, -1)

    # Compute Euclidean distances
    distances = euclidean_distances(question_coord, article_coords)[0]

    # Get top k indices (smallest distances)
    top_k_indices = np.argsort(distances)[:k]

    results = []
    for idx in top_k_indices:
        results.append({
            'index': int(idx),
            'title': article_titles[idx],
            'distance': float(distances[idx]),
            'coordinates': article_coords[idx].tolist()
        })

    return results


def main():
    print("="*80)
    print("QUESTION-ARTICLE NEIGHBOR DIAGNOSTIC")
    print("="*80)
    print()

    # Load data
    q_data = load_question_embeddings()
    a_data = load_article_embeddings()
    reducer = load_umap_reducer()

    question_embeddings = q_data['embeddings']
    question_texts = q_data['questions']

    article_embeddings = a_data['embeddings']
    article_titles = a_data['titles']

    print()
    print(f"Question embeddings shape: {question_embeddings.shape}")
    print(f"Article embeddings shape: {article_embeddings.shape}")
    print()

    # Project to UMAP space
    print("Projecting embeddings to UMAP space...")
    question_coords = reducer.transform(question_embeddings)
    article_coords = reducer.transform(article_embeddings)
    print(f"  Question UMAP coords: {question_coords.shape}")
    print(f"  Article UMAP coords: {article_coords.shape}")
    print()

    # Analyze question coordinate bounds
    print("Question UMAP coordinate bounds:")
    print(f"  x: [{question_coords[:, 0].min():.3f}, {question_coords[:, 0].max():.3f}]")
    print(f"  y: [{question_coords[:, 1].min():.3f}, {question_coords[:, 1].max():.3f}]")
    print()

    print("Article UMAP coordinate bounds:")
    print(f"  x: [{article_coords[:, 0].min():.3f}, {article_coords[:, 0].max():.3f}]")
    print(f"  y: [{article_coords[:, 1].min():.3f}, {article_coords[:, 1].max():.3f}]")
    print()

    # Calculate bounding box with 50% padding
    q_x_min, q_x_max = question_coords[:, 0].min(), question_coords[:, 0].max()
    q_y_min, q_y_max = question_coords[:, 1].min(), question_coords[:, 1].max()

    x_range = q_x_max - q_x_min
    y_range = q_y_max - q_y_min

    bbox_x_min = q_x_min - 0.5 * x_range
    bbox_x_max = q_x_max + 0.5 * x_range
    bbox_y_min = q_y_min - 0.5 * y_range
    bbox_y_max = q_y_max + 0.5 * y_range

    print("Question bounding box (with 50% padding):")
    print(f"  x: [{bbox_x_min:.3f}, {bbox_x_max:.3f}]")
    print(f"  y: [{bbox_y_min:.3f}, {bbox_y_max:.3f}]")
    print()

    # Count articles in bounding box
    articles_in_bbox = 0
    for coord in article_coords:
        x, y = coord
        if bbox_x_min <= x <= bbox_x_max and bbox_y_min <= y <= bbox_y_max:
            articles_in_bbox += 1

    print(f"Articles within question bounding box: {articles_in_bbox} / {len(article_coords)} ({articles_in_bbox/len(article_coords)*100:.1f}%)")
    print()

    # For each question, find nearest neighbors
    results = []

    print("="*80)
    print("NEAREST NEIGHBOR ANALYSIS")
    print("="*80)
    print()

    for i, (q_text, q_emb, q_coord) in enumerate(zip(question_texts, question_embeddings, question_coords)):
        print(f"Question {i+1}/{len(question_texts)}:")
        print(f"  Text: {q_text[:80]}...")
        print(f"  UMAP coord: ({q_coord[0]:.3f}, {q_coord[1]:.3f})")
        print()

        # Find nearest in embedding space
        emb_neighbors = find_nearest_in_embedding_space(q_emb, article_embeddings, article_titles, k=5)

        print("  Top 5 nearest in EMBEDDING space (cosine similarity):")
        for j, neighbor in enumerate(emb_neighbors):
            print(f"    {j+1}. [{neighbor['index']:5d}] {neighbor['title'][:60]:60s} (sim={neighbor['similarity']:.4f})")
        print()

        # Find nearest in UMAP space
        umap_neighbors = find_nearest_in_umap_space(q_coord, article_coords, article_titles, k=5)

        print("  Top 5 nearest in UMAP space (Euclidean distance):")
        for j, neighbor in enumerate(umap_neighbors):
            coord_str = f"({neighbor['coordinates'][0]:.3f}, {neighbor['coordinates'][1]:.3f})"
            print(f"    {j+1}. [{neighbor['index']:5d}] {neighbor['title'][:60]:60s} (dist={neighbor['distance']:.4f}, coord={coord_str})")
        print()

        # Check overlap
        emb_indices = set(n['index'] for n in emb_neighbors)
        umap_indices = set(n['index'] for n in umap_neighbors)
        overlap = emb_indices & umap_indices

        print(f"  Overlap: {len(overlap)}/5 articles appear in both lists")
        if overlap:
            print(f"    Shared articles: {[article_titles[idx] for idx in overlap]}")
        print()
        print("-"*80)
        print()

        results.append({
            'question': q_text,
            'question_coord': q_coord.tolist(),
            'embedding_neighbors': emb_neighbors,
            'umap_neighbors': umap_neighbors,
            'overlap_count': len(overlap)
        })

    # Save results
    output_file = 'neighbor_analysis.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print("="*80)
    print(f"✓ Analysis complete. Results saved to {output_file}")
    print("="*80)
    print()

    # Summary statistics
    avg_overlap = np.mean([r['overlap_count'] for r in results])
    print("Summary Statistics:")
    print(f"  Average overlap between embedding and UMAP neighbors: {avg_overlap:.1f}/5")
    print(f"  Articles in question bounding box: {articles_in_bbox} ({articles_in_bbox/len(article_coords)*100:.1f}%)")
    print()


if __name__ == '__main__':
    main()
