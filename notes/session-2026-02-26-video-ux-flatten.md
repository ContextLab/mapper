# Session: Video UX + Density Flattening (2026-02-26)

## Summary

Implemented the video markers/click/screenshot plan and re-ran density flattening to update all coordinate data.

## Completed Work

### Video Markers & Interaction
- **renderer.js**: Changed video marker color from Khan Academy blue to article-matching slate gray, size from 2.5 to 3.0
- **renderer.js**: Added `onVideoClick()` callback + click handler for `hit.type === 'video'`
- **renderer.js**: Added estimated knowledge lookup in `_hitTest()` for video markers, tooltip mirrors Wikipedia article style
- **video-modal.js**: New `playVideo(video)` export for direct single-video playback from map click
- **app.js**: Wired `renderer.onVideoClick` to `videoModal.playVideo` with field remapping
- **app.js**: Deferred `renderer.setVideos()` until `mapInitialized` (fixes static gray on welcome screen)

### Welcome Screen
- **particles.js**: Merged video catalog points into particle pool — videos get same dartmouth green color, spring physics, mouse-repulsion dodge as articles

### Screenshot Improvements (share.js)
- Added 50x50 grid lines (0.5px, subtle)
- Brighter article dots: 1px to 1.5px, alpha 0.35 to 0.55
- Added video squares (same color/size as articles)
- Added vertical colorbar legend (12x120px gradient, High/Low labels)
- Share text URL on its own line

### Density Flattening Pipeline
- **flatten_coordinates.py**: Fixed `compute_density_stats` index-out-of-bounds bug (np.clip for edge coords)
- Ran flattening: 250K articles + 1,864 video transcripts, mu=0.75, 1012 clusters
- Results: Empty cells 69.5% to 33.7%, Top10% concentration 71.1% to 31.6%, Max density 2251 to 632
- Semantic coherence: 0.166

### New Script: apply_flattened_coords.py
- KD-tree nearest-neighbor matching from original to flattened coordinates
- Updates all 50 domain JSON files (54,593 articles, 2,500 questions)
- Updates video catalog.json (64,175 windows, 13,233 unmatched — videos without transcript embeddings)
- Recomputes hierarchical bounding boxes in index.json
- Supports `--dry-run` flag

### Video Dot Subtlety & Trajectory on Hover
- **renderer.js**: Reduced video dot size from 3.0 to 2.0, opacity from 80/255 to 20/255
- **renderer.js**: Built `_videoTrajectories` Map (videoId → [{x,y}]) in `setVideos()` for O(1) lookup
- **renderer.js**: Track `_hoveredVideoId` in mousemove, trigger re-render on change
- **renderer.js**: New `_drawVideoTrajectory()` — Catmull-Rom spline through all windows of hovered video, fade-in dots along path, start ring indicator
- **renderer.js**: Tooltip shows segment count + "trajectory shown" for multi-window videos
- **share.js**: Video squares in screenshot reduced to 1px, alpha 0.14
- **index.html**: Fixed welcome screen particle interaction — `pointer-events: none` on `.landing-content`, `pointer-events: auto` on interactive children

## Test Results
- vitest: 75 passed (benchmark.test.js failure is pre-existing, requires benchmark mode)
- Playwright: pending

## Key Files Modified
| File | Changes |
|------|---------|
| `src/viz/renderer.js` | Video color/size, onVideoClick, tooltip, click handler, trajectory spline |
| `src/ui/video-modal.js` | New `playVideo()` export |
| `src/app.js` | Wire onVideoClick, defer setVideos, share data |
| `src/ui/share.js` | Grid lines, brighter dots, colorbar, URL line break |
| `src/viz/particles.js` | Merge video points into particle pool |
| `scripts/flatten_coordinates.py` | Bug fix for index out-of-bounds |
| `scripts/apply_flattened_coords.py` | NEW — applies flattened coords to all JSONs |
| `data/domains/*.json` | All coordinates updated with flattened values |
| `data/domains/index.json` | Bounding boxes recomputed |
| `data/videos/catalog.json` | Window coordinates updated |

### Continued Session (2026-02-27)

#### Particle Physics Fixes
- **particles.js**: Fixed repulsion dead-zone bug — `distSq > 1` guard skipped particles within 1px of cursor. Replaced with `dist < 0.5` threshold that pushes toward home at max force.
- **particles.js**: Balanced subsampling — 70% articles, 30% videos (was random from merged pool where 77K video windows dominated 6K articles)
- **particles.js**: Home-position shifting — when cursor is near a particle's home, the effective home shifts to edge of repulsion zone. This makes spring force *cooperate* with repulsion instead of fighting it. Fixes "stuck particles" in dense cluster centers.
- **particles.js**: Changed PARTICLE_COUNT from 3000 to 2500, REPEL_RADIUS from 12.5 to 20

#### Re-flattening with mu=0.85
- Ran `/tmp/run_flatten.py` with mu=0.85 (was 0.75)
- Results: Empty cells 33.7%→13.0%, Top10% 31.6%→17.8%, Max density 632→434, Coherence 0.344
- Applied to all JSONs: 54,593 articles, 2,500 questions, 67,723 video windows updated

#### Video Dot Opacity
- **renderer.js**: Video dot alpha from 20/255 to 5/255 (~2%)
- **share.js**: Video squares alpha from 0.14 to 0.02

#### Tensor02 Transcripts
- 5,103 transcripts on disk, 8,368/8,796 processed
- Script was stuck retrying 3 genuinely unavailable videos (`iP7HnX5mr5c`, `-rxUip6Ulnw`, `cY-iPEtvJAE`) — added to checkpoint to skip
- 428 remaining videos now being processed

#### Tensor01
- SSH to `tensor01.dartmouth.edu` (10.232.6.16) times out — user says IP address changed but DNS not updated yet

## Notes
- Bounding boxes expanded significantly after flattening (e.g. astrophysics x=[0.042, 0.296] to x=[0.005, 0.988])
- cognitive-psychology.json has title-only articles (no x,y) — handled gracefully
- The flattening adapter script is at `/tmp/run_flatten.py` (not in repo)
- Must use `.venv/bin/python3` (not system python) for coordinate file compatibility with numpy 2.x
