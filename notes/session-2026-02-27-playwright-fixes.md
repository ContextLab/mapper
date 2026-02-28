# Session 2026-02-27: Playwright E2E Test Fixes (T030)

## Summary
Continued the UX bugfix sweep (specs/003-ux-bugfix-cleanup). This session focused on T030: fixing ALL Playwright E2E tests. Reduced failures from 31 to 21 (across browsers), with 173 passing tests.

## What Was Done

### Root Cause of Original 31 Failures
All test files used `#landing-domain-wrapper` selector which doesn't exist in HTML. The landing page has a simple start button, not a domain selector.

### Fix Strategy (Completed)
Updated all 8 test files to use a two-step pattern:
1. Click `#landing-start-btn` to enter the map
2. Use header `.domain-selector` dropdown to pick domain

### Race Condition Fix (Completed)
Tests clicked the start button before JS event listeners were attached. Added `data-ready` attribute in `src/app.js` (line 145) after listener is attached. All tests now wait for `#landing-start-btn[data-ready]`.

### Test Assertion Fixes (Completed)
- `modes.spec.js`: Updated button counts (4 mode buttons, 0 insight buttons, 3 disabled)
- `skip-and-share.spec.js`: Fixed case sensitivity ("skip" not "Skip")

## Remaining 21 Failures (5 unique issues across browsers)

### 1. edge-cases T065: Progress overlay opacity (5 browsers)
- **Test**: `domain loading shows progress bar with slow connection`
- **Issue**: `expect(parseFloat(overlayOpacity)).toBeLessThanOrEqual(0.1)` fails — opacity stays at 1
- **Root cause**: The route interception delays domain data, but the progress overlay may not fade as expected with the new two-step load flow (click start → default 'all' domain loads → then switch to physics)
- **Fix approach**: The test intercepts `**/data/domains/**` but allDomainBundle already loaded before test starts. Need to either: (a) intercept earlier, (b) increase wait time significantly, or (c) rethink what the test should check since data is now pre-loaded at boot

### 2. edge-cases banner theme: `#theme-toggle` not found (5 browsers)
- **Test**: `banner respects theme colors (dark and light)`
- **Issue**: `locator.click: Test timeout of 30000ms exceeded` waiting for `#theme-toggle`
- **Fix approach**: Check if theme toggle has different ID or is inside the map view (not visible on landing). May need to enter the map first, or the banner auto-dismisses before toggle can be clicked (banner auto-dismisses at 8s).

### 3. responsive T062: Touch tap feedback empty (3 browsers: chromium, firefox, mobile-chrome)
- **Test**: `touch tap on answer button works on mobile`
- **Issue**: `.quiz-feedback` stays empty after `btn.tap()` + 500ms wait
- **Fix approach**: Use Playwright's auto-retrying assertion `expect(feedback).not.toBeEmpty({ timeout: 3000 })` instead of fixed waitForTimeout. Or investigate if tap() doesn't trigger the click handler properly.

### 4. accessibility: Escape key closes about modal (3 browsers: chromium, webkit, mobile-chrome)
- **Test**: Clicks `#about-btn`, waits for modal, presses Escape
- **Issue**: Likely `#about-btn` not visible on landing page (it's in the header which may be hidden)
- **Fix approach**: Enter the map first before testing about button, or check if about-btn is accessible from landing

### 5. accessibility: skip-to-content link (2 browsers: webkit, mobile-safari)
- **Test**: Presses Tab, expects `.skip-link` to be focused
- **Issue**: webkit/safari specific — Tab key may not focus elements the same way
- **Fix approach**: This may be a browser-specific behavior. Consider skipping on webkit or using a different approach to test skip links.

### 6. skip-and-share: randomized across reloads (2 browsers: webkit, mobile-safari)
- **Test**: Reloads page 5 times and checks option ordering varies
- **Issue**: Timeout on 4th reload during `selectDomain` — `waitForTimeout(1000)` exceeds test timeout
- **Fix approach**: Reduce `waitForTimeout(1000)` to 300ms, or reduce reload count from 5 to 3, or increase test timeout.

## Files Modified This Session

| File | Changes |
|------|---------|
| `src/app.js` | Added `landingStartBtn.dataset.ready = 'true'` at line 145 |
| `tests/visual/quiz-flow.spec.js` | Rewrote selectDomain helper |
| `tests/visual/transitions.spec.js` | Rewrote selectDomain helper |
| `tests/visual/modes.spec.js` | Rewrote selectDomain, fixed assertion counts |
| `tests/visual/edge-cases.spec.js` | Rewrote selectDomain, replaced inline selectors |
| `tests/visual/persona-simulation.spec.js` | Rewrote selectDomain (text-based matching) |
| `tests/visual/video-recommendations.spec.js` | Rewrote selectDomain, removed old selectors |
| `tests/visual/responsive.spec.js` | Rewrote inline domain selection with tap() |
| `tests/visual/skip-and-share.spec.js` | Rewrote selectDomain, fixed case sensitivity |

## Tasks Status
- T001-T029: Complete (previous sessions)
- **T030**: IN PROGRESS — 173/194 tests passing, 21 failures remain (5 unique issues)
- T031: Manual quickstart validation — pending
- T032: Verify no console errors after 150+ questions — pending
- T033: Verify share modal behavior — pending

## Test Results Summary
- **173 passed** (was 12 at start of previous session)
- **21 failed** (5 unique issues x multiple browsers)
- **21 skipped** (persona tests on non-chromium)

## Next Steps
1. Fix the 5 remaining unique test issues (see detailed analysis above)
2. Re-run full suite to confirm all pass
3. Mark T030 complete
4. Complete T031-T033
5. Commit and push
