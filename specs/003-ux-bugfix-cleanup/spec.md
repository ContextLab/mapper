# Feature Specification: UX Cleanup & Bug Fix Sweep

**Feature Branch**: `003-ux-bugfix-cleanup`
**Created**: 2026-02-27
**Status**: Draft
**Input**: User description: "Massive cleanup and bug fix effort addressing 13 reported issues across keyboard input, video discoverability, canvas rendering, estimator math, quiz UX, import flow, and share modal."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Knowledge Estimator Produces Accurate Maps After Many Questions (Priority: P1)

A user answers 100+ questions across a domain. The heatmap updates incrementally with each answer, reflecting a gradual refinement of their knowledge portrait. The map never collapses into a uniform blob, never jumps discontinuously, and "domain mapped" progresses steadily rather than stalling or leaping.

**Why this priority**: This is the core product experience. If the estimator breaks after extended use, the entire value proposition fails. Two critical math bugs feed this: (a) the estimator collapse at ~115-120 questions where the map jumps from 18% to 95%, and (b) Cholesky decomposition / divide-by-zero console errors indicating numerical instability.

**Independent Test**: Can be tested by automating 150 question-answer cycles and asserting that heatmap values change smoothly, "domain mapped" never jumps more than 5% in a single answer, and no console errors appear.

**Acceptance Scenarios**:

1. **Given** a user has answered 50 questions, **When** they answer question 51, **Then** the heatmap updates smoothly with no discontinuity greater than 5% in domain mapped.
2. **Given** a user has answered 120 questions, **When** they answer question 121, **Then** no Cholesky decomposition or divide-by-zero errors appear in the console and the map renders normally.
3. **Given** a user has answered 150 questions across varied difficulty levels, **When** viewing the heatmap, **Then** it shows a gradient of knowledge levels (not a uniform blob) and "domain mapped" reflects actual coverage.

---

### User Story 2 - Difficulty-Aware Knowledge Estimation (Priority: P1)

The system correctly weighs evidence from questions of different difficulty levels. Getting a hard question wrong provides less negative evidence than getting an easy question wrong (it's expected to miss hard questions). Skipping a question ("Don't know") provides stronger evidence of lack of knowledge than guessing incorrectly (the user is proactively declaring ignorance).

**Why this priority**: Incorrect weighting means the heatmap fundamentally misrepresents the user's knowledge, undermining trust in the core product.

**Independent Test**: Can be tested by comparing heatmap values for specific cells after controlled answer sequences — e.g., answering an expert question wrong vs. an easy question wrong at the same map location.

**Acceptance Scenarios**:

1. **Given** two questions at similar map coordinates with different difficulty levels, **When** the user answers the hard question incorrectly, **Then** the negative impact on the heatmap is smaller than answering the easy question incorrectly.
2. **Given** a question the user skips ("Don't know"), **When** comparing the heatmap impact to answering the same question incorrectly, **Then** the skip produces a larger negative impact (stronger evidence of lack of knowledge).

---

### User Story 3 - Skip Reveals Correct Answer (Priority: P2)

When a user selects "Don't know (skip)", the system reveals the correct answer and displays learning resource links (Wikipedia, Khan Academy, etc.), just like when a wrong answer is selected. This turns every interaction into a learning opportunity.

**Why this priority**: Important for the educational mission of the product. Users who skip want to learn — showing them the answer and resources is high-value, low-effort.

**Independent Test**: Can be tested by clicking "Don't know (skip)" and verifying the correct answer highlights and resource links appear.

**Acceptance Scenarios**:

1. **Given** a question is displayed, **When** the user clicks "Don't know (skip)", **Then** the correct answer is highlighted and source links (Wikipedia article, Khan Academy video if available) are displayed.
2. **Given** a question is displayed with auto-advance enabled, **When** the user clicks "Don't know (skip)", **Then** the correct answer and resources are shown for a brief viewing period before advancing.

---

### User Story 4 - Keyboard Shortcuts Respect Modifier Keys (Priority: P2)

Users can press A, B, C, or D to select quiz answers via keyboard. However, pressing these letters with modifier keys (Cmd, Ctrl, Alt, Shift) does NOT trigger answer selection. This prevents accidental answer submission when using standard keyboard shortcuts like Cmd+C (copy) or Ctrl+A (select all).

**Why this priority**: This silently corrupts user data — accidental answers cannot be undone and pollute the knowledge estimate.

**Independent Test**: Can be tested by pressing Cmd+C while a question is displayed and verifying no answer is selected.

**Acceptance Scenarios**:

1. **Given** a question with 4 options is displayed, **When** the user presses the bare "C" key, **Then** option C is selected.
2. **Given** a question with 4 options is displayed, **When** the user presses Cmd+C, **Then** no option is selected and the browser's copy function executes normally.
3. **Given** a question with 4 options is displayed, **When** the user presses Ctrl+A, Shift+B, or Alt+D, **Then** no option is selected.

---

### User Story 5 - Hover Popup Does Not Block Map Scrolling (Priority: P2)

When click-dragging to scroll the map, any open article/video hover popup dismisses immediately so it cannot intercept the drag gesture. The user can freely scroll in any direction without the popup trapping their cursor.

**Why this priority**: This makes basic map navigation frustrating, especially scrolling left where the popup appears directly in the drag path.

**Independent Test**: Can be tested by hovering over an article dot (popup appears), then click-dragging leftward through where the popup was and verifying continuous smooth scrolling.

**Acceptance Scenarios**:

1. **Given** a hover popup is visible for an article, **When** the user begins a click-drag gesture, **Then** the popup dismisses immediately and the map scrolls smoothly.
2. **Given** the user is click-dragging across the map, **When** the cursor passes over article/video dots, **Then** no popups appear during the drag.

---

### User Story 6 - Canvas Resize Alignment (Priority: P2)

When the user resizes their browser window, all visual layers (background grid, article dots, video markers, answered question markers) resize and reposition in lockstep. No layer drifts relative to others.

**Why this priority**: Visual misalignment undermines trust in the visualization's accuracy and looks buggy.

**Independent Test**: Can be tested by rendering the map, resizing the window, and verifying that article dots remain aligned with their corresponding grid cells.

**Acceptance Scenarios**:

1. **Given** the map is displayed with articles and answered questions visible, **When** the user resizes the browser window, **Then** articles, videos, and answered questions maintain their positions relative to the background grid.
2. **Given** the map is displayed at any zoom level, **When** the window is resized, **Then** no visual displacement occurs between any layers.

---

### User Story 7 - Import Progress Works From Landing Page (Priority: P2)

Uploading a progress JSON from the landing page (before entering the map) correctly loads all answered questions, displays all their markers on the map, and shows the full heatmap — identical to importing from within the map screen.

**Why this priority**: Users who export and re-import (e.g., switching devices) hit this on their first interaction. A broken import on the landing page is a bad first re-engagement experience.

**Independent Test**: Can be tested by exporting progress, reloading to the landing page, importing the JSON, and verifying all question markers and heatmap are present.

**Acceptance Scenarios**:

1. **Given** a user is on the landing page with an exported progress JSON, **When** they import the file, **Then** the map loads with all previously answered questions shown as markers and the heatmap reflects all responses.
2. **Given** a progress JSON with 50 answered questions, **When** imported from the landing page, **Then** all 50 question markers appear (not just the first one).

---

### User Story 8 - Minimap Viewport Dragging (Priority: P3)

Users can click and drag the viewport rectangle in the minimap to pan around the main map. The cursor shows a "grabbing" hand during drag, and the main map viewport follows the drag position smoothly.

**Why this priority**: The minimap already hints at this feature with its cursor styling. Fixing it completes an expected interaction pattern.

**Independent Test**: Can be tested by clicking the viewport rectangle in the minimap and dragging it to a new position, verifying the main map pans accordingly.

**Acceptance Scenarios**:

1. **Given** the minimap is visible with a viewport rectangle, **When** the user clicks inside the viewport rectangle and drags, **Then** the main map pans to follow the drag position.
2. **Given** the user clicks the minimap outside the viewport rectangle, **When** they release the click, **Then** the main map centers on the clicked position.

---

### User Story 9 - Video Discovery Panel (Priority: P3)

A left sidebar panel provides a browsable, viewport-filtered list of video lectures. The list dynamically updates as the user pans and zooms the map, showing only videos whose full-text embedding positions fall within the current viewport. Users can toggle video marker visibility on the map, hover over a video in the list to highlight its trajectory on the map, and click a video to open it in the embedded player.

**Why this priority**: Video trajectories being invisible by default makes the video recommendation system hard to discover. A dedicated panel solves discoverability without cluttering the map. Viewport filtering keeps the list manageable (typically 10-50 videos) instead of showing all 5,400+.

**Independent Test**: Can be tested by opening the video panel, panning the map to different regions and verifying the list updates, hovering over a video to see its trajectory appear on the map, and clicking to open the player.

**Acceptance Scenarios**:

1. **Given** the user is on the map screen, **When** they open the video panel, **Then** a scrollable list of videos whose embedding dots are in the current viewport appears in a left sidebar.
2. **Given** the video panel is open, **When** the user pans or zooms the map, **Then** the video list updates to reflect only videos with embedding positions visible in the new viewport.
3. **Given** the video panel is open, **When** the user hovers over a video in the list, **Then** that video's trajectory (map positions) is highlighted on the map.
4. **Given** the video panel is open, **When** the user clicks a video, **Then** the embedded YouTube player opens and plays that video.
5. **Given** the video panel is open, **When** the user types a search term in the filter input, **Then** the video list narrows to only videos whose titles match the search term (within the current viewport).
6. **Given** the video panel is open, **When** the user toggles "Show all videos", **Then** all video markers become visible/hidden on the map.

---

### User Story 10 - Share Modal Works Correctly (Priority: P3)

The share modal's social media buttons open the correct sharing URLs (Twitter/X, Facebook, etc.) directly in new tabs. The "Copy" button copies the share text to clipboard. The "Copy Image" button copies the generated screenshot image to clipboard. These are three distinct actions that each work independently.

**Why this priority**: The share feature is the primary viral growth mechanism but currently non-functional.

**Independent Test**: Can be tested by opening the share modal and verifying each button performs its specific action.

**Acceptance Scenarios**:

1. **Given** the share modal is open, **When** the user clicks a social media button (e.g., Twitter), **Then** a new tab opens with the platform's share composer pre-filled with the share text and image.
2. **Given** the share modal is open, **When** the user clicks "Copy", **Then** the share text is copied to the clipboard (verified by pasting).
3. **Given** the share modal is open, **When** the user clicks "Copy Image", **Then** the generated screenshot image is copied to the clipboard.

---

### User Story 11 - Article Title Formatting (Priority: P3)

Article titles displayed next to "Source:" in question metadata show clean, readable names with spaces — not raw Wikipedia URL slugs with underscores.

**Why this priority**: Minor polish issue but affects perceived quality on every question.

**Independent Test**: Can be tested by answering questions sourced from articles with multi-word titles and verifying no underscores appear.

**Acceptance Scenarios**:

1. **Given** a question sourced from a Wikipedia article with a multi-word title, **When** the source is displayed, **Then** the title shows spaces between words (e.g., "Quantum Field Theory" not "Quantum_Field_Theory").

---

### Edge Cases

- What happens when the estimator encounters a numerically singular matrix (all answers concentrated in a small region)?
- How does the system handle importing a progress file with questions that no longer exist in the current question set?
- What happens if the user rapidly resizes the window while the map is mid-transition?
- How does the video panel behave when there are 0 videos available for the current domain view?
- What happens when the user presses A/B/C/D while no question is displayed (e.g., between questions during auto-advance)?

## Requirements *(mandatory)*

### Functional Requirements

**Estimator & Math (Critical)**
- **FR-001**: System MUST handle numerically unstable matrix operations gracefully without producing console errors or visual artifacts, even after 200+ answered questions.
- **FR-002**: System MUST ensure "domain mapped" percentage progresses smoothly without jumps greater than 5% from a single answer.
- **FR-003**: System MUST weight incorrect answers on hard questions less negatively than incorrect answers on easy questions (difficulty-inverse penalty).
- **FR-004**: System MUST weight "Don't know (skip)" responses more negatively than incorrect guesses (skip implies stronger evidence of lack of knowledge).

**Quiz UX**
- **FR-005**: System MUST ignore keyboard answer shortcuts (A/B/C/D) when any modifier key (Cmd, Ctrl, Alt, Shift) is held.
- **FR-006**: System MUST reveal the correct answer and source/resource links when the user selects "Don't know (skip)".
- **FR-007**: System MUST display article source titles with spaces, not underscores.

**Map Interaction**
- **FR-008**: System MUST dismiss hover popups immediately when a click-drag gesture begins.
- **FR-009**: System MUST NOT show hover popups during an active drag gesture.
- **FR-010**: System MUST keep all visual layers (grid, articles, videos, answered questions) aligned during and after browser window resize.
- **FR-011**: System MUST support click-and-drag panning of the viewport rectangle within the minimap.

**Video Discovery**
- **FR-012**: System MUST provide a toggleable left sidebar panel listing viewport-filtered videos with a search/filter input.
- **FR-013**: System MUST highlight a video's map trajectory when the user hovers over it in the video panel list.
- **FR-014**: System MUST open the embedded YouTube player when a video is clicked in the panel list.
- **FR-015**: System MUST provide a toggle to show/hide all video markers on the map.

**Import/Export**
- **FR-016**: System MUST correctly display all answered question markers when progress is imported from the landing page (not just the first question).

**Share**
- **FR-017**: System MUST open social media share composers in new browser tabs with pre-filled content.
- **FR-018**: System MUST copy share text to clipboard when "Copy" is clicked.
- **FR-019**: System MUST copy the generated screenshot image to clipboard when "Copy Image" is clicked.

### Key Entities

- **Response**: A user's answer to a question — includes question ID, selected answer, correctness, skip status, difficulty level, and map coordinates.
- **Estimate**: A grid-cell-level knowledge prediction produced by the RBF estimator from accumulated responses.
- **Video Marker**: A point on the map representing a segment of a video lecture, with coordinates from the embedding pipeline.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can answer 200 questions without any console errors (Cholesky, divide-by-zero, or NaN).
- **SC-002**: "Domain mapped" percentage never jumps more than 5% from a single answer across 200-question sessions.
- **SC-003**: Heatmap visual continuity: no single answer causes more than 10% of grid cells to change by more than 0.3 (on a 0-1 scale).
- **SC-004**: Keyboard shortcuts (Cmd+C, Ctrl+A, etc.) never accidentally trigger answer selection.
- **SC-005**: Users can import previously exported progress from the landing page and see 100% of their answered question markers immediately.
- **SC-006**: All three share modal actions (social share, copy text, copy image) complete successfully without opening unintended native dialogs.
- **SC-007**: Map scrolling via click-drag is never blocked by hover popups.
- **SC-008**: After browser resize, no visual layer is offset by more than 1 pixel relative to any other layer.

## Clarifications

### Session 2026-02-27

- Q: Should the video panel show all 5,400+ videos or filter by context? → A: Show only videos whose full-text embedding dots fall within the current map viewport. List updates dynamically as user pans/zooms. Include a search/filter input for further narrowing by title.

## Assumptions

- The existing RBF kernel estimator architecture is retained; fixes address numerical stability and weight formulas, not a full rewrite.
- The video panel design mirrors the existing quiz panel pattern (collapsible sidebar) for UI consistency.
- "Difficulty level" for questions is already present in the question data (the `difficulty` field).
- The share modal issues are caused by incorrect use of the Web Share API vs. direct URL-based sharing; the fix will prefer direct URL sharing with Web Share API as a progressive enhancement fallback.
- Article title underscores originate from Wikipedia URL slugs stored in question source metadata.
