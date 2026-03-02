# Implementation Plan: Persona-Based User Testing Framework

**Branch**: `004-persona-user-testing` | **Date**: 2026-03-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-persona-user-testing/spec.md`

## Summary

Build a rigorous persona-based testing framework where AI agents (Sonnet 4.6 / Opus 4.6) role-play 21 diverse user personas interacting with the real Knowledge Mapper application. Each agent critically evaluates questions, map accuracy, and UX — producing belief narratives, question audits, and experience summaries. Pedant personas audit every question in a domain with web-search-verified corrections. Issues discovered drive code fixes submitted as PRs to the feature branch.

## Technical Context

**Language/Version**: JavaScript ES2022+ (ES modules)
**Primary Dependencies**: @playwright/test 1.58+, nanostores 1.1, deck.gl 9.2, Vite 7.3, Claude Code Task agents (Sonnet 4.6 / Opus 4.6 for persona evaluation — no API key needed)
**Storage**: File-based JSON (question banks in `data/domains/`), localStorage (user progress)
**Testing**: Playwright (E2E/visual), Vitest (unit)
**Target Platform**: Web browser (Chrome, Firefox, Safari) — desktop + mobile viewports
**Project Type**: Web application (static client-side) with AI-driven test framework
**Performance Goals**: Persona simulations complete within 5 minutes each (non-pedant), pedant simulations within 30 minutes per domain
**Constraints**: All persona agents must interact with the real running app (no mocks). Question corrections must be web-search-verified. All work on feature branch only.
**Scale/Scope**: 21 personas, ~2500 total questions across 50 domains, 50 questions per pedant domain audit

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Accuracy
- **PASS**: The pedant personas (P19-P21) are specifically designed to verify question correctness against web sources. FR-032 mandates zero-tolerance for hallucinated corrections. FR-036 requires web-search verification before any question bank changes. This feature directly strengthens Principle I compliance.

### Principle II: User Delight
- **PASS**: Reporter personas (P01-P03) evaluate first impressions. Learner personas (P08-P11) evaluate engagement and "aha moments." All personas produce experience summaries that surface UX issues. Screenshot-based evaluation at checkpoints ensures visual quality.

### Principle III: Compatibility
- **PASS**: Personas span Chrome/Firefox/Safari, desktop/tablet/mobile viewports (390px to 1920px). Cross-browser consistency is explicitly tested (US6). Mobile UX is tested by P02, P06.

**Gate Result**: ALL PASS — proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/004-persona-user-testing/
├── plan.md              # This file
├── spec.md              # Feature specification (21 personas, 9 user stories)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── persona-agent.md # Contract for AI agent persona simulation
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
tests/
├── visual/
│   ├── persona-simulation.spec.js    # EXISTING: 4 mechanical personas (to be replaced)
│   ├── personas/                     # NEW: AI agent persona framework
│   │   ├── runner.js                 # Playwright automation engine
│   │   ├── evaluator-prompts.js      # System prompts for AI evaluation agents
│   │   ├── report-compiler.js        # Assembles final reports from working data
│   │   ├── question-loader.js        # Question DB loader utility
│   │   └── correction-applicator.js  # Apply pedant-verified corrections to question JSON
│   ├── persona-agents.spec.js        # NEW: AI-driven persona test suite
│   ├── persona-pedant.spec.js        # NEW: Pedant persona audit suite
│   └── screenshots/
│       └── personas/                 # NEW: Per-persona checkpoint screenshots
│
├── fixtures/                         # NEW: Persona definitions and expected outcomes
│   ├── personas.json                 # All 21 persona profiles
│   └── expected-outcomes/            # Per-persona expected map patterns
│
src/
├── learning/
│   └── estimator.js                  # EXISTING: GP estimator (may need bug fixes)
├── ui/
│   ├── quiz.js                       # EXISTING: Quiz panel (keyboard shortcut fix)
│   ├── share.js                      # EXISTING: Share modal (button fixes)
│   └── video-panel.js                # EXISTING: Video panel
├── viz/
│   ├── renderer.js                   # EXISTING: Canvas renderer (resize alignment fix)
│   └── minimap.js                    # EXISTING: Minimap (drag-to-pan fix)
└── app.js                            # EXISTING: Main orchestrator

data/
└── domains/                          # EXISTING: Question JSON files (may get corrections)
    ├── index.json
    ├── physics.json                   # 50 questions
    ├── biology.json                   # 50 questions
    └── ... (50 domains × 50 questions each)
```

**Structure Decision**: Extend the existing `tests/visual/` directory with a new `personas/` module for the AI agent framework. Persona definitions go in `tests/fixtures/`. No new source directories needed — bug fixes go in existing source files.

## Architecture: Persona Agent Framework

### How Persona Agents Work — Claude Code Skill Pattern

The framework follows the same pattern as the `generate-questions` skill: a Claude Code skill (`.claude/skills/simulate-persona/SKILL.md`) orchestrates multi-step agent work using the Task tool to farm off sub-agents, with working files for checkpointing and TodoWrite for progress tracking.

**No API key required** — all AI evaluation runs through the user's Claude Code Max Pro subscription by spawning Task agents from the main session.

### Execution Flow

```
/simulate-persona P01          (invoke skill for one persona)
    │
    ├─ Phase 1: Playwright Automation
    │   └─ Task agent runs Playwright script
    │       ├─ Answers questions per persona profile
    │       ├─ Captures screenshots at checkpoints
    │       ├─ Records question text, options, answers, console logs
    │       └─ Writes checkpoint data to .working/ JSON files
    │
    ├─ Phase 2: AI Cognitive Evaluation (per checkpoint)
    │   └─ Task agent (Sonnet or Opus) reads checkpoint data + screenshots
    │       ├─ Role-plays persona, produces belief narrative
    │       ├─ Evaluates question quality (content validity, distractors)
    │       ├─ States expectations vs reality for map appearance
    │       ├─ Flags issues with severity ratings
    │       └─ Writes evaluation to .working/ JSON files
    │
    ├─ Phase 3: Pedant Web Verification (pedant personas only)
    │   └─ Task agent (Opus) for each flagged question
    │       ├─ Performs WebSearch to verify/refute the correction
    │       ├─ Cites source URL
    │       └─ Writes verified corrections to .working/ JSON
    │
    └─ Phase 4: Report Assembly
        └─ Compiles checkpoint data + evaluations into final report
            ├─ tests/visual/screenshots/personas/P01-*.png
            ├─ tests/visual/reports/P01-report.md
            └─ tests/visual/reports/P01-report.json
```

### Skill Structure

```
.claude/skills/simulate-persona/
└── SKILL.md                    # Skill definition (like generate-questions)

tests/visual/
├── personas/
│   ├── definitions.js          # All 21 persona profiles (exported)
│   ├── runner.js               # Playwright automation engine
│   ├── evaluator-prompts.js    # System prompts for AI evaluation agents
│   ├── report-compiler.js      # Assembles final reports from working data
│   ├── question-loader.js      # Question DB loader utility
│   └── correction-applicator.js # Apply pedant-verified corrections
├── persona-agents.spec.js      # Playwright test entry point (regular personas)
├── persona-pedant.spec.js      # Playwright test entry point (pedant personas)
├── reports/                    # Generated persona reports (gitignored)
└── screenshots/personas/       # Per-persona checkpoint screenshots (gitignored)

tests/fixtures/
├── personas.json               # Persona definitions (JSON mirror of definitions.js)
└── expected-outcomes/          # Per-persona expected map patterns
```

### Key Design Decisions

1. **Claude Code Task agents, not API calls**: Persona cognitive evaluation uses the Task tool to spawn sub-agents from the main session. This uses the user's Max Pro subscription — zero API cost. Sonnet 4.6 for regular personas, Opus 4.6 for pedant personas.

2. **Two-phase separation**: Phase 1 (Playwright automation) is purely mechanical and runs as a normal Playwright test. Phase 2 (cognitive evaluation) runs as Task agents that read the checkpoint files and screenshots, then produce evaluations. This separation means Phase 1 can run fast and Phase 2 can take its time.

3. **Working files for checkpointing**: Following the generate-questions pattern, all intermediate state is written to `tests/visual/.working/` JSON files. If context runs out mid-evaluation, the next agent reads working files to resume.

4. **Screenshot analysis via Read tool**: Task agents use the Read tool to view screenshot images (Claude Code is multimodal). The agent describes what it sees and compares to expectations.

5. **WebSearch for pedant verification**: Pedant Task agents use the WebSearch tool directly (available to all Claude Code agents) to verify suspected incorrect answers.

6. **Reports are JSON + Markdown**: Each persona simulation produces both `P01-report.json` (machine-readable for automated pass/fail) and `P01-report.md` (human-readable for review).

7. **Parallelizable**: Multiple persona simulations can run concurrently via parallel Task agent calls, limited only by how many agents the user wants running simultaneously.

## Complexity Tracking

No constitution violations requiring justification. The framework uses Claude Code's existing agent infrastructure (Task tool, WebSearch, Read for images) — no new external dependencies added to the production application.
