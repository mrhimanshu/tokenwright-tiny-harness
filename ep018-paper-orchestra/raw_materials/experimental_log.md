## 1. Experimental Setup
- Date: 16 Nov 2026. Hardware: one laptop CPU (Apple M4 Pro), no GPU. Total API spend for all LLM runs: $3.75.
- Data: Hugging Face dataset sapientinc/sudoku-extreme. Test sample = 500 test puzzles drawn from 5 seeded random pages; median 26 clues per puzzle. CRAM training data = the first 1,000 solved boards of the train split.
- LLM settings: adaptive thinking, effort high, max 32,000 output tokens per puzzle. Because of cost, the "solve directly" condition used a subset: Opus 5.5 and Sonnet 5.5 on 5 puzzles each, Haiku 5.5 on 10 puzzles.
- Solver-writing condition: one prompt per model asking for a standard-library Python Sudoku solver; 3 independent solvers per model (9 total); each solver run on all 500 puzzles.
- CRAM re-implementation: energy over an 81 x 9 belief grid (negative entropy + pairwise 9x9 couplings + bias), cells are opaque indices (the model is NOT told rows, columns or boxes). Fit by pseudolikelihood in NumPy. Inference: focused Gibbs search in C, 4 chains from random boards, one CPU core, budget 10 million moves per puzzle. Hand-set baseline: one weight value with Hopfield-Tank rules, no training.

## 2. Results: LLM solving directly
| model | puzzles | solved | ran out of tokens | wrong answer | $ per puzzle | $ per solved | median seconds |
|---|---|---|---|---|---|---|---|
| Opus 5.5 | 5 | 3 | 2 | 0 | 0.426 | 0.71 | 124.9 (max 247) |
| Sonnet 5.5 | 5 | 3 | 2 | 0 | 0.250 | 0.416 | 166.1 (max 196) |
| Haiku 5.5 | 10 | 3 | 5 | 2 | 0.014 | 0.045 | 105.7 |
- Haiku's 2 wrong answers had 74/81 and 78/81 cells right and were stated as the final answer.
- Sonnet and Opus failed on the same two puzzles (difficulty ratings 88 and 15); both hit the 32,000-token limit.

## 3. Results: LLM writing a solver (3 solvers per model, each run on all 500)
| model | solvers solving all 500 | median ms per puzzle | total seconds for 500 | cost to write | lines of code |
|---|---|---|---|---|---|
| Haiku 5.5 | 3/3 | 1.14-1.85 | 0.96-1.74 | $0.003-0.005 | 108-128 |
| Sonnet 5.5 | 3/3 | 1.02-1.48 | 0.80-1.17 | $0.018-0.020 | 96-109 |
| Opus 5.5 | 3/3 | 1.19-1.66 | 1.07-1.45 | $0.051-0.063 | 104-122 |
- 9 of 9 solvers solved 500 of 500 puzzles (4,500 of 4,500 solves). Time to write a solver: 12-44 seconds.

## 4. Results: CRAM re-implementation (500 puzzles)
| energy | seed | solved / 500 | wrong stops | fit seconds | median ms | p90 ms |
|---|---|---|---|---|---|---|
| hand-set (one weight) | 0 | 497 | 0 | 0 | 42.8 | 311 |
| learned | 0 | 496 | 0 | 2.51 | 53.2 | 351 |
| learned | 1 | 496 | 0 | 2.52 | 61.1 | 397 |
| learned | 2 | 497 | 0 | 2.52 | 54.2 | 425 |
- Constraint recovery: for every cell, the top-20 learned same-digit partners are exactly its 20 true row/column/box peers (peer recovery = 1.000).
- All failures were the move budget running out (about 6.3 s); no search ever stopped at a wrong board. Two puzzles failed in all 4 runs.
- On the 10 puzzles given to the LLMs, learned CRAM solved 10/10 (0.3 ms to 1.29 s), including the two that beat Opus and Sonnet (66 ms and 122 ms).
- Fit time: 2.5 s on our CPU. The original paper reports 42 ms on an H200 GPU (their number, not measured by us).

## 5. Notes and limitations
- The hand-set one-weight energy matched the learned energy (497 vs 496-497), matching the original authors' caveat that Sudoku is too easy to demonstrate reasoning.
- The direct-solving LLM condition used only 5-10 puzzles per model because of cost; its accuracy estimates are very uncertain.
- We did not run the original authors' code; numbers attributed to the original paper are theirs.
