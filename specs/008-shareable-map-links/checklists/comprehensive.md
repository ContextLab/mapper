# Requirements Quality Checklist: Shareable Map Links

**Purpose**: Comprehensive requirements quality validation — PR review gate after implementation
**Created**: 2026-03-12
**Feature**: [spec.md](../spec.md)
**Depth**: Standard (~30 items)
**Audience**: PR reviewer

## Requirement Completeness

- [ ] CHK001 - Are encoding value semantics defined for all possible response states (correct, incorrect, skipped, unanswered)? [Completeness, Spec §FR-002]
- [ ] CHK002 - Is the binary wire format fully specified with byte offsets, endianness, and field sizes? [Completeness, Contract §token-format]
- [ ] CHK003 - Are requirements for the "Copy Link" button placement and styling within the share modal specified? [Gap, Spec §FR-009]
- [ ] CHK004 - Is the CTA button's position, styling, and responsive behavior in the shared view defined? [Gap, Contract §url-contract]
- [ ] CHK005 - Are requirements specified for all 5 social platform share buttons (LinkedIn, X, Bluesky, Facebook, Instagram)? [Completeness, Spec §FR-015]
- [ ] CHK006 - Are loading/progress state requirements defined for the shared view while the GP estimator runs? [Gap]

## Requirement Clarity

- [ ] CHK007 - Is "minimal chrome" quantified with an explicit list of hidden vs. visible UI elements? [Clarity, Spec §FR-006]
- [ ] CHK008 - Is "visually identical" (SC-005) defined with measurable criteria (pixel diff threshold, screenshot comparison method)? [Ambiguity, Spec §SC-005]
- [ ] CHK009 - Is the "stable, deterministic index" sort order precisely defined (sort key, tie-breaking, collation)? [Clarity, Spec §FR-001]
- [ ] CHK010 - Is "gracefully handle" for invalid tokens defined with specific fallback behavior? [Clarity, Spec §FR-011]
- [ ] CHK011 - Is the OG preview image content specified with enough detail for a designer (text content, font sizes, positioning, contrast requirements)? [Clarity, Spec §FR-018]
- [ ] CHK012 - Is the Instagram "prompt to paste" UX described with specific wording, duration, and dismissal behavior? [Clarity, Spec §FR-020]

## Requirement Consistency

- [ ] CHK013 - Does the "read-only" requirement in US2 align with the "minimal chrome" clarification listing hidden elements? [Consistency, Spec §US2 vs §FR-006]
- [ ] CHK014 - Are the URL size guarantees in the token format contract consistent with FR-014 (under 2000 chars for ≤200 answers)? [Consistency, Contract §token-format vs Spec §FR-014]
- [ ] CHK015 - Is the terminology "token" used consistently across spec, plan, contracts, and tasks (not mixed with "hash", "code", "key")? [Consistency]
- [ ] CHK016 - Does the social platform list match across US3 acceptance scenarios, FR-015, FR-019, and SC-007 (all must list the same 5 platforms)? [Consistency]

## Acceptance Criteria Quality

- [ ] CHK017 - Can SC-001 ("generate shareable link in under 2 seconds") be objectively measured with a defined starting and ending event? [Measurability, Spec §SC-001]
- [ ] CHK018 - Can SC-002 ("fully rendered knowledge map within 3 seconds") be measured — is "fully rendered" defined (first paint? all dots visible? estimator complete?)? [Measurability, Spec §SC-002]
- [ ] CHK019 - Can SC-004 ("tokens remain decodable after question bank updates") be verified with a defined test procedure? [Measurability, Spec §SC-004]
- [ ] CHK020 - Can SC-007 ("link previews display correct title, description, and preview image") be verified — are "correct" values specified? [Measurability, Spec §SC-007]

## Scenario Coverage

- [ ] CHK021 - Are requirements defined for the zero-response state in shared view (user shares before answering any questions)? [Coverage, Edge Case]
- [ ] CHK022 - Are requirements specified for what happens when a shared URL is opened on an unsupported/old browser? [Coverage, Gap]
- [ ] CHK023 - Are requirements defined for the shared view when the "all" domain bundle fails to load (network error)? [Coverage, Exception Flow]
- [ ] CHK024 - Are requirements specified for concurrent sharing scenarios (user generates link, answers more questions, then recipient opens the old link)? [Coverage, Alternate Flow]

## Edge Case Coverage

- [ ] CHK025 - Does the spec define behavior when URL contains both `?t=TOKEN` and other query parameters (e.g., UTM tracking)? [Edge Case, Spec §Edge Cases]
- [ ] CHK026 - Are requirements defined for token URLs that pass through URL shorteners (bit.ly, t.co) — does the token survive? [Edge Case, Gap]
- [ ] CHK027 - Is behavior specified for extremely long tokens (all 2500 questions answered) on platforms with URL length limits? [Edge Case, Spec §Edge Cases]
- [ ] CHK028 - Are requirements defined for what happens if pako (compression library) fails to load or is unavailable? [Edge Case, Gap]

## Non-Functional Requirements

- [ ] CHK029 - Are accessibility requirements specified for the shared view CTA button (keyboard focus, screen reader label, contrast)? [Gap, Accessibility]
- [ ] CHK030 - Are performance requirements defined for token encoding/decoding operations (max latency on mid-range hardware)? [Gap, Performance]
- [ ] CHK031 - Are privacy considerations documented — do tokens reveal any personally identifiable information? [Gap, Privacy]
- [ ] CHK032 - Are WCAG AA color contrast requirements specified for the CTA button and shared view elements? [Gap, Accessibility]

## Dependencies & Assumptions

- [ ] CHK033 - Is the assumption "social platforms support URLs up to 2000 characters" validated for all 5 target platforms? [Assumption, Spec §Assumptions]
- [ ] CHK034 - Is the pako dependency version-pinned, and are fallback requirements specified if the CDN or npm package is unavailable? [Dependency, Gap]
- [ ] CHK035 - Is the assumption "GitHub Pages serves static OG meta tags correctly to social crawlers" validated? [Assumption, Spec §Assumptions]

## Notes

- This checklist validates the REQUIREMENTS quality, not the implementation
- Items marked [Gap] indicate missing requirements that should be added before final PR approval
- Items marked [Ambiguity] indicate requirements that need sharper definition
- Each item should be resolved by updating spec.md, not by verbal agreement
