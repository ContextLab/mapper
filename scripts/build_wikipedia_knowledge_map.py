#!/usr/bin/env python3
"""
Build knowledge map with Wikipedia articles + questions using nvidia/nemotron embeddings.

Dataset Strategy:
  - Hypertools wiki: Hand-curated subset spanning diverse content areas (quality breadth)
  - 250,000 Dropbox articles: Random sample from Wikipedia (quantity depth)
  - 10 quiz questions: Target items to map
  - Total: ~250,010+ items providing rich semantic coverage

This combination ensures both broad topic coverage (hypertools) and statistical depth
(250k random articles), creating a dense semantic space for accurate KNN-based labeling.

Steps:
1. Load ALL articles from hypertools + dropbox (no sampling - use everything)
2. Load questions from questions.json
3. Generate embeddings using nvidia/llama-embed-nemotron-8b (4096-dim)
4. Compute UMAP on combined dataset (~250k points)
5. Save embeddings + text + coordinates to pickle file

Resource Requirements:
  - Memory: ~40GB RAM (250k × 4096-dim × 4 bytes ≈ 4GB embeddings + UMAP overhead)
  - Time: 2-6 hours depending on hardware (GPU vs CPU)
  - Disk: ~3-5GB for final knowledge_map.pkl
"""

import os
import json
import pickle
import numpy as np
from datetime import datetime

# Fix for macOS
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

def load_wikipedia_articles():
    """
    Load ALL Wikipedia articles from both sources (no sampling).

    This will load ~250k articles from Dropbox + hypertools wiki dataset.
    Expected: ~250k+ total articles for rich semantic coverage.
    """
    print("="*80)
    print("Loading Wikipedia Articles (ALL articles, no sampling)")
    print("="*80)

    articles = []

    # Source 1: Hypertools wiki dataset
    print("\n1. Loading hypertools wiki dataset...")
    try:
        import hypertools as hyp
        wiki_hyp = hyp.load('wiki')

        # DataGeometry object - access .data attribute
        if hasattr(wiki_hyp, 'data'):
            wiki_data = wiki_hyp.data

            # If it's a list of lists, flatten
            if isinstance(wiki_data, list) and len(wiki_data) > 0:
                if isinstance(wiki_data[0], list):
                    # Each text_list is a document represented as list of words/features
                    for i, text_list in enumerate(wiki_data):
                        if isinstance(text_list, list):
                            text = ' '.join(str(x) for x in text_list if x)
                        else:
                            text = str(text_list)

                        articles.append({
                            'text': text,
                            'title': f"Hypertools Article {i+1}",
                            'source': 'hypertools'
                        })
                else:
                    # Simple list
                    for i, text in enumerate(wiki_data):
                        articles.append({
                            'text': str(text),
                            'title': f"Hypertools Article {i+1}",
                            'source': 'hypertools'
                        })

        print(f"   Loaded {len(articles):,} articles from hypertools")
    except Exception as e:
        print(f"   Error loading hypertools wiki: {e}")
        import traceback
        traceback.print_exc()

    # Source 2: Dropbox pickle file (250k articles - USE ALL OF THEM)
    print("\n2. Loading ALL articles from wikipedia.pkl...")
    try:
        with open('data/wikipedia.pkl', 'rb') as f:
            wiki_dropbox = pickle.load(f)

        print(f"   Total articles in file: {len(wiki_dropbox):,}")
        print(f"   Loading all {len(wiki_dropbox):,} articles (this may take a few minutes)...")

        # Process ALL articles (structure: list of dicts with id, url, title, text)
        for i, item in enumerate(wiki_dropbox):
            if i % 10000 == 0:
                print(f"     Progress: {i:,}/{len(wiki_dropbox):,} ({i/len(wiki_dropbox)*100:.1f}%)")

            if isinstance(item, dict):
                articles.append({
                    'text': item.get('text', item.get('content', str(item))),
                    'title': item.get('title', f"Wikipedia Article {i+1}"),
                    'source': 'dropbox',
                    'url': item.get('url', ''),
                    'id': item.get('id', '')
                })
            elif isinstance(item, str):
                articles.append({
                    'text': item,
                    'title': f"Wikipedia Article {i+1}",
                    'source': 'dropbox'
                })

        dropbox_count = sum(1 for a in articles if a['source'] == 'dropbox')
        print(f"   ✓ Loaded {dropbox_count:,} articles from Dropbox")

    except FileNotFoundError:
        print("   ✗ wikipedia.pkl not found - run download first")
    except Exception as e:
        print(f"   ✗ Error loading wikipedia.pkl: {e}")
        import traceback
        traceback.print_exc()

    print(f"\n✓ Total Wikipedia articles loaded: {len(articles):,}")
    return articles

def load_questions():
    """Load questions from questions.json."""
    print("\n" + "="*80)
    print("Loading Questions")
    print("="*80)

    with open('questions.json') as f:
        questions = json.load(f)

    # Convert to same format as articles
    question_items = []
    for q in questions:
        question_items.append({
            'text': q['question'],
            'title': q['question'],
            'source': 'question',
            'question_data': q  # Preserve original question data
        })

    print(f"\nLoaded {len(question_items)} questions")
    return question_items

def generate_embeddings_nemotron(texts, batch_size=32):
    """
    Generate embeddings using nvidia/llama-embed-nemotron-8b.

    This is a ~8B parameter model optimized for semantic similarity.
    Embedding dimension: 4096
    """
    print("\n" + "="*80)
    print("Generating Embeddings with nvidia/llama-embed-nemotron-8b")
    print("="*80)

    from sentence_transformers import SentenceTransformer

    print("\nLoading nemotron model...")
    model = SentenceTransformer('nvidia/llama-embed-nemotron-8b', trust_remote_code=True)

    print(f"Model loaded. Embedding dimension: {model.get_sentence_embedding_dimension()}")
    print(f"\nGenerating embeddings for {len(texts)} items...")
    print(f"Batch size: {batch_size}")

    # Generate embeddings in batches
    embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        if i % 100 == 0:
            print(f"  Progress: {i}/{len(texts)} ({i/len(texts)*100:.1f}%)")

        batch_embeddings = model.encode(batch, show_progress_bar=False)
        embeddings.extend(batch_embeddings)

    embeddings = np.array(embeddings)
    print(f"\nGenerated embeddings shape: {embeddings.shape}")

    return embeddings

def compute_umap_embeddings(embeddings, n_components=2, n_neighbors=15, min_dist=0.1):
    """Compute UMAP 2D projection."""
    print("\n" + "="*80)
    print("Computing UMAP Projection")
    print("="*80)

    import umap

    print(f"\nParameters:")
    print(f"  n_components: {n_components}")
    print(f"  n_neighbors: {n_neighbors}")
    print(f"  min_dist: {min_dist}")

    reducer = umap.UMAP(
        n_components=n_components,
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        metric='cosine',
        random_state=42
    )

    print(f"\nFitting UMAP on {embeddings.shape[0]} points...")
    coords_2d = reducer.fit_transform(embeddings)

    print(f"UMAP coordinates shape: {coords_2d.shape}")
    print(f"Coordinate ranges:")
    print(f"  X: [{coords_2d[:, 0].min():.3f}, {coords_2d[:, 0].max():.3f}]")
    print(f"  Y: [{coords_2d[:, 1].min():.3f}, {coords_2d[:, 1].max():.3f}]")

    return coords_2d, reducer

def save_knowledge_map(items, embeddings, coords_2d, reducer, output_file='knowledge_map.pkl'):
    """Save complete knowledge map to pickle file."""
    print("\n" + "="*80)
    print("Saving Knowledge Map")
    print("="*80)

    # Separate questions and articles
    question_indices = [i for i, item in enumerate(items) if item['source'] == 'question']
    article_indices = [i for i, item in enumerate(items) if item['source'] != 'question']

    # Normalize coordinates to [0, 1]
    x_min, x_max = coords_2d[:, 0].min(), coords_2d[:, 0].max()
    y_min, y_max = coords_2d[:, 1].min(), coords_2d[:, 1].max()

    coords_normalized = np.zeros_like(coords_2d)
    coords_normalized[:, 0] = (coords_2d[:, 0] - x_min) / (x_max - x_min)
    coords_normalized[:, 1] = (coords_2d[:, 1] - y_min) / (y_max - y_min)

    # Compute question bounding box (for heatmap zoom)
    question_coords = coords_normalized[question_indices]
    q_x_min, q_x_max = question_coords[:, 0].min(), question_coords[:, 0].max()
    q_y_min, q_y_max = question_coords[:, 1].min(), question_coords[:, 1].max()

    # Add padding (20% on each side)
    padding = 0.2
    x_range = q_x_max - q_x_min
    y_range = q_y_max - q_y_min

    q_x_min = max(0, q_x_min - padding * x_range)
    q_x_max = min(1, q_x_max + padding * x_range)
    q_y_min = max(0, q_y_min - padding * y_range)
    q_y_max = min(1, q_y_max + padding * y_range)

    knowledge_map = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'model': 'nvidia/llama-embed-nemotron-8b',
            'embedding_dim': embeddings.shape[1],
            'total_items': len(items),
            'num_questions': len(question_indices),
            'num_articles': len(article_indices),
            'umap_params': {
                'n_components': 2,
                'n_neighbors': 15,
                'min_dist': 0.1,
                'metric': 'cosine'
            },
            'bounds': {
                'x_min': float(x_min),
                'x_max': float(x_max),
                'y_min': float(y_min),
                'y_max': float(y_max)
            },
            'question_region': {
                'x_min': float(q_x_min),
                'x_max': float(q_x_max),
                'y_min': float(q_y_min),
                'y_max': float(q_y_max)
            }
        },
        'items': [
            {
                'text': item['text'],
                'title': item['title'],
                'source': item['source'],
                'embedding': embeddings[i].tolist(),
                'x': float(coords_normalized[i, 0]),
                'y': float(coords_normalized[i, 1]),
                'x_raw': float(coords_2d[i, 0]),
                'y_raw': float(coords_2d[i, 1]),
                **(item.get('question_data', {}))
            }
            for i, item in enumerate(items)
        ],
        'umap_reducer': reducer
    }

    print(f"\nKnowledge map statistics:")
    print(f"  Total items: {len(items)}")
    print(f"  Questions: {len(question_indices)}")
    print(f"  Articles: {len(article_indices)}")
    print(f"  Embedding dimension: {embeddings.shape[1]}")
    print(f"\nQuestion region (with {int(padding*100)}% padding):")
    print(f"  X: [{q_x_min:.3f}, {q_x_max:.3f}]")
    print(f"  Y: [{q_y_min:.3f}, {q_y_max:.3f}]")

    print(f"\nSaving to {output_file}...")
    with open(output_file, 'wb') as f:
        pickle.dump(knowledge_map, f)

    print(f"✓ Saved ({os.path.getsize(output_file) / 1024 / 1024:.1f} MB)")

    return knowledge_map

def main():
    print("\n" + "="*80)
    print("WIKIPEDIA KNOWLEDGE MAP BUILDER")
    print("="*80)
    print("\nBuilding knowledge map with:")
    print("  - Wikipedia articles (hypertools + dropbox)")
    print("  - Quiz questions")
    print("  - nvidia/llama-embed-nemotron-8b embeddings")
    print("  - UMAP 2D projection")

    # Step 1: Load data
    articles = load_wikipedia_articles()
    questions = load_questions()

    # Combine
    all_items = articles + questions
    all_texts = [item['text'] for item in all_items]

    print(f"\nTotal items to embed: {len(all_items)}")

    # Step 2: Generate embeddings
    embeddings = generate_embeddings_nemotron(all_texts)

    # Step 3: Compute UMAP
    coords_2d, reducer = compute_umap_embeddings(embeddings)

    # Step 4: Save
    knowledge_map = save_knowledge_map(all_items, embeddings, coords_2d, reducer)

    print("\n" + "="*80)
    print("✓ Knowledge map built successfully!")
    print("="*80)
    print("\nNext steps:")
    print("  1. Use knowledge_map.pkl for KNN-based label generation")
    print("  2. Update heatmap to zoom on question region")
    print("  3. Generate cell labels from nearest Wikipedia articles")

if __name__ == '__main__':
    main()
