# Tasks: Shareable Map Links

**Input**: Design documents from `/specs/008-shareable-map-links/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: Install dependencies and create module structure

- [ ] T001 Install pako dependency via `npm install pako` and verify in package.json
- [ ] T002 Create `src/sharing/` directory structure with empty module files: `token-codec.js`, `question-index.js`, `shared-view.js`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the question index and token codec that all user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 Implement stable question index builder in `src/sharing/question-index.js` — load all domain question data, sort by `(domain_ids[0], id)`, assign deterministic integer indices. Export `buildIndex(allQuestions)` returning `{ version, toIndex: Map<string,number>, toId: Map<number,string> }`
- [ ] T004 Implement token encoder in `src/sharing/token-codec.js` — `encodeToken(responses, questionIndex)` that maps response objects to sparse `(index, value)` pairs, serializes to binary format per `contracts/token-format.md` (version byte + uint16 count + entries), compresses with pako raw deflate, and returns base64url string
- [ ] T005 Implement token decoder in `src/sharing/token-codec.js` — `decodeToken(base64urlString, questionIndex)` that reverses the encoding: base64url → pako inflate → parse binary → map indices back to question_ids. Return array of `{ question_id, value }` objects. Return `null` for invalid/corrupted tokens
- [ ] T006 Write unit tests for question index in `tests/unit/question-index.test.js` — test deterministic ordering, stability across calls, handling of questions with multiple domain_ids
- [ ] T007 Write unit tests for token codec in `tests/unit/token-codec.test.js` — test round-trip encode/decode for various response counts (0, 1, 50, 200, 500), verify URL-safe characters only, verify size under 2000 chars for 200 responses, test invalid input handling

**Checkpoint**: Token codec and question index verified with unit tests

---

## Phase 3: User Story 1 - Generate Shareable Link (Priority: P1) MVP

**Goal**: Users can click "Copy Link" in the share modal to get a URL with their encoded responses

**Independent Test**: Click "Copy Link", paste URL in new tab — URL contains `?t=` parameter with valid base64url token

### Implementation for User Story 1

- [ ] T008 [US1] Add "Copy Link" button to the share modal in `src/ui/share.js` — insert a new button in both the teaser (pre-5-answers) and full share modal layouts, styled consistently with existing buttons. Use the link icon (`fa-solid fa-link`)
- [ ] T009 [US1] Wire "Copy Link" button in `src/ui/share.js` — on click: build question index from loaded domain data, call `encodeToken()` with current `$responses`, construct full URL (`window.location.origin + '/mapper/?t=' + token`), copy to clipboard, show "Copied!" feedback for 2 seconds
- [ ] T010 [US1] Handle edge case in `src/ui/share.js` — if user has 0 responses, "Copy Link" generates the generic URL (`context-lab.com/mapper/`) with no token parameter
- [ ] T011 [US1] Write Playwright test in `tests/visual/shared-link-generate.spec.js` — answer 10 questions, open share modal, click "Copy Link", verify clipboard contains a URL with `?t=` parameter, verify the token is valid base64url

**Checkpoint**: User Story 1 complete — "Copy Link" button generates valid token URLs

---

## Phase 4: User Story 2 - View Shared Map (Priority: P1) MVP

**Goal**: Recipients open a token URL and see a read-only knowledge map with minimal chrome

**Independent Test**: Open `localhost:5173/mapper/?t={token}` in incognito — map renders with response dots, no header/quiz/video, CTA button visible

### Implementation for User Story 2

- [ ] T012 [US2] Add `?t=` parameter detection in `src/app.js` — at boot, parse `URLSearchParams` for `t` param. If present and non-empty, set a flag (e.g., `window.__sharedViewMode = true`) and call `initSharedView(token)` instead of normal boot sequence
- [ ] T013 [US2] Implement shared view bootstrapper in `src/sharing/shared-view.js` — export `initSharedView(tokenString)` that: (1) decodes the token, (2) loads the "all" domain bundle, (3) builds question index, (4) maps decoded entries to SyntheticResponse objects with x/y coordinates from question data, (5) runs GP estimator with synthetic responses, (6) initializes the renderer with the heatmap + response dots
- [ ] T014 [US2] Implement minimal chrome in `src/sharing/shared-view.js` — hide header toolbar, quiz panel, video panel, minimap, drawer pulls, and landing screen. Show only the map canvas and a fixed-bottom CTA button: "Map your *own* knowledge!" linking to `/mapper/`
- [ ] T015 [US2] Style the CTA button in `src/sharing/shared-view.js` — fixed position bottom-center, prominent primary color background, rounded, responsive (adapts to mobile/desktop), with hover effect
- [ ] T016 [US2] Handle invalid tokens in `src/app.js` — if `decodeToken()` returns null, log a console warning and fall back to normal app boot (landing screen). No user-visible error
- [ ] T017 [US2] Ensure shared view does NOT touch localStorage — verify in `src/sharing/shared-view.js` that no `$responses.set()`, `$watchedVideos.set()`, or other persistent store writes occur. Also verify that rendering uses ONLY the decoded SyntheticResponse array, NOT `$responses.get()` from localStorage. If existing localStorage data is present, it must be ignored entirely in shared view mode
- [ ] T018 [US2] Write Playwright test in `tests/visual/shared-view.spec.js` — programmatically encode a token for 20 responses, navigate to `/?t={token}`, verify: (a) map canvas is visible, (b) response dots render (screenshot comparison), (c) no header toolbar visible, (d) CTA button visible and clickable, (e) CTA navigates to `/mapper/`

**Checkpoint**: User Stories 1 + 2 complete — full shareable link round-trip works

---

## Phase 5: User Story 3 - Social Media Share Buttons (Priority: P2)

**Goal**: Social share buttons use the token URL; Facebook and Instagram buttons added

**Independent Test**: Click each social button, verify compose/share window contains the token URL

### Implementation for User Story 3

- [ ] T019 [P] [US3] Add Facebook share button to both share modal layouts in `src/ui/share.js` — use `fa-brands fa-facebook` icon, Facebook blue (#1877f2), position in the button grid alongside existing buttons
- [ ] T020 [P] [US3] Add Instagram share button to both share modal layouts in `src/ui/share.js` — use `fa-brands fa-instagram` icon, Instagram gradient or purple (#e4405f), position in the button grid
- [ ] T021 [US3] Implement Facebook share action in `handleShareAction()` in `src/ui/share.js` — open `https://www.facebook.com/sharer/sharer.php?u={tokenUrl}` in a new tab
- [ ] T022 [US3] Implement Instagram share action in `handleShareAction()` in `src/ui/share.js` — copy share text (including token URL) to clipboard, show feedback prompt "Copied! Paste into Instagram" for 3 seconds
- [ ] T023 [US3] Update all social share buttons in `src/ui/share.js` to use the token URL — when responses exist, generate the token URL and pass it as the share URL to LinkedIn, X/Twitter, Bluesky, Facebook. Fall back to generic URL when no responses
- [ ] T024 [US3] Write Playwright test in `tests/visual/social-share-buttons.spec.js` — answer 5 questions, open share modal, verify all 5 social buttons are visible (LinkedIn, X, Bluesky, Facebook, Instagram), click Copy button and verify clipboard contains token URL

**Checkpoint**: All social share buttons use token URLs, Facebook and Instagram added

---

## Phase 6: User Story 4 - Token Versioning (Priority: P2)

**Goal**: Token format is versioned so old tokens remain valid when questions are added/removed

**Independent Test**: Generate a token, modify the question bank, reload the token URL — map still renders

### Implementation for User Story 4

- [ ] T025 [US4] Add version management to `src/sharing/question-index.js` — compute a version hash from the sorted question ID list (e.g., simple CRC or count-based version). Store the version byte in the index. Export `getIndexVersion()`.
- [ ] T026 [US4] Implement version-aware decoding in `src/sharing/token-codec.js` — when decoding, check the version byte. If the version matches the current index, decode normally. If it differs, decode entries and silently skip any index that has no matching question_id in the current index
- [ ] T027 [US4] Write unit test for forward compatibility in `tests/unit/token-codec.test.js` — encode a token, simulate adding/removing questions (modify the index), decode the token with the new index, verify: old responses decode correctly, removed questions are silently skipped, new questions appear as unanswered

**Checkpoint**: Token versioning verified — old tokens survive question bank changes

---

## Phase 7: User Story 5 - Social Media Link Previews (Priority: P2)

**Goal**: Open Graph and Twitter Card meta tags produce attractive link preview cards on all platforms

**Independent Test**: Paste URL into Twitter Card Validator and Facebook Sharing Debugger — preview card shows title, description, and image

### Implementation for User Story 5

- [ ] T028 [P] [US5] Create the OG preview image at `src/img/og-preview.png` — create a NEW 1200x630px canvas (do NOT reuse `generateShareImage()` which is 800x600). Render a pre-populated knowledge map heatmap at this size, then overlay white text with dark shadow: title "Knowledge Mapper" (top-center, bold, ~48px) and tagline "Map out everything you know!" (below title, ~24px). Ensure text is legible at both thumbnail and large card sizes
- [ ] T029 [P] [US5] Add Open Graph meta tags to `index.html` — add `og:title` ("Knowledge Mapper"), `og:description` ("An interactive tool that maps out everything you know. Answer questions and watch your personalized knowledge map take shape."), `og:image` (absolute URL to og-preview.png on GitHub Pages), `og:url`, `og:type` ("website")
- [ ] T030 [P] [US5] Add Twitter Card meta tags to `index.html` — add `twitter:card` ("summary_large_image"), `twitter:title`, `twitter:description`, `twitter:image` matching the OG values
- [ ] T031 [US5] Verify link previews using platform debugger tools — test with Twitter Card Validator, Facebook Sharing Debugger, LinkedIn Post Inspector. Take screenshots of each preview for verification. Document any platform-specific issues
- [ ] T032 [US5] Test Bluesky and Instagram link previews — share a deployed URL on Bluesky and verify the link card renders. For Instagram, verify the OG image appears when sharing a link in Instagram Stories/DMs

**Checkpoint**: Link previews verified on all 5 target platforms

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final quality, compatibility, and regression checks

- [ ] T033 Run all existing unit tests (`npm test`) and verify no regressions from new code
- [ ] T034 Run all existing Playwright tests (`npm run test:visual`) and verify no regressions
- [ ] T035 [P] Cross-browser Playwright test for shared view — test shared URL loading in Chromium, Firefox, and WebKit engines
- [ ] T036 [P] Mobile viewport Playwright test — test shared view at 375x667 (iPhone), 390x844 (iPhone 14), 360x800 (Android) — verify CTA button is visible and map renders
- [ ] T037 Run quickstart.md validation — manually execute all 8 quickstart scenarios and verify expected outcomes
- [ ] T038 Verify token size constraints — generate tokens for 50, 100, 200, 500, and 2500 responses, confirm URL lengths match size guarantees in contracts/token-format.md
- [ ] T039 Screenshot verification per Constitution Principle II — take Playwright screenshots of: (a) share modal with Copy Link button, (b) shared view with CTA, (c) shared view on mobile, (d) share modal with all 5 social buttons. Visually verify polish and consistency

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — MVP target
- **US2 (Phase 4)**: Depends on Phase 2 + partially on US1 (uses same codec)
- **US3 (Phase 5)**: Depends on Phase 2 — can run in parallel with US1/US2
- **US4 (Phase 6)**: Depends on Phase 2 — can run in parallel with US1/US2/US3
- **US5 (Phase 7)**: No code dependencies on other stories — can start anytime after Setup
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Depends on Foundational only — independent
- **US2 (P1)**: Depends on Foundational only — uses same codec as US1 but independently testable
- **US3 (P2)**: Depends on Foundational — builds on share modal (same file as US1 but different functions)
- **US4 (P2)**: Depends on Foundational — extends codec (same file as Phase 2 but additive)
- **US5 (P2)**: Depends on Setup only — static assets and HTML meta tags, no JS dependencies

### Parallel Opportunities

- T006 and T007 can run in parallel (different test files)
- T019 and T020 can run in parallel (different buttons, same file but additive)
- T028, T029, T030 can all run in parallel (different files)
- T035 and T036 can run in parallel (different test configurations)
- US5 can start as early as Phase 1 completion (no dependency on codec)

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Setup (install pako, create module structure)
2. Complete Phase 2: Foundational (question index + token codec with tests)
3. Complete Phase 3: US1 (Copy Link button in share modal)
4. Complete Phase 4: US2 (shared view rendering)
5. **STOP and VALIDATE**: Generate a link, open in new tab, verify full round-trip

### Incremental Delivery

1. Setup + Foundational → codec verified with unit tests
2. Add US1 → "Copy Link" button works → testable
3. Add US2 → full round-trip works → deployable MVP!
4. Add US3 → social buttons use token URL → enhanced sharing
5. Add US4 → versioned tokens → future-proof
6. Add US5 → OG previews → polished social presence
7. Polish → cross-browser, mobile, regression checks
