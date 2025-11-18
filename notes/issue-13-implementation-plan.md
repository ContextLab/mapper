# Implementation Plan: Multi-Level Question Difficulty System (Issue #13)

**Branch**: `feature/issue-13-multi-level-questions`
**Status**: Planning Complete - Ready for Review
**Timeline**: ~6-8 weeks (5 difficulty levels)
**Created**: 2025-11-18

---

## Executive Summary

This plan implements a hierarchical knowledge mapping system with **5 levels of difficulty** (0-4), starting from highly specific level-0 questions (current state) and progressively generating broader, more conceptual level-4 questions. The adaptive quiz will sample from high-level questions first, then progressively zoom into areas of demonstrated expertise or knowledge gaps.

**Key Design Principles**:
- ✅ **NO MOCK TESTS** - All integration uses real LM Studio API (Qwen3-14B on port 1234)
- ✅ **Real data verification** - UMAP reducer validation, embedding consistency checks, coordinate integrity
- ✅ **Comprehensive edge case testing** - Missing files, API failures, corrupt data, coordinate drift
- ✅ **Data safety** - Backups before modification, recovery procedures documented

---

## Current State Analysis

### Existing Data Files
- `cell_questions.json`: 513 level-0 questions across 1,521 cells (0.34 q/cell)
- `wikipedia_articles.json`: 39,673 level-0 articles with 2D coordinates
- `data/umap_reducer.pkl`: UMAP model (STATUS: NEEDS VERIFICATION)
- `data/wikipedia.pkl`: 250,000 Wikipedia articles with full text
- `embeddings/wikipedia_embeddings.pkl`: 25,000 article embeddings (768-dim)

### CRITICAL ISSUE: UMAP Reducer Verification Required

Per comment on issue #13:
> "it's possible the umap reducer that we've saved is from an old run. we need to check this."

**If UMAP is out of sync**:
1. All coordinates become invalid
2. Must rebuild: UMAP → optimal rectangle → heatmap labels → questions
3. **Estimated impact**: 2-3 days to regenerate all downstream data

**Action**: Phase 1 includes UMAP verification as first step

---

## Phase 1: Data Validation & Backup (Week 1)

### 1.1 CRITICAL: Verify UMAP Reducer Integrity

**Script**: `scripts/verify_umap_consistency.py`

**Tests**:
1. ✅ Reducer can transform current Wikipedia embeddings
2. ✅ Transformed coordinates match existing `umap_coords.pkl` (tolerance: 1e-5)
3. ✅ Question coordinates align with expected positions
4. ✅ Neighbor overlap is >60% (per `rebuild_umap.py` documentation)

**If ANY test fails** → UMAP rebuild required:
```bash
python scripts/rebuild_umap.py
# Then regenerate downstream:
python scripts/find_optimal_coverage_rectangle.py
python scripts/generate_heatmap_labels.py --grid-size 40 --k 10
python scripts/generate_cell_questions.py
```

**Real Test - No Mocks**:
```python
# Load actual UMAP reducer from disk
with open('data/umap_reducer.pkl', 'rb') as f:
    reducer = pickle.load(f)

# Load real embeddings from disk
with open('embeddings/wikipedia_embeddings.pkl', 'rb') as f:
    embeddings = pickle.load(f)['embeddings']

# Actual transformation (not mocked)
test_coords = reducer.transform(embeddings[:100])

# Load real saved coordinates
with open('umap_coords.pkl', 'rb') as f:
    saved_coords = pickle.load(f)['coords_2d']

# Real comparison with strict tolerance
max_diff = np.abs(test_coords - saved_coords[:100]).max()
assert max_diff < 1e-5, f"Coordinates drifted: {max_diff}"
```

### 1.2 Create Backups (ESSENTIAL - Before Any Modifications)

**Script**: `scripts/backup_existing_data.py`

**Creates**:
- `backups/backup_YYYYMMDD_HHMMSS/`
  - `cell_questions.json` (backup of original)
  - `wikipedia_articles.json` (backup of original)
  - `heatmap_cell_labels.json`
  - `optimal_rectangle.json`
  - `data/` (full directory copy)
  - `MANIFEST.json` (backup inventory)
  - `RECOVERY.md` (restoration instructions)

**Real Data Safety**:
```python
# Actually copy files to disk (not mocked)
shutil.copy2('cell_questions.json', backup_dir / 'cell_questions.json')

# Verify backup is readable
with open(backup_dir / 'cell_questions.json', 'r') as f:
    backup_data = json.load(f)  # Real JSON parsing

# Compare file sizes
original_size = os.path.getsize('cell_questions.json')
backup_size = os.path.getsize(backup_dir / 'cell_questions.json')
assert original_size == backup_size, "Backup size mismatch"
```

**Documentation**: All backup locations recorded in `notes/issue-13-implementation.md`

---

## Phase 2: Add Level Attributes (Week 1-2)

### 2.1 One-Off Script: Add Level to Existing Questions

**Script**: `scripts/add_level_to_questions.py`

**Operation**: Modifies `cell_questions.json` IN PLACE (backup verified first)

**Real Modification - No Mocks**:
```python
# Real file I/O
with open('cell_questions.json', 'r') as f:
    data = json.load(f)

# Actual in-place modification
for cell_data in data['cells']:
    for question in cell_data['questions']:
        question['level'] = 0  # Add level field

# Real file write
with open('cell_questions.json', 'w') as f:
    json.dump(data, f, indent=2)

# Real verification
with open('cell_questions.json', 'r') as f:
    verify_data = json.load(f)
    for cell in verify_data['cells']:
        for q in cell['questions']:
            assert 'level' in q, "Level field missing"
```

**Tests** (`tests/test_add_level_to_questions.py`):
1. ✅ Backup exists before running
2. ✅ All 513 questions get `'level': 0` field
3. ✅ No questions deleted or duplicated
4. ✅ File structure preserved (metadata, cell data intact)
5. ✅ Can restore from backup if modification fails

### 2.2 One-Off Script: Add Level to Existing Articles

**Script**: `scripts/add_level_to_articles.py`

**Operation**: Modifies `wikipedia_articles.json` IN PLACE

**Real Modification**:
```python
# Load real file
with open('wikipedia_articles.json', 'r') as f:
    articles = json.load(f)

# Modify all 39,673 articles
for article in articles:
    article['level'] = 0

# Save to disk
with open('wikipedia_articles.json', 'w') as f:
    json.dump(articles, f, indent=2)

# Verify on disk
with open('wikipedia_articles.json', 'r') as f:
    verify_data = json.load(f)
    assert all('level' in a for a in verify_data), "Missing level fields"
```

**Tests** (`tests/test_add_level_to_articles.py`):
1. ✅ Backup exists
2. ✅ All 39,673 articles get `'level': 0`
3. ✅ Coordinates unchanged (`x`, `y`, `umap_x`, `umap_y`)
4. ✅ No articles deleted
5. ✅ Restoration works from backup

### 2.3 Update generate_cell_questions.py

**Modification**: Add `'level': level` field when generating new questions

**Code Change** (lines 569-576):
```python
# Before:
parsed['cell_x'] = cell['center_x']
parsed['cell_y'] = cell['center_y']
parsed['source_article'] = title

# After:
parsed['cell_x'] = cell['center_x']
parsed['cell_y'] = cell['center_y']
parsed['source_article'] = title
parsed['level'] = level  # NEW: Add level parameter
```

**Test** (`tests/test_generate_questions_with_level.py`):
```python
# Real API call to LM Studio (not mocked)
question_data = generate_question_for_article(
    article=real_article,
    cell=real_cell,
    concepts_data=real_concepts,
    level=1  # Test level-1 generation
)

# Verify real response has level field
assert question_data['question']['level'] == 1
```

### 2.4 Update export_wikipedia_articles.py

**Modification**: Add `'level': 0` when exporting articles

**Code Change** (line 183-191):
```python
articles_json.append({
    'title': article.get('title', 'Untitled'),
    'url': article.get('url', ''),
    'excerpt': create_excerpt(article.get('text', ''), max_length=100),
    'x': item['x'],
    'y': item['y'],
    'umap_x': item['umap_x'],
    'umap_y': item['umap_y'],
    'index': item['index'],
    'level': 0  # NEW: All exported articles are level 0
})
```

---

## Phase 3: Higher-Level Article Discovery (Week 2-3)

### 3.1 Generate Level-1 Articles

**Script**: `scripts/generate_higher_level_articles.py`

**Algorithm**:
1. For each level-0 question in `cell_questions.json`:
   - Prompt Qwen3-14B via LM Studio (real API call) to suggest 1-3 broader Wikipedia article titles
   - Example: "mitochondria" → suggests "organelles", "cell biology", "eukaryotic cells"
2. Deduplicate article titles across all suggestions
3. Download Wikipedia articles (real Wikipedia API calls)
4. Generate embeddings using sentence-transformers (real model inference)
5. Project into UMAP space using saved reducer (real transformation)
6. Save to `wikipedia_articles_level_1.json`

**Real LM Studio API Integration**:
```python
def suggest_broader_articles(question_data):
    """
    Use real LM Studio API to suggest broader articles.
    NO MOCKS - actual HTTP request to http://localhost:1234
    """
    response = requests.post(
        "http://localhost:1234/v1/chat/completions",
        json={
            "model": "qwen/qwen3-14b",
            "messages": [
                {
                    "role": "system",
                    "content": "You suggest broader Wikipedia article titles that provide context for specific topics."
                },
                {
                    "role": "user",
                    "content": f"""Given this question about '{question_data['source_article']}':

Question: {question_data['question']}

Suggest 1-3 Wikipedia article titles that are ONE LEVEL BROADER than '{question_data['source_article']}'.

Examples:
- mitochondria → organelles, cellular respiration
- Patent Trial and Appeal Board → patent law, administrative law
- Thai Sign Language → sign language, language contact

Return ONLY article titles, one per line."""
                }
            ],
            "temperature": 0.3,
            "max_tokens": 200
        },
        timeout=60
    )

    if response.status_code != 200:
        raise Exception(f"LM Studio API error: {response.status_code}")

    # Parse real response
    content = response.json()['choices'][0]['message']['content']
    article_titles = [line.strip() for line in content.split('\n') if line.strip()]

    return article_titles
```

**Real Wikipedia Download**:
```python
import wikipediaapi

def download_wikipedia_article(title):
    """
    Download real Wikipedia article (no mocks).
    Returns None if article doesn't exist.
    """
    wiki = wikipediaapi.Wikipedia('en')
    page = wiki.page(title)

    if not page.exists():
        return None

    return {
        'title': page.title,
        'text': page.text,
        'url': page.fullurl
    }
```

**Real Embedding Generation**:
```python
from sentence_transformers import SentenceTransformer

def generate_embedding(article_text):
    """
    Generate real embedding using sentence-transformers.
    NO MOCKS - actual model inference.
    """
    model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
    embedding = model.encode([article_text], show_progress_bar=False)
    return embedding[0]  # Returns 768-dim vector
```

**Real UMAP Projection**:
```python
def project_to_umap(embedding):
    """
    Project embedding to 2D using real UMAP reducer.
    NO MOCKS - actual reducer.transform() call.
    """
    with open('data/umap_reducer.pkl', 'rb') as f:
        reducer = pickle.load(f)

    # Real transformation
    coords_2d = reducer.transform([embedding])
    return coords_2d[0]  # Returns [x, y]
```

**Tests** (`tests/test_generate_level_1_articles.py`):
1. ✅ **Real LM Studio connectivity**: Test actual API call succeeds
2. ✅ **Wikipedia download**: Download real article "Organelles" and verify content
3. ✅ **Embedding generation**: Generate real embedding, verify shape (768,)
4. ✅ **UMAP projection**: Project real embedding, verify 2D coords
5. ✅ **Deduplication**: Multiple questions suggesting "organelles" → single entry
6. ✅ **Missing articles**: Handle Wikipedia articles that don't exist (skip gracefully)
7. ✅ **API failures**: LM Studio timeout → retry logic, eventual skip
8. ✅ **Coordinate bounds**: Verify projected coords are within reasonable UMAP space

**Edge Cases**:
- ❌ LM Studio not running → Script fails with clear error message
- ❌ Wikipedia API timeout → Retry 3x, then skip article
- ❌ UMAP reducer file missing → Error + instructions to rebuild
- ❌ Embedding model not installed → Error + pip install instructions
- ❌ Suggested article is disambiguation page → Skip, log warning

**Output**: `wikipedia_articles_level_1.json`
```json
[
  {
    "title": "Organelles",
    "url": "https://en.wikipedia.org/wiki/Organelles",
    "excerpt": "In cell biology, an organelle is a...",
    "x": 0.412,
    "y": 0.583,
    "umap_x": 3.14,
    "umap_y": 2.71,
    "level": 1,
    "derived_from": ["mitochondria", "chloroplast", "ribosome"]
  },
  ...
]
```

### 3.2 Generate Level-1 Questions

**Script**: `scripts/generate_level_1_questions.py`

**Algorithm**:
1. Load `wikipedia_articles_level_1.json`
2. For each level-1 article:
   - Generate conceptual questions using existing two-step process
   - Set coordinates to **center of containing heatmap cell**
   - Set `level = 1`
3. Save to `cell_questions_level_1.json`

**Cell Center Calculation**:
```python
def find_containing_cell(article_x, article_y, grid_size=40):
    """
    Find which heatmap cell contains this article.
    Returns cell center coordinates.

    Real calculation - no mocks.
    """
    # Grid cells are evenly spaced in [0, 1] × [0, 1]
    cell_width = 1.0 / grid_size
    cell_height = 1.0 / grid_size

    # Find grid indices
    gx = int(article_x / cell_width)
    gy = int(article_y / cell_height)

    # Clamp to grid bounds
    gx = max(0, min(gx, grid_size - 1))
    gy = max(0, min(gy, grid_size - 1))

    # Calculate cell center
    center_x = (gx + 0.5) * cell_width
    center_y = (gy + 0.5) * cell_height

    return center_x, center_y, gx, gy
```

**Tests** (`tests/test_generate_level_1_questions.py`):
1. ✅ **Cell center calculation**: Verify article at (0.41, 0.58) → cell center (0.4125, 0.5875)
2. ✅ **Real question generation**: Use real LM Studio API to generate level-1 question
3. ✅ **Level field**: All questions have `'level': 1`
4. ✅ **Coordinates**: All questions have cell center coordinates (not article coordinates)
5. ✅ **Two-step process**: Concept extraction → question generation (both real API calls)
6. ✅ **Quality filters**: Conceptual questions only (no factual "what is" questions)

### 3.3 Repeat for Levels 2-4

**Scripts**:
- `scripts/generate_level_2_articles.py` (input: level-1 questions)
- `scripts/generate_level_2_questions.py`
- `scripts/generate_level_3_articles.py` (input: level-2 questions)
- `scripts/generate_level_3_questions.py`
- `scripts/generate_level_4_articles.py` (input: level-3 questions)
- `scripts/generate_level_4_questions.py`

**Progressive Broadening Examples**:
```
Level 0: "Patent Trial and Appeal Board"
  → Level 1: "Patent law", "Administrative law"
    → Level 2: "Intellectual property", "Regulatory agencies"
      → Level 3: "Legal systems", "Government regulation"
        → Level 4: "Law", "Public administration"

Level 0: "Thai Sign Language"
  → Level 1: "Sign language", "Language contact"
    → Level 2: "Language families", "Linguistic diversity"
      → Level 3: "Human language", "Communication systems"
        → Level 4: "Language", "Human communication"
```

**Expected Output Counts** (rough estimates):
- Level 0: 513 questions (existing)
- Level 1: ~300-400 questions (1-3 broader articles per level-0 question, deduplicated)
- Level 2: ~200-300 questions
- Level 3: ~100-200 questions
- Level 4: ~50-100 questions (very broad, high overlap)

**Total**: ~1,163-1,513 questions across all levels

---

## Phase 4: Adaptive Multi-Level Sampling (Week 4-5)

### 4.1 Quiz Flow Modifications

**Current Flow** (level-0 only):
1. Load all questions from `cell_questions.json`
2. Random/adaptive sampling from single pool
3. Show results after N questions

**New Multi-Level Flow**:
1. **Start at Level 4** (broadest questions)
   - Sample 2-3 level-4 questions across knowledge space
   - Assess general familiarity with broad topics
2. **Progress to Level 3** when coverage sufficient
   - Target areas where user answered correctly (areas of expertise)
   - Target areas where user answered incorrectly (knowledge gaps)
   - Adaptive sampling weighted by performance
3. **Progress through Levels 2, 1, 0**
   - Progressively narrow focus based on performance
   - Level 0 only sampled in final phase for fine-grained mapping

**Coverage Threshold** (when to move to next level):
- **Spatial coverage**: ≥70% of map cells within threshold distance of asked questions
- **Confidence**: Average uncertainty across cells ≥ 85%
- **Minimum questions**: At least 3 questions per level before progressing

### 4.2 Multi-Level Question Loader

**Script**: `scripts/load_multi_level_questions.js` (for index.html)

```javascript
async function loadMultiLevelQuestions() {
    // Load all question levels in parallel (real HTTP fetches)
    const [level0, level1, level2, level3, level4] = await Promise.all([
        fetch('cell_questions.json').then(r => r.json()),
        fetch('cell_questions_level_1.json').then(r => r.json()),
        fetch('cell_questions_level_2.json').then(r => r.json()),
        fetch('cell_questions_level_3.json').then(r => r.json()),
        fetch('cell_questions_level_4.json').then(r => r.json())
    ]);

    // Flatten and organize by level
    const questionsByLevel = {
        4: extractQuestions(level4),
        3: extractQuestions(level3),
        2: extractQuestions(level2),
        1: extractQuestions(level1),
        0: extractQuestions(level0)
    };

    return questionsByLevel;
}

function extractQuestions(levelData) {
    const questions = [];
    for (const cellData of levelData.cells) {
        for (const q of cellData.questions) {
            questions.push({
                ...q,
                cell_gx: cellData.cell.gx,
                cell_gy: cellData.cell.gy,
                cell_label: cellData.cell.label
            });
        }
    }
    return questions;
}
```

**Tests** (`tests/test_multi_level_loader.js`):
1. ✅ **Real HTTP fetches**: Load actual JSON files from disk
2. ✅ **Level extraction**: Verify level-4 questions have `level: 4`
3. ✅ **Question count**: Verify expected counts per level
4. ✅ **Missing files**: Handle gracefully if level-N file doesn't exist

### 4.3 Adaptive Level Progression

**Integration with Existing Adaptive Sampler** (from Issue #10):

```javascript
class MultiLevelAdaptiveSampler extends AdaptiveSampler {
    constructor(questionsByLevel, config) {
        super(/* ... */);
        this.questionsByLevel = questionsByLevel;  // {4: [...], 3: [...], ...}
        this.currentLevel = 4;  // Start at highest level
        this.levelHistory = [];  // Track progression
    }

    selectNextQuestion() {
        // Use current level's question pool
        const levelQuestions = this.questionsByLevel[this.currentLevel];

        // Apply adaptive sampling within current level
        const question = super.selectNextQuestion(levelQuestions);

        // Check if we should progress to next level
        if (this.shouldProgressToNextLevel()) {
            this.currentLevel--;
            console.log(`Progressing to Level ${this.currentLevel}`);
        }

        return question;
    }

    shouldProgressToNextLevel() {
        if (this.currentLevel === 0) {
            return false;  // Already at finest level
        }

        const confidence = this.computeConfidence();
        const questionsAsked = this.askedCells.length;

        // Progression criteria
        const coverageThreshold = 0.70;
        const confidenceThreshold = 0.85;
        const minQuestions = 3;

        return (
            questionsAsked >= minQuestions &&
            confidence.coverageConfidence >= coverageThreshold &&
            confidence.uncertaintyConfidence >= confidenceThreshold
        );
    }
}
```

**Tests** (`tests/test_multi_level_adaptive_sampler.js`):
1. ✅ **Level progression**: Start at level 4, progress to 3, 2, 1, 0
2. ✅ **Coverage threshold**: Don't progress until 70% coverage
3. ✅ **Minimum questions**: Don't progress before 3 questions per level
4. ✅ **Performance weighting**: Sample from correct areas (expertise) and incorrect areas (gaps)
5. ✅ **Early exit**: Allow exit at any level if confidence ≥ 90%

### 4.4 UI Updates

**Changes to `index.html`**:

1. **Level indicator** in quiz interface:
   ```html
   <div id="level-indicator">
       Current Level: <span id="current-level">4</span>
       <div class="level-description">General knowledge assessment</div>
   </div>
   ```

2. **Level progression feedback**:
   ```javascript
   function showLevelProgression(newLevel) {
       const descriptions = {
           4: "General knowledge - broad topics",
           3: "Intermediate topics",
           2: "Specific domains",
           1: "Specialized knowledge",
           0: "Expert-level detail"
       };

       showNotification(`Level ${newLevel}: ${descriptions[newLevel]}`);
   }
   ```

3. **Results breakdown by level**:
   ```javascript
   function generateResultsSummary(responses) {
       const byLevel = {0: [], 1: [], 2: [], 3: [], 4: []};

       for (const [cellKey, response] of Object.entries(responses)) {
           const level = response.question.level;
           byLevel[level].push(response);
       }

       // Show performance per level
       for (const [level, responses] of Object.entries(byLevel)) {
           const correct = responses.filter(r => r.correct).length;
           const total = responses.length;
           console.log(`Level ${level}: ${correct}/${total} correct`);
       }
   }
   ```

**Tests** (`tests/test_ui_multi_level.js`):
1. ✅ **Level indicator updates**: Verify displays "Current Level: 4" initially
2. ✅ **Progression notification**: Shows notification when level changes
3. ✅ **Results breakdown**: Displays correct counts per level
4. ✅ **Visual feedback**: Different colors/icons for different levels

---

## Phase 5: Testing & Validation (Week 6)

### 5.1 Integration Tests (Real Data, Real APIs)

**Test Suite**: `tests/integration/test_multi_level_end_to_end.py`

```python
def test_complete_multi_level_pipeline():
    """
    End-to-end test using REAL data and REAL APIs.
    NO MOCKS ANYWHERE.
    """
    # 1. Verify LM Studio is running
    response = requests.get('http://localhost:1234/v1/models')
    assert response.status_code == 200, "LM Studio not running on port 1234"

    # 2. Generate level-1 articles from real level-0 questions
    subprocess.run(['python', 'scripts/generate_level_1_articles.py', '--test-mode'], check=True)

    # Verify output file exists and is valid JSON
    with open('wikipedia_articles_level_1_test.json', 'r') as f:
        level1_articles = json.load(f)

    assert len(level1_articles) > 0, "No level-1 articles generated"
    assert all('level' in a for a in level1_articles), "Missing level field"
    assert all(a['level'] == 1 for a in level1_articles), "Wrong level value"

    # 3. Generate level-1 questions from real level-1 articles
    subprocess.run(['python', 'scripts/generate_level_1_questions.py', '--test-mode'], check=True)

    # Verify questions
    with open('cell_questions_level_1_test.json', 'r') as f:
        level1_data = json.load(f)

    questions = []
    for cell in level1_data['cells']:
        questions.extend(cell['questions'])

    assert len(questions) > 0, "No level-1 questions generated"
    assert all('level' in q for q in questions), "Missing level field in questions"
    assert all(q['level'] == 1 for q in questions), "Wrong question level"

    # 4. Verify coordinates are cell centers (not article positions)
    for q in questions:
        # Cell centers should be at grid positions + 0.5
        # e.g., (0.0125, 0.0125), (0.0375, 0.0125), etc for 40x40 grid
        cell_width = 1.0 / 40
        expected_x = (q['cell_gx'] + 0.5) * cell_width
        expected_y = (q['cell_gy'] + 0.5) * cell_width

        assert abs(q['cell_x'] - expected_x) < 1e-6, "Question not at cell center"
        assert abs(q['cell_y'] - expected_y) < 1e-6, "Question not at cell center"
```

### 5.2 Edge Case Tests (Real Failures)

**Test Suite**: `tests/edge_cases/test_real_failures.py`

```python
def test_lm_studio_timeout():
    """
    Test real LM Studio timeout handling.
    Uses actual HTTP request with aggressive timeout.
    """
    with pytest.raises(requests.Timeout):
        requests.post(
            'http://localhost:1234/v1/chat/completions',
            json={...},
            timeout=0.001  # Force timeout
        )

    # Verify retry logic
    result = suggest_broader_articles_with_retry(question_data, max_retries=3)
    # Should return None after 3 failed attempts

def test_wikipedia_missing_article():
    """
    Test real Wikipedia article that doesn't exist.
    """
    article = download_wikipedia_article("NonexistentArticleThatWillNeverExist12345")
    assert article is None, "Should return None for missing articles"

def test_umap_reducer_missing():
    """
    Test behavior when UMAP reducer file is deleted.
    """
    os.rename('data/umap_reducer.pkl', 'data/umap_reducer.pkl.backup')

    with pytest.raises(FileNotFoundError):
        project_to_umap(test_embedding)

    # Restore
    os.rename('data/umap_reducer.pkl.backup', 'data/umap_reducer.pkl')

def test_corrupt_json():
    """
    Test handling of corrupt JSON file.
    """
    # Write actually corrupt JSON to disk
    with open('test_corrupt.json', 'w') as f:
        f.write('{"incomplete": ')

    with pytest.raises(json.JSONDecodeError):
        with open('test_corrupt.json', 'r') as f:
            json.load(f)

    os.remove('test_corrupt.json')
```

### 5.3 Performance Tests (Real Timing)

**Test Suite**: `tests/performance/test_generation_timing.py`

```python
def test_level_1_generation_timing():
    """
    Measure REAL generation time for level-1 articles.
    Uses actual LM Studio API, Wikipedia downloads, embeddings.
    """
    import time

    # Use first 10 level-0 questions as test set
    with open('cell_questions.json', 'r') as f:
        data = json.load(f)

    test_questions = []
    for cell in data['cells']:
        test_questions.extend(cell['questions'][:1])  # 1 per cell
        if len(test_questions) >= 10:
            break

    start_time = time.time()

    # Real article generation
    level1_articles = []
    for question in test_questions:
        suggestions = suggest_broader_articles(question)  # Real LM Studio call
        for title in suggestions:
            article = download_wikipedia_article(title)  # Real Wikipedia download
            if article:
                embedding = generate_embedding(article['text'])  # Real embedding
                coords = project_to_umap(embedding)  # Real UMAP
                level1_articles.append({...})

    elapsed = time.time() - start_time

    print(f"Generated {len(level1_articles)} level-1 articles in {elapsed:.2f} seconds")
    print(f"Average: {elapsed / len(test_questions):.2f} sec per question")

    # Expected: ~5-10 seconds per question (LM Studio + Wikipedia + embedding)
    assert elapsed / len(test_questions) < 15, "Generation too slow"
```

### 5.4 Data Integrity Tests

**Test Suite**: `tests/integrity/test_data_consistency.py`

```python
def test_coordinate_bounds():
    """
    Verify all coordinates are within valid bounds.
    Tests real data files.
    """
    for level in range(5):
        filename = f'cell_questions_level_{level}.json' if level > 0 else 'cell_questions.json'

        if not os.path.exists(filename):
            continue

        with open(filename, 'r') as f:
            data = json.load(f)

        for cell in data['cells']:
            for question in cell['questions']:
                # Coordinates must be in [0, 1]
                assert 0 <= question['cell_x'] <= 1, f"Invalid x: {question['cell_x']}"
                assert 0 <= question['cell_y'] <= 1, f"Invalid y: {question['cell_y']}"

                # Level must match filename
                assert question['level'] == level, f"Level mismatch in {filename}"

def test_no_duplicate_articles():
    """
    Verify no duplicate articles within same level.
    Tests real data files.
    """
    for level in range(1, 5):  # Levels 1-4 are generated
        filename = f'wikipedia_articles_level_{level}.json'

        if not os.path.exists(filename):
            continue

        with open(filename, 'r') as f:
            articles = json.load(f)

        titles = [a['title'] for a in articles]
        assert len(titles) == len(set(titles)), f"Duplicate articles in level {level}"
```

---

## Phase 6: Documentation & Deployment (Week 6-7)

### 6.1 Update Documentation

**Files to Update**:
1. `CLAUDE.md` - Document multi-level system
2. `README.md` - Update architecture diagram
3. `notes/multi-level-implementation.md` - Complete implementation notes
4. `scripts/README.md` - Document new scripts

### 6.2 Deployment Checklist

- [ ] All tests pass (integration, edge cases, performance, integrity)
- [ ] UMAP consistency verified
- [ ] Backups created and verified
- [ ] Level attributes added to existing data
- [ ] All 5 levels of articles generated
- [ ] All 5 levels of questions generated
- [ ] Multi-level adaptive sampler implemented
- [ ] UI updated with level indicators
- [ ] Documentation complete
- [ ] Code reviewed
- [ ] Performance benchmarks met

---

## Timeline Summary

| Week | Phase | Deliverable |
|------|-------|-------------|
| 1 | Phase 1 | UMAP verified, backups created |
| 1-2 | Phase 2 | Level attributes added, scripts updated |
| 2-3 | Phase 3 | Levels 1-4 articles & questions generated |
| 4-5 | Phase 4 | Adaptive multi-level sampling implemented |
| 6 | Phase 5 | All tests passing |
| 6-7 | Phase 6 | Documentation complete, ready to merge |

**Total**: 6-8 weeks

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| UMAP out of sync | Verify first, rebuild if needed (Phase 1) |
| LM Studio API failures | Retry logic, graceful degradation, clear error messages |
| Wikipedia API timeouts | Retry with exponential backoff, skip after 3 failures |
| Corrupt data files | Backups + recovery procedures documented |
| Generation too slow | Parallel processing, batch API calls, progress checkpoints |
| Low article counts at high levels | Adjust threshold (1-3 → 2-5 suggestions per question) |
| Questions don't become broader | Review LM Studio prompts, add examples, tune temperature |

---

## Success Metrics

1. **Data Integrity**:
   - ✅ All existing questions retain `level: 0` attribute
   - ✅ All existing articles retain `level: 0` attribute
   - ✅ No data loss during migration

2. **Generation Quality**:
   - ✅ Level-1 articles are broader than level-0 (verified manually for sample of 20)
   - ✅ Level-4 articles are very broad (e.g., "Language", "Law", "Biology")
   - ✅ Questions remain conceptual (not factual) across all levels

3. **Coordinate Accuracy**:
   - ✅ All questions have coordinates at cell centers
   - ✅ All articles project to valid UMAP space
   - ✅ UMAP coordinates match saved reducer (max drift < 1e-5)

4. **System Performance**:
   - ✅ Quiz starts with level-4 questions
   - ✅ Progressive narrowing based on performance
   - ✅ User can exit early if high confidence achieved

5. **Test Coverage**:
   - ✅ All integration tests pass with real data
   - ✅ All edge cases handled gracefully
   - ✅ Performance benchmarks met (<15 sec per article generation)
   - ✅ Data integrity tests pass for all levels

---

## Questions for Discussion

1. **UMAP Verification**: Should we rebuild UMAP proactively, or only if verification fails?
2. **Article Suggestion Count**: Start with 1-3 suggestions per question, or use 2-5 for better coverage at higher levels?
3. **Level Progression Speed**: Should we require 3 or 5 questions per level before progressing?
4. **Parallel Generation**: Should levels 1-4 be generated in parallel (faster) or sequentially (safer)?
5. **Backup Strategy**: Keep all backups indefinitely, or only most recent 3?

---

**Ready for review and feedback!**
