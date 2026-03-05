# Contract: Persona Agent Simulation

**Date**: 2026-03-02 | **Branch**: `004-persona-user-testing`

## Overview

Defines the interface between the persona simulation skill orchestrator and the Task agents it spawns for cognitive evaluation. Two agent types exist: **Regular** (checkpoint evaluation) and **Pedant** (per-question audit with web verification).

## Agent Types

### Regular Persona Agent (Sonnet 4.6)

Spawned via `Task` tool with `subagent_type: "general-purpose"` and `model: "sonnet"`.

**Input**: The agent prompt includes:
- Persona profile (personality, expertise domains, weak domains)
- Checkpoint data JSON (questions answered, answers given, domain mapped %)
- Screenshot file path(s) to read via `Read` tool
- Console errors captured during this checkpoint window
- Previous checkpoint evaluations (for continuity)

**Output**: Agent writes a JSON file to `tests/visual/.working/` with this schema:

```json
{
  "personaId": "P01",
  "checkpointNumber": 3,
  "beliefNarrative": "String — first-person stream of consciousness in persona voice",
  "expectations": {
    "mapDescription": "What the persona expects the map to look like now",
    "colorExpectation": "Expected color pattern (e.g., 'bright in physics region')",
    "overallFeeling": "Expected emotional state (excited, confused, skeptical, etc.)"
  },
  "realityAssessment": {
    "mapDescription": "What the agent actually sees in the screenshot",
    "matchesExpectation": true,
    "gapDescription": "Description of any gap between expectation and reality"
  },
  "questionEvaluations": [
    {
      "questionId": "a1b2c3",
      "questionText": "Truncated question text...",
      "markedAnswer": "B",
      "agentAssessment": "B",
      "isCorrectAsMarked": true,
      "contentValidity": 4,
      "distractorQuality": 3,
      "difficultyRating": 3,
      "educationalValue": 4,
      "clarityRating": 5,
      "topicAligned": true,
      "notes": "Optional commentary"
    }
  ],
  "issuesFound": [
    {
      "severity": "minor",
      "category": "question-quality",
      "title": "Short description",
      "description": "Detailed description with evidence",
      "expectedBehavior": "What should happen",
      "actualBehavior": "What actually happened",
      "recommendation": "Suggested fix"
    }
  ],
  "engagementLevel": 4,
  "overallSentiment": "positive"
}
```

### Pedant Persona Agent (Opus 4.6)

Spawned via `Task` tool with `subagent_type: "general-purpose"` and `model: "opus"`.

**Input**: Same as Regular agent, plus:
- Full question text with all four options and marked correct answer
- The `source_article` field for each question (Wikipedia article title)
- Instruction to use `WebSearch` tool when disagreeing with marked answer

**Output**: Same schema as Regular agent, with these additions to `questionEvaluations`:

```json
{
  "questionId": "a1b2c3",
  "...": "...same fields as regular...",
  "isCorrectAsMarked": false,
  "webVerification": {
    "searched": true,
    "query": "What is the actual speed of light in vacuum?",
    "sourceUrl": "https://example.com/speed-of-light",
    "verdict": "CORRECTION_VERIFIED",
    "correctedAnswer": "C",
    "evidence": "Brief quote or summary from source"
  }
}
```

**Web verification verdicts**:
- `CORRECTION_VERIFIED`: Web evidence supports the agent's correction
- `ORIGINAL_CONFIRMED`: Web evidence confirms the original marked answer was correct
- `INCONCLUSIVE`: Insufficient evidence to decide; flag for human review

## Working File Conventions

All intermediate files written to `tests/visual/.working/personas/`:

| File Pattern | Description |
|---|---|
| `{personaId}-checkpoint-{N}.json` | Playwright checkpoint data (Phase 1 output) |
| `{personaId}-eval-{N}.json` | Agent evaluation (Phase 2 output) |
| `{personaId}-corrections.json` | Pedant verified corrections (Phase 3 output) |
| `{personaId}-report.json` | Final compiled report (Phase 4 output) |
| `{personaId}-report.md` | Human-readable final report (Phase 4 output) |

## Screenshot Conventions

Screenshots saved to `tests/visual/screenshots/personas/`:

| File Pattern | Description |
|---|---|
| `{personaId}-checkpoint-{N}.png` | Map state at checkpoint N |
| `{personaId}-final.png` | Final map state after all questions |

## Error Handling

- If a Task agent's context is exhausted mid-evaluation, the orchestrator detects the incomplete working file and spawns a new agent with the same checkpoint data plus a note to continue from where the previous agent stopped.
- If WebSearch fails (network error, no results), the pedant agent marks the verdict as `INCONCLUSIVE` and continues.
- If a screenshot cannot be read (corrupt file), the agent notes this in the evaluation and skips visual assessment for that checkpoint.

## Constraints

- Agents must NOT modify source code or question files directly. All corrections are written to working files for the orchestrator to apply after verification.
- Agents must cite specific evidence (quote text, URL) for every correction claim.
- Regular agents evaluate questions in batches (per checkpoint interval). Pedant agents evaluate every single question individually.
- All agent prompts must include the persona's personality description to maintain consistent voice across checkpoints.
