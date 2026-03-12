# mapper Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-02-27

## Active Technologies
- JavaScript ES2022+ (ES modules) + @playwright/test 1.58+, nanostores 1.1, deck.gl 9.2, Vite 7.3, Claude Code Task agents (Sonnet 4.6 / Opus 4.6 for persona evaluation — no API key needed) (004-persona-user-testing)
- File-based JSON (question banks in `data/domains/`), localStorage (user progress) (004-persona-user-testing)
- JavaScript ES2022+ (ES modules), HTML5, CSS3 + nanostores 1.1, Vite 7.3, Canvas 2D API, KaTeX (CDN), deck.gl 9.2 (006-performance-and-ux-refinement)
- localStorage (user progress), file-based JSON (question banks in `data/domains/`) (006-performance-and-ux-refinement)
- JavaScript ES2022+ (ES modules), HTML5, CSS3 + nanostores 1.1, Vite 7.3, deck.gl 9.2, KaTeX (CDN) (007-fix-mobile-mode)
- localStorage (user progress), file-based JSON (question banks) (007-fix-mobile-mode)
- JavaScript ES2022+ (ES modules), HTML5, CSS3 + nanostores 1.1, Vite 7.3, deck.gl 9.2, KaTeX (CDN), pako (new — for deflate compression) (008-shareable-map-links)
- localStorage (user progress), URL query parameter (shared state) (008-shareable-map-links)

- JavaScript ES2022+ (ES modules), HTML5, CSS3 + nanostores 1.1.0, Vite 7.3.1, Canvas 2D API, KaTeX (CDN) (003-ux-bugfix-cleanup)

## Project Structure

```text
backend/
frontend/
tests/
```

## Commands

npm test && npm run lint

## Code Style

JavaScript ES2022+ (ES modules), HTML5, CSS3: Follow standard conventions

## Recent Changes
- 008-shareable-map-links: Added JavaScript ES2022+ (ES modules), HTML5, CSS3 + nanostores 1.1, Vite 7.3, deck.gl 9.2, KaTeX (CDN), pako (new — for deflate compression)
- 007-fix-mobile-mode: Added JavaScript ES2022+ (ES modules), HTML5, CSS3 + nanostores 1.1, Vite 7.3, deck.gl 9.2, KaTeX (CDN)
- 006-performance-and-ux-refinement: Added JavaScript ES2022+ (ES modules), HTML5, CSS3 + nanostores 1.1, Vite 7.3, Canvas 2D API, KaTeX (CDN), deck.gl 9.2


<!-- MANUAL ADDITIONS START -->

## Mobile Testing

- Mobile view is **landscape** (the app locks to landscape on phone-sized devices)
- Test mobile at viewport ~812×375 (iPhone landscape), NOT portrait
- The landscape breakpoint is `@media (max-height: 500px) and (orientation: landscape)`
- The portrait ≤480px breakpoint also applies but landscape is the primary mobile experience

## Browser Automation (Playwright MCP)

- Use **screenshots** (`browser_take_screenshot`), NOT snapshots (`browser_snapshot`), to inspect page content — snapshots return massive DOM trees that exceed token limits on complex pages
- Use `browser_evaluate` for targeted DOM queries when you need specific element state
- The deck.gl canvas does NOT auto-resize when hiding DOM elements — must dispatch `window resize` event or reload at the correct viewport size

<!-- MANUAL ADDITIONS END -->
