# Research: Persona-Based User Testing Framework

**Date**: 2026-03-02 | **Branch**: `004-persona-user-testing`

## Research Topics

### R1: AI Agent Integration for Persona Simulation

**Decision**: Use Claude Code Task agents (spawned from the main session) for persona cognitive evaluation. Sonnet 4.6 for regular personas, Opus 4.6 for pedant personas. Orchestrated via a Claude Code skill (`.claude/skills/simulate-persona/SKILL.md`) following the same pattern as the existing `generate-questions` skill.

**Rationale**: The user's Max Pro subscription includes unlimited Claude Code agent usage — zero API cost. Task agents can read screenshots (multimodal via Read tool), perform web searches (WebSearch tool), and write structured JSON to working files. The two-phase separation (Phase 1: Playwright mechanical automation, Phase 2: Task agent cognitive evaluation) means Playwright runs fast while agents take their time evaluating checkpoint data.

**Alternatives considered**:
- Anthropic API (SDK): Works but costs money per call; Max Pro subscription already covers Task agents at no additional cost
- OpenAI GPT-4o: Good vision but lacks native Claude Code integration (no Task tool, no WebSearch)
- Local LLMs: Insufficient reasoning quality for critical domain-expert evaluation
- Pre-scripted responses: Defeats the purpose of genuine cognitive evaluation

### R2: Screenshot Analysis Approach

**Decision**: Use Claude's multimodal (vision) capabilities to analyze screenshots. Send screenshots as base64 images with structured prompts asking for specific evaluations (color distribution, layout integrity, visual coherence).

**Rationale**: Claude can evaluate "does this map look like it shows expertise in region X?" more meaningfully than pixel-level color analysis alone. Combine vision-based evaluation with simple programmatic checks (console errors, element visibility) for comprehensive assessment.

**Alternatives considered**:
- Pixel-level color sampling only: Too brittle, doesn't capture gestalt visual impression
- Image diff against baselines: Maps vary by question selection; no stable baseline exists
- Custom computer vision: Overkill for this use case, introduces significant complexity

### R3: Web Search for Pedant Verification

**Decision**: Use Claude Code's WebSearch tool (available to all Task agents) for fact-checking during pedant simulations. When the pedant agent suspects an incorrect answer, it formulates a search query, reviews results, and cites sources — all within the Task agent's execution context.

**Rationale**: The constitution (Principle I: Accuracy) mandates verification against authoritative sources. WebSearch is built into Claude Code and available to all spawned Task agents at no extra cost. The pedant Task agent (Opus 4.6) can search, evaluate evidence, and write verified corrections to working files in a single agent turn.

**Alternatives considered**:
- Pre-verified answer key: Defeats the purpose of ongoing quality auditing
- Wikipedia API only: Too narrow; some questions reference concepts that need broader verification
- Manual review: Not scalable for 2500+ questions
- Anthropic API tool_use: Would work but costs money; WebSearch in Task agents is free with Max Pro

### R4: Persona Agent Communication Format

**Decision**: Task agents write structured JSON to `.working/` files at each checkpoint. The skill's main orchestrator reads these files to track progress and compile reports. Schemas define belief narrative (string), question evaluations (array), expectations (object), issues found (array with severity).

**Rationale**: File-based communication follows the established `generate-questions` skill pattern. Working files provide natural checkpointing — if a Task agent's context runs out mid-evaluation, the next agent reads the working files and resumes. JSON is easily validated and compiled into final reports.

**Alternatives considered**:
- Free-form text in working files: Hard to parse for automated evaluation
- Direct agent-to-agent communication: Not supported by Task tool; file-based is the standard pattern
- Single monolithic evaluation: Too large for one agent context; checkpoint-based approach is more resilient

### R5: Question Data Volume Assessment

**Decision**: 50 questions per domain × 50 domains = 2,500 total questions. Physics has 50 questions. Biology has 50. Pedant personas need to audit ALL questions in their assigned domain(s).

**Rationale**: Verified by inspecting `data/domains/`. Each domain JSON has exactly 50 questions with structure: `{id, question_text, options, correct_answer, difficulty, source_article, domain_ids, concepts_tested, x, y}`. The "all" domain at the top level has 50 questions that are a sampled subset.

**Data**: The question bank is sufficient for all persona simulations. Power user P12 (125 questions) will exhaust a single domain (50) and need questions from related domains — this is handled by the existing domain loader which pulls from the broader pool.

### R6: Existing Test Infrastructure

**Decision**: Extend the existing `tests/visual/persona-simulation.spec.js` pattern rather than replacing it entirely. The existing file demonstrates a working approach for question lookup, answer selection, and screenshot capture. The new framework adds AI agent evaluation on top.

**Rationale**: The existing 354-line persona simulation already handles: question DB loading from JSON, fuzzy question text matching, probabilistic answer selection based on persona expertise, domain-based accuracy profiles, screenshot capture, and video recommendation checking. This infrastructure is solid and should be reused.

**Key existing patterns to preserve**:
- `questionDb` Map built from `data/domains/index.json` + per-domain JSONs
- `lookupQuestion()` fuzzy text matcher
- `answerQuestion()` with domain-based accuracy profiles
- `selectDomain()` via custom select dropdown
- Screenshot paths in `tests/visual/screenshots/`

### R7: Estimator Stability Issues

**Decision**: Investigate and fix the Cholesky decomposition / estimator collapse bugs as part of this testing effort, driven by power user persona P12 findings.

**Rationale**: The spec reports estimator collapse at ~115-120 questions and Cholesky decomposition errors. The existing `estimator.js` (421 lines) uses Cholesky-based exact GP inference which becomes numerically unstable as the observation matrix grows. Root cause likely: ill-conditioned kernel matrix when observations are very close together in embedding space.

**Probable fixes**:
- Add jitter (small diagonal addition) to the kernel matrix before Cholesky decomposition
- Cap maximum observations (e.g., summarize/prune observations beyond 100)
- Monitor condition number and gracefully degrade
