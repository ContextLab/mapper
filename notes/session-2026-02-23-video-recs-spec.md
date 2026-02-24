# Session Notes: Video Recommendations Spec (2026-02-23)

## What Was Done

### Three deliverables completed for Khan Academy Video Recommendation System:

1. **GitHub Issue #22** — https://github.com/ContextLab/mapper/issues/22
   - Full feature description with phases, technical notes, acceptance criteria

2. **Spec written** — `specs/002-video-recommendations/spec.md`
   - 5 user stories (P1-P3)
   - 20+ functional requirements (FR-V001 through FR-V043)
   - 10 success criteria (SC-V001 through SC-V010)
   - 7 edge cases
   - Architecture section with file structure, data flow, estimation budget
   - 6 assumptions, research references

3. **Spec-clarify analysis** — 39 clarification items (CL-001 through CL-039)
   - Produced by 3 parallel analyst agents (pipeline, math, UI)
   - 7 CRITICAL items, 17 HIGH, 10 MEDIUM, 5 LOW
   - 16 items marked [OPEN] requiring decisions
   - 23 items marked [RESOLVED] with recommended defaults

## Remaining Open Item

- **CL-016**: Run proof-of-concept with 50-100 video transcripts to validate
  UMAP `transform()` produces semantically meaningful coordinates for
  transcript text (action item, not a decision)

## Key Resolved Decisions (all 38)

**Critical (all resolved):**
- CL-001: Flattening is visual-only; estimation uses pre-flatten UMAP space
- CL-002: Stride = 50-word step (90% overlap, ~150 windows/video, ~1.35M total)
- CL-003: All video scoring uses `globalEstimator` (50×50, [0,1] space)
- CL-004: Snapshot per first video; diff map computed after 1+ question, USED after 5+; successive videos = concatenated single video
- CL-005: Transfer = max(0, D_running); fallback = global avg over sufficient-coverage cells
- CL-006: Video modal replaces concept list entirely
- CL-007: Un-hide suggest button on mobile

**High (all resolved):**
- CL-008: Spatial domain assignment (≥20% windows in bounding box)
- CL-009: Drop `topics` field for MVP
- CL-010: Per-domain split files, background-loaded during welcome screen
- CL-011: Snap window coords to nearest grid cell for TLP
- CL-012: Snapshots always use globalEstimator
- CL-015: All questions count toward 5-question threshold
- CL-018: Video modal ID = #video-modal
- CL-020: ≥20% windows threshold for domain filtering

**Formula change:**
- CL-030: TLP uses `(1 - K) × U` (boost uncertainty, active learning strategy)

## Research Reports Generated

Located in `.omc/scientist/reports/`:
- Khan Academy scraping feasibility
- YouTube transcript API research
- Video transcript embedding design
- UMAP transform projection analysis
- Knowledge gain estimation math framework
- Video UI/UX design
- Video recommender architecture integration

## Branch

Working branch: `generate-astrophysics-questions` (spec work only, no code changes)

## Next Steps

- Resolve the 16 [OPEN] clarification items (especially the 6 CRITICAL ones)
- Create contract files in `specs/002-video-recommendations/contracts/`
- Create checklists in `specs/002-video-recommendations/checklists/`
- Run proof-of-concept for CL-016: test UMAP transform() on sample transcripts
- Begin implementation after clarifications are resolved
