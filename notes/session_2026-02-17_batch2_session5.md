# Session 5 Notes — 2026-02-17

## Work Completed

### 1. Fixed Calculus batch2 length-balance (4 remaining mismatches → 0)
- Started from `/tmp/calculus_batch2_debug.json` with 4 mismatches at idx 2, 6, 9, 23
- Discovered the debug file had gotten corrupted from a previous session's partial edits
- Restarted from `/tmp/originals/calculus_batch2_questions.json` — all 22 needed fixing
- Fixed in 4 passes total (2 from prior session + 2 this session = comprehensive rewrite)
- Final: 0 mismatches, {8,8,7,7}, pick-longest 26.7%, pick-shortest 23.3%

### 2. Generated Linear Algebra batch2 (30 questions)
- Topics: solution sets/affine subspaces, transpose products, trace, null space, projection matrices, similarity, characteristic polynomial, inner products, LU decomposition, linear map determination, Hermitian eigenvalues, quadratic forms, Schur decomposition, Moore-Penrose pseudoinverse, Kronecker products, matrix norms, Rayleigh quotient, Woodbury identity, minimal polynomial, simultaneous diagonalization, Courant-Fischer, Gershgorin circles, Lanczos algorithm, wedge product, Weyr canonical form, Marchenko-Pastur, QR algorithm, Frobenius form, compressed sensing/RIP, nuclear norm
- Length-balanced in 2 passes: {8,8,7,7}, pick-longest 26.7%, pick-shortest 23.3%

### 3. Generated Number Theory batch2 (30 questions)
- Topics: Euclidean algorithm, Euler's totient, Legendre symbol, Wilson's theorem, Pythagorean triples, Euler's theorem, Möbius function, Hensel's lemma, primitive roots, quadratic reciprocity, Dirichlet's theorem, perfect numbers, Jacobi symbol, Riemann zeta functional equation, class numbers/Dedekind domains, Goldbach's conjecture, Dirichlet convolution, Miller-Rabin, class field theory, Hardy-Littlewood circle method, Iwasawa theory, AKS primality, Hasse's theorem, BSD conjecture, Langlands functoriality, Selberg trace formula, Vinogradov's theorem, Stark conjectures, monstrous moonshine, Cohen-Lenstra heuristics
- Length-balanced in 4 passes: {8,8,7,7}, pick-longest 26.7%, pick-shortest 23.3%

### 4. Generated Probability-Statistics batch2 (30 questions)
- Topics: independence vs mutual exclusivity, linearity of expectation, variance of sums, normal stability, law of total probability, Type I/II errors, likelihood function, sufficient statistics, exponential family, Neyman-Pearson lemma, EM algorithm, conditional expectation, delta method, Rao-Blackwell, MCMC/Metropolis-Hastings, multivariate normal conditionals, cross-validation LOO, AIC/BIC, Stein paradox, minimax estimation, Donsker theorem, de Finetti's theorem, semiparametric efficiency, Gibbs sampling, Le Cam LAN, Dirichlet process, high-dimensional statistics, Stein's method, optimal transport/Wasserstein, conformal prediction
- Length-balanced in 3 passes: {8,8,7,7}, pick-longest 26.7%, pick-shortest 23.3%

## Current State

**ALL 18 batch2 domains are now COMPLETE and length-balanced!**

| Batch 2 Status | Count |
|----------------|-------|
| Complete & balanced | 18/18 |
| Questions generated | 540 total (18 × 30) |
| Batch 1 (prior) | 360 total (18 × 20) |
| **Total questions** | **900** |

## Files

All batch2 files in `/tmp/`:
- `calculus_batch2_questions.json` ✅
- `linear_algebra_batch2_questions.json` ✅
- `number_theory_batch2_questions.json` ✅
- `probability_statistics_batch2_questions.json` ✅
- (plus 14 previously completed batch2 files)

All originals in `/tmp/originals/` for all 18 domains.

## Remaining Tasks

1. **Generate "all" domain** — 50 interdisciplinary questions (NOT tied to any single domain)
2. **Merge** batch1 + batch2 → 50 questions per domain (18 files)
3. **Compute embeddings** → UMAP coordinates → PCA z-coords
4. **Export domain bundles**
5. **Phases 10-13** (responsive, a11y, compliance, deploy)

## Key Learnings

- Starting from originals for each pass is critical — debug files can accumulate unexpected state
- Correct answer lengths in probability-statistics are especially long (350-515 chars), requiring very aggressive distractor expansion
- The comprehensive first-pass approach (fixing all 22 at once) typically gets 13-19 right, with 4-7 needing a second pass
- Third passes are usually needed for 1-4 near-misses (off by <20 chars)
