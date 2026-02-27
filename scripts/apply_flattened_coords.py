"""Apply flattened coordinates from pickle files to all domain JSON bundles.

Reads the flattened article/question/transcript coordinate pickles, then
updates every domain JSON file and the video catalog with the new positions.
Also recomputes bounding boxes in index.json.

Usage:
    python scripts/apply_flattened_coords.py [--dry-run]
"""
import json
import pickle
import sys
import time
from pathlib import Path

import numpy as np

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parent.parent
EMB_DIR = ROOT / "embeddings"
DOMAIN_DIR = ROOT / "data" / "domains"
VIDEO_CATALOG = ROOT / "data" / "videos" / "catalog.json"

MATCH_TOLERANCE = 0.001  # max distance for a valid coordinate match


def load_pickle(name):
    path = EMB_DIR / name
    with open(path, "rb") as f:
        return pickle.load(f)


def build_remap(orig, flat):
    """Build a KD-tree from original coords and return a lookup function."""
    tree = cKDTree(orig)

    def remap(x, y):
        dist, idx = tree.query([x, y])
        if dist > MATCH_TOLERANCE:
            return None, None
        return float(flat[idx, 0]), float(flat[idx, 1])

    return remap


def remap_articles(articles, remap_fn):
    updated = 0
    missed = 0
    for art in articles:
        if "x" not in art or "y" not in art:
            continue
        nx, ny = remap_fn(art["x"], art["y"])
        if nx is not None:
            art["x"] = round(nx, 6)
            art["y"] = round(ny, 6)
            updated += 1
        else:
            missed += 1
    return updated, missed


def remap_questions(questions, remap_fn):
    updated = 0
    missed = 0
    for q in questions:
        if "x" not in q or "y" not in q:
            continue
        nx, ny = remap_fn(q["x"], q["y"])
        if nx is not None:
            q["x"] = round(nx, 6)
            q["y"] = round(ny, 6)
            updated += 1
        else:
            missed += 1
    return updated, missed


def compute_bounding_box(articles, questions, margin=0.05, min_span=0.15):
    """Compute bounding box from questions (which retain spatial locality after flattening).

    After density flattening (mu=0.85), articles are spread uniformly and
    don't form tight domain clusters. Questions are displaced much less,
    so they still cluster meaningfully. Uses 5th-95th percentile of question
    coordinates, with a minimum span to avoid over-zooming on tight clusters.
    """
    # Prefer questions for the box; fall back to articles if no questions
    qx = [q["x"] for q in questions if "x" in q]
    qy = [q["y"] for q in questions if "y" in q]

    if qx:
        xs = np.array(qx)
        ys = np.array(qy)
    else:
        ax = [a["x"] for a in articles if "x" in a]
        ay = [a["y"] for a in articles if "y" in a]
        if not ax:
            return {"x_min": 0, "x_max": 1, "y_min": 0, "y_max": 1}
        xs = np.array(ax)
        ys = np.array(ay)

    x_lo, x_hi = np.percentile(xs, [5, 95])
    y_lo, y_hi = np.percentile(ys, [5, 95])

    # Enforce minimum span (prevents over-zoom on tight clusters)
    cx, cy = (x_lo + x_hi) / 2, (y_lo + y_hi) / 2
    span_x = max(x_hi - x_lo, min_span)
    span_y = max(y_hi - y_lo, min_span)
    x_lo, x_hi = cx - span_x / 2, cx + span_x / 2
    y_lo, y_hi = cy - span_y / 2, cy + span_y / 2

    return {
        "x_min": round(float(max(0, x_lo - margin)), 6),
        "x_max": round(float(min(1, x_hi + margin)), 6),
        "y_min": round(float(max(0, y_lo - margin)), 6),
        "y_max": round(float(min(1, y_hi + margin)), 6),
    }


def main():
    dry_run = "--dry-run" in sys.argv

    # --- Load flattened pickles ---
    print("Loading flattened coordinate pickles...")
    art_pkl = load_pickle("article_coords.pkl")
    q_pkl = load_pickle("question_coords.pkl")

    art_orig = art_pkl["coords_original"]
    art_flat = art_pkl["coords"]
    q_orig = q_pkl["coords_original"]
    q_flat = q_pkl["coords"]

    print(f"  Articles:    {art_orig.shape[0]:,} original → {art_flat.shape[0]:,} flattened")
    print(f"  Questions:   {q_orig.shape[0]:,} original → {q_flat.shape[0]:,} flattened")

    trans_remap = None
    try:
        t_pkl = load_pickle("transcript_coords.pkl")
        t_orig = t_pkl["coords_original"]
        t_flat = t_pkl["coords"]
        print(f"  Transcripts: {t_orig.shape[0]:,} original → {t_flat.shape[0]:,} flattened")
        trans_remap = build_remap(t_orig, t_flat)
    except FileNotFoundError:
        print("  No transcript coords found — skipping video catalog")

    # --- Build remap functions ---
    print("\nBuilding KD-trees...")
    # Merge article + transcript originals for article remap (they were flattened together)
    if trans_remap is not None:
        merged_orig = np.vstack([art_orig, t_pkl["coords_original"]])
        merged_flat = np.vstack([art_flat, t_pkl["coords"]])
    else:
        merged_orig = art_orig
        merged_flat = art_flat

    art_remap = build_remap(merged_orig, merged_flat)
    q_remap = build_remap(q_orig, q_flat)
    print("  Done")

    # --- Update domain JSONs ---
    domain_files = sorted(DOMAIN_DIR.glob("*.json"))
    domain_files = [f for f in domain_files if f.name not in ("index.json",)]

    print(f"\nUpdating {len(domain_files)} domain JSON files...")
    total_art_updated = 0
    total_art_missed = 0
    total_q_updated = 0
    total_q_missed = 0

    for df in domain_files:
        with open(df) as f:
            data = json.load(f)

        au, am = remap_articles(data.get("articles", []), art_remap)
        qu, qm = remap_questions(data.get("questions", []), q_remap)

        total_art_updated += au
        total_art_missed += am
        total_q_updated += qu
        total_q_missed += qm

        if not dry_run:
            with open(df, "w") as f:
                json.dump(data, f, separators=(",", ":"))

        status = f"  {df.name}: {au} articles, {qu} questions"
        if am or qm:
            status += f" (missed: {am} art, {qm} q)"
        print(status)

    print(f"\n  Total articles updated: {total_art_updated:,} (missed: {total_art_missed})")
    print(f"  Total questions updated: {total_q_updated:,} (missed: {total_q_missed})")

    # --- Update video catalog ---
    if trans_remap is not None and VIDEO_CATALOG.exists():
        print("\nUpdating video catalog...")
        with open(VIDEO_CATALOG) as f:
            catalog = json.load(f)

        vid_updated = 0
        vid_missed = 0
        for video in catalog:
            if "windows" not in video:
                continue
            new_windows = []
            for win in video["windows"]:
                nx, ny = trans_remap(win[0], win[1])
                if nx is not None:
                    new_windows.append([round(nx, 6), round(ny, 6)])
                    vid_updated += 1
                else:
                    new_windows.append(win)  # keep original if no match
                    vid_missed += 1
            video["windows"] = new_windows

        if not dry_run:
            with open(VIDEO_CATALOG, "w") as f:
                json.dump(catalog, f, separators=(",", ":"))

        print(f"  Windows updated: {vid_updated:,} (missed: {vid_missed})")

    # --- Recompute bounding boxes in index.json ---
    index_path = DOMAIN_DIR / "index.json"
    if index_path.exists():
        print("\nRecomputing bounding boxes in index.json...")
        with open(index_path) as f:
            index_data = json.load(f)

        # Build lookup: domain_id → domain JSON data
        domain_lookup = {}
        for df in domain_files:
            did = df.stem  # e.g. "physics" from "physics.json"
            with open(df) as f:
                domain_lookup[did] = json.load(f)

        updated_regions = 0
        for domain_entry in index_data.get("domains", []):
            did = domain_entry["id"]
            if did == "all":
                # "all" domain always spans [0,1]
                domain_entry["region"] = {
                    "x_min": 0.0, "x_max": 1.0,
                    "y_min": 0.0, "y_max": 1.0,
                }
                updated_regions += 1
                continue

            if did in domain_lookup:
                dd = domain_lookup[did]
                bbox = compute_bounding_box(
                    dd.get("articles", []),
                    dd.get("questions", []),
                )
                domain_entry["region"] = bbox
                updated_regions += 1

        # For general domains with sub-domains, expand bbox to cover children
        parent_map = {}  # parent_id → [child entries]
        for de in index_data["domains"]:
            pid = de.get("parent_id")
            if pid:
                parent_map.setdefault(pid, []).append(de)

        for de in index_data["domains"]:
            did = de["id"]
            if did in parent_map and did != "all":
                # Expand to cover all children
                children = parent_map[did]
                all_regions = [de["region"]] + [c["region"] for c in children]
                de["region"] = {
                    "x_min": round(min(r["x_min"] for r in all_regions), 6),
                    "x_max": round(max(r["x_max"] for r in all_regions), 6),
                    "y_min": round(min(r["y_min"] for r in all_regions), 6),
                    "y_max": round(max(r["y_max"] for r in all_regions), 6),
                }

        index_data["generated"] = time.strftime("%Y-%m-%dT%H:%M:%S")

        if not dry_run:
            with open(index_path, "w") as f:
                json.dump(index_data, f, indent=2)

        print(f"  Updated {updated_regions} domain regions")

    if dry_run:
        print("\n[DRY RUN] No files were modified.")
    else:
        print(f"\nDone! Updated {len(domain_files)} domain files + index.json")
        print("NOTE: Run `npm run dev` to verify the map renders correctly")


if __name__ == "__main__":
    main()
