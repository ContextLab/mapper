# Session Notes: 2026-02-17 Batch2 Session 4

## Summary
Continued batch2 question generation and length-balancing for the remaining sub-domains.

## Completed This Session
1. **Cognitive-neuroscience batch2** — Validated 30q, fixed 21 position mismatches, adjusted difficulties (L1:4→6, L2:5→6, L3:8→6 by promoting 2 to L1 and demoting 1 from L4 to L2). Length-balanced to {8,8,7,7} in 1 pass. File: `/tmp/cognitive_neuro_batch2_questions.json`

2. **Computational-neuroscience batch2** — Generated 30q covering FitzHugh-Nagumo, cable theory, WTA circuits, gain modulation, divisive normalization, Izhikevich model, synfire chains, mean-field theory, neural manifolds, stochastic resonance, predictive coding, balanced amplification, free energy principle, spike-frequency adaptation, efficient coding, line attractors, compartmental models, CTC hypothesis, BCM theory, dynamical systems motor control, criticality, VAEs as cortical models, binding problem, Boltzmann machines, optogenetics, neural noise/sampling, calcium imaging, ring attractors, short-term depression, degeneracy. Fixed 22 positions, L3→L1 (ring attractors). Length-balanced to {8,8,7,7} in 2 passes. File: `/tmp/computational_neuro_batch2_questions.json`

3. **Neurobiology batch2** — Generated 30q covering dendritic spikes, gap junctions, endocannabinoid retrograde signaling, neurotrophins/BDNF, Wallerian degeneration/SARM1, axonal transport, cortical layers, CPGs, ion channel diversity, Dale's principle/co-transmission, synaptic tagging, neural crest, nociception/gate control, neuromodulation, circadian rhythms/SCN, oligodendrocytes vs Schwann cells, metaplasticity, BBB transport, NMDA coincidence detection, proprioception, complement-mediated pruning, Dravet syndrome/channelopathies, neurotransmitter reuptake, mirror neurons, tripartite synapse, cortical migration/inside-out rule, autophagy, critical periods, gut-brain axis, epigenetics in memory. Fixed 22 positions, L4→L5 (mirror neurons). Length-balanced to {8,8,7,7} in 5 passes (neurobiology had unusually long correct answers ~480-510 chars making length-balancing difficult). File: `/tmp/neurobiology_batch2_questions.json`

## Current Batch2 Status (14 of 18 + "all" complete)

| Domain | Status | File |
|--------|--------|------|
| physics | ✅ | `/tmp/physics_batch2_questions.json` |
| biology | ✅ | `/tmp/biology_batch2_questions.json` |
| mathematics | ✅ | `/tmp/math_batch2_questions.json` |
| neuroscience | ✅ | `/tmp/neuro_batch2_questions.json` |
| art-history | ✅ | `/tmp/arthistory_batch2_questions.json` |
| astrophysics | ✅ | `/tmp/astrophysics_batch2_questions.json` |
| quantum-physics | ✅ | `/tmp/quantum_physics_batch2_questions.json` |
| european-art-history | ✅ | `/tmp/european_art_history_batch2_questions.json` |
| chinese-art-history | ✅ | `/tmp/chinese_art_history_batch2_questions.json` |
| molecular-cell-biology | ✅ | `/tmp/molecular_cell_biology_batch2_questions.json` |
| genetics | ✅ | `/tmp/genetics_batch2_questions.json` |
| cognitive-neuroscience | ✅ | `/tmp/cognitive_neuro_batch2_questions.json` |
| computational-neuroscience | ✅ | `/tmp/computational_neuro_batch2_questions.json` |
| neurobiology | ✅ | `/tmp/neurobiology_batch2_questions.json` |
| calculus | ❌ NOT STARTED | — |
| linear-algebra | ❌ NOT STARTED | — |
| number-theory | ❌ NOT STARTED | — |
| probability-statistics | ❌ NOT STARTED | — |
| "all" (interdisciplinary) | ❌ NOT STARTED | — |

## Remaining (4 math sub-domains + "all")
1. calculus (30q)
2. linear-algebra (30q)
3. number-theory (30q)
4. probability-statistics (30q)
5. "all" interdisciplinary (50q)

Then: merge batch1+batch2, compute embeddings, export domain bundles, phases 10-13.

## Observations
- Neurobiology batch2 was hardest to length-balance (5 passes) because correct answers were 480-510 chars — very close to the expanded distractor lengths.
- Standard fix approach: expand distractors with unnecessary qualifiers, redundant detail, and emphatic absolutes ("absolutely no", "whatsoever", "of any kind").
- Key: Always verify correct answer text is UNCHANGED from originals after every fix.
