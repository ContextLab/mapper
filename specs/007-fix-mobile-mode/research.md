# Research: Fix Mobile Mode

**Feature**: 007-fix-mobile-mode | **Date**: 2026-03-10

## R1: Header Button Split — Two Scrollable Containers

**Decision**: Use two separate scrollable containers (`.header-actions` and `.header-right`) instead of a single container with spacers.

**Rationale**: Three previous attempts with single-container approaches all failed:
1. `flex: 1` spacer div — collapses in scrollable containers (no fixed width constraint)
2. `margin-right: auto` — same collapse issue in overflow containers
3. CSS `order` with single scroll — can't achieve independent scroll directions

Two containers is the minimal solution that correctly separates button groups with independent scroll behavior.

**Alternatives considered**:
- Single container with JS-calculated spacer width — fragile, requires resize observers
- Position: sticky for button groups within single scroll — not reliable cross-browser for horizontal scroll
- Two rows of buttons — wastes vertical space on already-constrained mobile screens

## R2: Drawer Pull Centering Drift

**Decision**: Isolate drawer pull from all padding/margin inheritance with defensive `!important` rules and ensure panel itself never has padding.

**Rationale**: The drift bug occurs because:
- `#quiz-panel.open` previously applied `padding: 0.75rem 1rem` which narrowed the pull's containing block
- Previous fix moved padding to `.quiz-content`, but the pull still inherits the panel's box model
- The `order: -1` flex trick works for ordering but doesn't protect against padding changes

Root cause confirmed: any padding on `#quiz-panel` directly affects the `.drawer-pull` width calculation since it's `width: 100%` of the panel's content box.

**Alternatives considered**:
- Flex centering (`justify-content: center`) — vulnerable to sibling element interference
- Fixed positioning — would detach from panel scroll/animation
- JS-calculated centering — unnecessary complexity for a CSS layout issue

## R3: Colorbar Mobile Visibility

**Decision**: Position colorbar at `top: 8px; right: 8px` on mobile with `z-index: 16`.

**Rationale**: Bottom positioning overlaps with the quiz panel (z-index 20). Top-right keeps it visible in the map area above the panel. Height reduced to 80px to fit mobile screens.

**Alternatives considered**:
- Left side — could overlap with video panel toggle
- Inside the quiz panel — breaks the colorbar's purpose as a map legend
- Floating/moveable — already implemented via touch drag support
