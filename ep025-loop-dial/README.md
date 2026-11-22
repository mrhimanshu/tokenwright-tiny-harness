# EP025: turning SenseNova Loop-9B's loop dial on a CPU

Video: "This AI Runs Its Brain Twice. 4 Loops Made It Worse" (Tokenwright, 22 Nov 2026).
Story: [SenseNova-Loop-9B](https://huggingface.co/sensenova/SenseNova-Loop-9B) stores 32 layers and runs layers 4–27 twice (56 layer runs per token).

What's here (CPU only, 4 threads, $0 API):
- `replan_gguf.py`: rewrites the official GGUF's loop plan (block_count, loop.count, recurrent_layers, tail/MTP block indices) to 1/3/4 loops. Tensor bytes untouched. Set to 2, it reproduces the official file byte for byte.
- `run_loops.py`: runs the 90 seeded questions (`make_tasks2.py` → `tasks.jsonl`) through the [OpenSenseNova llama.cpp fork](https://github.com/OpenSenseNova/llama.cpp) @ 24ea7bb, greedy, thinking off.
- `ppl_loops.py`: perplexity on 3 Wikipedia articles (`text/`).
- `qwen_loop.py`: control, an ordinary model (Qwen2.5-1.5B-Instruct) with layers 4–23 repeated; `qcheck.py` checks cached vs uncached output.
- `analyze.py` → `summary.json`; `DATA.md` has the tables. Raw rows: `results.jsonl`, `ppl_results.jsonl` (+ earlier runs kept: `results_hard_v1.jsonl`, `results_qwen_*`).

Headline (correct /90): 1 loop 43 · 2 loops (shipped) 83 · 3 loops 79 · 4 loops 71. Perplexity 47.1 / 16.6 / 19.5 / 29.8. Speed 6.6 / 3.7 / 2.7 / 2.0 tok/s.
Qwen control: 68/90 → 18/90 when looped twice.
Their loop-scaling chart uses matched training and inference loops (a model trained per loop count), so the released model's loop count is baked in.
