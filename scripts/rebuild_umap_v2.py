#!/usr/bin/env python3
"""
Rebuild UMAP projections from article embeddings and transform question
embeddings into the same 2D space.

This ensures articles and questions share the same coordinate system.

Steps:
  1. Load article embeddings (250K × 768, google/embeddinggemma-300m)
  2. Fit UMAP on article embeddings only
  3. Load question embeddings (949 × 768, same model)
  4. Transform question embeddings through fitted UMAP
  5. Normalize everything to [0, 1]
  6. Save reducer, coordinates, bounds

Input:
  - embeddings/wikipedia_embeddings.pkl (250K articles)
  - embeddings/question_embeddings_949.pkl (949 questions)

Output:
  - embeddings/umap_reducer.pkl — trained UMAP model
  - embeddings/umap_article_coords.pkl — (250K, 2) normalized article coords
  - embeddings/umap_question_coords.pkl — (949, 2) normalized question coords
  - embeddings/umap_bounds.pkl — coordinate bounds for normalization

Usage:
    python scripts/rebuild_umap_v2.py
"""

import os
import sys
import time
import pickle
import numpy as np
from pathlib import Path
from datetime import datetime

# macOS threading fix
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

PROJECT_ROOT = Path(__file__).parent.parent
EMBEDDINGS_DIR = PROJECT_ROOT / "embeddings"


def main():
    print("=" * 70)
    print("UMAP REBUILD (Articles + Questions)")
    print("=" * 70)
    print(f"Started: {datetime.now()}")
    print()

    # ── Step 1: Load article embeddings ──
    print("Step 1: Loading article embeddings...")
    with open(EMBEDDINGS_DIR / "wikipedia_embeddings.pkl", "rb") as f:
        wiki_data = pickle.load(f)

    article_embeddings = wiki_data["embeddings"]
    article_model = wiki_data.get("model", "unknown")
    print(f"  Articles: {article_embeddings.shape} (model: {article_model})")

    nan_mask = np.isnan(article_embeddings).any(axis=1)
    nan_count = int(nan_mask.sum())
    if nan_count > 0:
        print(
            f"  ⚠ {nan_count:,} rows have NaN ({nan_count / len(article_embeddings) * 100:.1f}%)"
        )
        print(f"  Replacing NaN rows with zero vectors for UMAP stability")
        article_embeddings = article_embeddings.copy()
        article_embeddings[nan_mask] = 0.0

    # ── Step 2: Fit UMAP on articles ──
    print("\nStep 2: Fitting UMAP on article embeddings...")
    print("  This will take 30-60 minutes for 250K articles...")

    import umap

    umap_params = {
        "n_neighbors": 15,
        "min_dist": 0.1,
        "n_components": 2,
        "metric": "cosine",
        "random_state": 42,
    }
    print(f"  Params: {umap_params}")

    umap_start = time.time()
    reducer = umap.UMAP(**umap_params)
    article_coords_raw = reducer.fit_transform(article_embeddings)
    umap_time = time.time() - umap_start

    print(f"  UMAP complete in {umap_time / 60:.1f} min")
    print(f"  Article coords shape: {article_coords_raw.shape}")
    print(
        f"  Raw range: x=[{article_coords_raw[:, 0].min():.2f}, {article_coords_raw[:, 0].max():.2f}] "
        f"y=[{article_coords_raw[:, 1].min():.2f}, {article_coords_raw[:, 1].max():.2f}]"
    )

    # ── Step 3: Load question embeddings ──
    print("\nStep 3: Loading question embeddings...")
    with open(EMBEDDINGS_DIR / "question_embeddings_949.pkl", "rb") as f:
        q_data = pickle.load(f)

    question_embeddings = q_data["embeddings"]
    question_ids = q_data["question_ids"]
    question_model = q_data.get("model", "unknown")
    print(f"  Questions: {question_embeddings.shape} (model: {question_model})")

    # Verify same model
    assert article_model == question_model, (
        f"Model mismatch! Articles: {article_model}, Questions: {question_model}"
    )
    print(f"  ✓ Same model: {article_model}")

    # ── Step 4: Transform questions through UMAP ──
    print("\nStep 4: Transforming question embeddings through UMAP...")
    transform_start = time.time()
    question_coords_raw = reducer.transform(question_embeddings)
    transform_time = time.time() - transform_start

    print(f"  Transform complete in {transform_time:.1f}s")
    print(f"  Question coords shape: {question_coords_raw.shape}")
    print(
        f"  Raw range: x=[{question_coords_raw[:, 0].min():.2f}, {question_coords_raw[:, 0].max():.2f}] "
        f"y=[{question_coords_raw[:, 1].min():.2f}, {question_coords_raw[:, 1].max():.2f}]"
    )

    # ── Step 5: Normalize to [0, 1] ──
    print("\nStep 5: Normalizing coordinates to [0, 1]...")

    # Use article bounds for normalization (articles define the space)
    x_min = article_coords_raw[:, 0].min()
    x_max = article_coords_raw[:, 0].max()
    y_min = article_coords_raw[:, 1].min()
    y_max = article_coords_raw[:, 1].max()
    x_range = x_max - x_min
    y_range = y_max - y_min

    # Add small margin (1%) to avoid points exactly at 0 or 1
    margin = 0.01
    x_min -= x_range * margin
    x_max += x_range * margin
    y_min -= y_range * margin
    y_max += y_range * margin
    x_range = x_max - x_min
    y_range = y_max - y_min

    # Normalize articles
    article_coords = np.zeros_like(article_coords_raw)
    article_coords[:, 0] = (article_coords_raw[:, 0] - x_min) / x_range
    article_coords[:, 1] = (article_coords_raw[:, 1] - y_min) / y_range

    # Normalize questions using SAME bounds
    question_coords = np.zeros_like(question_coords_raw)
    question_coords[:, 0] = (question_coords_raw[:, 0] - x_min) / x_range
    question_coords[:, 1] = (question_coords_raw[:, 1] - y_min) / y_range

    print(
        f"  Article coords [0,1]: x=[{article_coords[:, 0].min():.4f}, {article_coords[:, 0].max():.4f}] "
        f"y=[{article_coords[:, 1].min():.4f}, {article_coords[:, 1].max():.4f}]"
    )
    print(
        f"  Question coords [0,1]: x=[{question_coords[:, 0].min():.4f}, {question_coords[:, 0].max():.4f}] "
        f"y=[{question_coords[:, 1].min():.4f}, {question_coords[:, 1].max():.4f}]"
    )

    # Check if any questions are outside [0, 1] (possible with transform)
    q_outside = np.sum(
        (question_coords[:, 0] < 0)
        | (question_coords[:, 0] > 1)
        | (question_coords[:, 1] < 0)
        | (question_coords[:, 1] > 1)
    )
    if q_outside > 0:
        print(f"  ⚠ {q_outside} questions outside [0,1] — clipping to bounds")
        question_coords = np.clip(question_coords, 0.0, 1.0)

    # ── Step 6: Save everything ──
    print("\nStep 6: Saving outputs...")

    bounds = {
        "x_min": float(x_min),
        "x_max": float(x_max),
        "y_min": float(y_min),
        "y_max": float(y_max),
        "x_range": float(x_range),
        "y_range": float(y_range),
        "margin": margin,
        "timestamp": datetime.now().isoformat(),
    }

    # Save UMAP reducer
    reducer_path = EMBEDDINGS_DIR / "umap_reducer.pkl"
    with open(reducer_path, "wb") as f:
        pickle.dump(reducer, f)
    print(f"  ✓ Reducer: {reducer_path} ({reducer_path.stat().st_size / 1024:.0f} KB)")

    # Save article coordinates
    article_path = EMBEDDINGS_DIR / "umap_article_coords.pkl"
    with open(article_path, "wb") as f:
        pickle.dump(
            {
                "coords": article_coords,
                "coords_raw": article_coords_raw,
                "titles": wiki_data.get("titles", []),
                "num_articles": len(article_coords),
                "timestamp": datetime.now().isoformat(),
            },
            f,
        )
    print(
        f"  ✓ Article coords: {article_path} ({article_path.stat().st_size / 1024 / 1024:.1f} MB)"
    )

    # Save question coordinates
    question_path = EMBEDDINGS_DIR / "umap_question_coords.pkl"
    with open(question_path, "wb") as f:
        pickle.dump(
            {
                "coords": question_coords,
                "coords_raw": question_coords_raw,
                "question_ids": question_ids,
                "num_questions": len(question_coords),
                "timestamp": datetime.now().isoformat(),
            },
            f,
        )
    print(
        f"  ✓ Question coords: {question_path} ({question_path.stat().st_size / 1024:.0f} KB)"
    )

    # Save bounds
    bounds_path = EMBEDDINGS_DIR / "umap_bounds.pkl"
    with open(bounds_path, "wb") as f:
        pickle.dump(bounds, f)
    print(f"  ✓ Bounds: {bounds_path}")

    # ── Summary ──
    print(f"\n{'=' * 70}")
    print("✓ UMAP REBUILD COMPLETE")
    print(f"{'=' * 70}")
    print(f"  Articles: {article_coords.shape[0]:,} points in [0,1]²")
    print(f"  Questions: {question_coords.shape[0]:,} points in [0,1]²")
    print(f"  Model: {article_model}")
    print(f"  UMAP time: {umap_time / 60:.1f} min")
    print(
        f"  Bounds: x=[{bounds['x_min']:.2f}, {bounds['x_max']:.2f}] "
        f"y=[{bounds['y_min']:.2f}, {bounds['y_max']:.2f}]"
    )
    print(f"  Finished: {datetime.now()}")
    print()
    print("Next: Run scripts/assign_domains_rag.py to assign articles to domains")


if __name__ == "__main__":
    main()
