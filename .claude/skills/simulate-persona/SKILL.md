# Simulate Persona

Simulate a persona-based user test against the live Knowledge Mapper application.

## Usage

```
/simulate-persona <PERSONA_ID>
```

Example: `/simulate-persona P01` runs Alex the Tech Reporter simulation.

## Arguments

- `$ARGUMENTS`: Persona ID (P01–P21) or category name (reporter, expert, learner, power-user, pedant, edge-case)

## Pipeline Overview

The simulation runs a 4-phase pipeline (5 phases if issues are found):

1. **Phase 1: Playwright Automation** — Mechanical browser interaction
2. **Phase 2: AI Cognitive Evaluation** — Task agent reads checkpoints + screenshots
3. **Phase 3: Pedant Web Verification** — (Pedant only) Opus agent verifies corrections
4. **Phase 4: Report Assembly** — Compile JSON + Markdown reports
5. **Phase 5: Issue Triage & Fix** — Create GitHub issues, implement fixes, submit PRs

## Execution Steps

### Step 0: Setup

1. Read persona definition from `tests/visual/personas/definitions.js` — find the persona matching `$ARGUMENTS`
2. Clean any stale working files: delete `tests/visual/.working/personas/{personaId}-*`
3. Verify dev server is running at `http://localhost:5173/mapper/`
4. Create TodoWrite entries for progress tracking

### Step 1: Playwright Automation (Phase 1)

Run the Playwright test for this persona:

```bash
npx playwright test persona-agents.spec.js -g "Persona: {personaName}"
```

For pedant personas:
```bash
npx playwright test persona-pedant.spec.js -g "Pedant: {personaName}"
```

This produces:
- `tests/visual/.working/personas/{personaId}-checkpoint-{N}.json` for each checkpoint
- `tests/visual/screenshots/personas/{personaId}-checkpoint-{N}.png` for each screenshot

Each checkpoint JSON contains:
```json
{
  "personaId": "P01",
  "checkpointNumber": 1,
  "questionsAnswered": 5,
  "questionsInBatch": [
    {
      "questionId": "abc123",
      "questionText": "...",
      "options": { "A": "...", "B": "...", "C": "...", "D": "..." },
      "correctAnswer": "B",
      "selectedAnswer": "B",
      "wasCorrect": true,
      "difficulty": 2,
      "domainId": "physics",
      "sourceArticle": "..."
    }
  ],
  "screenshotPath": "tests/visual/screenshots/personas/P01-checkpoint-1.png",
  "consoleErrors": [],
  "domainMappedPct": 12,
  "timestamp": 1709352000000
}
```

### Step 2: AI Cognitive Evaluation (Phase 2)

For EACH checkpoint, spawn a Task agent:

**Regular personas (Sonnet 4.6):**
```
Task agent (model: sonnet, subagent_type: general-purpose):
  "You are role-playing as {persona.name}. {persona.personality}

   Read the checkpoint data at: {checkpointPath}
   Read the screenshot at: {screenshotPath}

   BEFORE looking at the screenshot, state what you expect the map to look like.
   THEN read the screenshot and compare reality to your expectation.

   For each question in this batch, evaluate:
   - Is the marked answer correct?
   - Are the distractors plausible?
   - Does the question test meaningful understanding?
   - Rate content validity, distractor quality, difficulty, educational value, clarity (1-5 each)

   Write your evaluation as JSON to: {evalOutputPath}
   Use the AgentEvaluation schema from the data model."
```

**Pedant personas (Opus 4.6):**
```
Task agent (model: opus, subagent_type: general-purpose):
  Same as above but with additional instructions:
  "If you disagree with any marked answer, use the WebSearch tool to verify.
   Search for authoritative sources. Cite the URL.
   If web evidence supports your correction: verdict = CORRECTION_VERIFIED
   If web evidence confirms original: verdict = ORIGINAL_CONFIRMED
   If inconclusive: verdict = INCONCLUSIVE
   NEVER hallucinate a correction without web evidence."
```

Each evaluation produces:
- `tests/visual/.working/personas/{personaId}-eval-{N}.json`

#### Category-Specific Evaluation Guidance

**Reporter agents (P01-P03)** should focus on:
- Visual impact — would this screenshot look good in a tech article?
- Question quality for non-expert audience — nothing too obscure
- Polish — no loading spinners, no visual artifacts, smooth gradients
- First impression criteria from expected-outcomes/reporters.json

**Expert agents (P04-P07)** should focus on:
- Answer correctness — use real domain knowledge to verify marked answers
- Difficulty calibration — do questions test conceptual understanding vs trivia?
- Map accuracy — does the green/yellow/red distribution match their expertise profile?
- Distractor quality — all four options should be plausible at first glance

**Learner agents (P08-P11)** should focus on:
- Emotional arc — curiosity → mixed success → insight → continued engagement
- Question diversity — no more than 5 consecutive questions on the same sub-topic
- "Aha moments" — identify at least 1 moment where the map reveals something surprising
- Map readability for non-experts — clear color differentiation, intuitive layout
- Self-assessment: "Would I show this to a friend?" and "Did I learn something about myself?"

**Power user agents (P12-P14)** should focus on:
- Estimator stability — no Cholesky errors, NaN, or Infinity values
- Domain-mapped % smooth progression — no jumps >15 percentage points
- Domain switching cleanliness (P13) — no state leakage between domains
- Rapid input handling (P14) — no dropped answers or visual glitches

### Step 3: Pedant Web Verification (Phase 3 — pedant only)

For any question where the pedant agent flagged `isCorrectAsMarked: false`:

1. Read the eval JSON to find flagged questions
2. If the agent already searched (webVerification.searched = true), the verification is done
3. If not, spawn an additional Opus Task agent with WebSearch tool to verify
4. Write all verified corrections to: `tests/visual/.working/personas/{personaId}-corrections.json`

### Step 4: Report Assembly (Phase 4)

1. Read all checkpoint JSONs and evaluation JSONs from `.working/personas/`
2. Compile the PersonaReport:
   - Concatenate all belief narratives into experience summary
   - Collect all question evaluations into question audit
   - Collect all issues, sort by severity
   - Determine result: PASS / FAIL / AMBIGUOUS per spec criteria
3. Write outputs:
   - `tests/visual/reports/{personaId}-report.json` (machine-readable)
   - `tests/visual/reports/{personaId}-report.md` (human-readable)

### Step 5: Issue Triage & Fix (Phase 5 — if issues found)

For each blocker or major issue discovered:

1. Create a GitHub issue on the feature branch describing the problem
2. Spawn a Task agent to investigate and implement a fix
3. Verify the fix by re-running the affected checkpoint
4. Submit the fix as a commit on the `004-persona-user-testing` branch

## Resume from Checkpoint

If context runs out mid-simulation:

1. Check `tests/visual/.working/personas/` for existing files
2. Find the highest checkpoint number with a corresponding eval file
3. Resume from the next unevaluated checkpoint
4. The Playwright test only needs to re-run if checkpoint data files are missing

## Working File Conventions

All intermediate files in `tests/visual/.working/personas/`:

| Pattern | Phase | Description |
|---------|-------|-------------|
| `{id}-checkpoint-{N}.json` | 1 | Playwright automation output |
| `{id}-eval-{N}.json` | 2 | AI agent evaluation |
| `{id}-corrections.json` | 3 | Pedant verified corrections |
| `{id}-report.json` | 4 | Final compiled report |
| `{id}-report.md` | 4 | Human-readable report |

## Pass/Fail Criteria

- **PASS**: All checkpoints met expectations. No blocker/major issues. Positive experience summary. ≤10% low-quality questions.
- **FAIL**: Any blocker issue (crash, estimator collapse, wrong map). Negative experience summary. >25% problematic questions.
- **AMBIGUOUS**: Only minor/cosmetic issues but mixed feelings. Small but consistent expectation-reality gaps. Requires human review.

## Persona Categories Quick Reference

| Category | IDs | Model | Checkpoint Interval | Special |
|----------|-----|-------|--------------------|---------|
| Reporter | P01-P03 | Sonnet | 4-5 | First impressions |
| Expert | P04-P07 | Sonnet | 5 | Domain expertise verification |
| Learner | P08-P11 | Sonnet | 5 | Emotional arc, aha moments |
| Power User | P12-P14 | Sonnet | 10-20 | Stress test, stability |
| Pedant | P19-P21 | Opus | 1 (every Q) | Web-verified corrections |
| Edge Case | P15-P18 | Sonnet | 8-10 | Feature-specific testing |
