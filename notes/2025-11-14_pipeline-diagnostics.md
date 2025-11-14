# Pipeline Diagnostics - Issue #2
Date: 2025-11-14
Session: Debugging cell label generation quality

## Problem Statement

Initial spot checks showed poor label quality. Need to systematically diagnose where the pipeline is breaking down.

## Pain Points from Issue #2

The original issue identified several potential problems:

1. **UMAP Inversion Quality**
   - Are recovered embeddings similar to original question embeddings for nearby cells?
   - Are recovered embeddings properly interpolating for cells between questions?

2. **Vec2text Recovery Quality**
   - Do recovered tokens/text look correct given original text?
   - Are nearby coordinates producing similar recovered text?
   - Any strange or irrelevant tokens indicating poor performance?

3. **GPT-OSS Label Generation**
   - Do labels make sense given vec2text results?
   - Is formatting correct (2-4 words)?
   - Are labels human-readable?

4. **Label Diversity**
   - Are many cells getting tagged with identical labels?
   - For duplicate labels, are they at least spatially clustered?
   - If randomly scattered, indicates poor specificity

## Diagnostic Approach

Created `diagnose_pipeline.py` to systematically test each stage:

### Phase 1: UMAP Inverse Transform Quality

**Test 1A: Roundtrip Accuracy**
- For each question coordinate (x, y):
  - Original embedding → UMAP → 2D coordinates
  - 2D coordinates → UMAP inverse → recovered embedding
  - Compare: cosine similarity, L2 error
- **Target metrics:**
  - Cosine similarity > 0.9 (excellent), > 0.7 (acceptable)
  - Low L2 error

**Test 1B: Cells Near Questions**
- Test cells slightly offset from each question (5% toward center)
- Compare recovered embedding to original question embedding
- Check if embedding repair is needed and why

**Test 1C: Cells Between Questions**
- Test midpoint between pairs of questions
- Compare to both endpoints
- Check if recovered embedding is "between" the two (closer to average than to either endpoint)

### Phase 2: Vec2text Token Recovery Quality

**Test 2A: Question Coordinates**
- For each question, recover embedding → vec2text
- Check:
  - Recovered text content
  - Top tokens
  - Word overlap with original question
- **Warning signs:**
  - No word overlap
  - Nonsensical or irrelevant tokens
  - Generic/vague text

**Test 2B: Nearby Cells**
- Test cells at 0%, 2%, 5% offset from same question
- Check if nearby cells produce similar recovered text
- **Warning signs:**
  - All identical (caching/quantization issues)
  - Completely different (instability)

### Phase 3: GPT-OSS Label Generation

**Test 3A: LM Studio Accessibility**
- Test if LM Studio is running on port 1234
- Verify basic label generation works

**Test 3B: Label Quality**
- Test label generation from sample vec2text outputs
- Check:
  - Label length (should be 2-4 words)
  - Format correctness
  - Relevance to input text

### Phase 4: Label Diversity Analysis

**Using Existing Labels (3×3 grid)**
- Load `heatmap_cell_labels.json`
- Analyze:
  - Unique label count
  - Diversity ratio
  - Most common labels
  - Spatial distribution of duplicates

**Metrics:**
- Avg distance between cells with same label
- If dist < grid_size/4: spatially clustered (good)
- If dist > grid_size/2: scattered (bad - poor specificity)

## Expected Outputs

The diagnostic script will produce:
1. Quantitative metrics for each stage
2. Detailed examples showing actual data
3. Warning flags for problematic areas
4. Final diagnosis summary

This will pinpoint exactly where quality degrades, allowing targeted fixes rather than guesswork.

## Current Status

Running `diagnose_pipeline.py` - output saved to `diagnosis_output.txt`

## Next Steps

Based on diagnosis results:
1. If UMAP inversion poor: adjust repair strategy or UMAP parameters
2. If vec2text poor: try different vec2text parameters (num_steps, beam_width) or models
3. If GPT-OSS poor: improve prompts or try different model
4. If diversity poor: enhance label generation to encourage specificity

##  Files

- [diagnose_pipeline.py](../diagnose_pipeline.py): Comprehensive diagnostic script
- [diagnosis_output.txt](../diagnosis_output.txt): Output from diagnostic run
- [heatmap_cell_labels.json](../heatmap_cell_labels.json): Existing 3×3 labels for analysis
