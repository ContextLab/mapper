# Session Notes: Length Bias Fix Progress
**Date:** 2026-02-17
**Task:** Fix answer-length bias across all question files

## Completed Fixes (5/19 files)
All achieve {5,5,5,5} rank distribution, both "pick longest" and "pick shortest" = 25%

1. **physics batch1** - Fixed in prior session
2. **probability-statistics batch1** - Fixed (8.85× → balanced, ratio 0.80-2.37)
3. **european-art-history batch1** - Fixed (8.72× → balanced, ratio 0.85-2.93)
4. **linear-algebra batch1** - Fixed (7.69× → balanced, ratio 0.73-2.72)
5. **calculus batch1** - Fixed (6.17× → balanced, ratio 0.85-2.81)
6. **chinese-art-history batch1** - Fixed (6.04× → balanced, ratio 0.65-2.82)

## Fix Scripts Created
- `/tmp/fix_probability_statistics_batch1.py`
- `/tmp/fix_european_art_history_batch1.py`
- `/tmp/fix_linear_algebra_batch1.py`
- `/tmp/fix_calculus_batch1.py`
- `/tmp/fix_chinese_art_history_batch1.py`

## Remaining (13 files)
By severity:
- neurobiology batch1 (6.04×)
- number-theory batch1 (5.13×)
- cognitive-neuroscience batch1 (5.03×)
- physics batch2 (4.90×) - 30 questions, different rank distribution needed
- computational-neuroscience batch1 (4.30×)
- art-history batch1 (3.76×)
- quantum-physics batch1 (3.51×)
- genetics batch1 (3.49×)
- astrophysics batch1 (3.15×)
- mathematics batch1 (3.05×)
- neuroscience batch1 (2.89×)
- molecular-cell-bio batch1 (2.45×)
- biology batch1 (2.39×)

## Process
1. Read originals from `/tmp/originals/`
2. Assign rank targets: 5 per rank for 20q files
3. Write Python fix script with replacement dict
4. Run, check output, iterate if ranks aren't {5,5,5,5}
5. Common issue: estimated char counts are off by 10-30 chars, requiring 1-2 adjustment passes

## Standard Rank Assignment Template
For 20-question files:
- Rank 1 (correct longest): Q3, Q7, Q11, Q16, Q17
- Rank 2 (correct 2nd longest): Q1, Q5, Q9, Q13, Q19
- Rank 3 (correct 3rd longest): Q2, Q6, Q10, Q14, Q18
- Rank 4 (correct shortest): Q4, Q8, Q12, Q15, Q20
