#!/usr/bin/env python3
"""
Build knowledge map with Wikipedia articles + questions using nvidia/nemotron embeddings.

Improved version with:
- Proper hypertools numpy array handling
- Separate embedding caching (embeddings.pkl)
- Separate UMAP caching (umap_coords.pkl)
- Resume capability at each stage

Dataset Strategy:
  - Hypertools wiki: Hand-curated subset spanning diverse content areas (quality breadth)
  - 250,000 Dropbox articles: Random sample from Wikipedia (quantity depth)
  - 10 quiz questions: Target items to map
  - Total: ~253,000+ items providing rich semantic coverage

Steps:
1. Load ALL articles from hypertools + dropbox (no sampling - use everything)
2. Load questions from questions.json
3. Generate embeddings using nvidia/llama-embed-nemotron-8b (4096-dim) → save to embeddings.pkl
4. Compute UMAP on combined dataset (~250k points) → save to umap_coords.pkl
5. Save final knowledge_map.pkl with everything

Resource Requirements:
  - Memory: ~40GB RAM (250k × 4096-dim × 4 bytes ≈ 4GB embeddings + UMAP overhead)
  - Time: 2-6 hours depending on hardware (GPU vs CPU)
  - Disk: ~3-5GB for embeddings.pkl, ~500MB for umap_coords.pkl, ~3-5GB for knowledge_map.pkl
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
    Load ALL Wikipedia articles from wikipedia.pkl (no sampling).

    This will load ~250k articles from the Dropbox pickle file.
    Expected: 250,000 articles with proper structure (title, text, url, id).

    Note: Hypertools wiki dataset (3,136 articles) has been removed because:
    - No article titles or metadata (just raw text)
    - Only 1.2% of our dataset size
    - See notes/hypertools-wiki-dataset.md for details
    """
    print("="*80)
    print("Loading Wikipedia Articles from wikipedia.pkl")
    print("="*80)

    articles = []

    # Load from Dropbox pickle file (250k articles - USE ALL OF THEM)
    print("\nLoading ALL articles from wikipedia.pkl...")
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

    print(f"\n✓ Loaded {len(question_items)} questions")
    return question_items

def load_precomputed_embeddings():
    """
    Load precomputed embeddings for Wikipedia articles and questions.

    Returns:
        tuple: (combined_embeddings, article_count, question_count)
    """
    print("\n" + "="*80)
    print("Loading Precomputed Embeddings")
    print("="*80)

    # Load Wikipedia embeddings
    print("\nLoading Wikipedia embeddings from embeddings/wikipedia_embeddings.pkl...")
    with open('embeddings/wikipedia_embeddings.pkl', 'rb') as f:
        wiki_data = pickle.load(f)
    wiki_embeddings = wiki_data['embeddings']
    print(f"  ✓ Loaded {wiki_embeddings.shape[0]:,} Wikipedia article embeddings (dim={wiki_embeddings.shape[1]})")

    # Load question embeddings
    print("\nLoading question embeddings from embeddings/question_embeddings.pkl...")
    with open('embeddings/question_embeddings.pkl', 'rb') as f:
        q_data = pickle.load(f)
    question_embeddings = q_data['embeddings']
    print(f"  ✓ Loaded {question_embeddings.shape[0]} question embeddings (dim={question_embeddings.shape[1]})")

    # Verify dimensions match
    if wiki_embeddings.shape[1] != question_embeddings.shape[1]:
        raise ValueError(f"Embedding dimension mismatch: Wikipedia={wiki_embeddings.shape[1]}, Questions={question_embeddings.shape[1]}")

    # Combine embeddings (articles first, then questions)
    combined_embeddings = np.vstack([wiki_embeddings, question_embeddings])
    print(f"\n✓ Combined embeddings shape: {combined_embeddings.shape}")
    print(f"  Articles: {wiki_embeddings.shape[0]:,}")
    print(f"  Questions: {question_embeddings.shape[0]}")

    return combined_embeddings, wiki_embeddings.shape[0], question_embeddings.shape[0]

def generate_embeddings_qwen(texts, batch_size=32, cache_file='embeddings.pkl'):
    """
    Generate embeddings using Qwen/Qwen3-Embedding-0.6B.

    This is a ~600M parameter model optimized for efficient embedding generation.
    Embedding dimension: 1024 (good balance of quality and efficiency)

    Caches embeddings to cache_file for fast resume.
    """
    print("\n" + "="*80)
    print("Generating Embeddings with Qwen/Qwen3-Embedding-0.6B")
    print("="*80)

    # Check if embeddings already exist
    if os.path.exists(cache_file):
        print(f"\n✓ Found cached embeddings in {cache_file}")
        print(f"  Loading cached embeddings...")
        with open(cache_file, 'rb') as f:
            cached_data = pickle.load(f)

        embeddings = cached_data['embeddings']
        print(f"  ✓ Loaded {embeddings.shape[0]:,} embeddings (dim={embeddings.shape[1]})")

        # Verify count matches
        if embeddings.shape[0] == len(texts):
            print(f"  ✓ Count matches - using cached embeddings")
            return embeddings
        else:
            print(f"  ⚠  Count mismatch (cached: {embeddings.shape[0]}, needed: {len(texts)})")
            print(f"  Regenerating embeddings...")

    from sentence_transformers import SentenceTransformer
    import torch

    # Force CPU for compatibility (MPS has tensor size limitations)
    if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        print("\n⚠️  Disabling MPS (Apple GPU) due to tensor size limitations")
        print("   Using CPU instead (will be slower but more compatible)")
        device = 'cpu'
    else:
        device = None  # Let sentence-transformers auto-detect

    print("\nLoading Qwen3 embedding model...")
    model = SentenceTransformer('Qwen/Qwen3-Embedding-0.6B', trust_remote_code=True, device=device)

    print(f"✓ Model loaded. Embedding dimension: {model.get_sentence_embedding_dimension()}")
    print(f"\nGenerating embeddings for {len(texts):,} items...")
    print(f"Batch size: {batch_size}")
    print(f"This will take 1-4 hours depending on hardware...")

    # Generate embeddings with reasonable batch size
    # Qwen3-Embedding-0.6B is much smaller than nemotron, can use larger batches
    actual_batch_size = batch_size
    embeddings = []
    start_time = datetime.now()

    for i in range(0, len(texts), actual_batch_size):
        batch = texts[i:i+actual_batch_size]

        # Progress update every 100 batches or at milestones
        if i % (actual_batch_size * 100) == 0 or i == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            if i > 0:
                rate = i / elapsed
                remaining = (len(texts) - i) / rate
                print(f"  Progress: {i:,}/{len(texts):,} ({i/len(texts)*100:.1f}%) - "
                      f"Rate: {rate:.1f} items/sec - ETA: {remaining/3600:.1f}h")
            else:
                print(f"  Progress: {i:,}/{len(texts):,} ({i/len(texts)*100:.1f}%)")

        # Encode with convert_to_numpy=True to get numpy immediately
        batch_embeddings = model.encode(batch, show_progress_bar=False, convert_to_numpy=True)
        embeddings.append(batch_embeddings)

        # Save checkpoint every 10k items (reduced from 50k for better recovery)
        if i > 0 and i % 10000 == 0:
            checkpoint_file = f'embeddings_checkpoint_{i}.pkl'
            # Convert list of arrays to single array for checkpoint
            embeddings_so_far = np.vstack(embeddings)
            with open(checkpoint_file, 'wb') as f:
                pickle.dump({
                    'embeddings': embeddings_so_far,
                    'count': len(embeddings_so_far),
                    'timestamp': datetime.now().isoformat()
                }, f)
            print(f"  → Saved checkpoint to {checkpoint_file}")

            # Clear old checkpoint to save disk space
            prev_checkpoint = f'embeddings_checkpoint_{i-10000}.pkl'
            if os.path.exists(prev_checkpoint):
                os.remove(prev_checkpoint)

    # Convert list of arrays to single numpy array
    embeddings = np.vstack(embeddings)

    total_time = (datetime.now() - start_time).total_seconds()
    print(f"\n✓ Generated embeddings shape: {embeddings.shape}")
    print(f"  Total time: {total_time/3600:.2f}h ({total_time/60:.1f}min)")
    print(f"  Rate: {len(texts)/total_time:.1f} items/sec")

    # Save embeddings
    print(f"\nSaving embeddings to {cache_file}...")
    with open(cache_file, 'wb') as f:
        pickle.dump({
            'embeddings': embeddings,
            'count': len(embeddings),
            'model': 'nvidia/llama-embed-nemotron-8b',
            'dimension': embeddings.shape[1],
            'timestamp': datetime.now().isoformat()
        }, f)

    file_size = os.path.getsize(cache_file) / 1024 / 1024
    print(f"✓ Saved embeddings ({file_size:.1f} MB)")

    return embeddings

def compute_umap_embeddings(embeddings, n_components=2, n_neighbors=15, min_dist=0.1,
                            cache_file='umap_coords.pkl'):
    """
    Compute UMAP 2D projection.

    Caches UMAP coordinates and reducer for fast resume.
    """
    print("\n" + "="*80)
    print("Computing UMAP Projection")
    print("="*80)

    # Check if UMAP coords already exist
    if os.path.exists(cache_file):
        print(f"\n✓ Found cached UMAP coordinates in {cache_file}")
        print(f"  Loading cached coordinates...")
        with open(cache_file, 'rb') as f:
            cached_data = pickle.load(f)

        coords_2d = cached_data['coords_2d']
        reducer = cached_data['reducer']
        print(f"  ✓ Loaded coordinates shape: {coords_2d.shape}")

        # Verify count matches
        if coords_2d.shape[0] == embeddings.shape[0]:
            print(f"  ✓ Count matches - using cached UMAP")
            return coords_2d, reducer
        else:
            print(f"  ⚠  Count mismatch (cached: {coords_2d.shape[0]}, needed: {embeddings.shape[0]})")
            print(f"  Recomputing UMAP...")

    import umap

    print(f"\nParameters:")
    print(f"  n_components: {n_components}")
    print(f"  n_neighbors: {n_neighbors}")
    print(f"  min_dist: {min_dist}")
    print(f"  metric: cosine")

    reducer = umap.UMAP(
        n_components=n_components,
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        metric='cosine',
        random_state=42,
        verbose=True
    )

    print(f"\nFitting UMAP on {embeddings.shape[0]:,} points...")
    print(f"This will take 10-60 minutes depending on hardware...")

    start_time = datetime.now()
    coords_2d = reducer.fit_transform(embeddings)
    total_time = (datetime.now() - start_time).total_seconds()

    print(f"\n✓ UMAP coordinates shape: {coords_2d.shape}")
    print(f"  Total time: {total_time/60:.1f}min")
    print(f"\nCoordinate ranges:")
    print(f"  X: [{coords_2d[:, 0].min():.3f}, {coords_2d[:, 0].max():.3f}]")
    print(f"  Y: [{coords_2d[:, 1].min():.3f}, {coords_2d[:, 1].max():.3f}]")

    # Save UMAP results
    print(f"\nSaving UMAP coordinates to {cache_file}...")
    with open(cache_file, 'wb') as f:
        pickle.dump({
            'coords_2d': coords_2d,
            'reducer': reducer,
            'params': {
                'n_components': n_components,
                'n_neighbors': n_neighbors,
                'min_dist': min_dist,
                'metric': 'cosine'
            },
            'timestamp': datetime.now().isoformat()
        }, f)

    file_size = os.path.getsize(cache_file) / 1024 / 1024
    print(f"✓ Saved UMAP coordinates ({file_size:.1f} MB)")

    return coords_2d, reducer

def save_question_coordinates(question_items, coords_2d, article_count, output_file='data/question_coordinates.pkl'):
    """
    Save question coordinates to separate file.

    Args:
        question_items: List of question dictionaries
        coords_2d: Full UMAP coordinates (articles + questions)
        article_count: Number of articles (questions start at this index)
        output_file: Output pickle file path
    """
    print("\n" + "="*80)
    print("Saving Question Coordinates")
    print("="*80)

    # Extract question coordinates (they come after articles)
    question_coords = coords_2d[article_count:, :]

    # Normalize to [0, 1]
    x_min, x_max = coords_2d[:, 0].min(), coords_2d[:, 0].max()
    y_min, y_max = coords_2d[:, 1].min(), coords_2d[:, 1].max()

    coords_normalized = np.zeros_like(question_coords)
    coords_normalized[:, 0] = (question_coords[:, 0] - x_min) / (x_max - x_min)
    coords_normalized[:, 1] = (question_coords[:, 1] - y_min) / (y_max - y_min)

    # Compute bounds for question region
    q_x_min, q_x_max = coords_normalized[:, 0].min(), coords_normalized[:, 0].max()
    q_y_min, q_y_max = coords_normalized[:, 1].min(), coords_normalized[:, 1].max()

    question_data = {
        'coordinates': coords_normalized,
        'questions': [q['question_data'] for q in question_items],
        'bounds': {
            'x_min': float(q_x_min),
            'x_max': float(q_x_max),
            'y_min': float(q_y_min),
            'y_max': float(q_y_max)
        },
        'global_bounds': {
            'x_min': float(x_min),
            'x_max': float(x_max),
            'y_min': float(y_min),
            'y_max': float(y_max)
        },
        'timestamp': datetime.now().isoformat()
    }

    print(f"\nQuestion coordinate statistics:")
    print(f"  Total questions: {len(question_items)}")
    print(f"  Coordinate range (normalized):")
    print(f"    X: [{q_x_min:.3f}, {q_x_max:.3f}]")
    print(f"    Y: [{q_y_min:.3f}, {q_y_max:.3f}]")

    print(f"\nSaving to {output_file}...")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'wb') as f:
        pickle.dump(question_data, f)

    file_size = os.path.getsize(output_file) / 1024
    print(f"✓ Saved ({file_size:.1f} KB)")

    return question_data

def update_umap_bounds(coords_2d, article_count, output_file='data/umap_bounds.pkl'):
    """
    Update UMAP bounds to include both articles and questions.

    Args:
        coords_2d: Full UMAP coordinates (articles + questions)
        article_count: Number of articles (questions start at this index)
        output_file: Output pickle file path
    """
    print("\n" + "="*80)
    print("Updating UMAP Bounds")
    print("="*80)

    # Compute global bounds (all points)
    x_min, x_max = coords_2d[:, 0].min(), coords_2d[:, 0].max()
    y_min, y_max = coords_2d[:, 1].min(), coords_2d[:, 1].max()

    # Compute article-only bounds
    article_coords = coords_2d[:article_count, :]
    a_x_min, a_x_max = article_coords[:, 0].min(), article_coords[:, 0].max()
    a_y_min, a_y_max = article_coords[:, 1].min(), article_coords[:, 1].max()

    # Compute question-only bounds
    question_coords = coords_2d[article_count:, :]
    q_x_min, q_x_max = question_coords[:, 0].min(), question_coords[:, 0].max()
    q_y_min, q_y_max = question_coords[:, 1].min(), question_coords[:, 1].max()

    bounds_data = {
        'global': {
            'x_min': float(x_min),
            'x_max': float(x_max),
            'y_min': float(y_min),
            'y_max': float(y_max)
        },
        'articles': {
            'x_min': float(a_x_min),
            'x_max': float(a_x_max),
            'y_min': float(a_y_min),
            'y_max': float(a_y_max)
        },
        'questions': {
            'x_min': float(q_x_min),
            'x_max': float(q_x_max),
            'y_min': float(q_y_min),
            'y_max': float(q_y_max)
        },
        'timestamp': datetime.now().isoformat()
    }

    print(f"\nBounds summary:")
    print(f"  Global: X=[{x_min:.3f}, {x_max:.3f}], Y=[{y_min:.3f}, {y_max:.3f}]")
    print(f"  Articles: X=[{a_x_min:.3f}, {a_x_max:.3f}], Y=[{a_y_min:.3f}, {a_y_max:.3f}]")
    print(f"  Questions: X=[{q_x_min:.3f}, {q_x_max:.3f}], Y=[{q_y_min:.3f}, {q_y_max:.3f}]")

    print(f"\nSaving to {output_file}...")
    with open(output_file, 'wb') as f:
        pickle.dump(bounds_data, f)

    file_size = os.path.getsize(output_file) / 1024
    print(f"✓ Saved ({file_size:.1f} KB)")

    return bounds_data

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
    print(f"  Total items: {len(items):,}")
    print(f"  Questions: {len(question_indices)}")
    print(f"  Articles: {len(article_indices):,}")
    print(f"  Embedding dimension: {embeddings.shape[1]}")
    print(f"\nQuestion region (with {int(padding*100)}% padding):")
    print(f"  X: [{q_x_min:.3f}, {q_x_max:.3f}]")
    print(f"  Y: [{q_y_min:.3f}, {q_y_max:.3f}]")

    print(f"\nSaving to {output_file}...")
    with open(output_file, 'wb') as f:
        pickle.dump(knowledge_map, f)

    file_size = os.path.getsize(output_file) / 1024 / 1024
    print(f"✓ Saved ({file_size:.1f} MB)")

    return knowledge_map

def main():
    print("\n" + "="*80)
    print("WIKIPEDIA KNOWLEDGE MAP BUILDER V2")
    print("="*80)
    print("\nBuilding knowledge map with:")
    print("  - Wikipedia articles (precomputed embeddings)")
    print("  - Quiz questions (precomputed embeddings)")
    print("  - Combined UMAP 2D projection")
    print("\nThis version uses precomputed embeddings from:")
    print("  - embeddings/wikipedia_embeddings.pkl")
    print("  - embeddings/question_embeddings.pkl")

    # Step 1: Load precomputed embeddings
    combined_embeddings, article_count, question_count = load_precomputed_embeddings()

    # Step 2: Load metadata for articles and questions
    articles = load_wikipedia_articles()
    questions = load_questions()

    # Verify counts match
    if len(articles) != article_count:
        print(f"\n⚠ Warning: Article count mismatch (loaded: {len(articles)}, expected: {article_count})")
        print("  Using first {article_count} articles to match embeddings")
        articles = articles[:article_count]

    if len(questions) != question_count:
        raise ValueError(f"Question count mismatch: loaded={len(questions)}, expected={question_count}")

    # Combine items
    all_items = articles + questions

    print(f"\n✓ Total items: {len(all_items):,} (articles: {article_count:,}, questions: {question_count})")

    # Step 3: Compute UMAP on combined embeddings (with caching)
    coords_2d, reducer = compute_umap_embeddings(combined_embeddings, cache_file='umap_coords.pkl')

    # Step 4: Save question coordinates separately
    question_data = save_question_coordinates(questions, coords_2d, article_count)

    # Step 5: Update UMAP bounds to include questions
    bounds_data = update_umap_bounds(coords_2d, article_count)

    # Step 6: Save final knowledge map
    knowledge_map = save_knowledge_map(all_items, combined_embeddings, coords_2d, reducer)

    print("\n" + "="*80)
    print("✓ Knowledge map built successfully!")
    print("="*80)
    print("\nGenerated files:")
    print("  - umap_coords.pkl: UMAP coordinates for all items")
    print("  - data/question_coordinates.pkl: Question coordinates and bounds")
    print("  - data/umap_bounds.pkl: Updated bounds including questions")
    print("  - knowledge_map.pkl: Final knowledge map")
    print("\nNext steps:")
    print("  1. Use question_coordinates.pkl for visualization")
    print("  2. Update heatmap to zoom on question region")
    print("  3. Generate cell labels from nearest Wikipedia articles")

if __name__ == '__main__':
    main()
