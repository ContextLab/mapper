# Persona Simulation Results — 2026-02-26

## Summary

Ran 4 persona simulations with 30 stratified questions each across the full
map. Used a standalone SimpleGP (Matérn 3/2, lengthScale=0.18) and TLP video
scoring against the real 3,120-video catalog.

## Key Findings

### GOOD: GP map-persona consistency works for all 4 personas

| Persona | Correct | Strong Region | Weak Region | Consistent? |
|---------|---------|---------------|-------------|-------------|
| Physics/Math Expert | 37% | x=0.15 (acc=90%) | x=0.93 (acc=15%) | YES |
| Biology/Neuro Specialist | 67% | x=0.78 (acc=85%) | x=0.16 (acc=20%) | YES |
| Balanced Generalist | 43% | x=0.21 (acc=61%) | x=0.98 (acc=56%) | YES |
| Astrophysics Niche | 13% | x=0.02 (acc=40%) | x=0.81 (acc=10%) | YES |

The GP correctly identifies strong/weak regions relative to each persona's
answer pattern, even with only 30 observations.

### GOOD: Video recommendations target weak areas

| Persona | Avg Rec Accuracy | Targets Weak? |
|---------|-----------------|---------------|
| Physics/Math Expert | 40% | YES |
| Biology/Neuro Specialist | 52% | PARTIAL |
| Balanced Generalist | 60% | PARTIAL |
| Astrophysics Niche | 10% | YES |

### CRITICAL: Question coordinates are heavily SE-clustered

```
Question distribution:
  NW:   29 ( 1.2%)
  NE:  186 ( 7.4%)
  SW:   65 ( 2.6%)
  SE: 2220 (88.8%)
```

~89% of all 2,500 questions have coordinates in x>0.5, y>0.5. This severely
limits the GP's ability to observe/predict across the full map.

### CRITICAL: Domain region ↔ question coordinate mismatch

Domain bounding boxes from `index.json` don't match where questions actually
land. Example:

| Domain | Region Center | Question Centroid |
|--------|--------------|-------------------|
| Astrophysics | (0.17, 0.54) | (0.67, 0.63) |
| Physics | (0.18, 0.54) | (0.66, 0.62) |
| Biology | (0.22, 0.67) | (0.68, 0.60) |
| Mathematics | (0.18, 0.51) | (0.66, 0.65) |

All question centroids cluster around (0.65, 0.62) regardless of domain.
This strongly suggests the UMAP reducer used when generating questions is
different from the one that defined domain regions. The domain regions in
`index.json` appear to be from the OLD embedding, while question x,y coords
were computed with a NEWER unified reducer.

**Root cause hypothesis**: When questions were generated, they were embedded
and projected using the current reducer, but `index.json` was never updated
to reflect the new domain positions.

### ISSUE: Same #1 video recommendation for all personas

"Multiplication, division word problems" at (0.29, 0.87) wins TLP for every
persona because it sits in a region with:
- High uncertainty (far from question cluster)
- Low-to-moderate knowledge for all personas
- Only 1 window, so TLP = full cell score (not averaged down)

This suggests single-window videos get an unfair advantage. Consider
either a minimum window count filter or a window-count normalization.

### ISSUE: Many domains show region_center=(0.50, 0.50)

35 of 50 domains have region=[0,1]×[0,1] (the entire map). Only 15
domains have refined bounding boxes. This means `findDomain()` labels
are unreliable for ~70% of domains.

## Action Items

1. **Re-generate domain regions from actual question coordinates** — the
   index.json bounding boxes are stale
2. **Investigate why questions cluster in SE** — are the question embeddings
   being projected differently than article embeddings?
3. **Consider minimum window count for video recommendations** — filter out
   single-window videos or apply window-count weighting
4. **Re-run simulation after fixing domain regions** — current simulation
   validates the algorithm logic but spatial layout needs fixing

## Playwright End-to-End Simulation (v2)

Ran 4 domain-based personas through the REAL app via Playwright, answering
20 questions each using the actual BALD/phase-based question selection,
real GP estimator, and real video recommender.

### Personas & Results

| Persona | Domain | Accuracy | Top Video Recommendations | Gain |
|---------|--------|----------|---------------------------|------|
| Physics-Math Expert | physics | 18/20 (90%) | ALL World History (Aztec Empire, WWII, Spanish colonization) | 87-90% |
| Biology Specialist | biology | 15/20 (75%) | History + Math (Crusades, Middle Ages, word problems) | 47-50% |
| History Buff | All General | 12/20 (60%) | Ancient Greek/Roman history (Philip of Macedon, Persian Wars) | 64% |
| Struggling Novice | All General | 4/20 (20%) | Mixed (Lo-Fi Beats, solar system, math, eclipses) | 36-43% |

### Analysis

1. **Physics Expert → History videos** — CORRECT. System identifies physics
   mastery, recommends weakest area (history/humanities) with 87-90% gain.
2. **Biology Specialist → History videos** — CORRECT. Bio expertise detected,
   recommends non-bio content with moderate gain.
3. **History Buff → Ancient history videos** — INTERESTING EDGE CASE. The
   system recommends history videos for a history expert because those
   specific video regions (ancient Greece/Rome) are UNOBSERVED. The system
   targets spatial gaps, not topic gaps.
4. **Struggling Novice → Mixed low-gain** — CORRECT. System detects widespread
   weakness, gain scores are lowest (36-43%).

### Screenshots

Saved to `tests/visual/screenshots/persona-*-{map,videos}.png` (8 files).

## Scripts

- `scripts/persona_simulation.mjs` — standalone GP simulation (no browser)
- `tests/visual/persona-simulation.spec.js` — Playwright end-to-end simulation
