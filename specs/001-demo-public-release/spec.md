# Feature Specification: Ready Demo for Public Release

**Feature Branch**: `001-demo-public-release`
**Created**: 2026-02-16
**Status**: Draft
**Input**: GitHub Issue #18 — https://github.com/ContextLab/mapper/issues/18

## User Scenarios & Testing *(mandatory)*

### User Story 1 — First Visit: Explore a Knowledge Domain (Priority: P1)

A first-time visitor arrives at contextlab.github.io/mapper, reads a brief
introduction explaining that this demo maps their knowledge using text
embeddings, and selects a knowledge domain (e.g., "Neuroscience — General")
from a menu. The system presents a question of moderate difficulty. As the
visitor answers questions, a 2D heatmap fills in, showing their estimated
knowledge across the domain. The visitor can answer as many or as few
questions as they like and watch the map update in real time.

**Why this priority**: This is the core value proposition — a visitor must
be able to select a domain, answer questions, and see a knowledge map form.
Without this, nothing else matters.

**Independent Test**: Can be tested by loading the page, selecting any
single domain, answering 5–10 questions, and confirming the heatmap updates
with each answer.

**Acceptance Scenarios**:

1. **Given** a first-time visitor loads the page, **When** they read the
   introduction, **Then** they understand what the demo does, see a link to
   the research paper, and are invited to begin.
2. **Given** the visitor clicks "Start", **When** they see the domain
   selection menu, **Then** all domains and sub-domains are listed and
   selectable.
3. **Given** the visitor selects "Biology — General", **When** the map
   loads, **Then** the heatmap region for that domain is displayed with
   labeled grid squares, and the first question appears within 2 seconds.
4. **Given** the visitor answers a question, **When** the answer is
   submitted, **Then** the heatmap updates visibly, the confidence
   indicator changes, and the next question appears.

---

### User Story 2 — Navigate Between Domains (Priority: P2)

A visitor who has answered several questions in "Physics — General" wants to
zoom into "Quantum Physics." They open the domain menu and select the
sub-domain. The map smoothly transitions to the quantum physics region —
every visible data point (article dot, question marker) animates
continuously to its new position. If the target domain does not occupy a
cleanly separable 2D region in the current projection, the transition MAY
rotate through a 3D intermediate state to reach the new view, creating a
natural "turning the globe" effect. Points that leave the new view fade out
smoothly; points entering the new view fade in. Their previous physics
answers still influence the estimates, and the map shows partially filled
confidence even before answering any quantum physics questions specifically.
A navigation overview graphic shows which area of the overall knowledge
space they are currently viewing.

**Why this priority**: Domain navigation with smooth transitions and
cross-domain prediction is the key differentiator of this demo — it shows
the power of the embedding-based approach.

**Independent Test**: Can be tested by answering 5 questions in one domain,
switching to a related sub-domain, and confirming: (a) transition animation
plays with all points moving smoothly, (b) prior answers persist, (c) the
overview graphic updates, (d) no points "pop" or teleport.

**Acceptance Scenarios**:

1. **Given** a visitor has answered questions in "Physics — General",
   **When** they select "Quantum Physics" from the menu, **Then** the map
   performs a smooth animated transition where every data point
   continuously moves to its new coordinates (via pan/zoom and/or 3D
   rotation as needed by the geometry of the embedding space).
2. **Given** the visitor switches domains, **When** the new domain loads,
   **Then** all previously answered questions from any domain remain in
   memory and influence the displayed estimates.
3. **Given** the visitor is viewing a sub-domain, **When** they look at the
   navigation overview, **Then** the graphic highlights which region of the
   full embedding space is currently active, and clicking a different region
   switches the active domain.
4. **Given** the visitor switches between domains rapidly, **When**
   animations are still playing, **Then** the most recent selection takes
   priority and the transition completes without visual glitches.
5. **Given** the source and target domains do not occupy cleanly separable
   2D regions, **When** the transition plays, **Then** the animation
   rotates through a 3D intermediate state so that points appear to "turn"
   into view rather than cross over each other in 2D.
6. **Given** some data points exist in the source domain but not the
   target, **When** the transition plays, **Then** those points smoothly
   fade out (opacity 1→0) rather than abruptly disappearing.

---

### User Story 3 — Smart Question Modes (Priority: P3)

A visitor who has built up some map coverage wants to explore specific
aspects of their knowledge. They open a "Question Mode" menu that offers
options like: "Ask me an easy question," "Ask me the hardest question I can
answer," "Ask me something I don't know," and more. Each mode selects
questions using a different strategy based on the current confidence
estimates and knowledge map state.

**Why this priority**: These modes showcase the intelligence of the mapping
approach and make the demo engaging and shareable. They depend on having a
functioning map (P1) and enough answered questions to produce meaningful
estimates.

**Independent Test**: Can be tested by answering 15+ questions in a domain,
then selecting each question mode and verifying the selected question
matches the mode's strategy.

**Acceptance Scenarios**:

1. **Given** a visitor has answered at least 5 questions, **When** they
   select "Ask me an easy question", **Then** the system presents a
   basic-difficulty question biased toward regions where the visitor has
   demonstrated knowledge.
2. **Given** the visitor has built sufficient map coverage, **When** they
   select "Ask me the hardest question I can answer", **Then** the system
   selects the highest-difficulty question in a high-knowledge region.
3. **Given** sufficient coverage, **When** the visitor selects "Ask me
   something I don't know", **Then** the system selects the highest-
   difficulty question in the lowest-knowledge region.
4. **Given** the visitor has low coverage (fewer than 5 questions answered),
   **When** modes requiring high confidence are shown, **Then** those modes
   are visually disabled with a tooltip explaining more questions are needed.

---

### User Story 4 — Knowledge Insights (Priority: P4)

After answering enough questions, a visitor wants a summary of their
knowledge profile. They can access insight panels that list their areas of
expertise, areas of weakness, and suggested topics to learn more about.
These insights are derived from the knowledge map estimates and provide
clear, human-readable descriptions.

**Why this priority**: Insights provide the "payoff" for answering
questions and make the experience feel personalized. They depend on
sufficient map coverage from P1 and P3.

**Independent Test**: Can be tested by answering 20+ questions across
varying difficulty levels, then viewing each insight panel and confirming
the listed topics match the answer pattern.

**Acceptance Scenarios**:

1. **Given** a visitor has answered 20+ questions, **When** they select
   "List my areas of expertise", **Then** the system displays the top 5
   regions where the visitor has demonstrated the highest knowledge, using
   the human-readable cell labels.
2. **Given** sufficient coverage, **When** the visitor selects "List my
   areas of weakness", **Then** the system displays the 5 regions with the
   lowest estimated knowledge.
3. **Given** sufficient coverage, **When** the visitor selects "Suggest
   something to learn", **Then** the system displays 5 regions of medium
   estimated knowledge where learning effort would be most productive.

---

### User Story 5 — Cross-Domain Predictions (Priority: P5)

A visitor has answered questions in "Mathematics — General" but has never
selected "Probability and Statistics." When they switch to that sub-domain,
the map already shows partial estimates based on the mathematical proximity
of embedding coordinates. The visitor can see that the system predicts their
knowledge in related areas before they answer any sub-domain-specific
questions.

**Why this priority**: This is the signature research demonstration — that
embeddings capture conceptual relationships across domains. It requires
all prior stories to work and enough data coverage to produce meaningful
cross-domain estimates.

**Independent Test**: Can be tested by answering 15+ questions in a general
domain, then switching to a never-before-visited sub-domain, and confirming
the map shows non-zero estimates in regions conceptually related to
previously answered questions.

**Acceptance Scenarios**:

1. **Given** a visitor has answered questions only in "Mathematics —
   General", **When** they switch to "Probability and Statistics",
   **Then** the map displays non-zero knowledge estimates in areas
   conceptually related to already-answered math questions.
2. **Given** a visitor has answered questions in "Neuroscience — General",
   **When** they switch to "Biology — General", **Then** the biology
   map reflects partial knowledge from neuroscience-related regions.

---

### User Story 6 — Self-Contained Documentation (Priority: P6)

A visitor or researcher wants to understand the methodology behind the
knowledge mapping approach. They click an "About" or "Learn More" link and
read a self-contained explanation that covers: what the demo does, how the
embedding-based approach works conceptually, and links to the research paper
and GitHub repository. No external documentation is needed beyond the page.

**Why this priority**: Documentation completes the experience but does not
block core functionality.

**Independent Test**: Can be tested by reading the documentation section and
confirming all links work, explanations are clear to a non-technical
audience, and the paper citation is present.

**Acceptance Scenarios**:

1. **Given** a visitor clicks "About", **When** the documentation loads,
   **Then** it explains the knowledge mapping concept, describes the
   embedding approach in plain language, and links to the preprint
   (https://psyarxiv.com/dh3q2) and GitHub repository
   (https://github.com/ContextLab/efficient-learning-khan).
2. **Given** a published paper URL becomes available, **When** the
   documentation is updated, **Then** the published link replaces or
   supplements the preprint link.

---

### Edge Cases

- What happens when a visitor answers all 50 questions in a domain?
  The system notifies them that the domain is fully mapped and suggests
  switching to another domain or viewing insights.
- What happens when a visitor answers 0 questions and tries to view
  insights? Insight panels display a message explaining that at least
  10–20 questions must be answered before insights are available.
- What happens if the visitor's browser does not support modern features
  (e.g., older browsers without ES6)? The system displays a graceful
  fallback message recommending a supported browser.
- What happens if a CDN dependency (KaTeX, Font Awesome) fails to load?
  The system continues functioning with degraded styling; mathematical
  notation falls back to plain text representation.
- What happens on a slow connection when domain data is loading? The
  system displays a progress bar with percentage/bytes-loaded feedback.
  The interface remains responsive and interactive during the download.
- What happens on a mobile device with a small screen? The layout adapts
  to show the map and quiz panel in a stacked arrangement with touch-
  friendly controls for pan, zoom, and answer selection.
- What happens when localStorage is unavailable (private browsing,
  disabled, or full)? The system operates normally in a session-only
  mode and displays a non-blocking notice that progress will not be
  saved across visits.
- What happens when a returning visitor's stored data is from an older
  app version? The system detects the schema version mismatch, discards
  the incompatible data, and starts fresh with a brief notice that
  prior progress could not be restored.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST present a domain selection menu containing
  all defined knowledge domains and sub-domains, organized hierarchically
  (general domains with nested sub-domains).
- **FR-002**: System MUST provide exactly 50 questions per domain,
  spanning a range from beginner to expert difficulty, with every question
  and correct answer verified for 100% accuracy against primary sources.
- **FR-003**: System MUST display a 2D heatmap visualization showing
  estimated knowledge across the active domain's embedding space, updated
  in real time as questions are answered.
- **FR-004**: System MUST generate unique, human-readable labels for each
  grid square of the rectangular grid enclosing the active domain's
  question set.
- **FR-005**: System MUST perform a smooth animated transition when the
  user switches between domains, where every visible data point
  continuously moves to its new coordinates. When the source and target
  domains do not occupy cleanly separable 2D regions, the transition
  MUST rotate through a 3D intermediate state (a "turning the globe"
  effect) rather than allowing points to cross over each other in 2D.
  Points leaving the view MUST fade out smoothly; points entering MUST
  fade in.
- **FR-006**: System MUST maintain all user responses across domain
  switches within a single session, so that switching domains does not
  discard previously answered questions.
- **FR-007**: System MUST persist user responses across browser sessions
  using local storage, allowing visitors to return and continue. Stored
  data MUST include a schema version tag. When a returning visitor's
  stored data has an incompatible schema version, the system MUST
  discard the old data gracefully and start fresh rather than crashing
  or displaying corrupted state.
- **FR-008**: System MUST compute a confidence indicator representing
  the proportion of the active domain that has been mapped, factoring in
  both the number of answered questions and the spatial coverage of the
  embedding area they represent.
- **FR-009**: System MUST provide a navigation overview graphic that
  shows which region of the full knowledge space is currently active,
  and MUST allow the user to switch regions by interacting with the
  graphic.
- **FR-010**: System MUST provide at least the following smart question
  modes, selectable via a menu:
  - Ask me an easy question
  - Ask me the hardest question I think I can answer
  - Ask me something I don't know
  - List my areas of expertise
  - List my areas of weakness
  - Suggest something I might be interested in learning more about
- **FR-011**: System MUST disable smart question modes that require
  sufficient map coverage when the visitor has not yet answered enough
  questions, with a clear explanation of why the mode is unavailable.
- **FR-012**: System MUST run entirely in the browser with no server-side
  computation required. All question data, embeddings, and labels MUST
  be pre-computed and served as static assets. Domain data (questions,
  articles, labels) MUST be lazy-loaded per domain on demand rather
  than bundled into a single upfront download. The initial page load
  MUST include only the application code and the domain registry
  (~5 KB); no domain bundle is loaded until the visitor selects a
  domain from the menu. When domain data is loading (initial or on
  domain switch), the system MUST display a progress bar showing
  download progress to provide instant feedback, especially on slow
  connections.
- **FR-013**: System MUST include self-contained documentation accessible
  from the main interface, with links to the research preprint and
  GitHub repository.
- **FR-014**: System MUST support touch interactions (pan, zoom, answer
  selection) on mobile and tablet devices.
- **FR-015**: System MUST render all mathematical notation in questions
  using LaTeX, with correct display across all supported browsers.
- **FR-016**: System MUST select the next question using a principled
  active learning algorithm that maximizes expected information gain
  over the currently visible map region. The algorithm MUST consider
  only cells within the active viewport when computing acquisition
  scores, so that questions are relevant to what the visitor is
  currently viewing.
- **FR-017**: System MUST distinguish between "unknown" regions (no
  nearby answers, high prior uncertainty) and "uncertain" regions
  (conflicting nearby answers, high posterior uncertainty). Question
  selection MUST prioritize uncertain regions over unknown regions
  when both are visible, because uncertain regions contain more
  actionable information.
- **FR-018**: System MUST implement curriculum-style question
  progression: early questions SHOULD target central, well-connected
  "landmark" cells that provide maximum spatial coverage, while later
  questions SHOULD target niche boundary cells that refine the map's
  edges. The transition from landmark to niche MUST be adaptive based
  on cumulative coverage, not based on a fixed question count.
- **FR-019**: System MUST NOT permanently exclude a cell from question
  selection after one question has been asked in that cell. Cells with
  multiple available questions MUST remain eligible for re-selection
  when their uncertainty warrants it.
- **FR-020**: During domain transitions, every individual data point
  (article dot, question marker) MUST animate independently along a
  smooth interpolation path from its source coordinates to its target
  coordinates. Points MUST NOT teleport, pop, or move as a rigid
  group. The per-point animation MUST be synchronized so that all
  points complete their transitions within the same time window.
- **FR-021**: System MUST provide a visible "Reset Progress" control
  that clears all stored user responses and returns the interface to
  its initial first-visit state. The reset MUST require a confirmation
  step to prevent accidental data loss.
- **FR-022**: System MUST allow visitors to export their response
  history (questions answered, correctness, timestamps, domains) as a
  downloadable file before resetting, so that progress is not
  irrecoverably lost.
- **FR-023**: System MUST conform to WCAG 2.1 Level AA. All
  interactive controls (domain menu, answer selection, question modes,
  reset, export) MUST be keyboard-navigable with visible focus
  indicators. The heatmap visualization MUST provide text alternatives
  describing the knowledge distribution. Color contrast ratios MUST
  meet or exceed 4.5:1 for text and 3:1 for graphical elements. The
  heatmap color palette MUST be distinguishable by users with common
  color vision deficiencies (deuteranopia, protanopia).

### Defined Knowledge Domains

The following domains MUST be included at launch:

| General Domain | Sub-Domains |
|----------------|-------------|
| All (General) | *(merges all domains)* |
| Physics | Astrophysics, Quantum Physics |
| Art History | European Art History, Chinese Art History |
| Biology | Molecular and Cell Biology, Genetics |
| Neuroscience | Cognitive Neuroscience, Computational Neuroscience, Neurobiology |
| Mathematics | Calculus, Linear Algebra, Number Theory, Probability and Statistics |

Total: 6 general domains + 13 sub-domains = 19 selectable areas.
Each domain presents exactly 50 questions. Sub-domains have dedicated
unique questions. General domains mix questions drawn from their
children with unique "general" questions that span the broader domain.
"All (General)" draws from all other domains. Total unique questions
is approximately 750–800 (less than 19 × 50 = 950 because general
domains and "All" share some questions with sub-domains).

### Key Entities

- **Domain**: A knowledge area with a name, parent relationship
  (general or sub-domain), and a rectangular region in embedding space.
  Each domain contains exactly 50 questions and a set of labeled grid
  squares.
- **Question**: A verified quiz item with question text, answer choices,
  correct answer index, difficulty level (beginner to expert), embedding
  coordinates, and domain membership. A question MAY belong to multiple
  domains (e.g., a genetics question appears in both "Genetics" and
  "Biology — General").
- **Grid Label**: A unique human-readable label for one cell of the
  rectangular grid overlaying a domain's embedding region.
- **User Response**: A record of the visitor's answer to a specific
  question, including whether it was correct and a timestamp.
- **Knowledge Estimate**: A per-cell confidence value derived from
  answered questions, spatial proximity, and cross-domain embedding
  relationships.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first-time visitor can understand the demo's purpose,
  select a domain, and answer their first question within 60 seconds
  of page load.
- **SC-002**: The knowledge map heatmap updates visually within 500ms
  of each answered question, with no perceptible lag or jank.
- **SC-003**: Domain switching animations complete within 1 second and
  maintain 60fps throughout the transition.
- **SC-004**: 100% of pre-generated questions are factually accurate,
  verified against primary sources or Wikipedia.
- **SC-005**: The demo runs entirely in the browser with zero server
  calls after initial static asset loading — fully deployable to
  GitHub Pages.
- **SC-006**: All 19 domains load and display correctly, each with 50
  questions, unique grid labels, and proper embedding coordinates.
- **SC-007**: The visualization renders correctly and is fully
  interactive (pan, zoom, answer selection) on the latest two versions
  of Chrome, Firefox, Safari, and Edge, on Windows, macOS, and Linux.
- **SC-008**: The visualization is usable on mobile phones (320px+)
  and tablets (768px+) with touch controls for all interactions.
- **SC-009**: Cross-domain knowledge predictions produce non-zero
  estimates in conceptually related regions when a visitor has only
  answered questions in a different but related domain.
- **SC-010**: All smart question modes select questions matching their
  documented strategy at least 90% of the time, as validated by manual
  testing.
- **SC-011**: The active learning question selection algorithm (FR-016)
  achieves higher map accuracy (lower mean absolute error of knowledge
  estimates) than uniform random question selection, given the same
  number of answered questions, as measured by a simulated benchmark
  over 50-question sessions across all 19 domains.
- **SC-012**: During domain transition animations (FR-005, FR-020),
  every individual data point follows a smooth interpolation path with
  no frame where any point's position jumps by more than 5% of the
  viewport dimension, as verified by Playwright frame-by-frame
  screenshot comparison.
- **SC-013**: The demo passes WCAG 2.1 Level AA automated checks (axe
  or Lighthouse accessibility audit) with zero critical violations on
  all primary user flows (domain selection, question answering, mode
  switching, reset/export).

## Assumptions

- The domain list (19 areas) is the fixed launch set. The system should
  be structured so adding new domains requires only adding data files,
  not code changes.
- User responses persist within a session and across sessions via browser
  local storage. There is no user account system or server-side storage.
- The embedding model choice is an implementation detail; the spec
  requires high-quality embeddings that preserve semantic relationships
  across the defined domains.
- The navigation overview graphic will be a minimap showing the full
  embedding space with a highlighted rectangle indicating the active
  domain's region. This approach was chosen because it directly reflects
  the spatial nature of the embedding visualization and provides
  intuitive "click to navigate" behavior.
- "Pre-processing" (embedding generation, question creation, label
  generation) happens once using local compute or the existing GPU
  cluster. Only the final static data files are deployed to GitHub Pages.
- The published paper URL is not yet available; the preprint link will
  be used initially and updated when the published URL is provided.

## Clarifications

### Session 2026-02-16

- Q: How do parent-domain and sub-domain question sets relate — independent, hierarchical, or hybrid? → A: Hybrid. Sub-domains have dedicated unique questions. General domains mix questions drawn from their children with unique "general" questions. "All (General)" draws from all domains. Total unique questions ≈ 750–800.
- Q: How should localStorage handle version mismatches and user resets? → A: Store a schema version tag; discard incompatible old data gracefully. Provide a visible "Reset Progress" button with confirmation. Allow visitors to export their response history as a downloadable file before resetting.
- Q: What level of accessibility compliance should the demo target? → A: WCAG 2.1 Level AA — keyboard navigation, screen reader labels, 4.5:1 contrast ratios, color-blind-safe heatmap palette.
- Q: Should all domain data load upfront or lazily? → A: Lazy-load per domain. Initial payload is code + default domain only (~2–3 MB). Show progress bars with download feedback when loading domain data on slow connections.

### Session 2026-02-18 (Post-Implementation Review)

#### Embedding & Domain Pipeline (Critical — P0)

- **FINDING**: Question coordinates are NOT in the same embedding space as
  Wikipedia articles. Questions use PCA projection scaled to hand-drawn
  bounding boxes (`scripts/generate_question_coords.py` lines 64–103).
  Articles use UMAP projection from `Qwen/Qwen3-Embedding-0.6B` embeddings.
  Domain regions are hand-drawn grid rectangles, not derived from semantic
  clustering. Articles in domains are spatially filtered (whatever falls
  in the rectangle), not topically relevant.

- **REQUIREMENT**: Question embeddings MUST be projected through the SAME
  UMAP reducer as articles. Use RAG (embedding similarity search against
  the 250K article corpus) to find semantically related articles per domain
  (top 500 for sub-areas, 1000 for broad areas; "All" uses full corpus).
  Domain bounding rectangles MUST be computed from actual article+question
  clusters, not hand-drawn. Domains WILL overlap. Grid system: smallest
  region gets 50×50 grid; full space tiled proportionally.

- **REQUIREMENT**: When a domain is selected, content outside the domain
  MUST still be visible. The only change is a zoom into the domain's region
  and constraining questions to that area. Do NOT cut off content.

- **REQUIREMENT**: Since domains overlap, the minimap MUST NOT label
  regions with category names. Instead, show a viewport rectangle indicating
  the current position on the full map, updated on pan/zoom.

#### Theme Consistency (P1)

- **FR-024**: Theme toggle MUST update ALL visual elements simultaneously:
  main canvas, minimap, colorbar, particle system, quiz panel, mode buttons.
  No element should lag behind or require a domain switch to update.

- **FR-025**: The minimap MUST use theme-aware colors (not hardcoded dark
  mode values). Light mode: white/light background. Dark mode: navy
  background.

#### UI Polish (P1)

- **FR-026**: Mode buttons ("Auto", "Easy", etc.) MUST have readable text
  in both active and inactive states. The active state MUST NOT use dark
  text on dark green background. Use white text on dark backgrounds.

- **FR-027**: Disabled mode button tooltips MUST have a solid background,
  border, and proper contrast. They MUST NOT overlay directly on button
  text without a background.

- **FR-028**: Quiz question text and answer options MUST be fully
  left-justified. No first-line indentation.

- **FR-029**: Map tooltips MUST show: (a) article excerpt when hovering
  over article dots, (b) question text when hovering over question dots,
  (c) knowledge-colored backgrounds (green for correct, red for incorrect,
  neutral for unanswered). Style must match the main branch implementation.

- **FR-030**: The quiz panel MUST have a visible toggle button to open/close
  it. Pressing Escape dismisses the panel, but the toggle button remains
  visible to reopen it. Panel slides in/out with animation.

- **FR-031**: The colorbar MUST be visible whenever a domain is loaded (not
  only after questions are dismissed). It MUST use theme-appropriate text
  colors and system fonts (not "Space Mono"). Position MUST adjust when
  the quiz panel opens/closes.

- **FR-032**: The "Knowledge Mapper" title gradient (header + landing page)
  MUST be entirely green (Dartmouth Green shades). MUST NOT fade to blue.

#### New Features (P2)

- **FR-033**: The About modal MUST include a keyboard shortcuts section
  listing all available keyboard interactions.

- **FR-034**: System MUST support importing a previously exported response
  JSON file, restoring all answers and updating the knowledge map.

- **FR-035**: System MUST provide social sharing buttons (LinkedIn, X/
  Twitter, Bluesky, Instagram) that post a rendered image of the user's
  knowledge map with their top areas of expertise.

#### Comprehensive UX Testing (P3)

- **SC-014**: Playwright tests MUST simulate detailed interactions with
  at least 5 distinct user personas: casual browser, domain expert,
  curious college student, UI/UX expert, business professional. Each
  persona must exercise different interaction patterns and all must
  receive a delightful experience.

## Research References

The following research informs the active learning (FR-016–FR-019) and
transition animation (FR-005, FR-020) requirements. These are
background references for implementors, not binding specifications.

### Active Learning & Question Selection

- **Hacohen & Weinshall (2023)** — "Active Learning on a Budget."
  Introduces a derivative-based selector that dynamically switches
  between diversity-first and uncertainty-first strategies depending on
  annotation budget. Key insight: diversity sampling dominates in
  low-budget regimes (early questions), while uncertainty sampling
  dominates in high-budget regimes (later questions). Relevant to
  FR-018's curriculum progression.
  *Source: OpenReview / ICLR 2023 workshop.*

- **Hacohen & Weinshall (2020)** — "Curriculum Learning by Transfer
  Learning." Demonstrates that ordering training examples from easy to
  hard (curriculum learning) improves convergence and generalization.
  Relevant to FR-018's landmark-first, niche-later progression.
  *Source: ICML 2020.*

- **Hübotter et al. (2025)** — "Transductive Active Learning: Theory
  and Applications." Proposes restricting the acquisition function to
  the set of prediction targets (transductive setting) rather than the
  full input space. Relevant to FR-016's viewport-restricted question
  selection.
  *Source: arXiv:2402.15898.*

- **Müller et al. (2023)** — "PFNs4BO: In-Context Learning for
  Bayesian Optimization." Demonstrates Prior-Fitted Networks as
  surrogate models for Bayesian optimization with expected information
  gain acquisition. Relevant to FR-016's information-gain-based
  scoring as an alternative to Gaussian Process surrogates.
  *Source: arXiv:2305.17535.*

### 3D Transitions & Visualization

- **Geodesic interpolation on the Stiefel manifold** (Grand Tour
  literature) — Interpolating projection bases along geodesics
  produces rotation-like transitions between 2D views of
  high-dimensional data. Relevant to FR-005's 3D intermediate state.

- **deck.gl / regl-scatterplot / Embedding Atlas** — Production
  WebGL/WebGPU scatterplot libraries with built-in per-point
  transition animation support. Relevant to FR-020's per-point
  smooth interpolation requirement.
