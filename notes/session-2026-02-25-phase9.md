# Session Notes: Phase 9 CL-049 Implementation — 2026-02-25

## What Was Done

### Phase 9: On-the-fly Domain Question Aggregation (CL-049)

CL-049 requires parent domains to aggregate questions from all descendants at runtime,
rather than storing pre-aggregated questions in files.

#### Implementation (commit 4741e5d)

**T-V100: getDescendants() in registry.js**
- Added `getDescendants(domainId)` function
- "all" → returns all 49 other domain IDs
- Parent (e.g., "physics") → recursive traversal of childrenMap
- Leaf sub-domain → returns empty array

**T-V101: loadQuestionsForDomain() in loader.js**
- Loads domain + all descendants in parallel via Promise.all
- Deduplicates questions by ID using a Set
- Uses existing $domainCache so cached bundles resolve instantly
- Failed loads (.catch(() => null)) are silently skipped

**T-V102: Wired into switchDomain() in app.js**
- `switchDomain()` now calls `loadQuestionsForDomain(domainId)`
- Stores result in `aggregatedQuestions` state variable
- Updates questionIndex, indexQuestions, insights.setConcepts, renderer.addQuestions

**T-V103: Updated handleReset()**
- Clears `aggregatedQuestions = []` on reset

**T-V104: Updated announce()**
- Reports `aggregatedQuestions.length` instead of old static count

#### Tests (commit 6b271d7)

**T-V105: 22 tests in tests/algorithm/domain-aggregation.test.js**
- Uses real domain JSON files from disk (fetch stubbed to read filesystem)
- All 22 tests pass in ~570ms

Test categories:
- **Hierarchy traversal (9 tests)**: "all" returns 49, physics→2, neuroscience→3,
  mathematics→4, psychology→4, leaf→empty, no duplicates, single-parent ownership
- **Question aggregation (9 tests)**: leaf=50, physics=150, neuroscience=200,
  math=250, all=2500, unique IDs, field validation, insertion order
- **Caching (2 tests)**: second load hits cache, parent load pre-caches children
- **Performance (2 tests)**: "all" aggregation <500ms, parent aggregation <100ms

#### Verified
- Build passes (all 41 modules)
- All 68 algorithm tests pass (22 domain-aggregation + 24 gp-irt + 22 video-recommender)
- benchmark.test.js failure is pre-existing (bench mode file, not a regular test)

## Branch State
- Branch: `generate-astrophysics-questions`
- Latest commit: `6b271d7` (pushed)
- All Phase 9 implementation + tests committed and pushed

## Tensor02 Transcript Pipeline
- Status: Last checked at ~864 transcripts out of ~8,796
- Running autonomously in screen session `khan-transcripts` on tensor02
- Log: ~/khan-transcripts/transcripts_full.log
- Credentials in .credentials/ (gitignored)

## Unified Embedding Pipeline (Session 2 — evening)

### Completed
1. **Task plan** created (10 tasks with dependencies)
2. **Spec updated** — CL-050 documents unified pipeline (articles+questions+transcripts → joint UMAP)
3. **Article embeddings** copied from ~/mapper.io/embeddings (250K × 768, verified)
4. **embed_questions_v2.py** — embeds question_text + correct_answer_text → 2,500 × 768 in 17.9s on MPS
5. **embed_transcripts.py** — one embedding per full transcript → 1,864 × 768 in 198.2s on MPS
6. **fit_umap_joint.py** — fits UMAP on concatenated 254,364 documents (250K+2.5K+1.8K)
7. **export_coords_to_domains.py** — writes x/y coords back into domain JSON files
8. **42 embedding tests** all pass (articles:7, questions:14, transcripts:12, cross-consistency:6, +UMAP tests pending)
9. **Transcript pipeline** on tensor02 still running (~33% of 8,796 transcripts)

### In Progress
- **UMAP fitting** running in background (254K points, ~45% through 200 epochs)
- Once UMAP completes: run export script, then verify with UMAP tests

### Key Files
- `.venv/` — Python 3.12 with torch, sentence-transformers, umap-learn
- `scripts/embed_questions_v2.py` — question embedding script
- `scripts/embed_transcripts.py` — transcript embedding script
- `scripts/fit_umap_joint.py` — joint UMAP fitting
- `scripts/export_coords_to_domains.py` — export coords to domain JSONs
- `tests/test_embedding_pipeline.py` — 42+ pytest tests
- `embeddings/` — all pkl files (gitignored except reducer/bounds)

### Pipeline Architecture
```
articles (250K×768) ──┐
questions (2.5K×768) ─┤── concatenate ── UMAP fit_transform ── [0,1] normalized coords
transcripts (1.8K×768)┘                                         ├── article_coords.pkl
                                                                 ├── question_coords.pkl
                                                                 ├── transcript_coords.pkl
                                                                 ├── umap_reducer.pkl
                                                                 └── umap_bounds.pkl
```

Video sliding windows will later use `reducer.transform()` on the trained reducer.

## Remaining Work

### Unblocked Tasks
- **Phase 7B UI/Playwright Tests** (T-V064–T-V068, T-V070) — visual tests for video recommendations
- **Phase 1 Pipeline** (T-V004–T-V006, T-V069) — blocked on UMAP reducer (needs x/y coords on questions)

### Hierarchy Stats (from real data)
- 50 domains: 1 "all" + 13 general parents + 36 sub-domains
- Each file has exactly 50 unique questions (no ID overlap between related domains)
- Parent children counts: physics(2), neuroscience(3), mathematics(4), art-history(2),
  biology(2), world-history(3), computer-science(3), economics(2), philosophy(4),
  linguistics(3), sociology(2), psychology(4), archaeology(2)
