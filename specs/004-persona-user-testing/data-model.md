# Data Model: Persona-Based User Testing Framework

**Date**: 2026-03-02 | **Branch**: `004-persona-user-testing`

## Entities

### Persona

A simulated user profile driving a browser automation session.

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique identifier (P01-P21) |
| name | string | Human-readable persona name |
| category | enum | reporter / expert / learner / power-user / pedant / edge-case |
| device | object | `{ name, width, height }` — viewport configuration |
| browser | string | chromium / firefox / webkit |
| domain | string | Target domain name (e.g., "physics", "All") |
| numQuestions | number | How many questions to answer (or "ALL" for pedants) |
| aiModel | string | "sonnet-4-6" for regular, "opus-4-6" for pedants |
| personality | string | System prompt describing persona's personality, expertise, and critical lens |
| expertiseDomains | string[] | Domains where this persona has high knowledge |
| weakDomains | string[] | Domains where this persona has low knowledge |
| getAccuracy | function | `(domainId) → probability [0,1]` of answering correctly |
| checkpointInterval | number | Evaluate AI agent every N answers (5 for regular, 1 for pedants) |

### Question (existing, not modified)

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique hex identifier |
| question_text | string | The question (may contain KaTeX) |
| options | object | `{ A, B, C, D }` — four answer choices |
| correct_answer | string | "A", "B", "C", or "D" |
| difficulty | number | 1-4 (easy to expert) |
| source_article | string | Wikipedia article title this question is derived from |
| domain_ids | string[] | Domain(s) this question belongs to |
| concepts_tested | string[] | Key concepts being evaluated |
| x | number | Embedding x-coordinate [0,1] |
| y | number | Embedding y-coordinate [0,1] |

### Checkpoint

A snapshot of the simulation state at a defined evaluation point.

| Field | Type | Description |
|-------|------|-------------|
| personaId | string | Which persona this checkpoint belongs to |
| checkpointNumber | number | Sequential index (1, 2, 3...) |
| questionsAnswered | number | Total answers so far |
| questionsInBatch | object[] | Questions answered since last checkpoint |
| screenshotPath | string | Path to captured screenshot file |
| consoleErrors | string[] | Any console errors captured since last checkpoint |
| domainMappedPct | number | Current "domain mapped" percentage from UI |
| timestamp | number | Epoch ms |

### AgentEvaluation

The AI agent's structured assessment at a checkpoint.

| Field | Type | Description |
|-------|------|-------------|
| personaId | string | Persona being simulated |
| checkpointNumber | number | Which checkpoint |
| beliefNarrative | string | Stream-of-consciousness in persona's voice |
| expectations | object | `{ mapDescription, colorExpectation, overallFeeling }` |
| realityAssessment | object | `{ mapDescription, matchesExpectation, gapDescription }` |
| questionEvaluations | QuestionEval[] | Per-question assessments in this batch |
| issuesFound | Issue[] | Problems identified at this checkpoint |
| engagementLevel | number | 1-5 scale of persona engagement/interest |
| overallSentiment | string | "positive" / "neutral" / "negative" / "confused" |

### QuestionEval

Per-question assessment from the AI agent.

| Field | Type | Description |
|-------|------|-------------|
| questionId | string | Question identifier |
| questionText | string | The question text (truncated) |
| markedAnswer | string | The answer marked correct in the JSON |
| agentAssessment | string | What the agent believes the correct answer is |
| isCorrectAsMarked | boolean | Does the agent agree with the marked answer? |
| webVerification | object | `{ searched, query, sourceUrl, verdict }` — only for pedants when disagreement found |
| contentValidity | number | 1-5: Does question test what it claims? |
| distractorQuality | number | 1-5: Are wrong answers plausibly wrong? |
| difficultyRating | number | 1-5: Is difficulty appropriate? |
| educationalValue | number | 1-5: Does answering teach something? |
| clarityRating | number | 1-5: Is question unambiguous? |
| topicAligned | boolean | Is the question in the right map region? |
| notes | string | Free-form agent commentary |

### Issue

A problem found during persona simulation.

| Field | Type | Description |
|-------|------|-------------|
| id | string | Auto-generated issue ID |
| personaId | string | Which persona found this |
| checkpointNumber | number | When it was found |
| severity | enum | blocker / major / minor / cosmetic |
| category | enum | question-accuracy / map-accuracy / ux-bug / estimator-bug / visual-defect / question-quality |
| title | string | Short description |
| description | string | Detailed description with evidence |
| screenshotPath | string | Screenshot showing the issue (if visual) |
| expectedBehavior | string | What should happen |
| actualBehavior | string | What actually happened |
| recommendation | string | Suggested fix |

### PersonaReport

Final output for each persona simulation.

| Field | Type | Description |
|-------|------|-------------|
| personaId | string | Persona identifier |
| personaName | string | Human-readable name |
| startTime | number | Epoch ms |
| endTime | number | Epoch ms |
| totalQuestions | number | Questions answered |
| correctCount | number | Correct answers |
| checkpoints | Checkpoint[] | All checkpoints |
| evaluations | AgentEvaluation[] | All AI evaluations |
| experienceSummary | string | First-person narrative from persona's perspective |
| questionAudit | QuestionEval[] | All question evaluations |
| issuesFound | Issue[] | All issues, ranked by severity |
| result | enum | PASS / FAIL / AMBIGUOUS |
| resultReasoning | string | Why this result was assigned |

## Relationships

```
Persona ──┬── 1:N ──→ Checkpoint
           ├── 1:N ──→ AgentEvaluation
           ├── 1:N ──→ QuestionEval
           ├── 1:N ──→ Issue
           └── 1:1 ──→ PersonaReport

Checkpoint ── 1:1 ──→ AgentEvaluation (one eval per checkpoint)
AgentEvaluation ── 1:N ──→ QuestionEval (batch of questions since last checkpoint)
AgentEvaluation ── 1:N ──→ Issue (issues found at this checkpoint)
```

## State Transitions

### Persona Simulation Lifecycle

```
PENDING → RUNNING → EVALUATING → COMPLETE
                 ↑            │
                 └── (repeat) ←┘
```

- **PENDING**: Persona defined but simulation not started
- **RUNNING**: Playwright answering questions
- **EVALUATING**: AI agent analyzing checkpoint
- **COMPLETE**: All questions answered, final report generated

### Question Correction Lifecycle (Pedant only)

```
FLAGGED → SEARCHING → VERIFIED → CORRECTED
                    ↓
                    CONFIRMED (original answer was correct)
```

- **FLAGGED**: Agent suspects incorrect answer
- **SEARCHING**: Web search in progress
- **VERIFIED**: Web evidence found supporting correction
- **CONFIRMED**: Web evidence confirms original answer was correct
- **CORRECTED**: Question JSON updated with verified correction
