# Feature Specification: Fix Mobile Mode

**Feature Branch**: `007-fix-mobile-mode`
**Created**: 2026-03-10
**Updated**: 2026-03-11
**Status**: In Progress (Pivoted)
**Input**: Mobile mode fixes — force landscape on phones, fix colorbar/button issues, address GitHub issues #51-53

## Pivot Note

Portrait mode on phone-sized devices proved intractable for the header button layout. Landscape mode already works well. The new approach: **force landscape orientation on phone-sized devices** for the map screen. Portrait remains available for welcome/landing. Desktop and tablet modes must remain unaffected.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Force Landscape on Phone Map Screen (Priority: P1)

A phone-sized device user who clicks "Map my knowledge!" is automatically switched to landscape orientation for the map screen. The header, map, quiz panel, and drawer pull all render correctly in landscape. If the user returns to the welcome screen (e.g., via reset), portrait orientation is permitted again.

**Why this priority**: Portrait phone layout has persistent header overflow issues. Landscape provides sufficient width for all UI elements without scrollable button groups.

**Independent Test**: On a phone-sized viewport, verify the map screen forces landscape and the welcome screen allows portrait.

**Acceptance Scenarios**:

1. **Given** a phone-sized device (viewport width <=480px in portrait), **When** the user enters the map screen, **Then** the app requests landscape orientation lock.
2. **Given** the app is in landscape on a phone, **When** the user resets to the welcome screen, **Then** portrait orientation is allowed again.
3. **Given** a desktop browser (viewport >768px), **When** the user is on any screen, **Then** no orientation lock is applied.
4. **Given** a tablet device (e.g., iPad), **When** the user is on any screen, **Then** no orientation lock is applied; both portrait and landscape work.
5. **Given** a phone in landscape on the map screen, **When** the header renders, **Then** all buttons (left group + right group) are visible without scrolling or overflow.

---

### User Story 2 - Colorbar Visibility with Quiz Panel (Priority: P1, GitHub #51)

The colorbar (gradient legend) stays visible when the quiz panel is expanded. It repositions automatically to avoid being hidden behind the panel. Manual drag is preserved.

**Why this priority**: Users cannot interpret the heatmap without the colorbar. It's hidden in the most common state (panel expanded).

**Independent Test**: With quiz panel open, verify colorbar is fully visible and not overlapping the panel.

**Acceptance Scenarios**:

1. **Given** the quiz panel is expanded, **When** the user views the map area, **Then** the colorbar is fully visible and not hidden behind the panel.
2. **Given** the quiz panel is collapsed, **When** the user views the map, **Then** the colorbar remains in its visible position.
3. **Given** the quiz panel transitions between open/closed, **When** the animation completes, **Then** the colorbar position adjusts to stay visible.
4. **Given** any viewport size, **When** the colorbar is displayed, **Then** it remains draggable via mouse or touch.

---

### User Story 3 - Header Button Hover Clipping Fix (Priority: P2, GitHub #52)

Header buttons no longer have their borders clipped when hovered. The `transform: scale(1.05)` hover effect is removed since the overflow rules on the parent containers are needed for mobile scroll behavior.

**Why this priority**: Visual polish issue reported by team member. Quick fix.

**Independent Test**: Hover over each header button on desktop, verify border is not clipped.

**Acceptance Scenarios**:

1. **Given** a desktop viewport, **When** the user hovers over any header button, **Then** the button border and glow effect are fully visible (not clipped).
2. **Given** the hover state is active, **When** the button is rendered, **Then** no `transform: scale()` is applied.

---

### User Story 4 - Question Quality Fixes (Priority: P2, GitHub #53)

Two questions with quality issues are fixed or replaced:
1. Born rule question — rewritten to properly test conceptual understanding (psi is the function, not a function of psi).
2. t-statistic question — rewritten to avoid self-evident answer and 2-part structure.

**Why this priority**: Bad questions undermine user trust and make the knowledge assessment unreliable.

**Independent Test**: Locate and verify the corrected question text and answer keys in the question bank files.

**Acceptance Scenarios**:

1. **Given** the Born rule question, **When** it is displayed, **Then** it correctly refers to psi as the wave function and tests conceptual understanding.
2. **Given** the t-statistic question, **When** it is displayed, **Then** it has a single clear question with non-self-evident answer options.

---

### User Story 5 - Drawer Pull Centering (Priority: P1, Existing)

The drawer pull grab bar remains perfectly centered horizontally at all times. This was fixed (root cause: `position: absolute` → `position: fixed` + `width: 100vw`) and verified with 0.00px drift. Must remain working in landscape orientation.

**Acceptance Scenarios**:

1. **Given** the quiz panel in landscape on a phone, **When** the drawer pull is visible, **Then** it is horizontally centered within the viewport (within 1px tolerance).
2. **Given** 10 open/close cycles in landscape, **When** the pull bar position is measured, **Then** drift is <=1px.

---

### User Story 6 - Cross-Device and Cross-Mode Verification (Priority: P2)

All fixes verified across: phone landscape (forced), tablet portrait, tablet landscape, desktop portrait, desktop landscape. No regressions.

**Acceptance Scenarios**:

1. **Given** a phone-sized device in landscape, **When** all UI elements are inspected, **Then** header, map, quiz panel, drawer pull, and colorbar render correctly.
2. **Given** a tablet (iPad) in portrait and landscape, **When** the app is used, **Then** no orientation lock is applied and all UI works correctly.
3. **Given** a desktop browser in any window size, **When** the app is used, **Then** no regressions from mobile fixes.
4. **Given** Android emulator and iOS simulator, **When** each scenario is tested, **Then** behavior is consistent.

---

### User Story 7 - Reset Triggers Tutorial (Priority: P3, Existing)

When the user resets all progress, the tutorial state is cleared so the tutorial prompt re-appears on the next domain select, as if it were the first visit.

**Acceptance Scenarios**:

1. **Given** the user has completed the tutorial and resets progress, **When** they click "Map my knowledge!" and select a domain, **Then** the tutorial welcome prompt appears.

---

### Edge Cases

- What happens on a phone if the browser doesn't support the Screen Orientation API?
- How does the forced landscape interact with the device's orientation lock setting?
- What happens to the colorbar when the map area is very small (e.g., quiz panel at max height)?
- How does forced landscape affect the welcome screen particle animation?
- What if a tablet is exactly at the phone/tablet breakpoint boundary?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: On phone-sized devices (screen width <=480px in portrait), the map screen MUST request landscape orientation lock via the Screen Orientation API.
- **FR-002**: When returning to the welcome screen from the map screen on a phone, landscape lock MUST be released.
- **FR-003**: Desktop browsers (>768px) and tablets (481-768px) MUST NOT have any orientation lock applied.
- **FR-004**: The colorbar MUST remain visible when the quiz panel is expanded, repositioning as needed (GitHub #51).
- **FR-005**: Manual colorbar drag MUST be preserved; colorbar position updates MUST respect user-dragged position when possible (GitHub #51).
- **FR-006**: Header button hover MUST NOT clip borders — remove `transform: scale(1.05)` from `.btn-icon:hover` (GitHub #52).
- **FR-007**: Born rule and t-statistic questions MUST be corrected or replaced (GitHub #53).
- **FR-008**: The drawer pull grab bar MUST remain horizontally centered in landscape orientation.
- **FR-009**: Reset MUST clear tutorial state so the tutorial re-appears on next start.
- **FR-010**: Border thickness MUST be consistent (1.5px) across all UI elements using `--color-border`.
- **FR-011**: All header buttons (both groups) MUST be visible without scrolling in phone landscape mode.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Phone map screen successfully locks to landscape orientation on devices supporting Screen Orientation API.
- **SC-002**: Colorbar is visible (not obscured) with quiz panel expanded on all viewport sizes.
- **SC-003**: No header button border clipping on hover at any viewport size.
- **SC-004**: Drawer pull bar is within 1px of center across 10 cycles in landscape.
- **SC-005**: All existing Playwright tests pass after changes.
- **SC-006**: No regression in desktop or tablet layout/functionality.
- **SC-007**: Both corrected questions have accurate, non-trivial answer options.

## Assumptions

- The Screen Orientation API (`screen.orientation.lock('landscape')`) is supported on modern mobile browsers. Fallback: show a "rotate your device" overlay if API is unavailable.
- Phone breakpoint: <=480px portrait width (or <=667px if checking `screen.width`).
- Tablet breakpoint: 481-1024px — no orientation forcing.
- Colorbar drag is preserved; auto-repositioning only adjusts the default position when quiz panel state changes.
- Removing `transform: scale(1.05)` on hover is acceptable (confirmed by issue reporter as option 2).

## Clarifications

### Session 2026-03-11
- Q: Portrait or landscape for phone map screen? → A: Force landscape on phones for map screen.
- Q: Keep colorbar drag on mobile? → A: Yes, keep manual drag. Auto-reposition only adjusts default position with panel state.
- Q: Fix hover clipping via overflow or scale removal? → A: Remove scale (option 2 from #52), since overflow rules are needed for mobile scroll.
