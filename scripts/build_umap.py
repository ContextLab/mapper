#!/usr/bin/env python3
"""
Build UMAP projections by projecting ALL content types TOGETHER.

CRITICAL: All four embedding types are projected in ONE batch to ensure they
share exactly the same 2D coordinate space. This is essential for:
  - Questions appearing at semantically correct positions among articles
  - Video transcripts/windows landing near related articles
  - Bounding box calculations based on question positions
  - Consistent coordinate system across the entire visualization

Steps:
  1. Load article embeddings (250K x 768, google/embeddinggemma-300m)
  2. Load question embeddings (2,500 x 768, same model)
  3. Load transcript embeddings (~4,386 academic x 768, same model)
  4. Load window embeddings (~63K academic windows x 768, same model)
  5. Concatenate into single matrix and fit_transform UMAP on ALL points
  6. Split back into article, question, transcript, and window coordinates
  7. Normalize everything to [0, 1]
  8. Save reducer, coordinates, bounds

Input:
  - embeddings/wikipedia_embeddings.pkl (250K articles)
  - embeddings/question_embeddings_2500.pkl (2,500 questions)
  - embeddings/transcript_embeddings.pkl (5,407 transcripts, filtered to academic)
  - data/videos/.working/embeddings/{video_id}.npy (per-video window embeddings)
  - embeddings/video_audit_results.json (academic/non-academic classification)

Output:
  - embeddings/umap_reducer.pkl
  - embeddings/umap_article_coords.pkl
  - embeddings/umap_question_coords.pkl
  - embeddings/umap_transcript_coords.pkl
  - embeddings/umap_window_coords.pkl
  - embeddings/umap_bounds.pkl

Usage:
    python scripts/build_umap.py

Note: pickle is used intentionally for numpy array serialization. All .pkl
files are generated locally by our own pipeline scripts.
"""

import json
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
WINDOW_EMB_DIR = PROJECT_ROOT / "data" / "videos" / ".working" / "embeddings"
AUDIT_PATH = EMBEDDINGS_DIR / "video_audit_results.json"


def main():
    print("=" * 70)
    print("UMAP BUILD (Articles + Questions + Transcripts + Windows)")
    print("=" * 70)
    print(f"Started: {datetime.now()}")
    print()

    # ── Load video audit (academic IDs) ──
    print("Loading video audit results...")
    with open(AUDIT_PATH) as f:
        audit = json.load(f)
    academic_ids = set(audit["academic_ids"])
    print(f"  Academic videos: {len(academic_ids)}")
    print(f"  Non-academic (excluded): {audit['non_academic_count']}")

    # ── Step 1: Load article embeddings ──
    print("\nStep 1: Loading article embeddings...")
    with open(EMBEDDINGS_DIR / "wikipedia_embeddings.pkl", "rb") as f:
        wiki_data = pickle.load(f)

    article_embeddings = wiki_data["embeddings"]
    article_model = wiki_data.get("model", "unknown")
    n_articles = len(article_embeddings)
    print(f"  Articles: {article_embeddings.shape} (model: {article_model})")

    nan_mask = np.isnan(article_embeddings).any(axis=1)
    nan_count = int(nan_mask.sum())
    if nan_count > 0:
        print(f"  Warning: {nan_count:,} rows have NaN ({nan_count / len(article_embeddings) * 100:.1f}%)")
        print(f"  Replacing NaN rows with zero vectors for UMAP stability")
        article_embeddings = article_embeddings.copy()
        article_embeddings[nan_mask] = 0.0

    # ── Step 2: Load question embeddings ──
    print("\nStep 2: Loading question embeddings...")

    question_file_candidates = [
        "question_embeddings_2500.pkl",
        "question_embeddings_949.pkl",
        "question_embeddings.pkl",
    ]
    q_data = None
    for fname in question_file_candidates:
        fpath = EMBEDDINGS_DIR / fname
        if fpath.exists():
            with open(fpath, "rb") as f:
                q_data = pickle.load(f)
            print(f"  Loaded from: {fname}")
            break

    if q_data is None:
        print(f"  ERROR: No question embeddings found. Tried: {question_file_candidates}")
        print(f"  Run embed_questions.py first.")
        sys.exit(1)

    question_embeddings = q_data["embeddings"]
    question_ids = q_data["question_ids"]
    question_model = q_data.get("model", "unknown")
    n_questions = len(question_embeddings)
    print(f"  Questions: {question_embeddings.shape} (model: {question_model})")

    if article_model != "unknown" and question_model != "unknown":
        assert article_model == question_model, (
            f"Model mismatch! Articles: {article_model}, Questions: {question_model}"
        )
        print(f"  Model match confirmed: {article_model}")

    # ── Step 3: Load transcript embeddings (academic only) ──
    print("\nStep 3: Loading transcript embeddings (academic only)...")
    with open(EMBEDDINGS_DIR / "transcript_embeddings.pkl", "rb") as f:
        t_data = pickle.load(f)

    all_transcript_emb = t_data["embeddings"]
    all_video_ids = t_data["video_ids"]
    transcript_model = t_data.get("model", "unknown")
    print(f"  All transcripts: {all_transcript_emb.shape} (model: {transcript_model})")

    academic_mask = np.array([vid in academic_ids for vid in all_video_ids])
    transcript_embeddings = all_transcript_emb[academic_mask]
    transcript_video_ids = [vid for vid, keep in zip(all_video_ids, academic_mask) if keep]
    n_transcripts = len(transcript_embeddings)
    print(f"  Academic transcripts: {transcript_embeddings.shape}")
    print(f"  Filtered out: {len(all_transcript_emb) - n_transcripts} non-academic")

    if transcript_model != "unknown" and article_model != "unknown":
        assert transcript_model == article_model, (
            f"Model mismatch! Articles: {article_model}, Transcripts: {transcript_model}"
        )

    # ── Step 4: Load window embeddings (academic only) ──
    print("\nStep 4: Loading window embeddings (academic only)...")
    window_emb_list = []
    window_video_ids = []
    window_indices = []
    window_offsets = {}
    skipped_missing = 0

    for vid in sorted(academic_ids):
        npy_path = WINDOW_EMB_DIR / f"{vid}.npy"
        if not npy_path.exists():
            skipped_missing += 1
            continue
        emb = np.load(npy_path)
        start_idx = sum(e.shape[0] for e in window_emb_list)
        window_offsets[vid] = (start_idx, emb.shape[0])
        window_emb_list.append(emb)
        window_video_ids.extend([vid] * emb.shape[0])
        window_indices.extend(range(emb.shape[0]))

    if window_emb_list:
        window_embeddings = np.vstack(window_emb_list).astype(np.float32)
    else:
        window_embeddings = np.zeros((0, 768), dtype=np.float32)

    n_windows = len(window_embeddings)
    print(f"  Academic windows: {window_embeddings.shape}")
    if skipped_missing:
        print(f"  Skipped (no .npy file): {skipped_missing}")
    print(f"  Videos with windows: {len(window_offsets)}")

    # ── Step 5: JOINT UMAP projection ──
    total_points = n_articles + n_questions + n_transcripts + n_windows
    print(f"\nStep 5: Joint UMAP projection...")
    print(f"  Articles:    {n_articles:>10,}")
    print(f"  Questions:   {n_questions:>10,}")
    print(f"  Transcripts: {n_transcripts:>10,}")
    print(f"  Windows:     {n_windows:>10,}")
    print(f"  TOTAL:       {total_points:>10,}")
    print(f"  Memory: ~{total_points * 768 * 4 / 1e9:.2f} GB")
    print("  This will take 30-60 minutes...")

    combined_embeddings = np.vstack([
        article_embeddings,
        question_embeddings,
        transcript_embeddings,
        window_embeddings,
    ])
    print(f"  Combined shape: {combined_embeddings.shape}")

    import umap

    umap_params = {
        "n_neighbors": 15,
        "min_dist": 0.1,
        "n_components": 2,
        "metric": "cosine",
        "random_state": 42,
    }
    print(f"  UMAP params: {umap_params}")

    umap_start = time.time()
    reducer = umap.UMAP(**umap_params)
    combined_coords_raw = reducer.fit_transform(combined_embeddings)
    umap_time = time.time() - umap_start

    print(f"  UMAP complete in {umap_time / 60:.1f} min")
    print(f"  Output shape: {combined_coords_raw.shape}")

    # ── Step 6: Split back into 4 types ──
    print(f"\nStep 6: Splitting coordinates...")
    a_end = n_articles
    q_end = a_end + n_questions
    t_end = q_end + n_transcripts

    article_coords_raw = combined_coords_raw[:a_end]
    question_coords_raw = combined_coords_raw[a_end:q_end]
    transcript_coords_raw = combined_coords_raw[q_end:t_end]
    window_coords_raw = combined_coords_raw[t_end:]

    for label, c in [("Articles", article_coords_raw), ("Questions", question_coords_raw),
                      ("Transcripts", transcript_coords_raw), ("Windows", window_coords_raw)]:
        print(f"  {label}: {c.shape}  x=[{c[:, 0].min():.2f}, {c[:, 0].max():.2f}] y=[{c[:, 1].min():.2f}, {c[:, 1].max():.2f}]")

    # ── Step 7: Normalize to [0, 1] ──
    print("\nStep 7: Normalizing coordinates to [0, 1]...")

    x_min = combined_coords_raw[:, 0].min()
    x_max = combined_coords_raw[:, 0].max()
    y_min = combined_coords_raw[:, 1].min()
    y_max = combined_coords_raw[:, 1].max()
    x_range = x_max - x_min
    y_range = y_max - y_min

    margin = 0.01
    x_min -= x_range * margin
    x_max += x_range * margin
    y_min -= y_range * margin
    y_max += y_range * margin
    x_range = x_max - x_min
    y_range = y_max - y_min

    def normalize(raw):
        out = np.zeros_like(raw)
        out[:, 0] = (raw[:, 0] - x_min) / x_range
        out[:, 1] = (raw[:, 1] - y_min) / y_range
        return np.clip(out, 0.0, 1.0)

    article_coords = normalize(article_coords_raw)
    question_coords = normalize(question_coords_raw)
    transcript_coords = normalize(transcript_coords_raw)
    window_coords = normalize(window_coords_raw)

    for label, c in [("Articles", article_coords), ("Questions", question_coords),
                      ("Transcripts", transcript_coords), ("Windows", window_coords)]:
        print(f"  {label} [0,1]: x=[{c[:, 0].min():.4f}, {c[:, 0].max():.4f}] y=[{c[:, 1].min():.4f}, {c[:, 1].max():.4f}]")

    # ── Step 8: Save everything ──
    print("\nStep 8: Saving outputs...")

    bounds = {
        "x_min": float(x_min), "x_max": float(x_max),
        "y_min": float(y_min), "y_max": float(y_max),
        "x_range": float(x_range), "y_range": float(y_range),
        "margin": margin,
        "n_articles": n_articles, "n_questions": n_questions,
        "n_transcripts": n_transcripts, "n_windows": n_windows,
        "timestamp": datetime.now().isoformat(),
    }

    reducer_path = EMBEDDINGS_DIR / "umap_reducer.pkl"
    with open(reducer_path, "wb") as f:
        pickle.dump(reducer, f)
    print(f"  Reducer: {reducer_path} ({reducer_path.stat().st_size / 1024 / 1024:.1f} MB)")

    article_path = EMBEDDINGS_DIR / "umap_article_coords.pkl"
    with open(article_path, "wb") as f:
        pickle.dump({
            "coords": article_coords, "coords_raw": article_coords_raw,
            "titles": wiki_data.get("titles", []),
            "num_articles": len(article_coords),
            "timestamp": datetime.now().isoformat(),
        }, f)
    print(f"  Article coords: {article_path} ({article_path.stat().st_size / 1024 / 1024:.1f} MB)")

    question_path = EMBEDDINGS_DIR / "umap_question_coords.pkl"
    with open(question_path, "wb") as f:
        pickle.dump({
            "coords": question_coords, "coords_raw": question_coords_raw,
            "question_ids": question_ids,
            "num_questions": len(question_coords),
            "timestamp": datetime.now().isoformat(),
        }, f)
    print(f"  Question coords: {question_path} ({question_path.stat().st_size / 1024:.0f} KB)")

    transcript_path = EMBEDDINGS_DIR / "umap_transcript_coords.pkl"
    with open(transcript_path, "wb") as f:
        pickle.dump({
            "coords": transcript_coords, "coords_raw": transcript_coords_raw,
            "video_ids": transcript_video_ids,
            "num_transcripts": len(transcript_coords),
            "timestamp": datetime.now().isoformat(),
        }, f)
    print(f"  Transcript coords: {transcript_path} ({transcript_path.stat().st_size / 1024:.0f} KB)")

    window_path = EMBEDDINGS_DIR / "umap_window_coords.pkl"
    with open(window_path, "wb") as f:
        pickle.dump({
            "coords": window_coords, "coords_raw": window_coords_raw,
            "video_ids": window_video_ids,
            "window_indices": window_indices,
            "window_offsets": window_offsets,
            "num_windows": len(window_coords),
            "timestamp": datetime.now().isoformat(),
        }, f)
    print(f"  Window coords: {window_path} ({window_path.stat().st_size / 1024 / 1024:.1f} MB)")

    bounds_path = EMBEDDINGS_DIR / "umap_bounds.pkl"
    with open(bounds_path, "wb") as f:
        pickle.dump(bounds, f)
    print(f"  Bounds: {bounds_path}")

    # ── Summary ──
    print(f"\n{'=' * 70}")
    print("UMAP JOINT PROJECTION COMPLETE")
    print(f"{'=' * 70}")
    print(f"  Articles:    {n_articles:>10,} points")
    print(f"  Questions:   {n_questions:>10,} points")
    print(f"  Transcripts: {n_transcripts:>10,} points")
    print(f"  Windows:     {n_windows:>10,} points")
    print(f"  Total:       {total_points:>10,}")
    print(f"  Model: {article_model}")
    print(f"  UMAP time: {umap_time / 60:.1f} min")
    print(f"  Bounds: x=[{bounds['x_min']:.2f}, {bounds['x_max']:.2f}] y=[{bounds['y_min']:.2f}, {bounds['y_max']:.2f}]")
    print(f"  Finished: {datetime.now()}")
    print()
    print("Next steps:")
    print("  1. Run scripts/flatten_coordinates.py --mu 0.75")
    print("  2. Run scripts/compute_bounding_boxes.py")
    print("  3. Run scripts/export_coords_to_domains.py")


if __name__ == "__main__":
    main()
