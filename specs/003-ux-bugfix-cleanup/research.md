# Research: UX Cleanup & Bug Fix Sweep

**Date**: 2026-02-27
**Feature**: [spec.md](./spec.md)

## Technical Context Resolution

### Language/Version
- **Decision**: JavaScript ES2022+ (ES modules), HTML5, CSS3
- **Rationale**: Existing codebase is vanilla JS with ES module syntax, served via Vite. No framework (React, Vue, etc.) — all DOM manipulation is direct.
- **Alternatives**: None — this is a bug fix sweep on an existing codebase.

### Primary Dependencies
- **Decision**: nanostores (state), Vite (build), Canvas 2D API (rendering), KaTeX (math), Playwright (testing)
- **Rationale**: Already in use. No new dependencies needed for these fixes.
- **Key versions**: nanostores 1.1.0, Vite 7.3.1, Playwright 1.58.2, Vitest 4.0.18

### Storage
- **Decision**: localStorage via `@nanostores/persistent`
- **Rationale**: All user state (responses, watched videos, preferences) persists in localStorage. Import/export uses JSON files.

### Testing
- **Decision**: Vitest (unit/integration), Playwright (visual/E2E)
- **Rationale**: Already configured. `npm test` runs Vitest; `npx playwright test` runs visual tests.

### Target Platform
- **Decision**: Static web application (GitHub Pages), all modern browsers
- **Rationale**: Deployed at context-lab.com/mapper. No server-side component.

### Project Type
- **Decision**: Single-page web application (vanilla JS, Canvas 2D visualization)

## Research Findings

### R1: GP Estimator Numerical Stability (FR-001, FR-002)

**Problem**: After ~115-120 questions, the Cholesky decomposition in `choleskySolve()` (`src/utils/math.js:194`) fails. The kernel matrix becomes numerically singular because:
1. Many observations cluster in nearby coordinates, making rows near-identical
2. The JITTER constant (1e-6) is too small for matrices of size 120×120+
3. The `Math.max(diag, JITTER)` floor prevents NaN but produces near-zero diagonal values that amplify errors in forward/back substitution

**Root cause of "collapse"**: When Cholesky falls back to zeros (`math.js:244`), the GP predicts prior mean (0.5) everywhere. After many observations, accumulated numerical error can suddenly flip the entire solution vector, causing the 18% → 95% jump.

**Solution**:
1. **Adaptive jitter**: Scale jitter with matrix size: `JITTER = 1e-6 * n` where n = number of observations
2. **Pivoted Cholesky with retry**: If the diagonal element `K[i][i] - sum` is ≤ 0, increase jitter and retry decomposition (max 3 retries with 10× jitter increase each time)
3. **Incremental updates**: Instead of recomputing the full Cholesky from scratch each time, maintain the existing L and extend it with a new row/column. This avoids recomputing the entire matrix and is numerically more stable for growing observation sets.

**Decision**: Implement adaptive jitter + retry strategy. Incremental Cholesky is a future optimization — the retry approach solves the immediate stability issue with minimal code change.

### R2: Difficulty-Weighted Evidence (FR-003, FR-004)

**Problem**: The current `DIFFICULTY_WEIGHT_MAP` assigns *higher* weights to harder questions:
```js
{ 1: 0.25, 2: 0.5, 3: 0.75, 4: 1.0 }
```
This means getting an expert question wrong has MORE negative impact than getting an easy question wrong — the opposite of what's desired.

**Analysis**: The weight is applied symmetrically to both correct and incorrect answers via `wMerged = Math.sqrt(wi * wj)` in the kernel matrix. For *incorrect* answers, a higher weight amplifies the negative evidence. The spec requires:
- Wrong answer on hard question → less negative impact (expected to miss)
- Wrong answer on easy question → more negative impact (should have known)
- Skip → stronger negative evidence than wrong answer

**Solution**:
1. **Invert the weight map for incorrect/skip observations**: When `value < PRIOR_MEAN` (incorrect or skip), use `1 - DIFFICULTY_WEIGHT_MAP[d] + 0.25` so easy-wrong has weight 1.0 and expert-wrong has weight 0.25.
2. **Or simpler**: Keep weight map as-is but apply an *inverse* for incorrect answers in `observe()` and `observeSkip()`. Map: `{1: 1.0, 2: 0.75, 3: 0.5, 4: 0.25}` for incorrect, `{1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0}` (uniform) for correct.

**Decision**: Use two weight maps — one for correct answers (current map, higher difficulty = stronger positive evidence) and one for incorrect/skip answers (inverted, higher difficulty = weaker negative evidence). This is cleanest and preserves existing correct-answer behavior.

### R3: Skip Behavior (FR-004, FR-006)

**Problem 1 — Skip weight**: `observeSkip()` uses `SKIP_KNOWLEDGE_VALUE = 0.05` and `skipLengthScale = UNIFORM_LENGTH_SCALE * 0.5`. The reduced length scale (0.5× factor) means skip evidence has a *smaller* spatial footprint than wrong answers, making it appear as weaker evidence. The spec requires the opposite: skip should be *stronger* negative evidence.

**Solution**:
- Remove the `SKIP_LENGTH_SCALE_FACTOR = 0.5` reduction — skips should use the same length scale as wrong answers (or larger)
- Keep `SKIP_KNOWLEDGE_VALUE = 0.05` (low knowledge) but apply a higher difficulty weight multiplier (e.g., 1.25× the normal weight for that difficulty level) to make skips stronger negative evidence

**Problem 2 — Skip doesn't show correct answer**: `handleSkip()` in `app.js:570` immediately calls `selectAndShowNextQuestion()` without showing feedback. The quiz UI's `handleOptionClick()` highlights the correct answer and shows Wikipedia/Khan links, but this path is never triggered for skips.

**Solution**: Before advancing to next question, call a new `quiz.showSkipFeedback(question)` function that highlights the correct answer and shows resource links — same as wrong-answer feedback but with "Skipped" text.

### R4: Keyboard Modifier Keys (FR-005)

**Problem**: `handleKeyDown()` in `quiz.js:260` checks `e.key.toUpperCase()` without checking for modifier keys. Pressing Cmd+C triggers answer C.

**Solution**: Add guard at top of `handleKeyDown()`:
```js
if (e.metaKey || e.ctrlKey || e.altKey || e.shiftKey) return;
```

### R5: Hover Popup Blocks Scrolling (FR-008, FR-009)

**Problem**: The tooltip (hover popup) is shown via `_showTooltip()` during `_handleMouseMove()`. When click-dragging to scroll, the drag handler runs first but `_handleMouseMove` still fires and can show tooltips. If the cursor enters the tooltip DOM element, the canvas stops receiving mouse events, breaking the drag.

**Solution**:
1. Dismiss tooltip immediately when `mousedown` fires (drag start)
2. Don't show tooltips while `_isDragging` is true
3. Add `pointer-events: none` to the tooltip element CSS so it can never intercept mouse events

### R6: Canvas Resize Alignment (FR-010)

**Problem**: The heatmap is drawn in screen space (no pan/zoom transform) while articles/videos are drawn in world space (inside `ctx.save()/translate(panX,panY)/scale(zoom)`). On resize, `_resize()` updates `_width` and `_height` but the pan/zoom values (`_panX`, `_panY`, `_zoom`) are not recalculated to match the new dimensions, causing the world-space layers to drift relative to the screen-space heatmap.

**Analysis**: Looking at `_render()` (line 443):
- Heatmap: drawn at screen coordinates using `centerSX/centerSY` converted back to world coords
- Articles/videos/questions: drawn inside `ctx.translate(panX, panY); ctx.scale(zoom, zoom)` at `p.x * w, p.y * h`

The issue is that `panX`/`panY` are in CSS pixels from the old dimensions. When the canvas resizes, these pixel offsets no longer map to the same world position.

**Solution**: In `_handleResize()`, recalculate `_panX` and `_panY` proportionally:
```js
const scaleX = newWidth / oldWidth;
const scaleY = newHeight / oldHeight;
this._panX *= scaleX;
this._panY *= scaleY;
```

### R7: Import From Landing Page (FR-016)

**Problem**: `handleImport()` calls `renderer.setAnsweredQuestions()` (line 732) but if the map isn't initialized yet (`!currentDomainBundle`), the renderer hasn't been set up with articles/questions. The domain switch on line 742-743 triggers `switchDomain()` which rebuilds the renderer — but it calls `estimator.restore()` and `renderer.setAnsweredQuestions()` from the responses. The issue is that `switchDomain()` rebuilds the estimator from `$responses.get()`, which should include the imported responses.

**Deeper investigation needed**: The likely bug is that when importing from the landing page, the flow is:
1. `handleImport()` → sets `$responses`, calls `estimator.restore()`, calls `renderer.setAnsweredQuestions()`
2. Then `$activeDomain.set('all')` triggers `switchDomain()`
3. `switchDomain()` creates a *new* estimator and *new* renderer, calling `estimator.restore($responses.get())` — this should work
4. But `renderer.setAnsweredQuestions()` is only called if there are responses after the restore

**Most likely cause**: `switchDomain()` creates a new estimator via `estimator = new Estimator()` and then `estimator.init()` + `estimator.restore()`. The `responsesToAnsweredDots()` function needs `questionIndex` to have been built — but `questionIndex` may not be populated yet when importing from the landing page (questions haven't loaded).

**Solution**: After domain load completes in `switchDomain()`, ensure `renderer.setAnsweredQuestions()` is called with the full response set from `$responses.get()`.

### R8: Share Modal (FR-017, FR-018, FR-019)

**Problem**: The share buttons try `navigator.share()` (Web Share API) first, which opens the OS-level share sheet on macOS/iOS. Only if it fails or isn't available does it fall back to direct URL sharing. The "Copy" button (`action === 'copy'`) copies text AND image — it should only copy text. "Copy Image" is a separate action.

**Solution**:
1. Remove `navigator.share()` / `navigator.canShare()` calls from LinkedIn, Twitter, and Bluesky handlers — always use direct URL sharing
2. In the `copy` action, remove the image copy block (lines 448-455)
3. Keep `copy-image` action as-is (it correctly copies just the image)

### R9: Article Title Underscores (FR-007)

**Problem**: In `quiz.js:373`, `sourceLink.textContent = article` where `article` is `currentQuestion.source_article`. This is the raw Wikipedia slug (e.g., "Quantum_Field_Theory").

**Solution**: Replace underscores with spaces: `article.replace(/_/g, ' ')` when displaying. Keep the raw slug for the URL.

### R10: Minimap Viewport Dragging (FR-011)

**Analysis**: The minimap already implements viewport dragging! Looking at `minimap.js:162-175`:
- If pointer down is inside the viewport rect → `_isDragging = true`, tracks offset
- `_handleCanvasPointerMove` calls `navigateHandler()` during drag
- Cursor shows "grabbing" during drag

**Finding**: The minimap viewport dragging code appears functional. The reported bug ("zooms all the way out instead of dragging") may be caused by the selection logic interfering — if the pointer-down is slightly outside the viewport rect, it enters selection mode instead. The `_isInsideViewport` hit test may be too strict.

**Solution**: Relax the viewport hit test with a small padding (e.g., 3px inset) to make dragging easier to initiate. Also verify the `navigateHandler` call uses `false` for the `animate` parameter during drag (smooth following, not animated jump).

### R11: Video Discovery Panel (FR-012 through FR-015)

**Analysis**: This is a new feature, not a bug fix. It requires:
1. A left sidebar (mirroring the right quiz panel)
2. Viewport-filtered video list from the loaded catalog
3. Hover → highlight trajectory on map
4. Click → open YouTube player modal
5. Search/filter input
6. Toggle for showing/hiding all video markers

**Architecture**:
- New module: `src/ui/video-panel.js`
- Follows existing panel patterns (quiz panel on right)
- Uses `renderer.getViewport()` to filter videos by viewport
- Uses `renderer.setHoveredVideoId(id)` to highlight trajectory
- Uses existing `videoModal.playVideo()` for click-to-play
- CSS: mirror `.quiz-panel` styles for a `.video-panel` on the left

**Decision**: This is the largest single item. It will be its own implementation phase.
