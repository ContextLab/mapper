# Feature Specification: Persona-Based User Testing Framework

**Feature Branch**: `004-persona-user-testing`
**Created**: 2026-03-02
**Status**: Draft
**Input**: Rigorous user testing framework with 10-20 diverse personas — each simulated by an AI agent (Sonnet 4.6 or Opus 4.6) role-playing a specific person with domain knowledge, expectations, and critical judgment. Agents interact with the real application via browser automation, critically evaluate every aspect of the experience (questions, map accuracy, UX), and produce detailed belief-level assessments that drive improvements via GitHub issues and PRs.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reporter Quick Demo (Priority: P1)

A technology reporter visits Knowledge Mapper to evaluate it for an article. They have 5-10 minutes. They click "Start," answer 5-8 easy questions (selecting obvious answers quickly), skip or guess on 2-3 hard questions, then zoom around the map exploring the visualization. They hover over article dots, zoom in and out, and try to understand what the heatmap means.

The persona agent role-playing the reporter MUST think critically: *"Would I write a positive article about this? What would my headline be? What screenshot would I use? Is there anything embarrassing or confusing that would make me write a negative piece instead?"* The agent reads each question and evaluates whether it seems well-crafted, whether the reporter would understand what's being tested, and whether the experience feels polished enough for a tech publication.

**Why this priority**: First impressions drive press coverage. If the demo doesn't impress in 5 minutes, the opportunity is lost. This is the highest-stakes user journey.

**Independent Test**: Can be tested by simulating 5-8 correct answers + 2-3 skips, then capturing screenshots of the resulting map at multiple zoom levels. The persona agent evaluates visual impact, question quality, and produces a mock "reporter's impression" narrative. Pass requires a positive impression with no embarrassing artifacts.

**Acceptance Scenarios**:

1. **Given** a new user on the landing page, **When** they click Start and answer 5 easy questions correctly, **Then** the knowledge map shows visible colored regions (not blank/uniform) within 3 seconds of the last answer.
2. **Given** a user who has answered 5 questions, **When** they skip 2 hard questions, **Then** the map updates to reflect skipped areas (yellow markers visible) and the overall visualization remains visually coherent.
3. **Given** a user viewing the map, **When** they zoom in and out, **Then** the heatmap, article dots, grid lines, and answered-question markers all move together without misalignment, and the visualization responds within 500ms.
4. **Given** a user hovering over article dots on the map, **When** the popup appears, **Then** it shows the article title (without underscores), a brief description, and does not block the user's ability to scroll/pan.
5. **Given** the persona agent evaluating each question encountered, **When** the agent reads the question and options, **Then** the agent reports whether the question is clear, whether the correct answer is unambiguously correct, whether distractors are plausible, and whether a reporter would find the question interesting or confusing.
6. **Given** the persona agent completing the session, **When** it writes its "reporter's impression" narrative, **Then** the narrative must express genuine positive engagement — not just absence of bugs but active delight or intellectual curiosity.

---

### User Story 2 - Expert Scientist Deep Evaluation (Priority: P1)

A neuroscience professor wants to see if the system can accurately identify their expertise. They select the "neuroscience" domain, answer 30+ questions carefully and honestly (getting most right in their specialty, struggling in adjacent areas). They expect the heatmap to show strong knowledge (green) in their specialty area and weaker knowledge (red/yellow) in unfamiliar sub-topics.

The persona agent role-playing the professor MUST use real domain knowledge to evaluate every question: *"Is this question actually about neuroscience? Is the 'correct' answer genuinely correct? Would a real neuroscience professor find this question appropriate for assessing expertise, or would they think it's trivially easy, misleadingly hard, or testing the wrong thing?"* The agent should flag questions where the marked correct answer is debatable, where distractors are too obviously wrong (no real expert would be fooled), or where the question tests trivia rather than understanding. The agent also evaluates map accuracy: *"I know I'm strong in synaptic plasticity and weak in computational neuroscience — does the map reflect that, or is it showing something that contradicts my self-knowledge?"*

**Why this priority**: Scientific credibility depends on the estimator producing accurate, believable knowledge maps. If experts see incorrect assessments, trust is destroyed.

**Independent Test**: Can be tested by simulating an expert answer pattern (90%+ correct in one region, 30-50% in others), then verifying the heatmap shows clear differentiation. The persona agent produces a question quality audit and a belief-vs-reality assessment at each checkpoint. Pass requires both accurate mapping AND acceptable question quality.

**Acceptance Scenarios**:

1. **Given** an expert answering 30+ questions with 90%+ accuracy in one sub-domain, **When** the map is rendered, **Then** the expert's specialty area shows green distinctly different from unexplored or weak areas (red/yellow).
2. **Given** an expert who has answered 30+ questions, **When** they view the "domain mapped" percentage, **Then** it reflects a reasonable proportion (not stuck at 18% or jumping suddenly to 95%).
3. **Given** an expert answering incorrectly on hard questions outside their specialty, **When** the estimator updates, **Then** the penalty for wrong answers on hard questions is less severe than for wrong answers on easy questions (hard questions being wrong is expected).
4. **Given** an expert who skips questions they genuinely don't know, **When** the estimator updates, **Then** skipped questions provide stronger evidence of lack of knowledge than random wrong guesses.
5. **Given** the persona agent evaluating each question with real domain expertise, **When** the agent audits question content, **Then** no more than 10% of questions are flagged as having incorrect marked answers, ambiguous phrasing, or misaligned topic placement.
6. **Given** the persona agent comparing its known expertise profile to the rendered map, **When** the agent identifies regions where it answered strongly vs weakly, **Then** the map's color distribution matches the agent's self-assessment — strong areas are green, weak areas are red/yellow, with clear spatial separation.

---

### User Story 3 - Scientist Exploring Unfamiliar Domain (Priority: P2)

A physicist selects "biology" — a domain they know little about. They answer honestly, getting most questions wrong or skipping them. They expect the map to show predominantly red/yellow indicating lack of knowledge, with perhaps small green pockets of incidental knowledge.

**Why this priority**: The system must handle low-knowledge users gracefully without producing confusing or discouraging visualizations.

**Independent Test**: Can be tested by simulating mostly-wrong answers in an unfamiliar domain and verifying the map shows predominantly red/yellow without visual artifacts or estimator collapse.

**Acceptance Scenarios**:

1. **Given** a user answering mostly wrong (20-30% accuracy) across 20+ questions, **When** the map is rendered, **Then** the heatmap shows predominantly red/yellow with no sudden jumps or collapses.
2. **Given** a low-knowledge user who answers 20+ questions, **When** they check the domain mapped percentage, **Then** it increases smoothly and proportionally (no sudden jumps from low to very high values).
3. **Given** a user who gets a few scattered questions correct in an unfamiliar domain, **When** the map is rendered, **Then** small green pockets appear near those correct answers, surrounded by red/yellow regions.

---

### User Story 4 - Genuine Learner Self-Discovery (Priority: P2)

A curious undergraduate uses the "all" domain map to explore their overall knowledge. They answer 40-60 questions across multiple domains, performing well in some areas and poorly in others. They expect to discover patterns about themselves — strong in one field, weak in another — and feel motivated to explore further.

The persona agent role-playing the undergraduate MUST track its emotional arc: *"Am I having fun? Am I learning about myself? Do the questions feel fair — testing real knowledge, not obscure trivia? When I look at the map, can I actually understand what it's telling me? If I showed this to a friend, could I explain what the colors mean?"* The agent should flag moments where the experience stalls (map doesn't visibly change despite many answers), where questions feel repetitive or off-topic, or where the visualization is confusing rather than illuminating. The agent also evaluates whether questions span a genuine diversity of topics within each domain, or whether the same narrow sub-topic keeps recurring.

**Why this priority**: This is the core use case of Knowledge Mapper. Users who invest significant time must feel rewarded with genuine insights.

**Independent Test**: Can be tested by simulating mixed-knowledge answers across multiple domains and verifying the map shows distinct regional variation. The persona agent produces a belief narrative tracking engagement, confusion points, and "aha moments." Pass requires both visual accuracy AND a positive emotional arc in the agent's narrative.

**Acceptance Scenarios**:

1. **Given** a user answering 40-60 questions across multiple domains with mixed accuracy, **When** the map is rendered, **Then** the heatmap shows clearly distinct regions of strong and weak knowledge (not a uniform blob).
2. **Given** a learner who has completed 40+ questions, **When** they continue answering, **Then** the map evolves smoothly with each answer (no sudden complete recoloring or collapse).
3. **Given** a learner viewing their completed map, **When** they hover over different regions, **Then** they can identify which topics they know well and which they don't, matching their self-assessment.
4. **Given** a learner who wants to share their results, **When** they click the share button, **Then** the share modal opens with working social media links, a copy button that copies text, and a copy image button that copies the map screenshot.
5. **Given** the persona agent tracking its engagement level throughout the session, **When** the session ends, **Then** the agent's narrative reports at least one "aha moment" (a genuine insight about its knowledge profile) and no sustained periods of boredom or frustration lasting more than 5 consecutive questions.
6. **Given** the persona agent evaluating question diversity, **When** the agent reviews all questions encountered, **Then** no single narrow sub-topic accounts for more than 30% of questions within any domain, ensuring genuine breadth of assessment.

---

### User Story 5 - Mobile Reporter Quick Glance (Priority: P2)

A reporter uses their phone (iPhone or Android) to quickly check out the demo. They answer 3-5 questions, scroll around the map, and try the share feature. The experience must feel polished and touch-friendly.

**Why this priority**: Mobile traffic is significant and first impressions on mobile are even more fragile than desktop.

**Independent Test**: Can be tested on mobile viewports (390px iPhone, 393px Pixel) by simulating tap interactions and capturing screenshots to verify layout integrity.

**Acceptance Scenarios**:

1. **Given** a mobile user on the landing page, **When** they tap Start and answer 3 questions, **Then** the quiz panel is fully visible, options are tap-friendly (minimum 44px touch targets), and no content overflows the viewport.
2. **Given** a mobile user viewing the map, **When** they pinch-to-zoom and scroll, **Then** the map responds fluidly without misalignment between layers.
3. **Given** a mobile user, **When** they use keyboard shortcuts accidentally while typing, **Then** modifier keys (like selecting text) do not trigger quiz answer selection.

---

### User Story 6 - Cross-Browser Consistency (Priority: P3)

Users access Knowledge Mapper on different browsers (Chrome, Firefox, Safari). The experience must be consistent — same visual quality, same interaction patterns, same accuracy of knowledge mapping.

**Why this priority**: Browser inconsistencies erode trust and create support burden.

**Independent Test**: Can be tested by running identical persona simulations across all three browsers and comparing screenshots for visual consistency.

**Acceptance Scenarios**:

1. **Given** the same persona simulation (same answers, same sequence), **When** run on Chrome, Firefox, and Safari, **Then** the resulting heatmaps are visually equivalent (same color regions, same spatial distribution).
2. **Given** any browser, **When** the user completes 20+ questions, **Then** no console errors related to numerical instability (Cholesky decomposition, divide by zero) appear.
3. **Given** any browser, **When** the user interacts with the minimap viewport rectangle, **Then** dragging pans the view (does not zoom all the way out).

---

### User Story 7 - Power User Session (Priority: P3)

An engaged user answers 100-150 questions in a single session, pushing the system to its limits. They expect the map to evolve continuously and meaningfully throughout, never collapsing or producing nonsensical results.

**Why this priority**: Power users are the most valuable advocates. System failure after significant time investment is the worst possible outcome.

**Independent Test**: Can be tested by simulating 120+ answers and monitoring the estimator at checkpoints (every 20 questions) for smooth progression, absence of collapse, and consistent domain-mapped percentage growth.

**Acceptance Scenarios**:

1. **Given** a user who has answered 100+ questions, **When** they continue answering, **Then** the map continues to update meaningfully (not stuck as a uniform red/green blob).
2. **Given** a user at ~115-120 answers, **When** the estimator updates, **Then** the domain mapped percentage does not suddenly jump (e.g., from 18% to 95%) and the heatmap does not suddenly and completely change pattern.
3. **Given** a user with 100+ answers, **When** they check the browser console, **Then** no Cholesky decomposition errors or divide-by-zero warnings appear.
4. **Given** a user who exports their progress, closes the browser, and reimports from the landing page, **When** the map loads, **Then** it shows the complete history (all previously answered questions visible, not just the first one).

---

### User Story 8 - Video Discovery Journey (Priority: P3)

A learner who has mapped their knowledge (30+ questions answered) wants to find educational videos to fill their knowledge gaps. They open the video panel, browse recommended videos, watch one, and see their knowledge map update.

**Why this priority**: Video recommendations are a key differentiator. The experience must be seamless from discovery to completion.

**Independent Test**: Can be tested by simulating 30+ answers, opening the video panel, verifying recommendations appear, simulating video playback, and capturing screenshots showing the map update.

**Acceptance Scenarios**:

1. **Given** a user with 30+ answers and knowledge gaps visible on the map, **When** they open the video panel, **Then** recommended videos appear sorted by relevance to their weakest areas.
2. **Given** a user viewing video recommendations, **When** they hover over a video in the list, **Then** the video's trajectory highlights on the map showing what knowledge area it covers.
3. **Given** a user who completes watching a video, **When** they return to the map, **Then** the knowledge map updates to reflect the newly acquired knowledge (color shift in the video's coverage area).

---

### User Story 9 - Pedantic Content Audit (Priority: P1)

A meticulous domain expert goes through EVERY question in a domain, carefully evaluating each question's correctness, clarity, and educational value. They answer every question using genuine domain expertise, verify any suspected errors via web search, and track whether the map responds appropriately to each answer. Their goal is to produce a comprehensive quality audit of the entire question bank.

The persona agent (Opus 4.6) MUST have deep domain expertise and zero tolerance for inaccuracy. For each question: *"Is the marked answer actually correct? Let me verify... The question says the answer is B, but I believe it should be C because [specific reasoning]. Let me search the web to confirm before flagging this."* Every correction MUST be backed by a cited web source. The agent also evaluates whether each question tests meaningful understanding or obscure trivia, whether the difficulty matches the question's position in the knowledge map, and whether each answer produces an appropriate change in the heatmap.

**Why this priority**: Question quality is foundational — if questions have wrong answers, everything built on them (estimator accuracy, user trust, map fidelity) is compromised. This is the most important audit tier.

**Independent Test**: Can be tested by running the pedant agent through every question in a domain and reviewing the resulting audit spreadsheet. Pass requires fewer than 5% of questions flagged as having incorrect marked answers (verified by web search), and the resulting full-domain map shows clear spatial variation matching the agent's deliberate answer pattern.

**Acceptance Scenarios**:

1. **Given** a pedant agent answering every question in a domain, **When** the agent encounters a question where the marked correct answer appears wrong, **Then** the agent performs a web search to verify, cites the source, and flags the question only if the web evidence supports the correction.
2. **Given** a pedant agent completing all questions in a domain, **When** the full audit is produced, **Then** no more than 5% of questions have confirmed incorrect marked answers, and all flagged questions include cited web evidence.
3. **Given** a pedant agent tracking map changes after every answer, **When** the agent completes all questions, **Then** the cumulative expectation-reality gap report shows the map converged toward an accurate representation of the agent's deliberate answer pattern.
4. **Given** any question flagged by the pedant agent as having an incorrect answer, **When** the correction is implemented, **Then** the fix is verified by re-running the pedant simulation and confirming the agent no longer flags that question.
5. **Given** a pedant agent evaluating question quality, **When** the full audit is produced, **Then** no more than 15% of questions are rated below 3/5 on any quality dimension (accuracy, clarity, difficulty appropriateness, educational value).

---

### Edge Cases

- What happens when a user answers all questions in a domain? Does the system gracefully indicate completion?
- What happens when a user rapidly clicks through 10+ answers without reading? Does the estimator remain stable?
- What happens when a user resizes their browser window mid-session? Do all canvas layers realign correctly?
- What happens when a user imports a corrupted or empty JSON progress file? Does the system show a helpful error?
- What happens when network connectivity is lost mid-session? Does the system preserve progress locally?
- What happens on very small screens (320px width)? Is the core experience still usable?
- What happens when a user switches domains after answering 50+ questions? Does the new domain load correctly without leaking state from the previous domain?

## Cognitive Simulation Framework *(mandatory for this feature)*

### Persona Agents Are Thinking Humans, Not Click-Bots

Each persona is simulated by an AI agent (Sonnet 4.6 or Opus 4.6) that role-plays a specific person with real domain knowledge, expectations, and critical judgment. The agent does not simply follow a mechanical script — it **thinks** as the persona would think, **reacts** as the persona would react, and **evaluates** the experience as a critical human would evaluate it.

### What Persona Agents Must Evaluate

#### 1. Question Quality Assessment
For every question encountered, the persona agent MUST evaluate:
- **Content validity**: Does this question actually test the topic it claims to test? Is the question about the right concept for its position on the map?
- **Distractor quality**: Are the wrong answers plausible enough to be challenging but clearly wrong to an expert? Or are some distractors obviously ridiculous? Are any distractors arguably correct?
- **Difficulty calibration**: Does the question's apparent difficulty match where it appears in the knowledge map? Would an expert in this area find it appropriately challenging?
- **Clarity and phrasing**: Is the question unambiguous? Could a knowledgeable person misinterpret what's being asked? Are there grammatical errors or confusing wording?
- **Answer correctness**: Is the marked "correct" answer actually correct? The agent should use its own domain knowledge to verify.

#### 2. Belief-Level Tracking
At each checkpoint, the persona agent MUST report its internal beliefs:
- **"What am I thinking right now?"**: The agent narrates the persona's stream-of-consciousness reaction. Example: *"I just got 3 physics questions right but the map barely changed — I expected to see some blue appearing near those topics. This feels unresponsive."*
- **"What do I expect to see next?"**: Before looking at the map, the agent states what it expects. Example: *"I've answered 10 neuroscience questions with 90% accuracy. I expect the neuroscience region to be distinctly cooler than the surrounding areas."*
- **"Does reality match my expectation?"**: After viewing the screenshot, the agent compares reality to expectation. Example: *"The neuroscience area IS cooler, but the contrast is subtle — I expected a more dramatic difference given my strong performance."*
- **"How would I describe this to a colleague?"**: The agent summarizes the experience as the persona would relay it. This surfaces UX issues that metrics alone miss. Example: *"The questions were good but the map was hard to read — I couldn't tell where my knowledge gaps were."*
- **"What would make me stop using this?"**: The agent identifies friction points or deal-breakers for this persona type. Example: *"If I got a question that was clearly wrong or poorly worded, I'd lose trust in the entire system immediately."*

#### 3. Expectation-Reality Gap Analysis
Each persona agent MUST maintain a running log of expectation gaps:
- **Map accuracy gaps**: "I answered 5 biology questions correctly near topic X, but the map shows no knowledge in that area."
- **Estimator behavior gaps**: "I skipped a question I genuinely don't know, but the map penalized me less than when I guessed wrong — shouldn't it be the opposite?"
- **UX gaps**: "I expected hovering over a colored region to tell me what topic it represents, but nothing happened."
- **Question gaps**: "This question claims to test 'quantum mechanics' but it's really about classical thermodynamics."
- **Emotional gaps**: "After 30 questions I expected to feel a sense of accomplishment, but the map looks nearly the same as after 10 questions."

#### 4. Question-Map Alignment Audit
Each persona agent MUST evaluate whether questions are properly positioned:
- Does a question about "mitochondrial function" appear in the biology region of the map?
- If a question's article source is about Topic A, is the question actually testing knowledge of Topic A or something tangentially related?
- Are questions within a domain clustered in a way that makes semantic sense, or are unrelated topics mixed together arbitrarily?

### Persona Agent Output Format

Each persona simulation produces a structured report:

1. **Session Transcript**: Timestamped log of every action, thought, and reaction
2. **Question Audit**: Per-question evaluation (content validity, distractor quality, difficulty calibration, answer correctness) — flagging any problematic questions
3. **Checkpoint Beliefs**: At each screenshot checkpoint, the agent's expectations vs reality assessment
4. **Experience Summary**: The persona's overall impression, written in first person as the persona would describe it to a friend
5. **Critical Issues Found**: Ranked list of problems that would damage this persona's impression, with severity (blocker / major / minor / cosmetic)
6. **Recommendations**: Specific suggestions for improvement, tied to evidence from the session

### Pass/Fail/Ambiguous Criteria

For each persona simulation, the evaluation produces one of three results:

- **PASS**: The persona agent's expectations were met or exceeded at all checkpoints. No blocker or major issues found. The persona's "experience summary" is positive. Question audit found no incorrect answers and no more than 10% low-quality questions.
- **FAIL**: The persona agent found at least one blocker issue (crash, estimator collapse, completely wrong map, incorrect marked answer), OR the persona's experience summary expresses confusion, frustration, or distrust, OR more than 25% of questions flagged as problematic.
- **AMBIGUOUS**: The persona agent found only minor or cosmetic issues, but the experience summary expresses mixed feelings or mild disappointment. OR the expectation-reality gaps are small but consistent across multiple checkpoints. Ambiguous results require further investigation and human review.

## Personas *(mandatory for this feature)*

### Category A: Reporter/Demo Users

| ID  | Name                     | Device           | Browser | Behavior                                        | Domain  | Questions | Key Evaluation                  |
|-----|--------------------------|------------------|---------|--------------------------------------------------|---------|-----------|----------------------------------|
| P01 | Alex the Tech Reporter   | Desktop 1440px   | Chrome  | Quick: 5 correct, 2 skips, zoom around          | Physics | 7         | First impression, visual impact  |
| P02 | Maya the Mobile Journalist | iPhone 12 (390px) | Safari | Quick: 3 correct, 1 skip, scroll map           | Biology | 4         | Mobile UX, touch interactions    |
| P03 | Raj the Conference Demo  | Desktop 1920px   | Firefox | Moderate: 8 correct, 3 wrong, explore           | All     | 11        | Broad map coverage, wow factor   |

### Category B: Expert Scientists

| ID  | Name                       | Device           | Browser | Behavior                                  | Domain       | Questions | Key Evaluation                    |
|-----|----------------------------|------------------|---------|-------------------------------------------|--------------|-----------|-----------------------------------|
| P04 | Dr. Chen the Neuroscientist | Desktop 1440px  | Chrome  | Expert: 90%+ in neuro, 40% elsewhere     | Neuroscience | 35        | Accuracy of expertise detection   |
| P05 | Prof. Garcia the Physicist | Desktop 1280px   | Safari  | Expert: 95% physics, skips bio            | Physics      | 40        | Skip vs wrong weighting, accuracy |
| P06 | Dr. Okafor the Biologist  | Pixel 5 (393px)  | Chrome  | Expert on mobile: 85% bio                | Biology      | 30        | Mobile expert experience          |
| P07 | Prof. Kim the Generalist  | Desktop 1920px   | Firefox | Moderate across all: 60% average          | All          | 50        | Cross-domain map coherence        |

### Category C: Genuine Learners

| ID  | Name                        | Device           | Browser | Behavior                                       | Domain       | Questions | Key Evaluation                 |
|-----|-----------------------------|-----------------|---------|-------------------------------------------------|--------------|-----------|--------------------------------|
| P08 | Sam the Curious Undergrad   | Desktop 1366px  | Chrome  | Honest, mixed: 50% overall                     | All          | 45        | Self-discovery, map readability |
| P09 | Jordan the Career Changer   | Desktop 1440px  | Firefox | Strong CS, weak bio: 80%/30% split             | All          | 40        | Regional differentiation        |
| P10 | Priya the Lifelong Learner  | iPad (768px)    | Safari  | Moderate all, explores videos                   | Neuroscience | 35        | Video integration, learning path |
| P11 | Carlos the Night Owl        | Desktop 1280px  | Chrome  | Tired/rushed: random skips, fast answers        | Mathematics  | 25        | Noisy data resilience           |

### Category D: Stress Test / Power Users

| ID  | Name                      | Device           | Browser | Behavior                                      | Domain   | Questions | Key Evaluation                       |
|-----|---------------------------|------------------|---------|------------------------------------------------|----------|-----------|--------------------------------------|
| P12 | Dr. Tanaka the Marathoner | Desktop 1920px   | Chrome  | 120+ questions, steady pace                   | Physics  | 125       | Estimator stability, no collapse     |
| P13 | Lena the Domain Hopper    | Desktop 1440px   | Firefox | Switches domains 4 times, 15 per domain       | Multiple | 60        | Domain switching, state isolation    |
| P14 | Omar the Speed Clicker    | Desktop 1280px   | Chrome  | Rapid-fire: 1-2 seconds per answer            | Biology  | 50        | UI responsiveness, estimator stability |

### Category E: Pedantic Content Auditor

| ID  | Name                          | Device         | Browser | Behavior                                                              | Domain   | Questions | Key Evaluation                              |
|-----|-------------------------------|----------------|---------|-----------------------------------------------------------------------|----------|-----------|---------------------------------------------|
| P19 | Dr. Pedantic the Fact-Checker | Desktop 1440px | Chrome  | Answers ALL questions; critically evaluates every Q, answer, and map change | Physics  | ALL       | Answer correctness, question quality, map fidelity |
| P20 | Prof. Nitpick the Biologist   | Desktop 1440px | Chrome  | Answers ALL questions; critically evaluates every Q, answer, and map change | Biology  | ALL       | Answer correctness, question quality, map fidelity |
| P21 | Dr. Scrutiny the Generalist   | Desktop 1920px | Firefox | Answers ALL questions; critically evaluates every Q, answer, and map change | All      | ALL       | Cross-domain accuracy, topic placement      |

**Pedant Persona Protocol**:

The pedant personas are the most rigorous evaluation tier. They are driven by Opus 4.6 agents with deep domain expertise who answer EVERY question in a domain and critically evaluate EVERY aspect:

1. **Per-Question Critical Evaluation**: For each question, the agent:
   - Reads the question and all four options carefully
   - Uses its own domain knowledge to determine what the correct answer should be
   - Compares its assessment to the marked "correct" answer
   - If there is ANY disagreement or doubt, the agent MUST perform a web search to verify the factual claim before flagging it
   - Evaluates whether the distractors are plausible, clearly wrong, or arguably correct
   - Assesses whether the question tests meaningful understanding vs. obscure trivia
   - Checks the question's source article — does the question align with the article's actual content?
   - Rates the question on a 1-5 scale for: accuracy, clarity, difficulty appropriateness, and educational value

2. **Per-Answer Map Evaluation**: After EVERY answer, the agent:
   - States what it expects the map to look like given all answers so far
   - Captures a screenshot and compares expectation to reality
   - Documents whether the map change was appropriate, too small, too large, or in the wrong direction
   - Tracks cumulative drift between expected and actual map state

3. **Zero-Tolerance Verification**: The pedant persona has a strict evidence standard:
   - Any claim that a question's answer is wrong MUST be backed by a web search with a cited source
   - Any claim that a question is misplaced on the map MUST reference the question's source article and explain the discrepancy
   - Opinions about question quality MUST be accompanied by specific reasoning, not just "this seems bad"
   - NO hallucinated corrections — if the agent cannot find web evidence to support a correction, the original answer stands

4. **Output**: The pedant produces:
   - A complete question-by-question audit spreadsheet (question text, marked answer, agent's assessment, web verification result, quality rating)
   - A list of questions that need correction (with cited evidence)
   - A list of questions that need improvement (with specific suggestions)
   - A cumulative map-accuracy assessment tracking expectation-reality gaps over time

### Category F: Edge Case Users

| ID  | Name                       | Device           | Browser | Behavior                                         | Domain      | Questions | Key Evaluation                       |
|-----|----------------------------|------------------|---------|---------------------------------------------------|-------------|-----------|--------------------------------------|
| P15 | Zoe the Import/Exporter    | Desktop 1440px   | Chrome  | Answers 20, exports, reimports from landing       | Physics     | 20        | Import fidelity, progress restoration |
| P16 | Wei the Window Resizer     | Desktop variable | Safari  | Resizes window from 1920px to 800px mid-session   | Mathematics | 15        | Canvas realignment, layer sync       |
| P17 | Aisha the Keyboard User    | Desktop 1440px   | Chrome  | Uses A/B/C/D keys, also Cmd+C to copy            | Biology     | 20        | Keyboard shortcuts, modifier keys    |
| P18 | Felix the Sharer           | Desktop 1280px   | Firefox | Completes 25 questions, uses share modal          | Physics     | 25        | Share modal functionality            |

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST define at least 18 distinct user personas covering reporters, scientists, learners, power users, pedantic auditors, and edge-case users.
- **FR-002**: Each persona MUST have a documented interaction script specifying exact answer patterns (correct, wrong, skip), domains, device/viewport, and browser.
- **FR-003**: Each persona simulation MUST execute against the real running application (not mocked) using browser automation.
- **FR-004**: Each persona simulation MUST capture screenshots at key checkpoints: after first answer, at 25% completion, at 50%, at 75%, and at completion.
- **FR-005**: Each persona MUST have documented expectations for what the map should look like at each checkpoint, including expected color distributions and patterns.
- **FR-006**: System MUST evaluate each screenshot against expectations using measurable criteria (pixel color sampling, region analysis, visual coherence).
- **FR-007**: Each evaluation MUST produce a pass/fail/ambiguous result with documented evidence (screenshot comparison, pixel data, console logs).
- **FR-008**: Failed evaluations MUST generate actionable improvement recommendations with specific references to the failing persona and checkpoint.
- **FR-009**: Each improvement recommendation MUST be documented as a trackable issue with clear acceptance criteria.
- **FR-010**: Each improvement MUST be implemented, tested, and verified with before/after screenshot evidence showing the fix works.
- **FR-011**: All improvements MUST be committed to the feature branch and submitted as pull requests — never directly to the main branch.
- **FR-012**: The testing framework MUST support running persona simulations across multiple browsers (at minimum: Chrome, Firefox, Safari) and viewports (desktop, tablet, mobile).
- **FR-013**: System MUST detect and flag numerical instability (Cholesky decomposition errors, divide-by-zero, NaN values) during any persona simulation.
- **FR-014**: System MUST verify that keyboard shortcuts (A/B/C/D) only trigger on bare keypresses without modifier keys.
- **FR-015**: System MUST verify that the minimap viewport rectangle supports drag-to-pan (not zoom-to-fit).
- **FR-016**: System MUST verify that canvas layers (heatmap, articles, videos, grid, answered dots) remain aligned after browser window resize.
- **FR-017**: System MUST verify that "skip" responses receive stronger evidence weighting than wrong guesses, and that wrong answers on hard questions carry less negative weight than wrong answers on easy questions.
- **FR-018**: System MUST verify that skipping a question reveals the correct answer and relevant educational links.
- **FR-019**: System MUST verify that article titles display with spaces (not underscores).
- **FR-020**: System MUST verify that importing progress from the landing page correctly restores all previously answered questions (not just the first one).
- **FR-021**: System MUST verify that the share modal's social media buttons open correct websites, copy button copies text, and copy image button copies the map image.
- **FR-022**: System MUST verify that the hover popup does not block scrolling/panning when the cursor enters the popup during a drag operation.

#### Cognitive Simulation Requirements

- **FR-023**: Each persona simulation MUST be driven by an AI agent (Sonnet 4.6 or Opus 4.6) role-playing the persona with appropriate domain knowledge, personality, and critical judgment — not a mechanical script.
- **FR-024**: Each persona agent MUST read and evaluate every question encountered, assessing content validity (does it test what it claims?), distractor quality (plausible but wrong?), answer correctness (is the marked answer actually right?), and clarity of phrasing.
- **FR-025**: Each persona agent MUST maintain a running stream-of-consciousness narrative documenting what the persona is thinking, expecting, and feeling at each step of the interaction.
- **FR-026**: At each checkpoint, the persona agent MUST state its expectations BEFORE viewing the screenshot, then compare reality to expectations and document the gap (if any).
- **FR-027**: Each persona agent MUST produce a first-person "experience summary" written as the persona would describe the demo to a colleague or friend — surfacing UX issues that metrics alone miss.
- **FR-028**: Each persona agent MUST produce a ranked list of "critical issues" found during the session, categorized by severity (blocker / major / minor / cosmetic) with evidence references.
- **FR-029**: Each persona agent MUST evaluate whether questions are properly aligned to their map position — a question about "photosynthesis" should appear in the biology region, not physics.
- **FR-030**: Each persona agent MUST flag any question where the marked correct answer appears to be wrong or debatable, with an explanation of why.

#### Pedantic Audit Requirements

- **FR-031**: Pedant personas (P19, P20, P21) MUST answer EVERY question in their assigned domain(s), with no skipping.
- **FR-032**: Pedant personas MUST verify any suspected incorrect answer via web search before flagging it — zero tolerance for hallucinated corrections. Each correction MUST include a cited URL.
- **FR-033**: Pedant personas MUST rate every question on a 1-5 scale across four dimensions: accuracy, clarity, difficulty appropriateness, and educational value.
- **FR-034**: Pedant personas MUST evaluate after EVERY answer whether the map change was appropriate in direction and magnitude, building a cumulative expectation-vs-reality gap log.
- **FR-035**: Pedant personas MUST verify that each question's topic aligns with its source article — if the source is about Topic A, the question should test knowledge of Topic A.
- **FR-036**: Any question correction proposed by a pedant persona MUST be independently verified (web search with cited source) before being applied to the question bank. No changes based solely on the agent's assertion.
- **FR-037**: The pedant audit output MUST include a machine-readable question-by-question spreadsheet suitable for batch-updating the question bank.

### Key Entities

- **Persona**: A simulated user profile with device, browser, expertise level, answer strategy, domain focus, personality traits, and expected outcomes — embodied by an AI agent with real domain knowledge and critical judgment.
- **Interaction Script**: A high-level behavior description (not a rigid click sequence) that the persona agent interprets with appropriate variability — e.g., "answer honestly using domain expertise" rather than "click option B on question 3."
- **Checkpoint**: A specific moment during simulation where a screenshot is captured, the agent states expectations before viewing, then compares reality to expectations and documents the gap.
- **Belief Narrative**: The persona agent's running stream-of-consciousness documenting thoughts, expectations, emotional reactions, and critical evaluations throughout the session.
- **Question Audit**: Per-question evaluation of content validity, distractor quality, difficulty calibration, answer correctness, and topic-map alignment — produced by the persona agent using its domain knowledge.
- **Experience Summary**: A first-person narrative written as the persona would describe the demo to a colleague — the primary qualitative output used to assess whether the demo achieves its goals.
- **Evaluation Criteria**: Measurable conditions that determine pass/fail for each checkpoint, combining quantitative metrics (pixel color sampling, console errors) with qualitative assessments (belief narrative, question audit).
- **Issue**: A documented problem found during evaluation, with persona reference, screenshot evidence, belief narrative excerpt, expected vs actual behavior, and acceptance criteria for the fix.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 21 persona simulations complete without crashes, console errors, or unhandled exceptions across all targeted browsers and viewports.
- **SC-002**: Expert personas (P04, P05, P06, P07) produce heatmaps where the expert's specialty area is visibly cooler (blues/greens) than areas they answered poorly — verified by sampling pixel colors in known-strong vs known-weak regions and finding a measurable difference.
- **SC-003**: No persona simulation triggers Cholesky decomposition errors, divide-by-zero warnings, or NaN values in the browser console.
- **SC-004**: Power user persona (P12, 120+ questions) maintains smooth estimator progression — domain mapped percentage never jumps more than 15 percentage points between consecutive answers.
- **SC-005**: Mobile personas (P02, P06) complete their full interaction scripts without layout overflow, unresponsive touch targets, or content clipping — verified by screenshots showing complete UI within viewport bounds.
- **SC-006**: Import/export persona (P15) successfully reimports progress from the landing page and the map shows all 20 previously answered questions (not just the first one) — verified by counting visible answered-question markers.
- **SC-007**: Share persona (P18) successfully uses the share modal with all buttons working correctly — social media buttons open correct URLs, copy button copies text to clipboard, copy image button copies the map screenshot.
- **SC-008**: Keyboard persona (P17) confirms that Cmd+C, Ctrl+A, and other modifier combinations do NOT trigger answer selection — only bare A/B/C/D keypresses select answers.
- **SC-009**: Window resize persona (P16) confirms all canvas layers remain aligned after resize — article dots, video markers, and grid lines maintain their positions relative to the heatmap.
- **SC-010**: At least 90% of all persona checkpoint evaluations (across all personas, all checkpoints) produce a "pass" result after all improvements are implemented.
- **SC-011**: Cross-browser persona simulations (same persona run on Chrome, Firefox, Safari) produce visually equivalent heatmaps — sampled color values in the same map regions differ by no more than 10% across browsers.
- **SC-012**: All identified issues have corresponding pull requests with before/after screenshot evidence demonstrating the fix.
- **SC-013**: Across all persona simulations, no more than 5% of questions are flagged as having an incorrect marked answer — and every flagged answer is verified via web search before being changed or confirmed.
- **SC-014**: Across all persona simulations, no more than 15% of questions are flagged as having low-quality distractors (too obvious, arguably correct, or irrelevant to the topic).
- **SC-015**: Every expert persona (P04, P05, P06, P07) produces an experience summary that expresses trust in the system's accuracy — the agent believes the map reflects its knowledge profile.
- **SC-016**: Every reporter persona (P01, P02, P03) produces an experience summary that a reasonable person would interpret as "impressed" — expressing genuine interest, visual delight, or intellectual curiosity rather than confusion or indifference.
- **SC-017**: Every learner persona (P08, P09, P10, P11) reports at least one "aha moment" — a genuine insight about their knowledge profile discovered through the mapping process.
- **SC-018**: Question-map alignment audit finds no more than 10% of questions positioned in the wrong topical region of the map (e.g., a biology question appearing in the physics cluster).
- **SC-019**: Pedant personas (P19, P20, P21) complete a full audit of every question in their assigned domains. All corrections to question answers are backed by cited web sources — zero hallucinated corrections make it into the question bank.
- **SC-020**: After pedant-driven corrections are applied, a re-run of the pedant simulation flags no more than 2% of questions as having incorrect marked answers (down from the pre-fix baseline).

## Assumptions

- The application is running locally at `http://localhost:5173` (or the configured Vite dev server URL) during testing.
- Question banks for all tested domains (Physics, Biology, Neuroscience, Mathematics, All) are available and contain sufficient questions for the largest persona simulations (125+ for power user).
- "Correct" and "wrong" answers for persona simulations can be determined from the question data (correct answer is marked in the question JSON).
- Screenshots can be captured and analyzed programmatically using standard image processing approaches.
- Browser automation can simulate zoom, pan, hover, and click interactions on the canvas element.
- The existing estimator (Gaussian Process with Matern kernel) is the system under test — improvements may adjust parameters or fix bugs but should not replace the core algorithm.
- Video recommendations require sufficient answered questions (30+) to produce meaningful results.
- All development happens on the `004-persona-user-testing` branch; main branch is untouched until manual merge.

## Out of Scope

- Replacing the core estimation algorithm (GP with Matern kernel) — only parameter tuning and bug fixes.
- Adding new question domains or generating new questions.
- Backend/server infrastructure changes — the application is static/client-side.
- Accessibility compliance auditing (WCAG) — though basic usability on mobile is in scope.
- Performance benchmarking (load times, memory usage) — though obvious performance regressions should be flagged.
- Internationalization or localization.
