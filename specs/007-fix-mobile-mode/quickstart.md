# Quickstart: Fix Mobile Mode

**Feature**: 007-fix-mobile-mode | **Date**: 2026-03-10

## Setup

```bash
git checkout 007-fix-mobile-mode
npm install
npm run dev
```

## Verify Fixes

### 1. Header Button Layout
1. Open browser DevTools → toggle device toolbar → select iPhone SE (375x667)
2. Navigate to `http://localhost:5173/mapper/`
3. Click "Start" to enter map mode
4. Verify: reset/download/upload buttons appear after dropdown (left side)
5. Verify: trophy/video/share/tutorial/info buttons appear at far right
6. Swipe right on header → hidden left buttons revealed
7. Swipe left on header → hidden right buttons revealed
8. Dropdown stays fixed throughout

### 2. Drawer Pull Centering
1. Same mobile viewport
2. Select a domain to open quiz panel
3. Verify: grab bar is centered horizontally
4. Tap drawer pull to close → verify still centered
5. Tap again to open → verify still centered
6. Repeat 5 more times → never drifts

### 3. Colorbar Visibility
1. Same mobile viewport
2. Answer a question so heatmap appears
3. Verify: colorbar visible in top-right of map area
4. Touch and drag colorbar → moves smoothly

## Run Tests

```bash
# Unit tests
npm test

# All Playwright tests
npx playwright test

# Mobile-specific tests only
npx playwright test tests/visual/mobile-drawer.spec.js tests/visual/mobile-header.spec.js tests/visual/mobile-colorbar.spec.js
```

## Cross-Device Verification

### Android Emulator
```bash
# Start emulator, then open Chrome and navigate to local dev server
# (requires adb reverse for port forwarding)
adb reverse tcp:5173 tcp:5173
# Open http://localhost:5173/mapper/ in Chrome on emulator
```

### iOS Simulator
```bash
# Start iOS Simulator from Xcode
# Open Safari and navigate to local dev server
# (Simulator shares host network automatically)
# Open http://localhost:5173/mapper/ in Safari on simulator
```
