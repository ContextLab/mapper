#!/usr/bin/env python3
"""
Build UMAP projections for the Knowledge Mapper visualization.

Strategies:
  --strategy joint (original):
      fit_transform on ALL 320K points together. Articles dominate the
      nearest-neighbor graph, so niche-domain questions may cluster.

  --strategy questions-first (recommended):
      fit on questions + transcripts + windows (~70K points), then
      transform articles into that space. Gives questions first-class
      neighborhood structure while articles still land semantically.

  --strategy questions-only (fallback):
      fit on just 2,500 questions, then transform everything else.
      Maximum question separation but articles may be less precise.

All strategies produce the same output files in the same format.

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
    python scripts/build_umap.py --strategy questions-first
    python scripts/build_umap.py --strategy questions-only
    python scripts/build_umap.py --strategy joint  # original behavior

Note: pickle is used intentionally for numpy array serialization. All .pkl
files are generated locally by our own pipeline scripts.
"""

import argparse
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


def load_embeddings():
    """Load all four embedding types. Returns dict with embeddings and metadata."""

    # ── Load video audit (academic IDs) ──
    print("Loading video audit results...")
    with open(AUDIT_PATH) as f:
        audit = json.load(f)
    academic_ids = set(audit["academic_ids"])
    print(f"  Academic videos: {len(academic_ids)}")
    print(f"  Non-academic (excluded): {audit['non_academic_count']}")

    # ── Articles ──
    print("\nLoading article embeddings...")
    with open(EMBEDDINGS_DIR / "wikipedia_embeddings.pkl", "rb") as f:
        wiki_data = pickle.load(f)

    article_embeddings = wiki_data["embeddings"]
    article_model = wiki_data.get("model", "unknown")
    print(f"  Articles: {article_embeddings.shape} (model: {article_model})")

    nan_mask = np.isnan(article_embeddings).any(axis=1)
    nan_count = int(nan_mask.sum())
    if nan_count > 0:
        print(f"  Warning: {nan_count:,} NaN rows → replaced with zeros")
        article_embeddings = article_embeddings.copy()
        article_embeddings[nan_mask] = 0.0

    # ── Questions ──
    print("\nLoading question embeddings...")
    q_data = None
    for fname in ["question_embeddings_2500.pkl", "question_embeddings_949.pkl",
                   "question_embeddings.pkl"]:
        fpath = EMBEDDINGS_DIR / fname
        if fpath.exists():
            with open(fpath, "rb") as f:
                q_data = pickle.load(f)
            print(f"  Loaded from: {fname}")
            break

    if q_data is None:
        print("  ERROR: No question embeddings found.")
        sys.exit(1)

    question_embeddings = q_data["embeddings"]
    question_ids = q_data["question_ids"]
    question_model = q_data.get("model", "unknown")
    print(f"  Questions: {question_embeddings.shape} (model: {question_model})")

    if article_model != "unknown" and question_model != "unknown":
        assert article_model == question_model, (
            f"Model mismatch! Articles: {article_model}, Questions: {question_model}"
        )

    # ── Transcripts (academic only) ──
    print("\nLoading transcript embeddings (academic only)...")
    with open(EMBEDDINGS_DIR / "transcript_embeddings.pkl", "rb") as f:
        t_data = pickle.load(f)

    all_transcript_emb = t_data["embeddings"]
    all_video_ids = t_data["video_ids"]
    transcript_model = t_data.get("model", "unknown")

    academic_mask = np.array([vid in academic_ids for vid in all_video_ids])
    transcript_embeddings = all_transcript_emb[academic_mask]
    transcript_video_ids = [vid for vid, keep in zip(all_video_ids, academic_mask) if keep]
    print(f"  Academic transcripts: {transcript_embeddings.shape}")

    # ── Windows (academic only) ──
    print("\nLoading window embeddings (academic only)...")
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

    print(f"  Academic windows: {window_embeddings.shape}")
    if skipped_missing:
        print(f"  Skipped (no .npy file): {skipped_missing}")

    return {
        "article_embeddings": article_embeddings,
        "question_embeddings": question_embeddings,
        "transcript_embeddings": transcript_embeddings,
        "window_embeddings": window_embeddings,
        "question_ids": question_ids,
        "transcript_video_ids": transcript_video_ids,
        "window_video_ids": window_video_ids,
        "window_indices": window_indices,
        "window_offsets": window_offsets,
        "wiki_data": wiki_data,
        "article_model": article_model,
    }


def run_umap_joint(data, umap_params):
    """Original strategy: fit_transform on ALL points together."""
    article_emb = data["article_embeddings"]
    question_emb = data["question_embeddings"]
    transcript_emb = data["transcript_embeddings"]
    window_emb = data["window_embeddings"]

    n_a, n_q, n_t, n_w = len(article_emb), len(question_emb), len(transcript_emb), len(window_emb)
    total = n_a + n_q + n_t + n_w

    print(f"\nStrategy: JOINT (fit_transform on all {total:,} points)")
    print(f"  Articles:    {n_a:>10,}")
    print(f"  Questions:   {n_q:>10,}")
    print(f"  Transcripts: {n_t:>10,}")
    print(f"  Windows:     {n_w:>10,}")
    print(f"  Memory: ~{total * 768 * 4 / 1e9:.2f} GB")

    combined = np.vstack([article_emb, question_emb, transcript_emb, window_emb])

    import umap
    reducer = umap.UMAP(**umap_params)
    t0 = time.time()
    coords = reducer.fit_transform(combined)
    elapsed = time.time() - t0
    print(f"  UMAP complete in {elapsed / 60:.1f} min")

    return {
        "article_coords_raw": coords[:n_a],
        "question_coords_raw": coords[n_a:n_a + n_q],
        "transcript_coords_raw": coords[n_a + n_q:n_a + n_q + n_t],
        "window_coords_raw": coords[n_a + n_q + n_t:],
        "reducer": reducer,
        "umap_time": elapsed,
    }


def run_umap_questions_first(data, umap_params):
    """Fit on questions+transcripts+windows, transform articles."""
    article_emb = data["article_embeddings"]
    question_emb = data["question_embeddings"]
    transcript_emb = data["transcript_embeddings"]
    window_emb = data["window_embeddings"]

    n_q, n_t, n_w = len(question_emb), len(transcript_emb), len(window_emb)
    n_a = len(article_emb)
    fit_total = n_q + n_t + n_w

    print(f"\nStrategy: QUESTIONS-FIRST")
    print(f"  FIT set ({fit_total:,} points):")
    print(f"    Questions:   {n_q:>10,}")
    print(f"    Transcripts: {n_t:>10,}")
    print(f"    Windows:     {n_w:>10,}")
    print(f"  TRANSFORM set:")
    print(f"    Articles:    {n_a:>10,}")
    print(f"  Memory (fit):  ~{fit_total * 768 * 4 / 1e9:.2f} GB")
    print(f"  Memory (transform): ~{n_a * 768 * 4 / 1e9:.2f} GB")

    fit_embeddings = np.vstack([question_emb, transcript_emb, window_emb])

    import umap
    reducer = umap.UMAP(**umap_params)

    print(f"\n  Phase 1: fit_transform on {fit_total:,} points...")
    t0 = time.time()
    fit_coords = reducer.fit_transform(fit_embeddings)
    fit_time = time.time() - t0
    print(f"  fit_transform complete in {fit_time / 60:.1f} min")

    # Split fit coords back
    question_coords_raw = fit_coords[:n_q]
    transcript_coords_raw = fit_coords[n_q:n_q + n_t]
    window_coords_raw = fit_coords[n_q + n_t:]

    # Check question spread before transforming articles
    q_spread_x = question_coords_raw[:, 0].max() - question_coords_raw[:, 0].min()
    q_spread_y = question_coords_raw[:, 1].max() - question_coords_raw[:, 1].min()
    print(f"  Question spread: x={q_spread_x:.2f}, y={q_spread_y:.2f}")

    print(f"\n  Phase 2: transform {n_a:,} articles...")
    t1 = time.time()
    article_coords_raw = reducer.transform(article_emb)
    transform_time = time.time() - t1
    print(f"  transform complete in {transform_time / 60:.1f} min")

    total_time = fit_time + transform_time

    for label, c in [("Articles", article_coords_raw), ("Questions", question_coords_raw),
                      ("Transcripts", transcript_coords_raw), ("Windows", window_coords_raw)]:
        print(f"  {label}: x=[{c[:, 0].min():.2f}, {c[:, 0].max():.2f}] y=[{c[:, 1].min():.2f}, {c[:, 1].max():.2f}]")

    return {
        "article_coords_raw": article_coords_raw,
        "question_coords_raw": question_coords_raw,
        "transcript_coords_raw": transcript_coords_raw,
        "window_coords_raw": window_coords_raw,
        "reducer": reducer,
        "umap_time": total_time,
    }


def run_umap_questions_only(data, umap_params):
    """Fit on just questions, transform everything else."""
    article_emb = data["article_embeddings"]
    question_emb = data["question_embeddings"]
    transcript_emb = data["transcript_embeddings"]
    window_emb = data["window_embeddings"]

    n_q = len(question_emb)
    n_a, n_t, n_w = len(article_emb), len(transcript_emb), len(window_emb)

    print(f"\nStrategy: QUESTIONS-ONLY")
    print(f"  FIT set:")
    print(f"    Questions:   {n_q:>10,}")
    print(f"  TRANSFORM set ({n_a + n_t + n_w:,} points):")
    print(f"    Articles:    {n_a:>10,}")
    print(f"    Transcripts: {n_t:>10,}")
    print(f"    Windows:     {n_w:>10,}")

    import umap
    reducer = umap.UMAP(**umap_params)

    print(f"\n  Phase 1: fit_transform on {n_q:,} questions...")
    t0 = time.time()
    question_coords_raw = reducer.fit_transform(question_emb)
    fit_time = time.time() - t0
    print(f"  fit_transform complete in {fit_time:.1f}s")

    q_spread_x = question_coords_raw[:, 0].max() - question_coords_raw[:, 0].min()
    q_spread_y = question_coords_raw[:, 1].max() - question_coords_raw[:, 1].min()
    print(f"  Question spread: x={q_spread_x:.2f}, y={q_spread_y:.2f}")

    print(f"\n  Phase 2: transform {n_a + n_t + n_w:,} other points...")
    t1 = time.time()
    # Transform in batches to manage memory
    article_coords_raw = reducer.transform(article_emb)
    transcript_coords_raw = reducer.transform(transcript_emb)
    if n_w > 0:
        window_coords_raw = reducer.transform(window_emb)
    else:
        window_coords_raw = np.zeros((0, 2), dtype=np.float32)
    transform_time = time.time() - t1
    print(f"  transform complete in {transform_time / 60:.1f} min")

    total_time = fit_time + transform_time

    for label, c in [("Articles", article_coords_raw), ("Questions", question_coords_raw),
                      ("Transcripts", transcript_coords_raw), ("Windows", window_coords_raw)]:
        if len(c) > 0:
            print(f"  {label}: x=[{c[:, 0].min():.2f}, {c[:, 0].max():.2f}] y=[{c[:, 1].min():.2f}, {c[:, 1].max():.2f}]")

    return {
        "article_coords_raw": article_coords_raw,
        "question_coords_raw": question_coords_raw,
        "transcript_coords_raw": transcript_coords_raw,
        "window_coords_raw": window_coords_raw,
        "reducer": reducer,
        "umap_time": total_time,
    }


def normalize_and_save(result, data):
    """Normalize coordinates to [0,1] and save all outputs."""
    article_coords_raw = result["article_coords_raw"]
    question_coords_raw = result["question_coords_raw"]
    transcript_coords_raw = result["transcript_coords_raw"]
    window_coords_raw = result["window_coords_raw"]

    n_articles = len(article_coords_raw)
    n_questions = len(question_coords_raw)
    n_transcripts = len(transcript_coords_raw)
    n_windows = len(window_coords_raw)

    # ── Normalize to [0, 1] ──
    print("\nNormalizing coordinates to [0, 1]...")

    all_raw = np.vstack([c for c in [article_coords_raw, question_coords_raw,
                                      transcript_coords_raw, window_coords_raw] if len(c) > 0])

    x_min, x_max = all_raw[:, 0].min(), all_raw[:, 0].max()
    y_min, y_max = all_raw[:, 1].min(), all_raw[:, 1].max()
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
    window_coords = normalize(window_coords_raw) if n_windows > 0 else window_coords_raw

    for label, c in [("Articles", article_coords), ("Questions", question_coords),
                      ("Transcripts", transcript_coords), ("Windows", window_coords)]:
        if len(c) > 0:
            print(f"  {label} [0,1]: x=[{c[:, 0].min():.4f}, {c[:, 0].max():.4f}] "
                  f"y=[{c[:, 1].min():.4f}, {c[:, 1].max():.4f}]")

    # ── Per-domain question spread diagnostic ──
    print("\nPer-domain question spread:")
    q_ids = data["question_ids"]
    domain_ids = {}
    for i, qid in enumerate(q_ids):
        # question IDs are like "physics-q001" → domain is everything before last hyphen+q+digits
        parts = qid.rsplit("-q", 1)
        domain = parts[0] if len(parts) == 2 else "unknown"
        domain_ids.setdefault(domain, []).append(i)

    clustered = []
    well_spread = []
    for domain in sorted(domain_ids.keys()):
        indices = domain_ids[domain]
        if len(indices) < 2:
            continue
        coords = question_coords[indices]
        spread_x = coords[:, 0].max() - coords[:, 0].min()
        spread_y = coords[:, 1].max() - coords[:, 1].min()
        spread = max(spread_x, spread_y)
        if spread < 0.05:
            clustered.append((domain, spread))
        else:
            well_spread.append((domain, spread))

    print(f"  Well-spread (>0.05): {len(well_spread)} domains")
    print(f"  Clustered (<0.05):   {len(clustered)} domains")
    if clustered:
        for d, s in sorted(clustered, key=lambda x: x[1]):
            print(f"    {d}: {s:.4f}")

    # ── Save everything ──
    print("\nSaving outputs...")

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
        pickle.dump(result["reducer"], f)
    print(f"  Reducer: {reducer_path} ({reducer_path.stat().st_size / 1024 / 1024:.1f} MB)")

    article_path = EMBEDDINGS_DIR / "umap_article_coords.pkl"
    with open(article_path, "wb") as f:
        pickle.dump({
            "coords": article_coords, "coords_raw": article_coords_raw,
            "titles": data["wiki_data"].get("titles", []),
            "num_articles": n_articles,
            "timestamp": datetime.now().isoformat(),
        }, f)
    print(f"  Article coords: {article_path} ({article_path.stat().st_size / 1024 / 1024:.1f} MB)")

    question_path = EMBEDDINGS_DIR / "umap_question_coords.pkl"
    with open(question_path, "wb") as f:
        pickle.dump({
            "coords": question_coords, "coords_raw": question_coords_raw,
            "question_ids": data["question_ids"],
            "num_questions": n_questions,
            "timestamp": datetime.now().isoformat(),
        }, f)
    print(f"  Question coords: {question_path} ({question_path.stat().st_size / 1024:.0f} KB)")

    transcript_path = EMBEDDINGS_DIR / "umap_transcript_coords.pkl"
    with open(transcript_path, "wb") as f:
        pickle.dump({
            "coords": transcript_coords, "coords_raw": transcript_coords_raw,
            "video_ids": data["transcript_video_ids"],
            "num_transcripts": n_transcripts,
            "timestamp": datetime.now().isoformat(),
        }, f)
    print(f"  Transcript coords: {transcript_path} ({transcript_path.stat().st_size / 1024:.0f} KB)")

    window_path = EMBEDDINGS_DIR / "umap_window_coords.pkl"
    with open(window_path, "wb") as f:
        pickle.dump({
            "coords": window_coords, "coords_raw": window_coords_raw,
            "video_ids": data["window_video_ids"],
            "window_indices": data["window_indices"],
            "window_offsets": data["window_offsets"],
            "num_windows": n_windows,
            "timestamp": datetime.now().isoformat(),
        }, f)
    print(f"  Window coords: {window_path} ({window_path.stat().st_size / 1024 / 1024:.1f} MB)")

    bounds_path = EMBEDDINGS_DIR / "umap_bounds.pkl"
    with open(bounds_path, "wb") as f:
        pickle.dump(bounds, f)
    print(f"  Bounds: {bounds_path}")

    return {
        "n_articles": n_articles,
        "n_questions": n_questions,
        "n_transcripts": n_transcripts,
        "n_windows": n_windows,
        "n_clustered": len(clustered),
        "n_well_spread": len(well_spread),
    }


def main():
    parser = argparse.ArgumentParser(description="Build UMAP projections for Knowledge Mapper")
    parser.add_argument(
        "--strategy",
        choices=["joint", "questions-first", "questions-only"],
        default="questions-first",
        help="UMAP fitting strategy (default: questions-first)",
    )
    parser.add_argument("--n-neighbors", type=int, default=15, help="UMAP n_neighbors (default: 15)")
    parser.add_argument("--min-dist", type=float, default=0.1, help="UMAP min_dist (default: 0.1)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    args = parser.parse_args()

    print("=" * 70)
    print(f"UMAP BUILD — strategy: {args.strategy}")
    print("=" * 70)
    print(f"Started: {datetime.now()}")
    print()

    data = load_embeddings()

    umap_params = {
        "n_neighbors": args.n_neighbors,
        "min_dist": args.min_dist,
        "n_components": 2,
        "metric": "cosine",
        "random_state": args.seed,
    }
    print(f"\nUMAP params: {umap_params}")

    if args.strategy == "joint":
        result = run_umap_joint(data, umap_params)
    elif args.strategy == "questions-first":
        result = run_umap_questions_first(data, umap_params)
    elif args.strategy == "questions-only":
        result = run_umap_questions_only(data, umap_params)

    stats = normalize_and_save(result, data)

    print(f"\n{'=' * 70}")
    print(f"UMAP BUILD COMPLETE — strategy: {args.strategy}")
    print(f"{'=' * 70}")
    print(f"  Articles:      {stats['n_articles']:>10,} points")
    print(f"  Questions:     {stats['n_questions']:>10,} points")
    print(f"  Transcripts:   {stats['n_transcripts']:>10,} points")
    print(f"  Windows:       {stats['n_windows']:>10,} points")
    print(f"  UMAP time:     {result['umap_time'] / 60:.1f} min")
    print(f"  Well-spread:   {stats['n_well_spread']} domains")
    print(f"  Clustered:     {stats['n_clustered']} domains")
    print(f"  Finished: {datetime.now()}")
    print()
    print("Next step:")
    print("  Run: python scripts/flatten_coordinates.py --mu 0.75")
    print("  (This auto-exports to domain JSONs and updates index.json bounding boxes)")

    if stats["n_clustered"] > 0 and args.strategy != "questions-only":
        print(f"\n  WARNING: {stats['n_clustered']} domains still clustered.")
        print(f"  Try: python scripts/build_umap.py --strategy questions-only")


if __name__ == "__main__":
    main()
