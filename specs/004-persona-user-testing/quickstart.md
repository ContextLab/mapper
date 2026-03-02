# Quickstart: Persona-Based User Testing Framework

**Date**: 2026-03-02 | **Branch**: `004-persona-user-testing`

## Prerequisites

- Claude Code with Max Pro subscription (for Task agent spawning)
- Node.js 18+ with Playwright browsers installed (`npx playwright install`)
- Knowledge Mapper dev server running (`npm run dev` → `http://localhost:5173/mapper/`)

## Running a Single Persona Simulation

```bash
# Invoke the skill from Claude Code CLI
/simulate-persona P01
```

This runs the full 4-phase pipeline for persona P01 (Alex Chen, Reporter):
1. **Playwright automation**: Answers 15 questions in "all" domain, captures 3 checkpoints
2. **AI evaluation**: Sonnet 4.6 agent reads checkpoints + screenshots, produces belief narratives
3. **Report assembly**: Compiles `tests/visual/reports/P01-report.json` and `P01-report.md`

## Running a Pedant Simulation

```bash
/simulate-persona P19
```

Pedant personas (P19-P21) run a longer pipeline:
1. **Playwright automation**: Answers ALL 50 questions in assigned domain, checkpoint every question
2. **AI evaluation**: Opus 4.6 agent evaluates each question's correctness, content validity, distractors
3. **Web verification**: For any disagreements, agent searches the web and cites sources
4. **Report assembly**: Includes verified corrections with source URLs

## Running All Personas

```bash
# From Playwright CLI (mechanical automation only — no AI evaluation)
npx playwright test persona-agents.spec.js
npx playwright test persona-pedant.spec.js

# Full AI evaluation requires invoking the skill per persona
/simulate-persona P01
/simulate-persona P02
# ... etc
```

## Viewing Reports

After simulation completes:

```bash
# Human-readable report
cat tests/visual/reports/P01-report.md

# Machine-readable report (for automated pass/fail)
cat tests/visual/reports/P01-report.json

# Screenshots
ls tests/visual/screenshots/personas/P01-*.png
```

## Report Structure

Each report contains:
- **Experience Summary**: First-person narrative in persona's voice
- **Question Audit**: Per-question evaluations (content validity, distractor quality, clarity)
- **Issues Found**: Ranked by severity (blocker → major → minor → cosmetic)
- **Result**: PASS / FAIL / AMBIGUOUS with reasoning
- **Checkpoints**: Screenshot + belief narrative at each evaluation point

## Working Files

Intermediate data in `tests/visual/.working/personas/`:
- `P01-checkpoint-1.json` — Playwright checkpoint data
- `P01-eval-1.json` — Agent evaluation at checkpoint 1
- `P01-corrections.json` — Pedant verified corrections (pedant only)

These files enable resume-from-checkpoint if an agent's context is exhausted.

## Interpreting Results

| Result | Meaning | Action |
|--------|---------|--------|
| PASS | Persona had a positive experience, no major issues | None needed |
| FAIL | Critical issues found (wrong answers, broken UI, estimator crash) | File issues, implement fixes |
| AMBIGUOUS | Mixed signals — some good, some concerning | Review report, decide case-by-case |

## Applying Pedant Corrections

After pedant simulation, verified corrections appear in the report. To apply:

1. Review `P19-report.md` for corrections with `CORRECTION_VERIFIED` verdicts
2. Each correction includes: question ID, current answer, corrected answer, source URL, evidence
3. Update the domain JSON file (`data/domains/{domain}.json`) with corrected answers
4. Re-run pedant simulation to verify corrections are applied

## Common Scenarios

### Persona finds a question with wrong answer
→ Issue created with category `question-accuracy`, includes web-verified correction

### Persona finds estimator crash at high question count
→ Issue created with category `estimator-bug`, includes console error logs and screenshot

### Persona finds map doesn't reflect expertise
→ Issue created with category `map-accuracy`, includes expectation vs reality description

### Persona finds UI confusing on mobile
→ Issue created with category `ux-bug`, includes viewport size and screenshot
