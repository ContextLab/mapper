#!/usr/bin/env python3
"""
RAG-based domain assignment: assign articles to domains using chunk-level
cosine similarity search.

For each domain:
  1. Build a query from domain name + description + its questions
  2. Find top N most similar article chunks by cosine similarity
  3. Map chunks back to source articles → domain's curated article set
  4. Compute bounding rectangle from curated articles + questions in UMAP space
  5. Compute grid size proportional to region area

Domain hierarchy:
  - Sub-domains: top 500 closest articles
  - General domains: top 1000 closest articles ∪ all sub-domain articles
  - "All": union of all domain articles

Regions CAN overlap (sub-domain of Physics may overlap with Mathematics).

Input:
  - embeddings/chunk_embeddings.pkl — (N_chunks, 768) with article mapping
  - embeddings/umap_article_coords.pkl — (250K, 2) normalized coords
  - embeddings/umap_question_coords.pkl — (949, 2) normalized coords
  - embeddings/question_embeddings_949.pkl — (949, 768) question embeddings
  - embeddings/all_questions_for_embedding.json — question metadata
  - data/domains/index.json — current domain definitions (for hierarchy)

Output:
  - data/domains/index_v2.json — updated domain definitions with RAG regions
  - embeddings/domain_assignments.pkl — article→domain mapping

Usage:
    python scripts/assign_domains_rag.py
    python scripts/assign_domains_rag.py --top-sub 500 --top-general 1000
"""

import json
import os
import sys
import time
import pickle
import argparse
import numpy as np
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# macOS threading fix
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

PROJECT_ROOT = Path(__file__).parent.parent
EMBEDDINGS_DIR = PROJECT_ROOT / "embeddings"
DOMAINS_DIR = PROJECT_ROOT / "data" / "domains"

# Minimum grid size for smallest domain
MIN_GRID_SIZE = 50


def parse_args():
    parser = argparse.ArgumentParser(description="RAG domain assignment")
    parser.add_argument(
        "--top-sub", type=int, default=500, help="Top N articles for sub-domains"
    )
    parser.add_argument(
        "--top-general",
        type=int,
        default=1000,
        help="Top N articles for general domains",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10000,
        help="Batch size for cosine similarity computation",
    )
    return parser.parse_args()


def cosine_similarity_batched(query_emb, corpus_emb, batch_size=10000):
    """Compute cosine similarity between query and corpus in batches.

    Args:
        query_emb: (D,) or (Q, D) query embedding(s)
        corpus_emb: (N, D) corpus embeddings
        batch_size: process corpus in batches to manage memory

    Returns:
        (N,) or (Q, N) similarity scores
    """
    if query_emb.ndim == 1:
        query_emb = query_emb[np.newaxis, :]

    # Normalize
    query_norm = query_emb / np.linalg.norm(query_emb, axis=1, keepdims=True)

    all_scores = []
    for i in range(0, len(corpus_emb), batch_size):
        batch = corpus_emb[i : i + batch_size]
        batch_norm = batch / np.linalg.norm(batch, axis=1, keepdims=True)
        scores = query_norm @ batch_norm.T  # (Q, batch_size)
        all_scores.append(scores)

    return np.hstack(all_scores).squeeze()


def find_top_articles_via_chunks(
    domain_query_emb, chunk_embeddings, chunk_article_indices, top_n, batch_size=10000
):
    """Find top N articles by chunk-level cosine similarity.

    For each chunk, compute similarity to domain query.
    For each article, take the MAX similarity across its chunks.
    Return top N article indices by max chunk similarity.
    """
    # Compute similarity to all chunks
    chunk_scores = cosine_similarity_batched(
        domain_query_emb, chunk_embeddings, batch_size
    )

    # Aggregate: max similarity per article
    article_max_sim = defaultdict(float)
    for chunk_idx, score in enumerate(chunk_scores):
        article_idx = chunk_article_indices[chunk_idx]
        article_max_sim[article_idx] = max(article_max_sim[article_idx], float(score))

    # Sort by similarity descending
    sorted_articles = sorted(article_max_sim.items(), key=lambda x: -x[1])

    # Return top N
    top_articles = sorted_articles[:top_n]
    return {idx: sim for idx, sim in top_articles}


def build_domain_query(
    domain_info, domain_questions, question_embeddings, question_ids
):
    """Build a query embedding for a domain by averaging its question embeddings.

    Falls back to domain name embedding if no questions match.
    """
    # Find question embeddings that belong to this domain
    domain_id = domain_info["id"]
    matching_indices = []
    for i, qid in enumerate(question_ids):
        for q in domain_questions:
            if q["id"] == qid:
                matching_indices.append(i)
                break

    if matching_indices:
        # Average of domain's question embeddings
        domain_embs = question_embeddings[matching_indices]
        query = domain_embs.mean(axis=0)
        # Normalize
        query = query / np.linalg.norm(query)
        return query, len(matching_indices)

    return None, 0


def compute_bounding_rect(article_coords, question_coords, margin_frac=0.02):
    """Compute a bounding rectangle that encloses all article + question coordinates.

    Adds a small margin (2% of range) on each side.
    """
    all_coords = (
        np.vstack([article_coords, question_coords])
        if len(question_coords) > 0
        else article_coords
    )

    x_min, y_min = all_coords.min(axis=0)
    x_max, y_max = all_coords.max(axis=0)

    x_range = x_max - x_min
    y_range = y_max - y_min

    # Add margin
    x_min = max(0, x_min - x_range * margin_frac)
    x_max = min(1, x_max + x_range * margin_frac)
    y_min = max(0, y_min - y_range * margin_frac)
    y_max = min(1, y_max + y_range * margin_frac)

    return {
        "x_min": round(float(x_min), 6),
        "x_max": round(float(x_max), 6),
        "y_min": round(float(y_min), 6),
        "y_max": round(float(y_max), 6),
    }


def compute_grid_sizes(domains_with_regions):
    """Compute grid sizes proportional to region area.

    Smallest region gets MIN_GRID_SIZE. Others scaled proportionally
    based on the square root of area ratio (grid is 2D).
    """
    # Compute areas
    areas = {}
    for d in domains_with_regions:
        r = d["region"]
        areas[d["id"]] = (r["x_max"] - r["x_min"]) * (r["y_max"] - r["y_min"])

    # Find smallest non-"all" area
    non_all_areas = {k: v for k, v in areas.items() if k != "all"}
    min_area = min(non_all_areas.values()) if non_all_areas else 1.0

    for d in domains_with_regions:
        if d["id"] == "all":
            # "All" gets its own grid based on its area
            d["grid_size"] = MIN_GRID_SIZE
        else:
            # Scale grid by sqrt of area ratio
            ratio = areas[d["id"]] / min_area
            d["grid_size"] = max(
                MIN_GRID_SIZE, int(round(MIN_GRID_SIZE * np.sqrt(ratio)))
            )

    return domains_with_regions


def main():
    args = parse_args()

    print("=" * 70)
    print("RAG-BASED DOMAIN ASSIGNMENT")
    print("=" * 70)
    print(f"Started: {datetime.now()}")
    print(f"Sub-domain top-N: {args.top_sub}")
    print(f"General domain top-N: {args.top_general}")
    print()

    # ── Load data ──
    print("Loading data...")

    # Chunk embeddings
    print("  Loading chunk embeddings...")
    with open(EMBEDDINGS_DIR / "chunk_embeddings.pkl", "rb") as f:
        chunk_data = pickle.load(f)
    chunk_embeddings_raw = chunk_data["embeddings"]
    chunk_article_indices_raw = chunk_data["article_indices"]
    print(f"    Chunks (raw): {chunk_embeddings_raw.shape}")

    # Filter out NaN rows (articles with no text produce NaN embeddings)
    valid_mask = ~np.isnan(chunk_embeddings_raw).any(axis=1)
    chunk_embeddings = chunk_embeddings_raw[valid_mask]
    chunk_article_indices = [
        chunk_article_indices_raw[i]
        for i in range(len(chunk_article_indices_raw))
        if valid_mask[i]
    ]
    print(
        f"    Chunks (valid): {chunk_embeddings.shape} "
        f"({valid_mask.sum()}/{len(valid_mask)}, "
        f"dropped {(~valid_mask).sum()} NaN rows)"
    )

    # UMAP coordinates
    print("  Loading UMAP article coordinates...")
    with open(EMBEDDINGS_DIR / "umap_article_coords.pkl", "rb") as f:
        article_coord_data = pickle.load(f)
    article_coords = article_coord_data["coords"]  # (250K, 2)
    print(f"    Article coords: {article_coords.shape}")

    print("  Loading UMAP question coordinates...")
    with open(EMBEDDINGS_DIR / "umap_question_coords.pkl", "rb") as f:
        question_coord_data = pickle.load(f)
    question_coords = question_coord_data["coords"]  # (949, 2)
    question_ids_from_umap = question_coord_data["question_ids"]
    print(f"    Question coords: {question_coords.shape}")

    # Question embeddings (for building domain queries)
    print("  Loading question embeddings...")
    with open(EMBEDDINGS_DIR / "question_embeddings_949.pkl", "rb") as f:
        q_emb_data = pickle.load(f)
    question_embeddings = q_emb_data["embeddings"]
    question_ids = q_emb_data["question_ids"]
    print(f"    Question embeddings: {question_embeddings.shape}")

    # Question metadata
    print("  Loading question metadata...")
    with open(EMBEDDINGS_DIR / "all_questions_for_embedding.json") as f:
        all_questions = json.load(f)
    questions_by_id = {q["id"]: q for q in all_questions}
    print(f"    Questions: {len(all_questions)}")

    # Domain definitions (for hierarchy)
    print("  Loading domain index...")
    with open(DOMAINS_DIR / "index.json") as f:
        domains_data = json.load(f)
    domains = domains_data["domains"]
    domains_by_id = {d["id"]: d for d in domains}
    print(f"    Domains: {len(domains)}")

    # Wikipedia articles (for titles)
    print("  Loading wikipedia.pkl for titles...")
    with open(PROJECT_ROOT / "wikipedia.pkl", "rb") as f:
        articles = pickle.load(f)
    article_titles = [a.get("title", "Untitled") for a in articles]
    print(f"    Articles: {len(articles):,}")
    print()

    # ── Build question-to-UMAP-index mapping ──
    qid_to_umap_idx = {qid: i for i, qid in enumerate(question_ids_from_umap)}

    # ── Process each domain ──
    print("Processing domains...")
    domain_assignments = {}  # domain_id → set of article indices
    domain_results = []

    # First pass: sub-domains
    sub_domains = [d for d in domains if d.get("level") == "sub"]
    general_domains = [d for d in domains if d.get("level") == "general"]
    all_domain = [d for d in domains if d.get("level") == "all" or d["id"] == "all"]

    for domain in sub_domains:
        domain_id = domain["id"]
        print(f"\n  [{domain_id}] (sub-domain, top {args.top_sub})")

        # Get this domain's questions
        domain_qs = [q for q in all_questions if domain_id in q.get("domain_ids", [])]
        print(f"    Questions: {len(domain_qs)}")

        # Build query from question embeddings
        query_emb, n_matched = build_domain_query(
            domain, domain_qs, question_embeddings, question_ids
        )

        if query_emb is None:
            print(f"    ⚠ No matching question embeddings, skipping")
            continue

        print(f"    Query built from {n_matched} question embeddings")

        # Find top articles via chunk similarity
        t0 = time.time()
        top_articles = find_top_articles_via_chunks(
            query_emb,
            chunk_embeddings,
            chunk_article_indices,
            args.top_sub,
            args.batch_size,
        )
        t1 = time.time()

        domain_assignments[domain_id] = set(top_articles.keys())

        # Get UMAP coords for assigned articles
        assigned_indices = list(top_articles.keys())
        assigned_coords = article_coords[assigned_indices]

        # Get question coords for this domain
        domain_q_coords = []
        for q in domain_qs:
            if q["id"] in qid_to_umap_idx:
                idx = qid_to_umap_idx[q["id"]]
                domain_q_coords.append(question_coords[idx])
        domain_q_coords = (
            np.array(domain_q_coords) if domain_q_coords else np.empty((0, 2))
        )

        # Compute bounding rectangle
        region = compute_bounding_rect(assigned_coords, domain_q_coords)

        sims = list(top_articles.values())
        print(
            f"    Articles: {len(top_articles)}, "
            f"sim range: [{min(sims):.3f}, {max(sims):.3f}]"
        )
        print(
            f"    Region: x=[{region['x_min']:.3f}, {region['x_max']:.3f}] "
            f"y=[{region['y_min']:.3f}, {region['y_max']:.3f}]"
        )
        print(f"    Time: {t1 - t0:.1f}s")

        # Sample top titles
        top_5_indices = sorted(top_articles, key=top_articles.get, reverse=True)[:5]
        for idx in top_5_indices:
            print(f"      Top: {article_titles[idx]} (sim={top_articles[idx]:.3f})")

        domain_results.append(
            {
                **domain,
                "region": region,
                "question_count": len(domain_qs),
                "article_count": len(top_articles),
            }
        )

    # Second pass: general domains (include sub-domain articles)
    for domain in general_domains:
        domain_id = domain["id"]
        children = [d for d in domains if d.get("parent_id") == domain_id]
        child_ids = [c["id"] for c in children]

        print(
            f"\n  [{domain_id}] (general, top {args.top_general} + children: {child_ids})"
        )

        # Get domain questions
        domain_qs = [q for q in all_questions if domain_id in q.get("domain_ids", [])]

        # Also include child domain questions for broader query
        for child_id in child_ids:
            child_qs = [q for q in all_questions if child_id in q.get("domain_ids", [])]
            domain_qs.extend(child_qs)
        # Deduplicate
        seen = set()
        unique_qs = []
        for q in domain_qs:
            if q["id"] not in seen:
                seen.add(q["id"])
                unique_qs.append(q)
        domain_qs = unique_qs

        print(f"    Questions (incl children): {len(domain_qs)}")

        # Build query
        query_emb, n_matched = build_domain_query(
            domain, domain_qs, question_embeddings, question_ids
        )

        if query_emb is None:
            print(f"    ⚠ No matching question embeddings, skipping")
            continue

        # Find top articles
        t0 = time.time()
        top_articles = find_top_articles_via_chunks(
            query_emb,
            chunk_embeddings,
            chunk_article_indices,
            args.top_general,
            args.batch_size,
        )
        t1 = time.time()

        # Union with child domain articles
        assigned = set(top_articles.keys())
        for child_id in child_ids:
            if child_id in domain_assignments:
                assigned |= domain_assignments[child_id]

        domain_assignments[domain_id] = assigned

        # Compute region from ALL assigned articles
        assigned_list = list(assigned)
        assigned_coords = article_coords[assigned_list]

        domain_q_coords = []
        for q in domain_qs:
            if q["id"] in qid_to_umap_idx:
                idx = qid_to_umap_idx[q["id"]]
                domain_q_coords.append(question_coords[idx])
        domain_q_coords = (
            np.array(domain_q_coords) if domain_q_coords else np.empty((0, 2))
        )

        region = compute_bounding_rect(assigned_coords, domain_q_coords)

        print(
            f"    RAG articles: {len(top_articles)}, "
            f"+ children: {len(assigned) - len(top_articles)}, "
            f"total: {len(assigned)}"
        )
        print(
            f"    Region: x=[{region['x_min']:.3f}, {region['x_max']:.3f}] "
            f"y=[{region['y_min']:.3f}, {region['y_max']:.3f}]"
        )
        print(f"    Time: {t1 - t0:.1f}s")

        domain_results.append(
            {
                **domain,
                "region": region,
                "question_count": len(domain_qs),
                "article_count": len(assigned),
            }
        )

    # Third pass: "All" domain = union of everything
    for domain in all_domain:
        domain_id = domain["id"]
        print(f"\n  [{domain_id}] (all = union of all domains)")

        all_assigned = set()
        for aid_set in domain_assignments.values():
            all_assigned |= aid_set

        domain_assignments[domain_id] = all_assigned

        region = {
            "x_min": 0.0,
            "x_max": 1.0,
            "y_min": 0.0,
            "y_max": 1.0,
        }

        all_qs = all_questions
        print(f"    Articles: {len(all_assigned):,}")
        print(f"    Region: full [0,1]²")

        domain_results.append(
            {
                **domain,
                "region": region,
                "question_count": len(all_qs),
                "article_count": len(all_assigned),
            }
        )

    # ── Compute grid sizes ──
    print("\n\nComputing grid sizes...")
    domain_results = compute_grid_sizes(domain_results)
    for d in domain_results:
        print(
            f"  {d['id']}: grid={d['grid_size']}, "
            f"articles={d.get('article_count', '?')}, "
            f"questions={d.get('question_count', '?')}"
        )

    # ── Save outputs ──
    print("\nSaving outputs...")

    # Save updated domain index
    output_domains = []
    for d in domain_results:
        output_domains.append(
            {
                "id": d["id"],
                "name": d["name"],
                "parent_id": d.get("parent_id"),
                "level": d.get("level", "sub"),
                "region": d["region"],
                "grid_size": d["grid_size"],
                "question_count": d.get("question_count", 50),
            }
        )

    index_v2 = {
        "schema_version": "2.0.0",
        "domains": output_domains,
        "generated": datetime.now().isoformat(),
        "params": {
            "top_sub": args.top_sub,
            "top_general": args.top_general,
            "min_grid_size": MIN_GRID_SIZE,
        },
    }

    index_path = DOMAINS_DIR / "index_v2.json"
    with open(index_path, "w") as f:
        json.dump(index_v2, f, indent=2)
    print(f"  ✓ Domain index: {index_path}")

    # Save assignments
    assignments_path = EMBEDDINGS_DIR / "domain_assignments.pkl"
    with open(assignments_path, "wb") as f:
        pickle.dump(
            {
                "assignments": {k: sorted(v) for k, v in domain_assignments.items()},
                "params": {"top_sub": args.top_sub, "top_general": args.top_general},
                "timestamp": datetime.now().isoformat(),
            },
            f,
        )
    print(f"  ✓ Assignments: {assignments_path}")

    # ── Summary ──
    print(f"\n{'=' * 70}")
    print("✓ RAG DOMAIN ASSIGNMENT COMPLETE")
    print(f"{'=' * 70}")
    print(f"  Domains: {len(domain_results)}")
    total_assignments = sum(len(v) for v in domain_assignments.values())
    print(
        f"  Total article assignments: {total_assignments:,} "
        f"(articles appear in multiple domains)"
    )
    print(
        f"  Unique articles assigned: {len(set().union(*domain_assignments.values())):,}"
    )
    print(f"  Finished: {datetime.now()}")
    print()
    print("Next: Run scripts/export_domain_bundles.py to generate domain JSON files")


if __name__ == "__main__":
    main()
