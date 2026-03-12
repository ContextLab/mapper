# Quickstart Scenarios: Shareable Map Links

**Date**: 2026-03-12 | **Branch**: `008-shareable-map-links`

## Scenario 1: Generate and Share a Link

**Precondition**: User has answered 10+ questions across domains.

1. Click the Share button in the header toolbar
2. Share modal opens showing the knowledge map preview image
3. Click "Copy Link" button
4. Button text changes to "Copied!" for 2 seconds
5. Clipboard contains a URL like `https://context-lab.com/mapper/?t=eJxz...`
6. Paste the URL into a new browser tab
7. Map renders with the same heatmap and response dots — no landing screen, no quiz panel

**Verify**: Dot positions and colors (green/red/yellow) match the original session.

## Scenario 2: Open a Shared Link (Fresh Browser)

**Precondition**: Have a token URL (from Scenario 1).

1. Open the URL in an incognito/private window (no localStorage)
2. Landing screen is skipped — map renders immediately
3. Only the map canvas and a "Map your *own* knowledge!" CTA button are visible
4. No header toolbar, no quiz panel, no video panel, no minimap
5. Click the CTA button
6. Navigates to `/mapper/` — normal app with landing screen

**Verify**: Shared view has zero interactive quiz elements. CTA navigates correctly.

## Scenario 3: Social Media Share with Token URL

**Precondition**: User has answered 10+ questions.

1. Open Share modal
2. Click the Twitter/X button
3. Twitter compose window opens with pre-filled text including the token URL
4. Click the Facebook button
5. Facebook share dialog opens with the token URL
6. Click the Instagram button
7. Clipboard is populated with share text + token URL; a brief prompt appears ("Copied! Paste into Instagram")

**Verify**: Each platform's compose/share window contains the token URL, not the generic mapper URL.

## Scenario 4: Link Preview on Social Platforms

**Precondition**: App is deployed to GitHub Pages with OG meta tags.

1. Paste a token URL into Twitter's Card Validator
2. Preview shows: title "Knowledge Mapper", description, and the sample map screenshot image
3. Paste the same URL into Facebook's Sharing Debugger
4. Preview shows the same OG card with image, title, description
5. Paste into LinkedIn's Post Inspector
6. Preview shows the same card

**Verify**: All 5 platforms (LinkedIn, X, Bluesky, Facebook, Instagram) render a preview card with the correct image and title.

## Scenario 5: Invalid/Corrupted Token

**Precondition**: None.

1. Navigate to `/mapper/?t=INVALID_GARBAGE_STRING`
2. App loads normally — landing screen appears, full UI
3. No error message shown to the user
4. Console shows a warning (not an error)

**Verify**: Graceful fallback, no crash, no user-visible error.

## Scenario 6: Token Forward Compatibility

**Precondition**: Have a token URL generated with the current question bank.

1. Add a new question to a domain JSON file
2. Rebuild and reload the token URL
3. Map renders correctly — all original responses appear
4. The new question appears as unanswered (no dot)

**Verify**: Old tokens survive question bank changes. No decoding errors.

## Scenario 7: Extreme Token Size

**Precondition**: Answer all ~2500 questions (or simulate programmatically).

1. Open Share modal and click "Copy Link"
2. URL is generated (may exceed 2000 chars — expected for extreme case)
3. Paste into a new tab — map renders correctly
4. Test pasting into Twitter compose — URL may be truncated by platform character limits

**Verify**: Encoding handles max load. Document platform-specific URL length limits for edge cases.

## Scenario 8: Mobile Shared View

**Precondition**: Have a token URL.

1. Open the token URL on a mobile device (or emulate 375×667 viewport)
2. Map renders in minimal chrome — no toolbar, no drawers
3. CTA button is visible and tappable at the bottom
4. Map is pannable/zoomable via touch

**Verify**: Responsive layout works for shared view on mobile.
