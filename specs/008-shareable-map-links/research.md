# Research: Shareable Map Links

**Date**: 2026-03-12 | **Branch**: `008-shareable-map-links`

## R1: Client-Side Compression Library

**Decision**: Use [pako](https://github.com/nickel-js/pako) for deflate compression/decompression.

**Rationale**: pako is the de-facto standard JS deflate library (~50KB minified, tree-shakeable). It provides `deflate`/`inflate` for raw DEFLATE streams — no gzip header overhead. Used by thousands of projects for URL-safe data compression. No server required.

**Alternatives considered**:
- **lz-string**: Simpler API, but produces longer output for small payloads. Less efficient compression ratio for structured binary data.
- **CompressionStream API**: Native browser API, but not available in all target browsers (Safari 16.4+), requires async streams, and is harder to test.
- **No compression**: Raw base64url of sparse pairs. For 100 responses × 4 bytes each = 400 bytes → 534 base64 chars. Marginal — compression gives ~40-60% reduction.

## R2: Base64url Encoding

**Decision**: Use standard base64 encoding with URL-safe character substitution (`+` → `-`, `/` → `_`, strip `=` padding).

**Rationale**: base64url is the standard for URL-safe binary encoding (RFC 4648 §5). Native `btoa`/`atob` handle standard base64; a simple character swap produces URL-safe output without dependencies.

**Alternatives considered**:
- **base62/base58**: Higher information density per character, but no native support and harder to debug.
- **hex encoding**: 2x larger output than base64. Not practical for URL constraints.

## R3: Sparse Response Encoding Format

**Decision**: Encode only non-zero responses as packed binary: `[version_byte][count_uint16][index_uint16, value_int8]...`

**Rationale**:
- ~2500 questions total, so uint16 (0-65535) covers all indices
- Values are {-1=incorrect, 1=skipped, 2=correct}, fitting in int8
- 3 bytes per response entry + 3 bytes header = very compact
- 100 responses = 303 bytes raw → ~200 bytes deflated → ~268 base64url chars
- Well under the 2000-char URL limit

**Alternatives considered**:
- **Bitfield encoding**: 2 bits per question × 2500 = 625 bytes raw. Efficient for dense responses but wasteful for sparse (most questions unanswered). Also harder to version.
- **JSON + compress**: `JSON.stringify({id: value, ...})` + deflate. Readable but ~3-5x larger than binary.
- **Run-length encoding**: Overkill for sparse data with no runs.

## R4: Stable Question Indexing Strategy

**Decision**: Sort all questions by `(domain_id[0], question_id)` alphabetically to produce a deterministic integer index. Store a version byte in the token that maps to a snapshot of the question bank.

**Rationale**:
- Questions already have unique `id` fields and `domain_ids` arrays
- Sorting by first domain_id + question_id gives stable ordering that only changes when questions are added/removed
- Version byte allows decoder to detect mismatches and handle gracefully
- New questions get indices at the end (appended after existing sort order) if we use insertion-order-preserving versioning

**Alternatives considered**:
- **Hash-based indexing**: Hash question_id to index. Collision risk, harder to debug.
- **Sequential file order**: Depends on JSON array ordering in domain files. Fragile.
- **Question ID as key**: Using string IDs in the token. Much larger payload.

## R5: Open Graph Meta Tags for GitHub Pages

**Decision**: Add static OG meta tags to `index.html`. Use a pre-generated screenshot as the `og:image` hosted in the repo at `src/img/og-preview.png` (served via GitHub Pages).

**Rationale**: GitHub Pages serves static files — no server-side rendering to generate dynamic OG tags per token. A static preview image is the only option. Social platforms don't execute JavaScript, so the same preview appears for all shared links regardless of token content.

**Alternatives considered**:
- **Dynamic OG via serverless function**: Cloudflare Workers or Vercel Edge function could render per-token images. But this adds infrastructure complexity, a separate domain/CORS concerns, and goes against the "no server" constraint.
- **Meta tag injection via JS**: Platforms don't execute JS when scraping, so this doesn't work.

## R6: Social Platform Share Intents

**Decision**: Use each platform's native share URL scheme:

| Platform | URL Pattern |
|-|-|
| X/Twitter | `https://twitter.com/intent/tweet?text={text}` |
| LinkedIn | `https://www.linkedin.com/sharing/share-offsite/?url={url}` |
| Bluesky | `https://bsky.app/intent/compose?text={text}` |
| Facebook | `https://www.facebook.com/sharer/sharer.php?u={url}` |
| Instagram | No URL share intent — copy to clipboard + prompt user |

**Rationale**: These are the standard, well-documented share URLs used by all major apps. Instagram has no web share intent API — the standard pattern is to copy text to clipboard and instruct the user to paste into the Instagram app.

## R7: Read-Only Shared View Architecture

**Decision**: Single `index.html` with conditional boot path. When `?t=` parameter is present, `app.js` calls `shared-view.js` instead of the normal boot sequence. The shared view imports the same renderer and estimator but skips quiz panel, video panel, minimap, header toolbar, and landing screen.

**Rationale**: Using the same HTML file and renderer guarantees visual parity (FR-013). A separate `load.html` would inevitably drift. The conditional boot is a clean separation — `shared-view.js` is a small orchestrator that:
1. Decodes the token
2. Reconstructs synthetic response objects
3. Loads the "all" domain bundle
4. Runs the GP estimator
5. Renders the map
6. Adds minimal chrome (CTA button)

**Alternatives considered**:
- **Separate load.html**: Explicitly rejected by spec (FR-013) and issue author. Drift risk.
- **iframe embed**: Overkill. Same-origin complexity.
