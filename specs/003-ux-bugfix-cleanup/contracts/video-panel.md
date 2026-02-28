# Contract: Video Discovery Panel

**Module**: `src/ui/video-panel.js`
**Date**: 2026-02-27

## Public API

### `init(container: HTMLElement, options: VideoPlayerOptions)`
Initialize the video panel in the given container element.
- `options.onVideoSelect(videoId: string)`: Callback when user clicks a video
- `options.onVideoHover(videoId: string | null)`: Callback when user hovers/unhovers a video
- `options.onToggleMarkers(visible: boolean)`: Callback when user toggles marker visibility

### `setVideos(videos: VideoMarker[])`
Set the full video catalog (all markers from all videos). Called once on domain load.

### `updateViewport(viewport: {x_min, x_max, y_min, y_max})`
Filter the video list to show only videos with markers inside the given viewport. Called on every pan/zoom.

### `setWatchedVideos(watchedSet: Set<string>)`
Update which videos show a "watched" indicator.

### `show()` / `hide()` / `toggle()`
Control panel visibility.

### `destroy()`
Remove all event listeners and DOM elements.

## UI Layout

```
┌─────────────────────┐
│ Videos  [×] [👁 toggle] │
│ ┌─────────────────┐ │
│ │ 🔍 Search...     │ │
│ └─────────────────┘ │
│ ┌─────────────────┐ │
│ │ 📺 Video Title 1 │ │  ← hover highlights trajectory on map
│ │    12:34  5 pts  │ │     click opens YouTube player modal
│ │ 📺 Video Title 2 │ │
│ │    45:12  3 pts ✓│ │  ← ✓ = watched
│ │ ...              │ │
│ └─────────────────┘ │
│ Showing 23 of 5,044 │
└─────────────────────┘
```

## Viewport Filtering

Videos are grouped by `videoId`. A video appears in the list if **any** of its markers fall within the current viewport. The list shows unique videos (not individual markers), sorted by marker count in viewport (most relevant first).

## Events

| User Action | Result |
|-------------|--------|
| Hover video in list | `onVideoHover(videoId)` → renderer highlights trajectory |
| Unhover | `onVideoHover(null)` → renderer clears trajectory |
| Click video | `onVideoSelect(videoId)` → opens YouTube modal |
| Type in search | Filters list by title substring (client-side) |
| Toggle markers | `onToggleMarkers(visible)` → renderer shows/hides all video dots |
| Close panel | `hide()` — panel slides out, no cleanup |
