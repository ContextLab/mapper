# Feature Specification: Tutorial Mode, Data Fixes & UX Polish

**Feature Branch**: `005-tutorial-and-polish`
**Created**: 2026-03-05
**Status**: Draft
**Issue**: [#35 — Tutorial Mode](https://github.com/ContextLab/mapper/issues/35)
**Input**: Persona testing results (18 personas, 56% pass rate), issue #35 tutorial proposal, M3 motion design guidelines.

## Motivation

Persona testing across 18 simulated users (636 total questions, 76 issues) revealed three categories of problems:

1. **Data integrity failures** — Broken questions with empty options, incorrect answer keys, missing metadata. These cause hard FAIL verdicts.
2. **Engagement collapse** — Users lose interest after 15-20 questions due to lack of pacing, milestones, guidance, or session conclusion. Engagement drops from 4/5 to 1/5.
3. **Discoverability gaps** — Most users never find the expertise modal, learning modal, share feature, or minimap without explicit prompting.

A guided tutorial mode (issue #35) solves problems 2 and 3 simultaneously. Combined with targeted data and UX fixes, the goal is to raise the persona pass rate from 56% to 90%+.

## Success Criteria

- **SC-001**: Persona pass rate >= 90% (re-run all 18 personas after changes)
- **SC-002**: Zero broken questions served (empty options, missing answer keys)
- **SC-003**: Tutorial completes in under 4 minutes for a new user
- **SC-004**: All tutorial animations render at 60fps on desktop, 30fps+ on mobile
- **SC-005**: Tutorial toggle persists across sessions (localStorage)
- **SC-006**: No regression in existing Playwright tests (179+ core, 24 persona)
- **SC-007**: All flagged answer keys verified correct

---

## Phase A: Data Integrity Fixes

### A1. Fix Broken Questions (empty options)

**Problem**: 4+ questions render with empty option objects `{}`, making them unanswerable. Affects P05, P11, P12, P13, P16, P18.
**Known broken questions**:
- Chern-Simons theory (SU(2)_k)
- Perturbation theory E_0^(2)
- Primitive root modulo n
- QCD asymptotic freedom (N_f)

**Fix**: Locate these questions in `data/domains/*.json`, fix their options (likely LaTeX rendering issues in the generation pipeline), and ensure all 4 options are non-empty strings. Add a runtime guard in `src/ui/quiz.js` that skips any question with fewer than 4 valid options.

### A2. Rewrite Larmor Ambiguity

**Problem**: Question uses "Larmor rotation" and "Larmor precession" as separate options. The distinction is ambiguous — standard physics uses "Larmor precession" as the canonical term.
**Fix**: Rewrite the question to avoid the rotation/precession ambiguity entirely. E.g., test a different aspect of Larmor's theorem (the precession frequency formula, or the relationship to gyromagnetic ratio).

### A3. Fill Missing Domain Metadata

**Problem**: Multiple questions have `domainId: "unknown"` and empty `sourceArticle`. They don't contribute to domain-specific knowledge mapping.
**Fix**: Audit all question banks for entries with `domainId` of "unknown", empty string, or missing. For each:
1. **Verify source articles via web search** — confirm the Wikipedia article (or other source) actually exists. If the article doesn't exist or was renamed, find the correct article title.
2. **Assign correct domain IDs** — domain IDs must match actual domains present in `data/domains/index.json`. For questions in the "all" (general) domain, `domainId: "all"` is acceptable. For all other questions, the domainId must correspond to a real domain in the demo.
3. Questions that can't be properly categorized or whose source articles don't exist should be removed.

### A4. Audit Weak Distractors

**Problem**: Some distractors are obviously wrong (e.g., "Persona" for Freud's structural model, "Drops to zero" for Vmax with competitive inhibitor).
**Fix**: Run targeted audit on flagged questions. Replace implausible distractors with domain-plausible alternatives.

---

## Phase B: Critical UX Fixes

### B1. Question Validation Guard

**Problem**: Broken questions reach the user because there's no validation before serving.
**Fix**: In the question selection pipeline, add a guard that rejects questions where:
- Fewer than 4 options have non-empty string values
- `correctAnswer` is missing or doesn't match any option key
- `questionText` is empty or under 10 characters

Skip silently and serve the next valid question.

### B2. Fix domainMappedPct

**Problem**: `domainMappedPct` is stuck at 0% (or 12%) across all personas despite visible map coverage. The metric never updates.
**Fix**: Investigate and fix the calculation. It should reflect the fraction of the domain's coordinate space that has been "explored" by nearby answered questions (e.g., percentage of grid cells with non-default estimates).

### B3. Investigate "?" Answers in Persona Runner

**Problem**: Multiple persona checkpoints show `selectedAnswer: "?"`. This was initially misdiagnosed as an auto-advance timeout, but investigation revealed:
- The app has **no per-question time limit** — users have unlimited time to answer
- The 800ms auto-advance triggers **after** answering, not before — and its timing is fine
- The "?" answers originate in the **persona test runner** (`tests/visual/personas/runner.js`), not the app itself, from three causes:
  1. Question not found in the database (broken questions with empty options) → line 128
  2. Button-to-option-key mapping failure → line 219
  3. Mapping error where intended-correct answer registers as wrong → line 235

**Fix**: Most "?" answers should disappear once Phase A fixes the broken questions (A1). Additionally:
- Add defensive logging in `runner.js` when a "?" is produced, capturing which path triggered it
- Verify that after A1 fixes, re-running personas produces zero "?" answers
- If any remain, fix the specific runner mapping logic that produces them

### B4. Cross-Domain Question Filtering

**Problem**: When a specific domain is selected (e.g., Mathematics), questions from unrelated domains (e.g., Freud/clinical-psychology) still appear.
**Fix**: When `$activeDomain` is set to a specific domain, only serve questions whose `domainId` matches that domain or its ancestors/descendants in the domain tree.

---

## Phase C: Tutorial Mode

### Overview

A guided, first-run tutorial that walks new users through the Knowledge Mapper experience. Enabled by default, dismissible at any time, toggled off/on via a button in the header. The tutorial consists of 8 steps (with sub-steps), each presented as a modal overlay with inline animations demonstrating the relevant feature.

**Total questions during tutorial**: ~12-15 (enough to see the map develop without causing fatigue).

### Design Principles (M3 Motion)

All animations follow Material Design 3 motion guidelines:

**Easing**:
- **Emphasized decelerate**: `cubic-bezier(0.05, 0.7, 0.1, 1.0)` — for elements entering view (modals appearing, highlights fading in). Starts fast, settles gently.
- **Emphasized accelerate**: `cubic-bezier(0.3, 0.0, 0.8, 0.15)` — for elements exiting (modals closing, highlights fading out). Starts slow, exits quickly.
- **Standard**: `cubic-bezier(0.2, 0.0, 0.0, 1.0)` — for map color transitions, progress indicators, and continuous state changes.

**Duration**:
- **Short (150ms)**: Button hover states, highlight pulses
- **Medium (300ms)**: Modal enter/exit, tooltip appear/disappear
- **Long (500ms)**: Map animation playback, step transitions
- **Extra-long (800ms)**: Full map before/after comparison animation

**Visual Style**:
- Tutorial modals use the existing UI theme (dark panel background, white text, accent colors matching the heatmap palette)
- Highlight rings: 2px accent-colored border with soft glow (`box-shadow`), pulsing at 1.5s interval
- Inline animations are simplified SVG renderings of the actual UI, not screenshots — maintaining crispness at any resolution
- All animations are CSS-driven (no JS animation libraries) for performance
- Reduced motion: respect `prefers-reduced-motion` — replace animations with instant transitions

### Tutorial Steps

**Step 1: Welcome & UI Orientation** (after landing → map transition)

A brief guided tour of the three main UI areas, highlighting each in turn:

**1a: The Knowledge Map** (highlight: the main canvas/heatmap area)
- Modal: "Welcome to Knowledge Mapper! This is your Knowledge Map. Instead of places, each location represents a distinct *concept*. Related concepts are nearby on the map."
- "As our system learns what you know, colors will appear — green means likely knowledge, red means a gap. Because concepts are organized spatially, answering just one question tells us about *many* related concepts nearby!"
- "Scroll and pan to explore different knowledge areas."

**1b: The Quiz Panel** (highlight: the quiz panel on the right / bottom on mobile)
- Modal: "This is your quiz module. It picks questions intelligently to help fill in your knowledge map."

**1c: The Video Explorer** (highlight: the video panel on the left — skip on mobile ≤480px)
- Modal: "This is your video exploration tool. It shows Khan Academy videos related to where you're looking on the map. Hover over any video to see which concepts it covers, or click to watch!"

**Step 2: First Questions** (after Step 1 dismissed)
- Modal: "Let's try it! Answer a few questions and watch your map come to life."
- Highlight: The quiz panel
- Action: User answers their first question
- On answer: Show inline SVG animation of a simplified map gaining its first color blob (before → after, 800ms transition)
- Explain: "You just answered a question about [concept]. The map is updating — see how the colors are starting to appear?"

**Step 3: Building the Map** (after 3 more questions, ~4 total)
- Modal: "Great! You've answered [n] questions. Notice how the map is developing — each answer teaches the system more about what you know."
- If user got one wrong: "Getting a question wrong is valuable too — it helps the map identify areas where you might want to learn more."
- Highlight: The heatmap canvas
- Inline animation: Simplified map SVG showing progressive color development (3-frame sequence, 500ms each)

**Step 4: Skipping** (after step 3 modal dismissed — conditional)
- **If user has already skipped a question** before reaching this step: skip Step 4 entirely (the user already discovered the feature organically).
- **Otherwise**: Modal: "You can also skip questions you're unsure about. Skipping tells the system something too!" Highlight the Skip button, but do NOT require the user to press it. The user may answer normally or skip — either action advances to Step 5.
- **On first skip during tutorial** (whether at Step 4 or at any other step): show a one-time toast: "Noted! The system now knows this topic might be unfamiliar." This toast appears only once per tutorial session and only in tutorial mode — outside tutorial mode, skipping has no popup or confirmation message.

**Step 5: Switch Domains** (after ~6 questions total)
- Modal: "Now let's explore a different area of knowledge. Use the dropdown to pick a specific domain."
- Highlight: The domain dropdown in the header
- Action: User selects a new domain
- On selection: "You're now seeing questions about [domain]. Answer a couple to see how your map changes in this region."
- If the domain has a different map region: highlight the minimap and explain: "The minimap shows your position on the full knowledge landscape. Drag it to navigate!"

**Step 6: Explore Another Domain** (after ~9 questions total)
- Modal: "Try one more domain — pick something very different from [previous domain]."
- Suggest the most distant domain from the current one
- Action: User selects another domain, answers 2-3 questions
- Brief: "See how different regions of your map are taking shape? Each domain occupies its own area."

**Step 7: Discover Features** (after ~12 questions total)
- Modal sequence (3 sub-steps, each highlighting one feature):

**7a: Highlight "My Areas of Expertise"**
- Highlight the expertise button with tutorial overlay
- Overlay text: "Your estimated strongest topics, ranked. Tap to explore!"
- User can click the button to open the modal, or press "Next" to continue

**7b: Highlight "Suggested Learning"**
- Highlight the suggested learning button with tutorial overlay
- Overlay text: "Videos picked for your biggest knowledge gaps. Watching these gives you the largest boost!"
- User can click to open, or press "Next" to continue

**7c: Highlight Share**
- Highlight the share button with tutorial overlay
- Overlay text: "Share your knowledge map with friends!"
- User can click to open, or press "Next" to continue

**Step 8: Completion** (tutorial end)
- Modal: "You've explored your knowledge landscape! Here's a quick snapshot:"
- Show simplified 2-line summary derived from the estimator state:
  - "Strongest area: [domain name]" (highest average estimate)
  - "Most room to grow: [domain name]" (lowest average estimate)
- "These are estimates based on your answers so far — the more you explore, the more accurate they get!"
- "Continue answering to refine your map, or share it now!"
- Footer: "To learn more, read our paper (link). We're building tools to help people learn more quickly and efficiently."
- Toggle info: "You can replay this tutorial anytime from the menu."

### Tutorial State Management

```
localStorage key: 'mapper-tutorial'
value: { completed: boolean, step: number, dismissed: boolean }
```

- On first visit (no localStorage key): tutorial starts automatically
- User can dismiss at any step via "×" or "Skip Tutorial" button
- Dismissed = `{ completed: false, dismissed: true }` — tutorial won't restart
- Completed = `{ completed: true }` — tutorial won't restart
- Toggle button in header menu: resets to step 0 and restarts
- **Returning users**: Re-enabling tutorial does NOT clear existing responses/estimates. Tutorial text adapts to existing state — e.g., Step 1 says "Your map already has some data — let's explore further!" instead of "watch your map come to life" when prior answers exist. Check `$responses` length to determine which variant to show.

### Tutorial Toggle UI

- Header menu (☰ or settings icon) contains "Tutorial Mode" toggle
- When toggled ON: resets tutorial state and begins from Step 1
- When toggled OFF: immediately dismisses any active tutorial modal
- Visual indicator: subtle dot/badge on menu icon when tutorial is active

### Inline Animation Specifications

Each tutorial step contains an inline SVG animation within the modal. These are NOT screenshots — they are simplified, themed vector illustrations of the relevant UI element.

**Map evolution animation** (Steps 1-2):
- 200×120px SVG canvas
- Shows a simplified grid with color cells
- Frame 1: mostly gray/neutral
- Frame 2: one region gains green tint
- Frame 3: another region gains red/pink tint
- Transition: CSS `opacity` crossfade between frames, 500ms standard easing
- Colors match the actual heatmap palette (green=#4CAF50, yellow=#FFC107, red=#F44336)

**Feature highlight animation** (Step 6):
- Small SVG showing a button → panel opening sequence
- 2 frames: closed state → open state
- Transition: CSS `transform: translateY` + `opacity`, 300ms emphasized-decelerate

**Minimap animation** (Step 4, if applicable):
- 80×80px SVG showing simplified minimap
- Animated viewport rectangle sliding from one region to another
- Transition: CSS `transform: translate`, 500ms standard easing

All SVGs use `currentColor` where possible to inherit the theme. Specific accent colors are CSS custom properties (`--tutorial-accent`, `--tutorial-success`, `--tutorial-gap`) for easy theming.

### Highlight Overlay

When a tutorial step highlights a UI element:
1. A semi-transparent dark overlay covers the full viewport (except the highlighted element)
2. The highlighted element gets a pulsing accent border ring
3. The tutorial modal is positioned near (but not overlapping) the highlighted element
4. Click-through: only the highlighted element and the modal are interactive; clicking the overlay does nothing (prevents confusion)

Implementation: CSS `mix-blend-mode` or a `clip-path` cutout on the overlay div, avoiding canvas interaction conflicts.

### Mobile Adaptation (≤480px)

On mobile viewports where the minimap is a toggle overlay and the modes wrapper is hidden:
- **Step 1c (Video Explorer)**: Skipped on mobile ≤480px (video panel is not visible by default on mobile).
- **Step 5 (Switch Domains)**: Skip the minimap highlight and animation. Show only the domain dropdown highlight and explanation. The minimap explanation is omitted entirely.
- **Step 6 (Explore Another Domain)**: Simplified — no reference to "different regions" of the minimap. Focus on "try a different topic" framing.
- **Step 7 (Discover Features)**: Skip any sub-steps for features not visible on mobile (e.g., if modes wrapper is hidden, don't highlight it).
- All modal positioning uses bottom-sheet style on mobile (anchored to bottom of viewport) instead of floating near the highlighted element.

---

## Phase D: Engagement & Session Design

### D1. Milestone Celebrations

At questions 10, 25, and 50, show a brief toast notification:
- "10 questions! Your map is taking shape." (+ CSS-only confetti burst: ~12 small colored squares/circles that burst outward and fade via `@keyframes`, 1s duration, no JS)
- "25 questions! You're building a detailed knowledge profile."
- "50 questions! Comprehensive coverage — impressive dedication."

Toast: slides in from bottom-right, 3s display, auto-dismiss. M3 standard easing for enter, emphasized-accelerate for exit.

### D2. Expertise Button Highlight

The existing "My Areas of Expertise" modal already serves as a session summary. The problem is discoverability — personas never found it without prompting.

**Fix**: After the user answers 15+ questions (outside of tutorial mode), add a one-time subtle pulsing animation to the "My Areas of Expertise" button to draw attention. The pulse uses the same M3 highlight ring as tutorial highlights (2px accent border, soft glow, 1.5s interval) but fires only once and auto-stops after 6 seconds or on any user interaction. Track in localStorage so it only triggers once per session.

### D3. Running Progress Display

Add a subtle, non-intrusive progress indicator to the quiz panel:
- Question count: "Q12" in the panel header
- Current domain accuracy: small bar or percentage next to domain name
- Streak indicator: "3 in a row!" for consecutive correct answers (motivating for competitive users)

### D4. Proactive Video Recommendations

After identifying weak areas (3+ incorrect in a domain):
- Show a subtle suggestion in the quiz panel: "Want to learn more about [domain]? We have video recommendations."
- Link to the video panel / suggested learning modal
- Don't interrupt the quiz flow — show between questions during the feedback delay

---

## Phase E: Persona Re-Testing

### E1. Preserve Testing Framework

The persona testing framework from spec 004 is fully preserved:
- `tests/visual/personas/definitions.js` — 21 persona definitions
- `tests/visual/personas/runner.js` — Playwright automation
- `tests/visual/personas/evaluator-prompts.js` — AI evaluation prompts
- `tests/visual/personas/report-compiler.js` — Report generation
- `tests/visual/persona-agents.spec.js` — Phase 1 Playwright tests
- `scripts/run_persona_phase2.mjs` — Phase 2 orchestration

### E2. Tutorial-Aware Persona Testing

Add a tutorial-aware testing mode:
- **New personas** (or existing personas on second run): start with tutorial enabled
- Persona agents evaluate the tutorial experience as part of their assessment
- Tutorial can be pre-disabled via localStorage injection for personas testing non-tutorial flows
- Add new evaluation dimensions to the prompt: `tutorialClarity`, `tutorialPacing`, `tutorialCompleteness`

### E3. Re-Run Validation

After all Phase A-D changes are implemented:
1. Re-run Phase 1 for all 18 personas (fresh checkpoints)
2. Re-run Phase 2 AI evaluations
3. Compile aggregate report
4. Target: 90%+ pass rate (SC-001)

If pass rate < 90%, iterate on the specific failing personas before declaring the spec complete.

---

## Clarifications

### Session 2026-03-05

- Q: How should the tutorial adapt for mobile viewports (≤480px) where minimap and modes wrapper are hidden? → A: Adapt steps — skip minimap highlights on mobile, simplify domain-switch steps. No separate mobile tutorial flow.
- Q: If a returning user re-enables the tutorial with existing map state, what happens? → A: Keep existing state intact. Tutorial text adapts to acknowledge existing progress (e.g., "Your map already has some data").
- Q: How should the session summary (D2) be triggered? → A: No auto-trigger. The existing "My Areas of Expertise" modal already serves this purpose. After 15+ questions, highlight the button with a subtle pulsing animation to draw attention.
- Q: What scope for the milestone confetti animation? → A: CSS-only keyframe animation (~12 small colored elements, burst outward + fade). No canvas particle system, no JS library.
- Q: Should tutorial Step 7 build a custom summary or use existing modals? → A: Both. First show a simplified 2-line summary (strongest + weakest areas). Then highlight the "My Areas of Expertise" button with a brief overlay, then highlight the "Suggested Learning" button with a brief overlay. Reuse existing modals, no duplicate UI.

---

## Non-Goals

- Full redesign of the quiz panel or map renderer
- New question generation (only fixing existing broken questions)
- Pedant persona testing (P19-P21) — deferred to future spec
- Accessibility audit (important but separate scope)
- Tutorial localization / i18n

## Dependencies

- Spec 004 persona framework (complete, on branch `004-persona-user-testing`)
- Existing UI components (quiz panel, header, map, minimap, modals)
- `data/domains/*.json` question banks
- Vite dev server for local testing

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|-|-|-|-|
| Tutorial feels intrusive | Medium | High | Dismissible at every step, skip button always visible |
| Animations cause jank on mobile | Medium | Medium | CSS-only animations, `will-change` hints, `prefers-reduced-motion` |
| Tutorial breaks existing tests | Low | High | Tutorial disabled by default in test fixtures via localStorage |
| Data fixes introduce new errors | Low | Medium | Run /audit-questions after each fix, verify with persona re-test |
| SVG animations look cheap | Medium | High | Professional design pass, consistent theme colors, M3 easing |
