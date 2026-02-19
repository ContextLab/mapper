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
       │
       ▼
[2] rebuild_umap_v2.py                →  UMAP 2D coordinates
       │
       ▼
[3] flatten_coordinates.py            →  density-balanced coordinates
       │
       ▼
[4] compute_pca_z.py                  →  z-coordinates (depth axis)
       │
       ▼
[5] define_domains.py                 →  data/domains/index.json (19 domains)
       │
       ▼
[6] embed_article_chunks.py           →  embeddings/chunk_embeddings.pkl
       │
       ▼
[7] assign_domains_rag.py             →  RAG-based article→domain mapping
       │
       ▼
[8] generate_domain_questions.py      →  data/domains/*_questions.json
       │
       ▼
[9] embed_questions.py                →  embeddings/question_embeddings.pkl
       │
       ▼
[10] generate_question_coords.py      →  question x,y,z coordinates
       │
       ▼
[11] export_domain_bundles.py         →  data/domains/{domain_id}.json
     export_domain_data.py               (two exporters, slightly different inputs)
       │
       ▼
[12] precompute_cell_labels.py        →  data/cell_labels.json (50x50 grid)
```

## Script Reference

### Embedding & Projection

| Script | Description |
|--------|-------------|
| `generate_embeddings_local_full.py` | Embed all 250K Wikipedia articles using `google/embeddinggemma-300m` on Apple Silicon MPS. Checkpoints every 5000 articles. Output: `embeddings/wikipedia_embeddings.pkl` (250000 x 768). |
| `rebuild_umap_v2.py` | Fit UMAP on article embeddings, then transform question embeddings into the same 2D space. Normalizes all coordinates to [0, 1]. |
| `flatten_coordinates.py` | Redistribute UMAP coordinates via approximate optimal transport (Hungarian assignment + k-NN interpolation) to reduce density imbalance. Configurable mixing parameter `mu` in [0, 1]. |
| `compute_pca_z.py` | Extract the 3rd principal component from embeddings, normalize to [0, 1], and save as z-coordinates for 3D domain transitions. |
| `embed_article_chunks.py` | Chunk all 250K articles into ~500-token pieces and embed each chunk. Used for RAG-based domain assignment. |
| `embed_questions.py` | Embed all quiz questions using the same model as articles so UMAP `transform()` places them in the same coordinate space. |

### Domain Definition & Assignment

| Script | Description |
|--------|-------------|
| `define_domains.py` | Define 19 non-overlapping domain regions as tiles in embedding space. Outputs `data/domains/index.json` with the full domain hierarchy (6 general + 13 sub-domains). |
| `assign_domains_rag.py` | Assign articles to domains using chunk-level cosine similarity search. Builds a query from each domain's name, description, and questions, then finds the top N most similar article chunks. |

### Question Generation & Coordinates

| Script | Description |
|--------|-------------|
| `generate_domain_questions.py` | Generate 50 quiz questions per domain using GPT-5-nano. Each question gets difficulty level, concepts tested, and a source Wikipedia article reference. |
| `generate_question_coords.py` | Project quiz questions into 2D UMAP space per domain and compute PCA-3 z-coordinates. Places each domain's questions within its pre-defined region. |
| `validate_article_existence.py` | Validate that all `source_article` references in generated questions correspond to real Wikipedia articles via the Wikipedia REST API. Use `--fix` to remove questions with invalid articles. |

### Export & Postprocessing

| Script | Description |
|--------|-------------|
| `export_domain_bundles.py` | Generate per-domain JSON bundles for the frontend from RAG assignments. Includes articles, questions with coordinates, and grid labels. |
| `export_domain_data.py` | Alternative exporter that reads domain definitions, questions, heatmap labels, and articles, then produces `data/domains/{domain_id}.json` files. |
| `precompute_cell_labels.py` | Precompute labels for a 50x50 global grid. For each cell, finds the nearest question and stores its concepts and source article. Used for O(1) tooltip lookups. |

### Utilities

| Script | Description |
|--------|-------------|
| `verify_coordinates.py` | End-to-end coordinate integrity checks: all values in [0,1], no NaN/Inf, questions inside domain regions, grid coverage, etc. |
| `warp_demo.py` | Quick iteration tool: apply density flattening with a given `mu` parameter and re-export domain bundles in one step. Re-runnable with different `mu` values. |
