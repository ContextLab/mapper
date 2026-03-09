# Feature Specification: Performance & UX Refinement

**Feature Branch**: `006-performance-and-ux-refinement`
**Created**: 2026-03-08
**Status**: Draft
**Input**: Persona testing feedback from 32 simulated users (4,632 questions) revealing Safari performance issues, domain filtering bugs, mobile UX gaps, and cold-start visual problems.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Smooth Experience on Safari (Priority: P1)

A user opens Knowledge Mapper in Safari on macOS. They click through the quiz, open the video panel, switch domains, and interact with modals. All animations are smooth, UI is responsive, and no stuttering or glitching occurs. The experience is indistinguishable from Chrome.

**Why this priority**: Safari is the default browser on macOS and iOS. Glitchy animations and unresponsive UI create a broken first impression and may cause users to abandon the tool entirely. This is the most critical issue because it affects basic usability.

**Independent Test**: Open the app in Safari, complete 10 questions while toggling panels, switching domains, and opening modals. All transitions should be smooth with no visible stutter.

**Testing approach**: Safari performance MUST be measured in two phases:
1. **Baseline capture** (before changes): Run WebKit Playwright tests to document current performance issues — stuttering transitions, dropped frames, UI freezes. This establishes the "before" benchmark.
2. **Verification** (after changes): Re-run the same tests to confirm issues are resolved and no new regressions are introduced in Chrome or Firefox.

**Acceptance Scenarios**:

1. **Given** a user on Safari (macOS or iOS), **When** they open and close the quiz panel, **Then** the panel transition animates smoothly without stuttering or layout jumps
2. **Given** a user on Safari, **When** they open the video panel while the quiz panel is open, **Then** both panels render correctly with no overlapping or flickering
3. **Given** a user on Safari, **When** they switch domains from the dropdown, **Then** the map updates and the quiz refreshes without UI freezing
4. **Given** a user on Safari, **When** they interact with any modal (expertise, share, about), **Then** the modal opens/closes with smooth animation and correct positioning
5. **Given** the Safari performance fixes are applied, **When** the full Playwright suite runs on Chromium and Firefox, **Then** no existing tests regress

---

### User Story 2 - Domain-Correct Questions Only (Priority: P1)

A user selects "Mathematics" from the domain dropdown. Every question they receive is a mathematics question. No psychology, biology, or other unrelated domain questions appear. When they switch to "Biology," only biology questions appear.

**Why this priority**: Serving cross-domain questions undermines trust in the system and corrupts the knowledge map. This is a correctness bug, not a polish issue.

**Independent Test**: Select a specific domain, answer 20 questions, and verify every question belongs to that domain or its sub-domains.

**Acceptance Scenarios**:

1. **Given** a user with "Mathematics" selected as active domain, **When** they receive a new question, **Then** the question's domain is Mathematics or a Mathematics sub-domain
2. **Given** a user with "Biology" selected, **When** they answer 50 questions, **Then** zero questions from unrelated domains (e.g., psychology, philosophy) appear
3. **Given** a user on the "All" domain, **When** they receive questions, **Then** questions from any domain may appear (no filtering)

---

### User Story 3 - Usable Map on Mobile (Priority: P2)

A user opens Knowledge Mapper on their phone. The map occupies enough screen space to be visually meaningful and interactive. They can easily toggle between the map view and the quiz, and the map is large enough to appreciate the knowledge visualization.

**Why this priority**: Mobile users reported the map is "too small to appreciate" and "doesn't pop on a phone screen." While the app is functional on mobile, the core visual experience — the knowledge map — is compromised.

**Independent Test**: Open the app on a 375px-wide viewport, answer 5 questions, and verify the map is large enough to see color patterns and the quiz doesn't permanently obscure it.

**Acceptance Scenarios**:

1. **Given** a user on a mobile device (viewport ≤ 480px), **When** the quiz panel is visible, **Then** the map is still visible and occupies at least 40% of the viewport height
2. **Given** a user on a mobile device, **When** they swipe down or tap the quiz panel header, **Then** the panel collapses to a thin drawer pull handle, revealing the full map
3. **Given** a user on a mobile device with the quiz panel collapsed, **When** they tap or swipe up on the drawer pull, **Then** the quiz panel expands back with their progress preserved and a smooth transition

---

### User Story 4 - Clean Question Content (Priority: P3)

All questions served to users have proper domain assignments, source attributions, and appropriate difficulty. No questions have "unknown" domain IDs, empty source articles, or self-answering content. Questions flagged as ambiguous in persona evaluations are fixed.

**Why this priority**: Content quality issues are minor compared to functional bugs but erode trust over time. Questions where the answer is embedded in the question text undermine the assessment's validity. Incorrectly assigned domain_ids cause cross-domain contamination (US2).

**Independent Test**: Run an audit script across all question banks to verify no orphaned domains and no self-answering patterns.

**Acceptance Scenarios**:

1. **Given** the complete question bank, **When** audited for metadata, **Then** zero questions have `domainId: "unknown"` or empty `sourceArticle` — every question's `domain_ids` must reference one of the 50 existing domains
2. **Given** the complete question bank, **When** audited for self-answering patterns, **Then** no question has the correct answer's key term embedded in the question stem
3. **Given** a user answering questions in any domain, **When** they encounter a question, **Then** the question is appropriately challenging (not trivially guessable from the question text alone)
4. **Given** questions flagged as ambiguous in persona evaluations (e.g., quantum teleportation wording, Labrador genetics epistasis/hypostasis), **When** reviewed, **Then** all flagged questions are fixed or verified correct with clear reasoning

---

### Edge Cases

- What happens when Safari version is older (Safari 15 or earlier)?
- How does the app behave on iPad (between mobile and desktop breakpoints)?
- What happens when a domain has fewer than 5 questions (sparse domain)?
- How does the cold-start visual behave when a returning user has loaded saved progress?
- What happens when a user rapidly toggles panels on Safari?
- How does domain filtering work for sub-domains with shared questions?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All CSS transitions and animations MUST render without visible stutter on Safari (macOS and iOS)
- **FR-002**: Panel transitions (quiz, video) MUST use GPU-compositable properties (transform, opacity) where possible
- **FR-003**: The domain filtering logic MUST ensure that when a specific domain is selected, only questions belonging to that domain or its descendants are served
- **FR-004**: On mobile viewports (≤ 480px), the quiz panel MUST be collapsible via swipe-down or tap to a thin drawer pull handle, revealing the full map; tapping or swiping up on the handle MUST restore the panel
- **FR-006**: All questions in the question bank MUST have a valid, non-"unknown" `domainId` and a non-empty `sourceArticle` field
- **FR-007**: Questions where the correct answer term appears verbatim in the question stem MUST be revised or replaced
- **FR-009**: Existing Playwright tests (unit + visual) MUST continue to pass after all changes
- **FR-010**: Safari-specific tests MUST be added to the test suite covering panel transitions, domain switching, and modal interactions

### Key Entities

- **Question**: Extended with validated `domainId` (non-"unknown") and `sourceArticle` (non-empty). Questions flagged as self-answering are revised.
- **Domain Filter**: The logic that maps the active domain to a set of valid question domain IDs, including descendants in the domain hierarchy.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All panel transitions on Safari complete smoothly with no dropped frames (verified via WebKit browser tests)
- **SC-002**: Zero cross-domain question contamination when a specific domain is selected (verified across 100+ questions per domain)
- **SC-003**: On mobile (375px viewport), the map occupies at least 40% of viewport height when the quiz panel is visible
- **SC-005**: Zero questions with `domainId: "unknown"` or empty `sourceArticle` in any question bank file
- **SC-006**: All 88+ existing unit tests pass with no regressions
- **SC-007**: All existing Playwright visual tests pass on Chromium, with new WebKit-specific tests added
- **SC-008**: Persona re-evaluation maintains 100% pass rate (32/32)

## Clarifications

### Session 2026-03-08

- Q: What mobile interaction pattern should users use to view the full map? → A: Collapsible quiz panel with drawer pull handle (no question number display); swipe/tap to collapse, swipe/tap to expand
- Q: Should cold-start map visuals be changed? → A: No, current rendering is fine as-is. Removed from scope.
- Q: Should a video recommendation badge indicator be added? → A: No, video discoverability is already covered by the tutorial. A badge after every question would be meaningless. Removed from scope.
- Q: How should Safari testing work? → A: Two-phase approach — baseline capture before changes to document current issues, then verification after changes to confirm fixes and no regressions.
- Q: What about question quality issues from persona evals? → A: Fix all orphaned domain_ids (must map to one of 50 existing domains), fix ambiguous questions flagged by persona evaluations.

## Assumptions

- Safari 16+ is the minimum supported version (released 2022, covers macOS Ventura+)
- iPad viewports (768px-1024px) follow desktop layout, not mobile
- The GP estimator's length scale already determines the visual spread of answered questions; cold-start improvements focus on rendering/presentation, not algorithm changes
- Self-answering question detection can be partially automated but may require manual review for edge cases
