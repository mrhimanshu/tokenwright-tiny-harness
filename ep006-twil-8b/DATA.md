# EP006 data: TwIL-8B (Q4_K_M balanced, llama.cpp 0.7.0, M4 Pro 24 GB) in the EP005 harness, 7 Nov 2026

Same 5 tasks, prompts and tools as EP005 (harness v2 with edit_file). 3 runs per task = 15 runs. Settings: temp 1.0, top_p 0.95
(model defaults), 64k context, q8 KV cache, max 12,000 output tokens per reply, max 30 turns. Server RSS ~10 GB; system memory free 18% during runs.

| task | passed | seconds per run | turns |
|---|---|---|---|
| t1 shop (820-line file) | 2/3 | 1375, 550, 742 | 29, 13, 7 |
| t2 slug | 2/3 | 249, 284, 95 | 6, 7, 5 |
| t3 pagination | 3/3 | 58, 55, 83 | 6, 6, 7 |
| t4 --json flag | 3/3 | 36, 52, 42 | 6, 6, 6 |
| t5 rename | 1/3 | 56, 192, 45 | 11, 24, 8 |
| **total** | **11/15 (73%)** | 65.3 min total · median 83 s · mean 261 s | |

Generation speed median 36 tok/s (20–22 tok/s at ~30k context). 89,874 output tokens in total (mean 5,992 per run).

Comparison (EP005, 6 Nov, same harness + tasks, Claude Haiku 5.5): 25/25 passed, mean 6.4 s per task, $0.00166 per task
→ 15 tasks ≈ 1.6 min and ≈ $0.025. Claude Code: 25/25, 13.5 s, $0.0042.

## The 4 failures (all "stopped without acting")
1. t2 slug run 0: ended its turn with 1 test still failing ("What's" → "what-s"). (no transcript for run 0)
2. t5 rename run 1: read all 4 files in one turn, then believed calc_total lived in the empty store/__init__.py; read that empty file 18 times in total; no edit ever landed; gave up at turn 24.
3. t1 shop run 2: one reply of 12,000 tokens (the per-reply cap) worked out both fixes in its thinking and was cut off before calling a tool; harness saw no tool call → run ended. 1 of 147 replies hit the cap.
4. t5 rename run 2: planned the rename, then wrote its next tool call inside its private <think> block, where the harness can't see it → 0 edits.
Run 0 of t1 passed but took 29 turns / 23 min, including adding print statements to tests/test_cart.py while debugging (assertions unchanged).
