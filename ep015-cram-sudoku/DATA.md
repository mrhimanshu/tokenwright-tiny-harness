# EP015 DATA (lab run 16 Nov 2026 21:50–22:55 UTC on the Mac, M4 Pro CPU, no GPU; summarised 17 Nov)
Raw: lab/results.jsonl (Claude thinking), lab/code.jsonl (Claude-written solvers), lab/cram_results.jsonl (rebuilt CRAM), lab/summary.json.
Puzzles: 500 Sudoku-Extreme test puzzles (sapientinc/sudoku-extreme, 5 seeded pages), median 26 clues. Training for CRAM: 1,000 solved train boards.
API spend: $3.75 total.

## 1. Claude solving in its head (adaptive thinking, effort high, max 32,000 output tokens)
| model | n | solved | ran out of tokens | wrong answer | $/puzzle | $/solved | median secs |
|---|---|---|---|---|---|---|---|
| Opus 5.5 | 5 | 3 | 2 | 0 | 0.426 | 0.71 | 124.9 (max 247) |
| Sonnet 5.5 | 5 | 3 | 2 | 0 | 0.250 | 0.416 | 166.1 (max 196) |
| Haiku 5.5 | 10 | 3 | 5 | 2 (74/81 and 78/81 cells right, stated as the answer) | 0.014 | 0.045 | 105.7 |
- Sonnet and Opus failed on the SAME two puzzles (#2 difficulty rating 88, #4 rating 15): both hit 32,000 tokens.

## 2. Claude writing a solver (one prompt, standard library Python, we run it on all 500), n=3 per model
| model | all 500 solved | median ms/puzzle | total secs for 500 | cost to write | lines |
|---|---|---|---|---|---|
| Haiku 5.5 | 3/3 | 1.14–1.85 | 0.96–1.74 | $0.003–0.005 | 108–128 |
| Sonnet 5.5 | 3/3 | 1.02–1.48 | 0.80–1.17 | $0.018–0.020 | 96–109 |
| Opus 5.5 | 3/3 | 1.19–1.66 | 1.07–1.45 | $0.051–0.063 | 104–122 |
- 9/9 solvers solved 500/500 = 4,500/4,500. Write time 12–44 s.

## 3. CRAM rebuilt from the paper (NumPy pseudolikelihood fit + C focused Gibbs search, 4 chains, one CPU core, budget 10M moves)
| energy | seed | solved/500 | wrong stops | fit secs | median ms | p90 ms |
|---|---|---|---|---|---|---|
| hand-set (one weight value, Hopfield-Tank rules) | 0 | 497 | 0 | 0 | 42.8 | 311 |
| learned | 0 | 496 | 0 | 2.51 | 53.2 | 351 |
| learned | 1 | 496 | 0 | 2.52 | 61.1 | 397 |
| learned | 2 | 497 | 0 | 2.52 | 54.2 | 425 |
- Learned energy is NOT told rows/cols/boxes; peer_recovery = 1.000: every cell's top-20 learned same-digit partners are exactly its 20 real row/col/box peers.
- Failures = budget ran out (~6.3 s), never a wrong stop. Puzzles #93 and #136 failed in all 4 runs.
- On the 10 puzzles Claude saw, learned CRAM solved 10/10: 0.3 ms to 1.29 s (the two that beat Opus/Sonnet: 66 ms and 122 ms).
- Fit: 2.5 s on our CPU vs the paper's 42 ms on an H200 (their number).

## Headline
- Thinking: Opus 3/5 at 43 cents a puzzle, ~2 min each.  CRAM rebuild: 99.2–99.4% at ~54 ms on one core, 2.5 s training.
- A 100-line solver Claude wrote for under 2 cents: 500/500, ~1.4 ms a puzzle, every time (9/9).
- The paper's own caveat matches: the one-weight hand-set energy did as well as the learned one (497 vs 496–497). Sudoku is too easy to prove "reasoning".
