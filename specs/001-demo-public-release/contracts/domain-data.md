# Contract: Domain Data Files

**Consumers**: `src/domain/loader.js`, `src/domain/registry.js`
**Producer**: Pipeline (`scripts/export_domain_data.py`)

## Domain Registry (startup)

**File**: `data/domains/index.json`
**Loaded**: On page load (always)

```jsonc
{
  "schema_version": "1.0.0",
  "domains": [
    {
      "id": "all",
      "name": "All (General)",
      "parent_id": null,
      "level": "all",
      "region": { "x_min": 0, "x_max": 1, "y_min": 0, "y_max": 1 },
      "grid_size": 39,
      "question_count": 50
      // question_ids omitted — loaded with domain bundle
    }
    // ... 18 more domains
  ]
}
```

**Invariants**:
- `domains.length === 19`
- Every domain has a unique `id`
- Every sub-domain's `parent_id` references a valid general domain's `id`
- `"all"` domain has `parent_id: null` and `level: "all"`

## Domain Bundle (lazy-loaded)

**File**: `data/domains/{domain_id}.json`
**Loaded**: On first access to a domain (FR-012)

```jsonc
{
  "domain": {
    "id": "quantum-physics",
    "name": "Quantum Physics",
    "parent_id": "physics",
    "level": "sub",
    "region": { "x_min": 0.2, "x_max": 0.5, "y_min": 0.3, "y_max": 0.7 },
    "grid_size": 20,
    "question_ids": ["a1b2c3...", "d4e5f6...", /* ... 48 more */]
  },
  "questions": [
    {
      "id": "a1b2c3...",
      "question_text": "What is the Schrödinger equation for a free particle?",
      "options": { "A": "...", "B": "...", "C": "...", "D": "..." },
      "correct_answer": "B",
      "difficulty": 3,
      "x": 0.35,
      "y": 0.52,
      "z": 0.12,           // PCA-3 depth for 3D transitions
      "source_article": "Schrödinger equation",
      "domain_ids": ["quantum-physics", "physics"],
      "concepts_tested": ["wave function", "momentum operator"]
    }
    // ... 49 more questions
  ],
  "labels": [
    {
      "gx": 0,
      "gy": 0,
      "center_x": 0.21,
      "center_y": 0.31,
      "label": "Quantum Foundations",
      "article_count": 14
    }
    // ... more grid cells
  ],
  "articles": [
    {
      "title": "Schrödinger equation",
      "url": "https://en.wikipedia.org/wiki/Schr%C3%B6dinger_equation",
      "x": 0.34,
      "y": 0.51,
      "z": 0.11
    }
    // ... ~200-1000 articles in this domain's region
  ]
}
```

**Invariants**:
- `questions.length === 50`
- Every `question.id` appears in `domain.question_ids`
- Every `question.x/y` falls within `domain.region`
- Every `question.z` is a valid PCA-3 coordinate (for 3D transitions)
- `labels` covers the full grid: `labels.length === grid_size * grid_size`
  (cells with no articles may have `label: "Unexplored"`)

## Progress Events

`loader.js` MUST emit progress events during fetch:

```javascript
// Event contract for FR-012 progress bars
loader.load("quantum-physics", {
  onProgress: ({ loaded, total, percent }) => { /* update UI */ },
  onComplete: (domainBundle) => { /* render */ },
  onError: (error) => { /* fallback */ }
});
```
