# Spot Check Progress - Cell Label Verification
Date: 2025-11-14
Session: Continuation of Issue #2

## Overview

Before generating the full 40×40 grid (1600 cells), we're conducting a systematic spot check to verify that the recovered labels from vec2text make sense relative to the questions in the knowledge map.

## Spot Check Strategy

### Phase 1: Cells Near Questions
- Test cells nearest to each of the 10 questions
- Verify that recovered text is semantically similar to the question content
- Expected: Labels should relate to the concepts being tested by nearby questions

### Phase 2: Cells Between Questions
- Test cells at midpoints between pairs of close questions
- Focus on the 3 closest question pairs
- Expected: Labels should represent intermediate concepts between the two questions

### Phase 3: Peripheral Cells
- Test 8 peripheral cells (4 corners + 4 edge midpoints)
- These are far from any questions in the embedding space
- Expected: Labels may be more abstract or represent boundary concepts

## Implementation Details

### Script: [spot_check_labels.py](../spot_check_labels.py)

**Key Functions:**
- `generate_single_cell_label(gx, gy, grid_size)`: Generate label for a single cell
  - Convert grid coords → normalized coords → UMAP coords
  - Perform UMAP inverse transform to recover high-dim embedding
  - Validate and repair embedding if needed
  - Use vec2text to recover tokens from embedding
  - Generate label via LM Studio (if running)

- `find_cell_near_question(question)`: Find grid cell nearest to question
- `find_cell_between_questions(q1, q2)`: Find midpoint cell
- `find_peripheral_cells(questions)`: Sample corner and edge cells

### Pipeline for Each Cell:

1. **Coordinate Conversion**
   ```
   Grid (gx, gy) → Normalized [0,1] → UMAP space → Embedding (768-dim)
   ```

2. **Embedding Validation**
   - Check L2 norm (reasonable range)
   - Check value ranges (mean ± 3σ)
   - Check cosine similarity to nearest neighbor

3. **Embedding Repair** (if invalid)
   - L2 normalization to reference mean
   - Clip outliers to ±3σ
   - PCA projection onto reference subspace
   - Re-normalization to target norm
   - Nearest neighbor blending for very low quality

4. **Token Recovery via Vec2text**
   - Load gtr-base corrector
   - Neural inversion: embedding → text
   - Output: Well-formed sentences

5. **Label Generation via LM Studio** (optional)
   - Pass recovered text to LLM
   - Generate concise 2-4 word label
   - Note: May be empty if LM Studio not running

## Expected Verification Outcomes

### Near Questions (Phase 1)
For each question, the cell label should:
- Contain keywords or concepts from the question
- Relate to the topic being tested
- Make semantic sense

**Example:**
- Question: "What is the primary function of mitochondria in cells?"
- Expected label concepts: energy, ATP, cellular respiration, powerhouse

### Between Questions (Phase 2)
For cells between questions, labels should:
- Represent intermediate or shared concepts
- Bridge the topics of the two questions
- Make sense in context of both questions

**Example:**
- Q1: "Mitochondria function?" (energy production)
- Q2: "Chloroplast function?" (photosynthesis)
- Expected midpoint concepts: cellular energy, organelles, metabolic processes

### Peripheral Cells (Phase 3)
For cells on the periphery, labels may:
- Be more abstract or general
- Represent boundary concepts in the domain
- Possibly be less coherent (far from training data)

## Current Status

**Running:** spot_check_labels.py in background
- Processing ~21 cells total (10 near + 3 between + 8 peripheral)
- Each cell requires:
  - UMAP inverse transform
  - Embedding validation/repair
  - Vec2text model loading (first time only - slow!)
  - Token recovery via neural inversion
  - LM Studio API call (if available)

**Est. Time:** 5-10 minutes (vec2text models are large)

## Output Files

- `spot_check_final.txt`: Full console output
- `spot_check_results.json`: Structured results with:
  - Cell coordinates (grid + normalized)
  - Quality scores
  - Recovered tokens
  - Generated labels
  - Diagnostic information

## Next Steps

1. **Review Results:**
   - Manually inspect recovered tokens for each cell
   - Compare tokens to nearby question content
   - Verify labels make semantic sense

2. **Decision Point:**
   - ✅ If results look good → Proceed with full 40×40 grid generation
   - ❌ If results show issues → Debug and fix before full generation

3. **Potential Issues to Check:**
   - Strange/nonsensical tokens
   - Labels unrelated to nearby questions
   - Embedding repair failures
   - Vec2text quality degradation

## Model Consistency Verification

All components confirmed to use gtr-base (768-dim):
- ✅ generate_embeddings.py: sentence-transformers/gtr-t5-base
- ✅ questions.json: 768-dim embeddings
- ✅ umap_reducer.pkl: Fitted on 768-dim
- ✅ generate_cell_labels.py: Maps to vec2text 'gtr-base'
- ✅ Vec2text corrector: Pre-trained on gtr-base (768-dim T5Stack)

## Technical Notes

- Vec2text returns **well-formed sentences**, not just tokens
- Example output: "gimmicks of art at belco/patino. Write original chapter book..."
- The output is then tokenized and weighted for analysis
- LM Studio prompt now uses full recovered text (not tokenized weights)
