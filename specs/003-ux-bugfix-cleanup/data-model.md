# Data Model: UX Cleanup & Bug Fix Sweep

**Date**: 2026-02-27
**Feature**: [spec.md](./spec.md)

## Entities

### Response (existing — modified)

A user's answer to a question, persisted in localStorage via `$responses`.

| Field | Type | Description |
|-------|------|-------------|
| question_id | string | Unique question identifier |
| domain_id | string | Active domain when answered |
| selected | string\|null | Selected option key (A/B/C/D), null if skipped |
| is_correct | boolean | Whether selected answer matches correct_answer |
| is_skipped | boolean | Whether user clicked "Don't know (skip)" |
| timestamp | number | Unix timestamp (ms) |
| x | number | Question's normalized x coordinate [0,1] |
| y | number | Question's normalized y coordinate [0,1] |

**Changes**: No schema changes. The `is_skipped` field already exists.

### Observation (internal — modified)

An observation recorded in the GP estimator's internal array. Not persisted directly — rebuilt from Responses on restore.

| Field | Type | Description |
|-------|------|-------------|
| x | number | Normalized x coordinate [0,1] |
| y | number | Normalized y coordinate [0,1] |
| value | number | Knowledge value: 1.0 (correct), 0.0 (incorrect), 0.05 (skip) |
| lengthScale | number | RBF kernel width for this observation |
| difficultyWeight | number | **CHANGED**: Now varies by correctness — see below |

**Changes to difficultyWeight**:
- Previously: Single map `{1: 0.25, 2: 0.5, 3: 0.75, 4: 1.0}` for all observations
- Now: Two maps based on observation outcome:
  - **Correct**: `{1: 0.25, 2: 0.5, 3: 0.75, 4: 1.0}` (unchanged — harder questions provide stronger positive evidence)
  - **Incorrect/Skip**: `{1: 1.0, 2: 0.75, 3: 0.5, 4: 0.25}` (inverted — missing hard questions is expected, missing easy questions is more telling)

**Changes to lengthScale for skips**:
- Previously: `UNIFORM_LENGTH_SCALE * 0.5` (reduced spatial footprint)
- Now: `UNIFORM_LENGTH_SCALE * 1.0` (same footprint as wrong answers) — skip evidence should be spatially equivalent, differentiated only by value and weight

### CellEstimate (existing — unchanged)

A grid-cell-level knowledge prediction from the GP estimator.

| Field | Type | Description |
|-------|------|-------------|
| gx | number | Grid x index (0–49) |
| gy | number | Grid y index (0–49) |
| value | number | Predicted knowledge [0,1] |
| uncertainty | number | Posterior uncertainty [0,1] |
| evidenceCount | number | Count of nearby observations |
| state | string | 'unknown' \| 'uncertain' \| 'estimated' |
| difficultyLevel | number | IRT difficulty level (0–4) |

### VideoMarker (existing — unchanged)

A point on the map representing a video segment.

| Field | Type | Description |
|-------|------|-------------|
| x | number | Normalized x coordinate [0,1] |
| y | number | Normalized y coordinate [0,1] |
| videoId | string | YouTube video ID |
| title | string | Video title |
| thumbnailUrl | string | YouTube thumbnail URL |
| durationS | number | Video duration in seconds |
| windowIdx | number | Segment index within the video |

### VideoPanelEntry (new)

A video entry in the discovery panel, aggregated from multiple VideoMarkers.

| Field | Type | Description |
|-------|------|-------------|
| videoId | string | YouTube video ID |
| title | string | Video title |
| durationS | number | Video duration in seconds |
| thumbnailUrl | string | YouTube thumbnail URL |
| markerCount | number | Number of visible markers in viewport |
| isWatched | boolean | Whether user has watched this video |

## State Transitions

### Skip Flow (modified)

```
Question displayed
  → User clicks "Don't know (skip)"
    → [NEW] Show correct answer highlight + resource links (Wikipedia, Khan Academy)
    → [NEW] Show "Skipped" feedback text
    → [NEW] Show "Next" button (wait for user to proceed)
    → Record skip observation with full-width length scale and inverted difficulty weight
    → Update heatmap
```

Previously: Skip immediately advanced to next question with no feedback.

### Import Flow (from landing page — fixed)

```
Landing page displayed
  → User uploads progress JSON
    → Parse and validate responses
    → Set $responses store
    → Switch to "all" domain ($activeDomain.set('all'))
      → switchDomain() triggers:
        → Load domain bundle (articles, questions, labels)
        → Build questionIndex
        → Create new Estimator, restore from $responses
        → [FIX] Call renderer.setAnsweredQuestions() AFTER questionIndex is built
        → Render heatmap + all answered question markers
```

## Validation Rules

- Difficulty level must be 1–4 (integer). Default to 3 if missing or out of range.
- Observation value must be 0.0, 0.05, or 1.0 (no other values).
- Length scale must be > 0. Default to `UNIFORM_LENGTH_SCALE` (0.18) if missing.
- Difficulty weight must be in [0.25, 1.0]. Computed from weight map, never user-supplied.
- Import responses must have `question_id`, `domain_id`, and `is_correct` boolean.
- Cholesky jitter retry: max 3 attempts with 10× jitter increase each time.
