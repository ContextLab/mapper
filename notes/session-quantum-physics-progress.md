# Quantum Physics Question Generation — COMPLETE

**Date**: 2026-02-20
**Status**: ✅ ALL 50/50 questions finalized and assembled into domain JSON

## Completed Questions (50/50)

- **Q1-Q13**: Level 1 (High-level vocabulary) — ALL DONE
- **Q14-Q26**: Level 2 (Low-level vocabulary) — ALL DONE
- **Q27-Q38**: Level 3 (Basic working knowledge) — ALL DONE
- **Q39-Q50**: Level 4 (Deep knowledge) — ALL DONE

## Difficulty Distribution
- Level 1: 13 questions
- Level 2: 13 questions
- Level 3: 12 questions
- Level 4: 12 questions

## Answer Slot Distribution
- A: 13, B: 12, C: 13, D: 12 (near-uniform)

## Level 4 Topics Covered (Q39-Q50)
- Q39: Path integral formulation (Feynman, classical limit, stationary action)
- Q40: Quantum field theory (beta function, asymptotic freedom, critical N_f)
- Q41: Quantum chromodynamics (N_f bound for asymptotic freedom)
- Q42: Quantum electrodynamics (Schwinger's anomalous magnetic moment)
- Q43: Quantum Hall effect (role of disorder, IQHE plateaus)
- Q44: Topological quantum computing (Fibonacci anyons, SU(2)_k universality)
- Q45: Spontaneous symmetry breaking (type-B Goldstone bosons, Watanabe-Brauner)
- Q46: Second quantization (anticommutation → Pauli exclusion)
- Q47: Renormalization (Wilsonian RG, relevant/marginal/irrelevant operators)
- Q48: Berry phase (TKNN formula, Chern number quantization, torus topology)
- Q49: Fock space (vacuum state, number operator, annihilation property)
- Q50: Casimir effect (Boyer 1968 spherical shell repulsive force)

## Files
- **Final domain JSON**: `data/domains/quantum-physics.json` (50 questions, 4356 labels, 2500 articles)
- **Working questions**: `data/domains/.working/quantum-physics-questions.json` (50 questions, raw format)
- **Final checkpoint**: `data/domains/.working/quantum-physics-questions-COMPLETE-50of50.json`
- **Concepts**: `data/domains/.working/quantum-physics-concepts.json` (50 concepts)

## Additional Changes Made This Session
1. **Button placement fix** (`src/ui/quiz.js`): Moved Next/Wikipedia/Khan Academy buttons ABOVE answer options after answering, so users don't need to scroll to see them
2. **Khan Academy issue** (#21): Created GitHub issue for validating Khan Academy search links and adding fallback URLs
3. **Skip weight + difficulty RBF weights** (`src/learning/estimator.js`, `src/app.js`): Skip weight 0.05 (was 0.5), difficulty-based RBF weights {1:0.25, 2:0.5, 3:0.75, 4:1.0}
4. **Embedding pipeline docs/code**: Updated README, scripts README, AGENTS.md; created compute_bounding_boxes.py and regenerate_question_pipeline.py
5. **Skill file update** (`.claude/skills/generate-questions.md`): Added proper YAML front matter, $ARGUMENTS support, final assembly section

## Pipeline Notes
Each question went through 5 separate agent calls:
1. Step 1: Generate Q+A (Opus agent)
2. Step 2: Review Q+A (DIFFERENT Opus agent — catches factual/difficulty issues)
3. Step 3: Generate distractors (Opus agent)
4. Step 4: Review distractors (DIFFERENT Opus agent — catches arguably-correct/eliminable distractors)
5. Step 5: Compile final JSON and save

Key catches from review agents:
- Cross-question overlap detection (Q47↔Q40/Q41, Q49↔Q46) — led to complete rewrites
- Distractor eliminability via logic (e.g., $\delta S = \hbar$ when $\hbar \to 0$)
- Word count violations caught and fixed
- Factual accuracy verified via web searches
- Two-part questions consolidated into single interrogatives

## Next Steps
- Run the embedding pipeline to assign x/y coordinates to new questions
- Validate Khan Academy links (issue #21)
- Update the "all" domain JSON to include new quantum physics questions
