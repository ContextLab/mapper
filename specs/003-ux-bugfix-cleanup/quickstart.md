# Quickstart: UX Cleanup & Bug Fix Sweep

**Date**: 2026-02-27
**Branch**: `003-ux-bugfix-cleanup`

## Setup

```bash
git checkout 003-ux-bugfix-cleanup
npm install
npm run dev
# Open http://localhost:5173/mapper/
```

## Verification Workflow

### 1. GP Estimator Stability (P1)

```bash
# Run unit tests for estimator stability
npx vitest run --grep "estimator"
```

Manual verification:
1. Open mapper, select "All" domain
2. Answer 150+ questions (mix of correct, incorrect, and skips)
3. Open browser console — verify NO Cholesky/NaN/divide-by-zero errors
4. Verify "domain mapped" percentage increases smoothly (no >5% jumps)
5. Verify heatmap shows gradient, not uniform blob

### 2. Difficulty Weighting (P1)

```bash
npx vitest run --grep "difficulty"
```

Unit test verifies: answering an expert question wrong produces smaller negative heatmap impact than answering an easy question wrong at the same location.

### 3. Skip Behavior (P2)

1. Open mapper, start answering questions
2. Click "Don't know (skip)" on a question
3. Verify: correct answer highlights green, Wikipedia/Khan Academy links appear
4. Verify: "Next" button appears (doesn't auto-advance)
5. Verify: console shows skip observation with full-width length scale

### 4. Keyboard Modifier Keys (P2)

1. Display a question with options A–D
2. Press bare `C` key → option C should be selected
3. Press `Cmd+C` → nothing selected, clipboard copy works normally
4. Press `Ctrl+A`, `Shift+B`, `Alt+D` → no options selected

### 5. Hover Popup & Scrolling (P2)

1. Hover over an article dot (tooltip appears)
2. Begin click-drag → tooltip dismisses immediately
3. Drag across article dots → no tooltips appear during drag
4. Release → tooltips work again on hover

### 6. Canvas Resize (P2)

1. Display map with articles and answered questions visible
2. Resize browser window
3. Verify: article dots remain aligned with heatmap grid cells
4. Verify: no layer drift between heatmap, articles, videos, and questions

### 7. Import from Landing Page (P2)

1. Export progress JSON from an active session
2. Reload to landing page (fresh state)
3. Upload the exported JSON
4. Verify: ALL answered question markers appear (not just the first)
5. Verify: heatmap reflects all responses

### 8. Share Modal (P3)

1. Answer 5+ questions, click Share button
2. Click Twitter/X button → new tab opens twitter.com/intent/tweet (not native share dialog)
3. Click "Copy" → clipboard contains share text only
4. Click "Copy Image" → clipboard contains PNG image

### 9. Article Titles (P3)

1. Answer a question sourced from a multi-word Wikipedia article
2. Verify: source displays "Quantum Field Theory" not "Quantum_Field_Theory"

### 10. Minimap Dragging (P3)

1. Zoom into a region of the map
2. In the minimap, click inside the viewport rectangle
3. Drag → main map pans to follow
4. Click outside viewport rectangle → map centers on clicked position

### 11. Video Discovery Panel (P3)

1. Click the video panel toggle button (left side)
2. Verify: scrollable list of videos in current viewport
3. Pan map → list updates
4. Hover video in list → trajectory highlights on map
5. Click video → YouTube player opens
6. Type in search box → list filters by title
7. Toggle "Show all videos" → markers appear/disappear on map

## Running All Tests

```bash
# Unit tests
npm test

# Visual/E2E tests
npx playwright test

# All together
npm test && npx playwright test
```
