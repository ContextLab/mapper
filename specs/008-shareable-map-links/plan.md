# Implementation Plan: Shareable Map Links

**Branch**: `008-shareable-map-links` | **Date**: 2026-03-12 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/008-shareable-map-links/spec.md`

## Summary

Enable shareable URLs that encode a user's quiz responses as a compressed token in the query string (`?t=TOKEN`). Recipients open the link and see a read-only knowledge map rendered entirely client-side using the same renderer, estimator, and layout as the main app. The share modal gains a "Copy Link" button, Facebook/Instagram share buttons, and all social share buttons use the token URL. Open Graph and Twitter Card meta tags provide attractive link previews on all major platforms.

## Technical Context

**Language/Version**: JavaScript ES2022+ (ES modules), HTML5, CSS3
**Primary Dependencies**: nanostores 1.1, Vite 7.3, deck.gl 9.2, KaTeX (CDN), pako (new — for deflate compression)
**Storage**: localStorage (user progress), URL query parameter (shared state)
**Testing**: Vitest (unit), Playwright (visual/E2E)
**Target Platform**: Web (GitHub Pages at context-lab.com/mapper/), all modern browsers
**Project Type**: Single-page web application (static hosting, no server)
**Performance Goals**: Token generation <100ms, shared map render <3s, 60fps map interaction
**Constraints**: No server-side processing; all encoding/decoding client-side; URLs <2000 chars for typical sessions
**Scale/Scope**: ~2500 questions, typical share sessions 50-200 answered questions

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Accuracy)**: Token encoding/decoding must be lossless — every response (correct, incorrect, skipped) must round-trip exactly. Verified by unit tests with real response data, not mocks.
- **Principle II (User Delight)**: Shared map view must be visually identical to main app. Verified by Playwright screenshot comparison. CTA button and minimal chrome must look polished. OG preview image must be attractive.
- **Principle III (Compatibility)**: Shared URLs must work across all supported browsers. Token decoding must handle edge cases (truncated URLs, URL-encoded characters). Social share buttons must work on mobile and desktop. OG tags verified on all 5 platforms.

**Gate status**: PASS — no violations. Feature adds a new module without modifying core rendering.

## Project Structure

### Documentation (this feature)

```text
specs/008-shareable-map-links/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── token-format.md  # Token binary format contract
│   └── url-contract.md  # URL parameter contract
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── app.js                    # Modified: detect ?t= param, boot shared view mode
├── sharing/                  # NEW module
│   ├── token-codec.js        # Encode/decode response tokens (pako + base64url)
│   ├── question-index.js     # Stable question→integer index mapping
│   └── shared-view.js        # Read-only view bootstrap (minimal chrome, CTA)
├── ui/
│   └── share.js              # Modified: add Copy Link, Facebook, Instagram buttons
└── img/
    └── og-preview.png        # NEW: Open Graph preview image (1200x630)

index.html                    # Modified: add OG + Twitter Card meta tags

tests/
├── unit/
│   ├── token-codec.test.js   # Round-trip, compression, edge cases
│   └── question-index.test.js # Deterministic ordering, stability
└── visual/
    └── shared-view.spec.js   # Playwright: shared URL loads correctly
```

**Structure Decision**: New `src/sharing/` module keeps token logic isolated from existing code. The shared view bootstrapper (`shared-view.js`) imports from existing modules (renderer, estimator) to guarantee visual parity (FR-013). No separate HTML page — `index.html` detects the `?t=` parameter and switches to shared view mode.

## Complexity Tracking

No constitution violations — table not needed.
