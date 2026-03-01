# Data Pipeline Scripts

These scripts generate the data that powers the Knowledge Mapper frontend. They process 250K Wikipedia articles through embedding, dimensionality reduction, domain assignment, question generation, and coordinate projection to produce the per-domain JSON bundles consumed by the web app.

## Prerequisites

- Python 3.10+
- Apple Silicon Mac with MPS (for local embedding) or CUDA GPU
- HuggingFace token in `.credentials/hf.token`
- OpenAI API key in environment (`OPENAI_API_KEY`)
- ~50 GB disk for intermediate embeddings

Install dependencies:

```bash
pip install numpy scipy scikit-learn sentence-transformers umap-learn torch openai
```

## Pipeline Overview

The scripts run roughly in this order:

```
wikipedia.pkl (250K articles)
       │
       ▼
[1] generate_embeddings_local_full.py  →  embeddings/wikipedia_embeddings.pkl
       │                                    (250K × 768, google/embeddinggemma-300m)
       ▼
[2] generate_domain_questions.py       →  data/domains/*_questions.json
       │                                    (50 questions per domain via Claude Opus 4.6)
       ▼
[3] embed_questions.py                 →  embeddings/question_embeddings.pkl
       │                                    (same model as articles for consistency)
       ▼
[4] rebuild_umap_v2.py                 →  UMAP 2D coordinates
       │                                    (project articles + questions TOGETHER
       │                                     in ONE batch for shared coordinate space)
       ▼
[5] flatten_coordinates.py --mu 0.75  →  density-balanced coordinates
       │                                    (approximate optimal transport flattening)
       ▼
[6] compute_bounding_boxes.py          →  hierarchical bounding boxes
       │                                    (sub-domain → domain → all)
       ▼
[7] export_domain_bundles.py           →  data/domains/{domain_id}.json
       │                                    (questions with coords + bounding boxes)
       ▼
[8] precompute_cell_labels.py          →  data/cell_labels.json (50x50 grid)
```

## Core Embedding/Projection Pipeline

The embedding and projection pipeline follows these steps:

### Step 1: Embed Articles
```bash
python scripts/generate_embeddings_local_full.py
```
Embeds all 250K Wikipedia articles using `google/embeddinggemma-300m`.

### Step 2: Generate Questions (if needed)
```bash
python scripts/generate_domain_questions.py
```
Generates 50 quiz questions per domain using Claude Opus 4.6.

### Step 3: Embed Questions
```bash
python scripts/embed_questions.py
```
Embeds all questions using the SAME model (`google/embeddinggemma-300m`) as articles.
This ensures questions can be projected into the same coordinate space.

### Step 4: Joint UMAP Projection
```bash
python scripts/rebuild_umap_v2.py
```
**CRITICAL**: Projects ALL articles AND questions TOGETHER in a single UMAP batch.
This ensures articles and questions share exactly the same 2D coordinate space.
- Input: article embeddings (250K × 768) + question embeddings (~950 × 768)
- Output: normalized [0, 1] coordinates for both articles and questions

### Step 5: Density Flattening
```bash
python scripts/flatten_coordinates.py --mu 0.75
```
Applies approximate optimal transport to redistribute points more uniformly:
- `mu=0` preserves original UMAP structure
- `mu=1` fully flattens to uniform distribution
- `mu=0.75` (default) balances semantic structure with visual spread
The same displacement field is applied to both articles AND questions.

### Step 6: Compute Bounding Boxes
```bash
python scripts/compute_bounding_boxes.py
```
Computes hierarchical bounding boxes for each area:
- **Sub-domains**: bounding box around that area's questions only
- **Broad domains**: bounding box around that domain's questions AND its sub-domains' questions
- **"All (general)"**: full view [0, 1] × [0, 1] to enclose all articles + questions

### Step 7: Export Domain Bundles
```bash
python scripts/export_domain_bundles.py
```
Integrates question coordinates and bounding boxes into `data/domains/{domain_id}.json`.

## Quick Regeneration After Question Changes

If you've regenerated questions and need to update coordinates:

```bash
# Embed the new questions
python scripts/embed_questions.py

# Re-run joint UMAP projection (articles + questions together)
python scripts/rebuild_umap_v2.py

# Apply density flattening
python scripts/flatten_coordinates.py --mu 0.75

# Recompute bounding boxes from question positions
python scripts/compute_bounding_boxes.py

# Export updated domain bundles
python scripts/export_domain_bundles.py
```

Or use the convenience script:
```bash
python scripts/regenerate_question_pipeline.py
```

## Script Reference

### Embedding & Projection

| Script | Description |
|--------|-------------|
| `generate_embeddings_local_full.py` | Embed all 250K Wikipedia articles using `google/embeddinggemma-300m` on Apple Silicon MPS. Checkpoints every 5000 articles. Output: `embeddings/wikipedia_embeddings.pkl` (250000 x 768). |
| `embed_questions.py` | Embed all quiz questions using `google/embeddinggemma-300m` (same model as articles). Output: `embeddings/question_embeddings.pkl`. |
| `rebuild_umap_v2.py` | **Joint projection**: Fit UMAP on articles AND questions together in ONE batch, ensuring shared coordinate space. Normalizes all coordinates to [0, 1]. |
| `flatten_coordinates.py` | Redistribute UMAP coordinates via approximate optimal transport (Hungarian assignment + k-NN interpolation) to reduce density imbalance. Default `mu=0.75`. Applies same displacement to articles AND questions. |
| `compute_pca_z.py` | Extract the 3rd principal component from embeddings, normalize to [0, 1], and save as z-coordinates for 3D domain transitions. |
| `embed_article_chunks.py` | Chunk all 250K articles into ~500-token pieces and embed each chunk. Used for RAG-based domain assignment. |

### Bounding Box Computation

| Script | Description |
|--------|-------------|
| `compute_bounding_boxes.py` | Compute hierarchical bounding boxes from question positions: sub-domain boxes around that area's questions; broad domain boxes around that domain's + sub-domains' questions; "all" is full [0,1] view. |

### Domain Definition & Assignment

| Script | Description |
|--------|-------------|
| `define_domains.py` | Define 19 non-overlapping domain regions as tiles in embedding space. Outputs `data/domains/index.json` with the full domain hierarchy (6 general + 13 sub-domains). |
| `assign_domains_rag.py` | Assign articles to domains using chunk-level cosine similarity search. Builds a query from each domain's name, description, and questions, then finds the top N most similar article chunks. |

### Question Generation

| Script | Description |
|--------|-------------|
| `generate_domain_questions.py` | Generate 50 quiz questions per domain using Claude Opus 4.6. Each question gets difficulty level, concepts tested, and a source Wikipedia article reference. |
| `validate_article_existence.py` | Validate that all `source_article` references in generated questions correspond to real Wikipedia articles via the Wikipedia REST API. Use `--fix` to remove questions with invalid articles. |

### Export & Postprocessing

| Script | Description |
|--------|-------------|
| `export_domain_bundles.py` | Generate per-domain JSON bundles for the frontend. Integrates questions with their UMAP coordinates and hierarchical bounding boxes. |
| `export_domain_data.py` | Alternative exporter that reads domain definitions, questions, heatmap labels, and articles, then produces `data/domains/{domain_id}.json` files. |
| `precompute_cell_labels.py` | Precompute labels for a 50x50 global grid. For each cell, finds the nearest question and stores its concepts and source article. Used for O(1) tooltip lookups. |
| `regenerate_question_pipeline.py` | Convenience script: runs the full question regeneration pipeline (embed → UMAP → flatten → bounding boxes → export). |

### Utilities

| Script | Description |
|--------|-------------|
| `verify_coordinates.py` | End-to-end coordinate integrity checks: all values in [0,1], no NaN/Inf, questions inside domain regions, grid coverage, etc. |
| `warp_demo.py` | Quick iteration tool: apply density flattening with a given `mu` parameter and re-export domain bundles in one step. Re-runnable with different `mu` values. |
