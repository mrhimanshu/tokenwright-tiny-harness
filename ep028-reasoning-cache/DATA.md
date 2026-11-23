# EP028 DATA — mini CPU-ARC, my runs 23 Nov 2026 (22:05–22:10 UTC)

Setup: 6 word-problem families (loan payment, savings balance, tiered shipping, two trains meeting, work rate, business days).
Per family: 1 seed + 8 same-shape variants (new numbers, 3 wordings) + 3 shape-shift variants (one extra sentence: arrangement fee, deposits stop, remote fee, halfway stop, third worker, public holiday). Ground truth from my own Python solvers.
Arms: Opus 5.5 fresh (effort medium, n=1 per item, 72 calls); Haiku 5.5 fresh (n=3, 216 calls); cache = Opus solves the seed, Opus (effort high) turns the trace into a Python solve() + param list, verified against the source answer on the seed; at hit time Haiku 5.5 (effort low) picks the entry, extracts params and says whether the entry captures the whole problem; CPU runs the code (n=3 per item, 198 calls).
Differences from the paper: Opus 5.5/Haiku 5.5 instead of Opus 4.5/Haiku 4.5; Haiku picks the entry instead of an embedding index; one function per entry, not a network of semantic functions; word problems, not AIME.

| arm | split | right | mean $ per call | mean s |
|---|---|---|---|---|
| opus | same | 48/48 (100.0%) | 0.01477 | 6.81 |
| haiku | same | 142/144 (98.6%) | 0.00064 | 5.57 |
| cache | same | 144/144 (100.0%) | 0.00031 | 1.65 |
| opus | shift | 18/18 (100.0%) | 0.01777 | 8.07 |
| haiku | shift | 50/54 (92.6%) | 0.00090 | 7.72 |
| cache | shift | 12/54 (22.2%) | 0.00040 | 2.19 |
| guarded | shift | 54/54 (100.0%) | 0.01456 | 0.00 |

- Same shape: cache 144/144 at $0.00031 vs Opus $0.0148 → **47× cheaper** per call. Haiku alone 142/144 at $0.00064 → cache only **2.0×** cheaper than plain Haiku. Haiku's 2 misses were loan payments (arithmetic).
- Build: 6 entries, all verified on the first try, builder cost $0.141 total (+ $0.090 for the 6 Opus seed solves). Break-even vs Opus ≈ 10 calls (16 incl. seeds) — paper: ~13 (AIME) to ~90 (GSM8K).
- CPU time of solve(): median 31 µs, max 29 ms. Latency per cache call ≈ 1.7 s (the Haiku call) vs Opus 6.8 s.
- Shape shift, no guard (use the cache answer anyway): **12/54 right, 42 wrong, 0 errors raised** (silent). Per family: loan 9/9 (Haiku folded the fee into the principal), trains 3/9 (meeting happened before the halfway stop), savings 0/9, shipping 0/9, workrate 0/9, bizdays 0/9. Example: business days due 2026-07-24, truth 2026-07-27; savings 36,976.84 vs truth 9,912.77.
- Shape shift, with the guard (Haiku's fits flag; not fits → fall back to Opus): 45/54 flagged, 0 silent wrongs, **54/54 right**, mean $0.0146 per call (≈ Opus price). Same-shape items: 0/144 flagged (no false alarms).
- Routing: 144/144 same-shape and 53/54 shift items went to the right entry.
- Opus 5.5 fresh: 72/72 right (incl. all shift items). Haiku shift 50/54 (loan 5/9).
- Total API spend: $1.48.

Raw: lab/results.jsonl · cache entries: lab/cache.json · tasks: lab/tasks.json · summary: lab/summary.json
