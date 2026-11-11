# EP008 DATA — StartLux-Decision v1.1 4B AutoThink on an M4 Pro (my runs, 11 Nov 2026)
Raw: lab/results_local.jsonl (240 local decisions), lab/results_claude.jsonl (144 Claude decisions), lab/summary.json, lab/logs/.
Test set: 48 DecisionPivot v1.1 items = 24 contrast pairs (8 each from filter_match, log_count_check, state_goal; level 2; seed 20261111).
A pair counts only if BOTH answers are right (coin-flip baseline for a yes/no pair = 25%).
Model: Q8_0 GGUF (4.48 GB, sha256 verified), llama-server 0.7.0, 16k ctx, q8 KV cache, 1 slot, StartLux engine --backend llamacpp.

| condition | thinks on | accuracy | pairs right | s / decision (mean · median) |
|---|---|---|---|---|
| one pass (think never) | 0% | 54.2% (26/48) | 4/24 = 16.7% | 1.47 · 1.15 |
| AutoThink gate 0.6 (default) | 54.2% | 77.1% (37/48) | 13/24 = 54.2% | 24.8 · 20.9 |
| AutoThink gate 0.9 (their published setting) | 100% | 100% (48/48) | 24/24 | 39.9 · 34.9 |
| think always (run 1 · run 2) | 100% | 100% · 100% | 24/24 · 24/24 | 38.9 · 39.2 |
| Claude Haiku 5.5 (3 runs) | — | 100% ×3 | 24/24 ×3 | 3.6–3.9 |

- Thought length (always): mean 1,319 tokens, median 1,107, range 460–3,996.
- Highest one-pass confidence on all 48 items = 0.812. So at gate 0.9 the gate NEVER skipped thinking: "only when unsure" = always.
- One-pass calibration (top probability → share right): 0.5–0.6: 59.1% (n=22) · 0.6–0.7: 45.5% (n=11) · 0.7–0.8: 50.0% (n=8) · 0.8–0.9: 66.7% (n=3).
- 11 items were answered WRONG in one pass with confidence above 0.6, so the default gate skipped thinking on them; all 11 were right after thinking.
- Gate sweep (derived from the "always" run's first read-outs): 0.5 → pairs 20.8%, thinks 8% · 0.6 → 54.2%, 54% · 0.7 → 79.2%, 77% · 0.8 → 95.8%, 94% · 0.9 → 100%, 100%.
- Claude Haiku cost: $0.027 per 48 decisions (≈ $0.00056 each), ~890 output tokens each. Local cost: $0 (electricity), ~32 min per 48 decisions with thinking.

## The one-cent example (filter_match pair 178)
Same request, same record; the ONLY difference is the price: 401.83 vs 401.82 EUR (list 502.28). Rule: price cut at least 20%, worked out exactly.
502.28 × 0.8 = 401.824 → 401.82 passes ("yes"), 401.83 fails ("no").
- One pass: "yes" at 60.3% vs "yes" at 60.4%. Gate 0.6 → both above the gate → no thinking → the 401.83 case is wrong.
- With thinking: 811 tokens, ~23 s, finds 401.83 > 401.824 → "no" (right). Partner: 2,276 tokens, ~66 s → "yes" (right).
- Claude Haiku: right on both in all 3 runs ("falls just short of 20% when worked out exactly").

## Caveats
- 48 items, 3 of 13 families, level 2 only: easier than the full benchmark (their 4B pair accuracy on the full set = 59.9 at gate 0.9).
- Q8_0 GGUF via llama.cpp, not their vLLM / MLX setup; their speed figure (94 ms per read-out on an M5 Pro, MLX 8-bit) is theirs, not ours.
- Weights are CC BY-NC 4.0 (non-commercial).
