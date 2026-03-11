# Feature Specification: Fix Mobile Mode

**Feature Branch**: `007-fix-mobile-mode`
**Created**: 2026-03-10
**Status**: Draft
**Input**: User description: "Fix mobile mode: header button layout with left/right groups, drawer pull centering, colorbar visibility, cross-device testing on Android and iOS emulators"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Header Button Split Layout (Priority: P1)

A mobile user sees the header bar with two distinct button groups: action buttons (reset, download, upload) on the left side immediately after the domain dropdown, and discovery buttons (top areas, video recs, share, tutorial, info) on the right side. When buttons in either group cannot fit on screen, they are hidden off-screen and revealed by horizontal swiping — drag right to reveal left-group buttons, drag left to reveal right-group buttons. The dropdown menu always remains fixed/visible regardless of scroll position.

**Why this priority**: The header is the primary navigation. Misplaced buttons confuse users and make core actions inaccessible on narrow screens.

**Independent Test**: On a 375px-wide viewport, verify button group positions, scroll behavior, and dropdown fixedness.

**Acceptance Scenarios**:

1. **Given** a mobile viewport (<=480px), **When** the quiz is active, **Then** reset/download/upload buttons appear immediately right of the dropdown, and trophy/video/share/tutorial/info buttons appear at the far right.
2. **Given** a mobile viewport too narrow to show all buttons, **When** user swipes right on the header, **Then** hidden left-group buttons are progressively revealed.
3. **Given** a mobile viewport too narrow to show all buttons, **When** user swipes left on the header, **Then** hidden right-group buttons are progressively revealed.
4. **Given** any mobile viewport width, **When** the user scrolls the header icon bar, **Then** the domain dropdown remains fixed and never scrolls away.
5. **Given** the welcome/landing screen on mobile, **When** the page loads, **Then** only upload (left-justified) and share/info (right-justified) are visible in the header.
6. **Given** insufficient room for the map icon alongside dropdown and all menu icons, **When** the page renders, **Then** the map icon is hidden.

---

### User Story 2 - Drawer Pull Centering (Priority: P1)

A mobile user sees the drawer pull handle (gray grab bar) perfectly centered horizontally within the drawer panel at all times — on initial load, after opening the drawer, after closing the drawer, and after any number of open/close cycles. The pull indicator never shifts or drifts from center.

**Why this priority**: This bug has persisted through multiple fix attempts. The drawer pull is a core mobile interaction element and visual misalignment erodes trust.

**Independent Test**: Open and close the drawer 5 times, measure the pull bar's horizontal offset from center each time; it must be zero (within 1px tolerance).

**Acceptance Scenarios**:

1. **Given** the quiz panel is closed on mobile, **When** the page loads, **Then** the drawer pull bar is horizontally centered within the panel width.
2. **Given** the quiz panel is open on mobile, **When** the user views the drawer pull, **Then** the bar is horizontally centered.
3. **Given** the user has opened and closed the drawer multiple times, **When** the drawer is in any state, **Then** the pull bar remains horizontally centered (no drift or offset).
4. **Given** any panel padding or content changes, **When** the drawer transitions between states, **Then** the pull bar position is not affected by padding changes on parent or sibling elements.

---

### User Story 3 - Colorbar Visibility on Mobile Portrait (Priority: P2)

A mobile user in portrait orientation can see the knowledge colorbar (gradient legend) on the map area. The colorbar is positioned where it does not overlap with the quiz panel or header. The colorbar is draggable via touch, matching desktop drag behavior.

**Why this priority**: Without the colorbar, mobile users cannot interpret the heatmap colors, reducing the map's usefulness.

**Independent Test**: Load the app on a 375x667 viewport, answer a question, verify the colorbar is visible and can be touch-dragged.

**Acceptance Scenarios**:

1. **Given** a mobile portrait viewport with the map visible, **When** the heatmap is rendered, **Then** the colorbar is visible and not obscured by any UI element.
2. **Given** the colorbar is visible on mobile, **When** the user touches and drags it, **Then** it moves smoothly following the finger, matching desktop mouse-drag behavior.
3. **Given** the quiz panel is open (covering lower portion), **When** the user views the map area, **Then** the colorbar remains visible above the panel.

---

### User Story 4 - Cross-Device Verification (Priority: P2)

All mobile fixes are verified on both Android (emulator) and iOS (Xcode simulator) to ensure consistent behavior across platforms. Screenshots document the verified state on each platform.

**Why this priority**: Fixes verified only in Playwright's Chromium may not reflect real mobile browser behavior. Cross-device testing catches platform-specific rendering issues.

**Independent Test**: Run a verification checklist on Android emulator and iOS simulator, capturing screenshots for each fix area.

**Acceptance Scenarios**:

1. **Given** the app is loaded in an Android emulator, **When** each fix area (header layout, drawer pull, colorbar) is inspected, **Then** all acceptance criteria from Stories 1-3 pass.
2. **Given** the app is loaded in an iOS simulator, **When** each fix area is inspected, **Then** all acceptance criteria from Stories 1-3 pass.
3. **Given** both emulators have been tested, **When** results are compared, **Then** behavior is consistent across both platforms.

---

### Edge Cases

- What happens when the viewport is exactly 480px (breakpoint boundary)?
- How does the header behave when the domain name in the dropdown is very long?
- What happens to the drawer pull when the device is rotated from portrait to landscape and back?
- How does the colorbar behave when the quiz panel is open at 55vh, leaving minimal map space?
- What happens when the user swipes the header bar while the drawer is animating?
- How does the drawer pull render on devices with a notch or home indicator (safe area insets)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Header MUST display two scrollable button groups: left group (reset, download, upload) immediately after the dropdown, and right group (trophy, video recs, share, tutorial, info) at the far right.
- **FR-002**: Each button group MUST independently hide buttons that overflow, revealed by horizontal swipe in the appropriate direction (right for left group, left for right group).
- **FR-003**: The domain dropdown MUST remain fixed/pinned and never scroll with the button groups.
- **FR-004**: The map icon MUST be hidden when insufficient space exists for it alongside the dropdown and all menu icons.
- **FR-005**: The drawer pull grab bar MUST be horizontally centered within the drawer panel width at all times, regardless of panel open/close state or number of state transitions.
- **FR-006**: The drawer pull's centering MUST NOT be affected by padding, margin, or layout changes applied to the panel or its children during open/close transitions.
- **FR-007**: The colorbar MUST be visible on mobile portrait viewports, positioned where it does not overlap with the quiz panel or header.
- **FR-008**: The colorbar MUST support touch-based dragging on mobile devices (touchstart/touchmove/touchend).
- **FR-009**: On the welcome/landing screen, only upload (left) and share/info (right) buttons MUST be visible in the header.
- **FR-010**: All fixes MUST be verified on Android emulator and iOS simulator with screenshot evidence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Drawer pull bar is within 1px of horizontal center on every open/close cycle (tested across 10 cycles).
- **SC-002**: All header buttons are accessible via swipe on a 375px viewport — left-group buttons revealed by swiping right, right-group buttons revealed by swiping left.
- **SC-003**: Colorbar is visible (not obscured) on a 375x667 viewport with the quiz panel both open and closed.
- **SC-004**: All existing Playwright tests pass (unit tests, visual tests, mobile drawer tests, drawer performance tests).
- **SC-005**: Visual verification screenshots from Android emulator and iOS simulator confirm correct rendering for all three fix areas.
- **SC-006**: No regression in desktop layout or functionality after mobile fixes.

## Assumptions

- Mobile breakpoint remains at 480px as currently implemented.
- The drawer pull uses absolute positioning for centering (not flex) to avoid layout interference from sibling elements.
- The header uses two separate scrollable containers rather than a single scrollable bar, to achieve independent left/right button group behavior.
- Colorbar position on mobile is top-right of the map area to avoid overlap with the bottom-positioned quiz panel.
- Android testing uses the existing Android emulator setup; iOS testing uses Xcode Simulator.
- Safe area insets (notch, home indicator) are handled via `env(safe-area-inset-*)` CSS functions.
