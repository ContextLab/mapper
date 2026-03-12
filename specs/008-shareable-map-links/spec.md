# Feature Specification: Shareable Map Links

**Feature Branch**: `008-shareable-map-links`
**Created**: 2026-03-12
**Status**: Draft
**Input**: GitHub Issue #59 — improve social media sharing
**References**: [ContextLab/scheduler](https://github.com/ContextLab/scheduler) (prior art for token-based state encoding)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate Shareable Link (Priority: P1)

A user has answered several quiz questions and wants to share their knowledge map with someone else. Instead of downloading an image and manually pasting it, they click "Share" and get a URL that encodes their responses. They copy this link and paste it into a social media post, email, or message.

**Why this priority**: This is the core value proposition — eliminating the awkward manual image-pasting workflow. A shareable URL is the simplest, most universal way to share state across any platform.

**Independent Test**: Generate a token URL after answering questions, paste it into a new browser tab, and verify the map renders correctly with the same response data.

**Acceptance Scenarios**:

1. **Given** a user has answered at least 1 question, **When** they click "Share" and then "Copy Link", **Then** a URL containing an encoded token is copied to their clipboard
2. **Given** a user has answered 100 questions, **When** a link is generated, **Then** the URL is under 2000 characters total
3. **Given** a user has answered questions across multiple domains, **When** a link is generated, **Then** all responses (correct, incorrect, skipped) are encoded in the token
4. **Given** a user has answered 0 questions, **When** they open the share modal, **Then** the "Copy Link" button generates a generic link to the mapper (no token)

---

### User Story 2 - View Shared Map (Priority: P1)

A recipient clicks a shared link (e.g., `context-lab.com/mapper/?t=TOKEN`). The page loads directly into map view showing the "All (general)" domain with the sharer's responses pre-populated. The GP estimator runs, the heatmap renders, and answered questions appear as dots — all without user interaction. The view is read-only (no quiz panel, no ability to answer new questions).

**Why this priority**: Without a working load route, shareable links have no value. This is co-equal with US1.

**Independent Test**: Construct a token URL manually (or programmatically), open it in a fresh browser, and verify the map renders with correct response markers.

**Acceptance Scenarios**:

1. **Given** a valid token URL, **When** a user opens it in a new browser, **Then** the map renders with the encoded responses visible as colored dots (green=correct, red=incorrect, yellow=skipped)
2. **Given** a valid token URL, **When** the page loads, **Then** the view is minimal chrome: map rendering only, no header toolbar, no video panel, no minimap, no quiz drawer — plus a "Map your *own* knowledge!" CTA button linking to the main app
3. **Given** a valid token URL, **When** the page loads, **Then** it displays the "All (general)" domain view regardless of which domain the sharer was using
4. **Given** a valid token URL, **When** the page loads, **Then** the landing/welcome screen is skipped entirely
5. **Given** a token URL with an invalid or corrupted token, **When** a user opens it, **Then** the app loads normally (landing screen) with no error shown to the user

---

### User Story 3 - Social Media Share Buttons with Token URL (Priority: P2)

When the share modal opens and a token URL is available, the social media buttons (LinkedIn, X/Twitter, Bluesky, Facebook, Instagram) pre-fill the post with the token URL instead of the generic `context-lab.com/mapper` link. Recipients who click the link in the social post see the sharer's actual map.

**Why this priority**: Enhances the sharing experience but builds on US1/US2. The core copy-link flow works without this.

**Independent Test**: Click each social share button, verify the pre-filled post text contains the token URL, and confirm the linked map renders correctly.

**Acceptance Scenarios**:

1. **Given** a user has answered questions and opens the share modal, **When** they click the Twitter/X button, **Then** the tweet compose window pre-fills with text containing the token URL
2. **Given** a user has answered questions, **When** they click LinkedIn, **Then** the share URL passed to LinkedIn is the token URL (not the generic mapper URL)
3. **Given** a user has answered questions, **When** they click Bluesky, **Then** the compose window pre-fills with the token URL
4. **Given** a user has answered questions, **When** they click Facebook, **Then** the Facebook share dialog opens with the token URL
5. **Given** a user has answered questions, **When** they click Instagram, **Then** the share text (with token URL) is copied to clipboard with a prompt to paste into Instagram (Instagram does not support direct URL share intents)

---

### User Story 4 - Token Versioning and Forward Compatibility (Priority: P2)

The token format includes a version identifier so that when new questions are added or removed in future updates, old tokens remain valid. Questions that no longer exist are silently ignored. New questions appear as unanswered.

**Why this priority**: Without versioning, shared links break every time the question bank changes. This is essential for link longevity but can be added alongside US1/US2.

**Independent Test**: Generate a token, add a new question to a domain, reload the token URL, and verify the map still renders correctly (new question shows as unanswered, all old responses preserved).

**Acceptance Scenarios**:

1. **Given** a token generated with version 1 of the question bank, **When** new questions are added (version 2), **Then** the token still decodes correctly — old responses display, new questions show as unanswered
2. **Given** a token generated with the current question bank, **When** a question is removed, **Then** the response for that question is silently ignored during decoding
3. **Given** any valid token, **When** decoded, **Then** the version byte is present and parseable

---

### User Story 5 - Social Media Link Previews (Priority: P2)

When a token URL is shared on social media platforms (LinkedIn, X/Twitter, Bluesky, Facebook, Instagram), the link preview card looks polished and inviting. Since social platforms don't execute JavaScript, the preview uses static Open Graph meta tags with a compelling generic image, title, and description that encourage clicks.

**Why this priority**: Link previews are what most people see first — a broken or missing preview makes shares look unprofessional and reduces click-through. This is critical for virality but depends on US1/US2 being functional first.

**Independent Test**: Paste a token URL into each platform's link preview debugger/validator tool and verify the preview card renders correctly with the expected image, title, and description.

**Acceptance Scenarios**:

1. **Given** a token URL is pasted into a LinkedIn post, **When** LinkedIn fetches the preview, **Then** a card appears with the Knowledge Mapper title, a descriptive tagline, and an attractive preview image
2. **Given** a token URL is pasted into a tweet on X/Twitter, **When** the tweet is previewed, **Then** a Twitter Card appears with a large image preview, title, and description
3. **Given** a token URL is posted on Facebook, **When** Facebook scrapes the URL, **Then** an Open Graph card renders with image, title, and description
4. **Given** a token URL is shared on Bluesky, **When** Bluesky fetches the preview, **Then** a link card appears with image and title
5. **Given** a generic mapper URL (no token) is shared, **When** any platform fetches the preview, **Then** the same preview card appears (previews are static, not token-specific)
6. **Given** the preview image, **When** viewed at various card sizes across platforms, **Then** the image looks good at both small (thumbnail) and large (summary_large_image) sizes

---

### Edge Cases

- What happens when a token URL is shared on a platform that truncates URLs beyond a certain length? Tokens for typical sessions (~100 questions) should stay under 2000 chars. For extreme cases (all 2500 questions answered), URLs may reach ~1000 chars — still well within browser and platform limits.
- What happens when a user visits a token URL on mobile? The same responsive layout applies; the read-only map should render correctly on all screen sizes.
- What happens when the same user opens their own shared link? They see their map in read-only mode (same as any other recipient). To continue answering, they use the normal app or import/export.
- What happens if the token contains responses for questions that don't exist in the current question bank? Those responses are silently ignored.
- What happens if the URL has `?t=` with an empty value? App loads normally (landing screen).
- What happens if both `?t=TOKEN` and localStorage responses exist? The token takes precedence for the shared view — localStorage is not modified.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST assign each question a stable, deterministic index based on domain name + question ID (sorted order)
- **FR-002**: System MUST encode user responses as a sparse representation: only non-zero entries stored as (index, value) pairs where 0=unanswered, 1=skipped, 2=correct, -1=incorrect
- **FR-003**: System MUST compress the sparse encoding and produce a URL-safe base64 token
- **FR-004**: System MUST include a version byte in the token format to support forward compatibility
- **FR-005**: System MUST decode a valid token from the `?t=` URL parameter and reconstruct the response array
- **FR-006**: System MUST render the shared map in minimal chrome mode — map only with a "Map your *own* knowledge!" CTA button. No header toolbar, no video panel, no minimap, no quiz drawer
- **FR-007**: System MUST always render shared maps in the "All (general)" domain view
- **FR-008**: System MUST skip the landing/welcome screen when a valid token is present
- **FR-009**: System MUST preserve the existing "Download Image" and "Copy Image" share options alongside the new "Copy Link" option
- **FR-010**: System MUST update social media share buttons to use the token URL when responses exist
- **FR-011**: System MUST gracefully handle invalid/corrupted tokens by falling back to normal app load
- **FR-012**: System MUST NOT modify localStorage when loading a shared token URL
- **FR-013**: The shared view page MUST use the exact same rendering code as the main mapper — no separate "load page" that could drift out of sync
- **FR-014**: System MUST generate URLs under 2000 characters for sessions with 200 or fewer answered questions
- **FR-015**: Share modal MUST include Facebook and Instagram share buttons in addition to existing LinkedIn, X/Twitter, and Bluesky buttons
- **FR-016**: System MUST include Open Graph meta tags (`og:title`, `og:description`, `og:image`, `og:url`) in the page HTML for social media link previews
- **FR-017**: System MUST include Twitter Card meta tags (`twitter:card`, `twitter:title`, `twitter:description`, `twitter:image`) for X/Twitter previews
- **FR-018**: The preview image MUST be a pre-generated knowledge map screenshot with title/tagline overlaid, sized for both thumbnail and large card formats (minimum 1200x630px for Open Graph, 800x418px for Twitter)
- **FR-019**: Link previews MUST display correctly on all 5 target platforms (LinkedIn, X/Twitter, Bluesky, Facebook, Instagram) as verified using each platform's preview debugger/validator
- **FR-020**: Instagram share button MUST copy the share text (including token URL) to clipboard with a user-facing prompt, since Instagram does not support direct URL share intents

### Key Entities

- **Response Token**: A versioned, compressed, URL-safe encoding of a user's quiz responses. Contains: version byte, sparse (index, value) pairs for all non-zero responses.
- **Question Index**: A stable mapping from (domain, question ID) to a deterministic integer index. Used to encode/decode response positions in the token.
- **Shared View**: A read-only rendering of the knowledge map from a decoded token. Uses the same renderer, estimator, and layout as the main app but with the quiz panel disabled.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can generate a shareable link in under 2 seconds from the share modal
- **SC-002**: Recipients see a fully rendered knowledge map within 3 seconds of opening a shared link
- **SC-003**: 100% of token URLs generated from sessions with 200 or fewer answers are under 2000 characters
- **SC-004**: Tokens generated today remain decodable after question bank updates (verified by adding/removing questions and re-testing)
- **SC-005**: The shared map view is visually identical to the main app's map view for the same response data
- **SC-006**: All existing share functionality (download image, copy image, social buttons) continues working without regression
- **SC-007**: Link previews on all 5 target platforms (LinkedIn, X/Twitter, Bluesky, Facebook, Instagram) display the correct title, description, and preview image as verified by platform debugger tools
- **SC-008**: Share modal includes all 5 social platform buttons (LinkedIn, X/Twitter, Bluesky, Facebook, Instagram) plus Copy Link, Copy Image, and Download Image

## Clarifications

### Session 2026-03-12

- Q: What UI elements should be visible in the shared read-only view? → A: Minimal chrome — map only + a slim "Map your *own* knowledge!" CTA button linking to the main app. No header toolbar, no video panel, no minimap.
- Q: What should the Open Graph preview image depict? → A: A real pre-generated knowledge map screenshot with title/tagline overlaid, showing what the product actually looks like.

## Assumptions

- The app is hosted on GitHub Pages at `context-lab.com/mapper/` — no server-side processing is available. All encoding/decoding must happen client-side.
- Compression (deflate/pako) can reduce sparse response data to fit comfortably in URL query parameters.
- Social media platforms (Twitter, LinkedIn, Bluesky) support URLs up to at least 2000 characters in share intents.
- The question bank currently has ~2500 questions. A typical sharing session involves 50-200 answered questions.
- Watched-video state is NOT included in the token (per issue discussion).
- Active domain is NOT encoded — shared maps always show "All (general)" view.
