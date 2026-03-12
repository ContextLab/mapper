# Feature Specification: Fix Mobile Mode

**Feature Branch**: `009-fix-mobile-mode`
**Created**: 2026-03-12
**Status**: Draft
**Input**: User description: "100% functional mobile mode with systematic emulator verification. Header button grouping with swipe-reveal overflow. Drawer pull centering fix."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Header Button Layout and Overflow (Priority: P1)

A mobile user opens the app on a narrow phone screen. The header bar organizes buttons into two distinct groups separated by a fixed domain dropdown. The **left group** (reset, download, upload) sits immediately right of the dropdown. The **right group** (top areas/trophy, video recs/suggest, share, tutorial, info) sits at the far right. When the screen is too narrow to show all buttons in a group without overlapping, buttons hide individually (rightmost first in left group, leftmost first in right group). The user drags RIGHT on the header to reveal hidden left-group buttons, or drags LEFT to reveal hidden right-group buttons.

**Why this priority**: Without correct button layout and overflow, core app functionality is inaccessible on mobile devices. This is the most-reported mobile issue.

**Independent Test**: Load the app in an Android emulator at 360px width. Verify left-group buttons appear right of dropdown, right-group buttons appear at far right. Resize to 320px and confirm buttons hide progressively. Swipe right/left on header to reveal hidden buttons.

**Acceptance Scenarios**:

1. **Given** a 360px-wide screen, **When** the app loads on the map screen, **Then** the left group (reset/download/upload) appears immediately right of the dropdown, and the right group (trophy/suggest/share/tutorial/about) appears at the far right
2. **Given** a 320px-wide screen where left-group buttons overflow, **When** the user drags RIGHT on the header bar, **Then** the hidden left-group buttons scroll into view
3. **Given** a 320px-wide screen where right-group buttons overflow, **When** the user drags LEFT on the header bar, **Then** the hidden right-group buttons scroll into view
4. **Given** any mobile width, **When** the header renders, **Then** the domain dropdown remains fixed (never scrolls or hides)
5. **Given** an extremely narrow screen, **When** there is not enough room for the map icon + dropdown + all icons, **Then** the map icon hides first (dropdown and button groups remain)

---

### User Story 2 - Drawer Pull Horizontal Centering (Priority: P1)

A mobile user sees the quiz panel collapsed at the bottom of the screen. The drawer pull handle (the small bar the user grabs to open the panel) is visually centered horizontally within the panel, regardless of device width or safe-area insets.

**Why this priority**: The drawer pull is the primary interaction point for opening the quiz panel on mobile. Off-center placement looks broken and reduces user confidence.

**Independent Test**: Open the app on both Android (360px) and iPhone (375px) emulators. With the quiz panel collapsed, verify the drawer pull bar is exactly centered horizontally. Measure pixel offset from left and right edges.

**Acceptance Scenarios**:

1. **Given** the quiz panel is collapsed on a 360px Android device, **When** the drawer pull renders, **Then** the pull bar is horizontally centered within the panel (equal left/right spacing, within 1px tolerance)
2. **Given** the quiz panel is collapsed on a 375px iPhone device, **When** the drawer pull renders, **Then** the pull bar is horizontally centered within the panel
3. **Given** the video panel drawer pull is visible, **When** it renders, **Then** it is also horizontally centered

---

### User Story 3 - Android Emulator Verification (Priority: P2)

A developer runs the full app in an Android emulator to systematically verify that all mobile features work correctly. Every interactive element is reachable and functional: header buttons, dropdown, drawer pulls, quiz answering, video panel, map interaction, minimap, share, and about modal.

**Why this priority**: Android represents the largest mobile platform. Systematic emulator testing catches device-specific rendering and touch interaction bugs that CSS-only inspection misses.

**Independent Test**: Launch the app in Android Studio emulator (Pixel 7, 412x915). Walk through a complete user journey: welcome screen, start quiz, answer questions, open video panel, switch domains, share map, view about modal.

**Acceptance Scenarios**:

1. **Given** an Android emulator (Pixel 7, API 34), **When** the app loads, **Then** the welcome screen renders correctly with start button accessible
2. **Given** the map screen on Android, **When** the user taps header buttons (share, about, dropdown), **Then** each responds correctly with no layout breakage
3. **Given** the quiz panel on Android, **When** the user drags the drawer pull up, **Then** the panel opens smoothly revealing quiz content with tappable answer options
4. **Given** any screen on Android, **When** the user interacts with the map (pan, pinch-zoom), **Then** the map responds without lag or visual artifacts

---

### User Story 4 - iPhone Emulator Verification (Priority: P2)

A developer runs the full app in the Xcode iPhone Simulator to verify all mobile features work correctly on iOS Safari, accounting for safe-area insets (notch/Dynamic Island), iOS-specific touch behaviors, and WebKit rendering differences.

**Why this priority**: iOS Safari has unique rendering behaviors (safe-area insets, rubber-band scrolling, viewport handling) that require separate verification from Android.

**Independent Test**: Launch the app in Xcode Simulator (iPhone 15, iOS 17). Walk through the same complete user journey as Android verification.

**Acceptance Scenarios**:

1. **Given** an iPhone 15 Simulator, **When** the app loads, **Then** the welcome screen renders correctly respecting the Dynamic Island safe area
2. **Given** the map screen on iPhone, **When** the user opens the quiz panel, **Then** the bottom sheet respects `env(safe-area-inset-bottom)` and content is not obscured by the home indicator
3. **Given** the header on iPhone, **When** the user swipes to reveal hidden buttons, **Then** the swipe gesture works correctly without conflicting with iOS back-swipe navigation
4. **Given** any modal on iPhone, **When** it opens, **Then** it renders correctly and is dismissible via expected iOS interaction patterns

---

### Edge Cases

- What happens when the device is rotated from portrait to landscape? Header layout should adapt without breaking button grouping
- What happens when the keyboard opens (e.g., if user focuses a text field)? Panels should not be pushed off-screen
- What happens on a very wide phone (e.g., 430px iPhone Pro Max)? All buttons should be visible without overflow scrolling
- What happens with accessibility font scaling (large/extra-large text)? Header buttons should remain tappable even if text overflows
- What happens when the user drags the header but there are no hidden buttons? The scroll should bounce/resist naturally
- What happens on devices with no safe-area insets (older phones, Android without gesture nav)? Layout should degrade gracefully with fallback spacing

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Header MUST organize buttons into two scrollable groups: left group (reset, download, upload) positioned immediately right of the domain dropdown, and right group (trophy, suggest, share, tutorial, about) positioned at the far right
- **FR-002**: Each button group MUST independently hide buttons when insufficient horizontal space exists, removing them one at a time (left group hides rightmost first; right group hides leftmost first)
- **FR-003**: Users MUST be able to drag/swipe RIGHT on the header to reveal hidden left-group buttons, and drag/swipe LEFT to reveal hidden right-group buttons
- **FR-004**: The domain dropdown MUST remain fixed (non-scrollable) at all screen widths on mobile
- **FR-005**: The map icon MUST hide when there is insufficient room to display it alongside the dropdown and all visible menu icons
- **FR-006**: The drawer pull bar on both quiz and video bottom sheets MUST be exactly horizontally centered within its container at all mobile screen widths
- **FR-007**: All interactive elements (buttons, drawer pulls, quiz options, map gestures) MUST be functional on Android devices running Chrome
- **FR-008**: All interactive elements MUST be functional on iOS devices running Safari, respecting safe-area insets
- **FR-009**: Bottom sheet drawer pulls MUST respond to vertical drag gestures to open/close panels
- **FR-010**: Header swipe gestures MUST NOT conflict with browser back/forward navigation gestures
- **FR-011**: All touch targets MUST meet the 44x44px minimum size recommendation for mobile accessibility

### Key Entities

- **Header Left Group**: Contains reset button, download button, upload button. Scrollable container with right-swipe reveal
- **Header Right Group**: Contains trophy, suggest, share, tutorial, about buttons. Scrollable container with left-swipe reveal
- **Drawer Pull**: A 56x6px rounded bar centered in a 32px-tall touch target at the top of each bottom sheet panel
- **Domain Dropdown**: Fixed-position element between header-left (logo) and header-actions (left button group)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of header buttons are reachable (via direct tap or swipe-reveal) on screens as narrow as 320px
- **SC-002**: Drawer pull bar is centered within 1px tolerance on both Android (360px, 412px) and iPhone (375px, 393px) screen widths
- **SC-003**: All acceptance scenarios pass on Android emulator (Pixel 7, API 34, Chrome)
- **SC-004**: All acceptance scenarios pass on iPhone Simulator (iPhone 15, iOS 17, Safari)
- **SC-005**: No header button overlaps another button or the dropdown at any supported screen width (320px-430px)
- **SC-006**: Map pan/zoom gestures work without interference from header swipe areas on both platforms
- **SC-007**: Quiz answering flow (open drawer, read question, tap answer, see feedback) completes successfully on both platforms

## Assumptions

- Android testing uses Android Studio emulator with a Pixel 7 profile (412x915, API 34)
- iPhone testing uses Xcode Simulator with iPhone 15 profile (393x852, iOS 17)
- Minimum supported mobile width is 320px (iPhone SE / small Android devices)
- The app is accessed via mobile browser (Chrome on Android, Safari on iOS) — not a native app wrapper
- Portrait orientation is the primary mobile layout; landscape is secondary but should not break
