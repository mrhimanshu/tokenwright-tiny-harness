# EP025 DATA: SenseNova Loop-9B loop dial (my runs, 22 Nov 2026)

Machine: Quill cloud computer, 4 CPU threads, no GPU. Model: official sensenova/SenseNova-Loop-9B-GGUF Q4_K_M (5,818,631,072 bytes,
sha256 5528b06c…eeed, matches HF API). Runtime: OpenSenseNova/llama.cpp @ 24ea7bb (built from source, CPU, web UI off).
Loop count changed by rewriting the GGUF header (lab/replan_gguf.py: block_count, loop.count, attention.recurrent_layers; tail/MTP
tensor block indices renumbered; tensor bytes untouched). Check: replan to k=2 → `cmp` byte-identical to the official file.

## Task accuracy (lab/results.jsonl, task set v2 = lab/tasks.jsonl; 3 seeded sets × 30; greedy, max 12 tokens, thinking off)
| loops | layer runs | correct /90 | per set | add /24 | mul /24 | 2-step /21 | capital /21 | gen tok/s (median) | prompt tok/s |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 32 | 43 | .53/.47/.43 | 23 | 10 | 2 | 8 | 6.63 | 17.2 |
| 2 (shipped) | 56 | 83 | .97/.87/.93 | 24 | 24 | 14 | 21 | 3.66 | 9.7 |
| 3 | 80 | 79 | .87/.83/.93 | 24 | 24 | 10 | 21 | 2.65 | 6.7 |
| 4 | 104 | 71 | .80/.77/.80 | 24 | 23 | 5 | 19 | 1.99 | 5.2 |
- City names scored accent-insensitive (Brasília = Brasilia) in lab/analyze.py.
- Examples: 1 loop: Australia → "Cannonball", Canada → 'The city name is "Ottard."', France → "2025", Poland → "Poland", Spain → "Spain", Turkey → "Bursa". 4 loops: Chile → "Washington DC", Argentina → "Buen Aires".
- Weights identical at every setting (same 5.82 GB tensors). Server RSS at first request: 8.8 / 9.0 / 9.2 / 9.4 GB (grows later with llama-server's prompt cache).

## Perplexity (lab/ppl_results.jsonl; llama-perplexity ctx 512, 1 chunk per article, Wikipedia plain-text extracts fetched 22 Nov)
| loops | Lighthouse | Sourdough | Tardigrade | mean |
|---|---|---|---|---|
| 1 | 65.92 | 52.65 | 22.79 | 47.12 |
| 2 | 19.57 | 19.55 | 10.69 | 16.60 |
| 3 | 22.91 | 22.09 | 13.53 | 19.51 |
| 4 | 38.55 | 29.28 | 21.71 | 29.85 |
2 loops is best on every article.

## Hard task set v1 (lab/results_hard_v1.jsonl, kept, not used on screen)
Multi-step word problems + shuffled 3/5/7-hop variable chains, answer-only: 1 loop 0/60, 2 loops 1/60 (too hard without thinking; replaced by v2 before loops 3–4 ran).

## Control: Qwen2.5-1.5B-Instruct looped (lab/qwen_loop.py; layers 4–23 repeated, shared weights; KV cache per visit, checked equal to no-cache output)
| loops | layer runs | correct /90 | per set | add /24 | mul /24 | 2-step /21 | capital /21 | perplexity (mean of 3) |
|---|---|---|---|---|---|---|---|---|
| 1 | 28 | 68 | 0.767/0.767/0.733 | 23/24 | 24/24 | 0/21 | 21/21 | 10.296 |
| 2 | 48 | 18 | 0.167/0.2/0.233 | 0/24 | 0/24 | 0/21 | 18/21 | 13.764 |
- Example at 2 loops: "What is 700 + 122?" → "700 + 122 = 843"; "734 + 158" → "734"; capital of Canada → "Toronto". 3 loops not run for Qwen (CPU time; 2 loops already broke it).
- First pass used max 12 new tokens; looped Qwen started restating sums ("700 + 122 = 8…") and got cut off, so it was re-run with 40 tokens and scored on the number after the last "=" (lab/results_qwen_v1_trunc12.jsonl kept).

## Their numbers (not mine)
Loop scaling vs 1 loop, matched training and inference loops: AIDABench-QA +6.42% (3 loops), Workbuddy-office +16.93% (3), LiveCodeBench V6 +8.10% (4), AIDABench data-vis +8.55% (4).
Cost: $0 API. CPU ~1.5 h total.
