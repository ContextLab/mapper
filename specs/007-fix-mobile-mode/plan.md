# Implementation Plan: Fix Mobile Mode

**Branch**: `007-fix-mobile-mode` | **Date**: 2026-03-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/007-fix-mobile-mode/spec.md`

## Summary

Fix three persistent mobile UI bugs: (1) split header buttons into left/right groups with independent scrollable overflow, (2) fix drawer pull grab bar horizontal centering that drifts after open/close cycles, (3) ensure colorbar is visible and touch-draggable on mobile portrait. Verify all fixes on Android emulator and iOS simulator.

## Technical Context

**Language/Version**: JavaScript ES2022+ (ES modules), HTML5, CSS3
**Primary Dependencies**: nanostores 1.1, Vite 7.3, deck.gl 9.2, KaTeX (CDN)
**Storage**: localStorage (user progress), file-based JSON (question banks)
**Testing**: Playwright (E2E/visual), Vitest (unit)
**Target Platform**: Mobile web (iOS Safari, Android Chrome), Desktop web
**Project Type**: Single-page web application (static, no backend)
**Performance Goals**: 60fps animations, drawer toggle <600ms, no white flash
**Constraints**: Pure CSS/JS fixes, no new dependencies, mobile breakpoint <=480px
**Scale/Scope**: 3 bug fixes + cross-device verification

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Principle I (Accuracy)**: No data/content changes — N/A for this feature
- [x] **Principle II (User Delight)**: All visual changes will be verified via Playwright screenshots. Drawer animation stays at 60fps. No layout shifts introduced.
- [x] **Principle III (Compatibility)**: Fixes target mobile specifically. Will test across Chromium, WebKit (iOS), and Firefox via Playwright. Android emulator + iOS simulator verification required.

All gates pass. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/007-fix-mobile-mode/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (minimal — no data changes)
├── quickstart.md        # Phase 1 output
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
# Files modified by this feature:
index.html               # CSS changes: header layout, drawer pull, colorbar
src/app.js               # JS changes: button group insertion, scroll behavior

# Files for testing:
tests/visual/mobile-drawer.spec.js    # Existing mobile drawer tests
tests/visual/drawer-perf.spec.js      # Existing drawer perf tests
tests/visual/mobile-header.spec.js    # NEW: header button layout tests
tests/visual/mobile-colorbar.spec.js  # NEW: colorbar visibility tests
```

**Structure Decision**: All changes are in the existing single-page app structure. No new directories needed. Two new test files for the new fix areas.

## Design Decisions

### DD-1: Two Scrollable Containers for Header Buttons

**Problem**: Previous attempts used a single `.header-right` scrollable container with flex spacers, `margin-right: auto`, and CSS `order` to separate left/right button groups. All failed because scroll containers collapse spacers — there's no fixed width constraint to push groups apart.

**Solution**: Split the header into three sections:
1. `.header-left` — fixed, contains logo + domain dropdown (unchanged)
2. `.header-actions` — NEW scrollable container, contains reset/download/upload buttons, aligned left
3. `.header-right` — existing scrollable container, contains trophy/video/share/tutorial/info buttons, aligned right

Both `.header-actions` and `.header-right` use `overflow-x: auto` with hidden scrollbars. They share remaining space via `flex: 1` with `min-width: 0`. A small CSS gap separates them.

**On mobile (<=480px)**:
- `.header-actions` scrolls right to reveal hidden left buttons
- `.header-right` scrolls left to reveal hidden right buttons
- Buttons that fit are visible; overflow is hidden off-screen
- Initial scroll: `.header-actions` at `scrollLeft=0` (leftmost visible), `.header-right` at `scrollLeft=scrollWidth` (rightmost visible)

**Why not single container**: Proven to fail in 3+ previous attempts. Two containers is the simplest approach that correctly implements independent scroll directions.

### DD-2: Drawer Pull Centering via Isolated Box Model

**Problem**: The drawer pull bar drifts right after the panel opens because:
1. `#quiz-panel.open` previously applied padding that narrowed the pull's containing block
2. JS-inserted elements (progress bar, modes) can affect flex layout
3. `order: -1` works for DOM ordering but doesn't isolate the pull from padding changes

**Solution**:
- The `.drawer-pull` uses `position: relative; width: 100%` with NO padding on itself or inherited from parent during transitions
- The `.drawer-pull-bar` uses `position: absolute; left: 50%; transform: translateX(-50%)` for centering
- **Critical**: Ensure `#quiz-panel` has `padding: 0` in BOTH open and closed states on mobile. All content padding is applied to `.quiz-content` and sibling elements individually, never to the panel itself.
- Add a defensive CSS rule: `.drawer-pull { padding: 0 !important; margin: 0 !important; box-sizing: border-box; }` to prevent any inherited or JS-set padding from affecting centering.

### DD-3: Colorbar Positioning on Mobile

**Problem**: Colorbar was positioned at `bottom: 60px` which put it behind the quiz panel (z-index 20). Changed to `top: 8px` but visibility not confirmed on real devices.

**Solution**: Keep `top: 8px; right: 8px` positioning. Ensure `z-index: 16` (below header z-index 100, above map). Touch drag events already added in previous work — just need to verify they function on real devices.

## Implementation Phases

### Phase A: Header Button Split (US1 — P1)

1. **HTML**: Add `.header-actions` div between `.header-left` and `.header-right` in `index.html`
2. **CSS (base)**: Style `.header-actions` with `overflow-x: auto`, hidden scrollbars, `flex: 1`, `min-width: 0`
3. **CSS (mobile)**: Set both `.header-actions` and `.header-right` to use `flex: 1; gap: 0.25rem`
4. **JS (app.js)**: Move button insertion from `.header-right` to `.header-actions`. Set initial scroll positions.
5. **CSS (welcome)**: Show only upload in `.header-actions`, share/info in `.header-right`
6. **Test**: New `mobile-header.spec.js` — verify button positions, scroll reveal, dropdown fixedness

### Phase B: Drawer Pull Centering (US2 — P1)

1. **CSS**: Add defensive `padding: 0 !important; margin: 0 !important; box-sizing: border-box` to `.drawer-pull`
2. **CSS**: Verify `#quiz-panel` has `padding: 0` in both open and closed states (already set, but audit)
3. **CSS**: Ensure no padding/margin inheritance chain from panel → pull
4. **Test**: Add centering verification test — measure pull bar offset across 10 open/close cycles

### Phase C: Colorbar Visibility (US3 — P2)

1. **CSS**: Verify `top: 8px; right: 8px; z-index: 16` on mobile (already set)
2. **JS**: Verify touch drag events work (already added in renderer.js)
3. **Test**: New `mobile-colorbar.spec.js` — verify visibility and drag behavior

### Phase D: Cross-Device Verification (US4 — P2)

1. Run Playwright tests across Chromium, WebKit, Firefox viewports
2. Capture screenshots on Android emulator
3. Capture screenshots on iOS simulator
4. Document results with screenshot evidence
