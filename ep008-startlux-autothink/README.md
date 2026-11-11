# EP008 · StartLux AutoThink: an AI that only thinks when it's unsure (tested on a Mac)

Video: Tokenwright, "This AI Only Thinks When It's Unsure. I Tested It" (YouTube @Tokenwright).

StartLux-Decision v1.1 AutoThink reads a probability for every option in one pass and only writes a thought when the top
probability is below a gate (default 0.6; their published results use 0.9). I ran the 4B AutoThink (Q8_0 GGUF, llama.cpp,
Apple M4 Pro 24 GB) on 48 DecisionPivot v1.1 items (24 contrast pairs, level 2) four ways, and Claude Haiku 5.5 three times.

| condition | thinks on | accuracy | pairs right | s / decision |
|---|---|---|---|---|
| one pass (never think) | 0% | 54.2% | 4/24 | 1.5 |
| AutoThink gate 0.6 (default) | 54.2% | 77.1% | 13/24 | 24.8 |
| AutoThink gate 0.9 (published) | 100% | 100% | 24/24 | 39.9 |
| always think (x2) | 100% | 100% | 24/24 | ~39 |
| Claude Haiku 5.5 (x3) | n/a | 100% | 24/24 | 3.7 ($0.027 per 48) |

Highest one-pass confidence on any item: 0.812, so gate 0.9 never skipped thinking. Full numbers and caveats: DATA.md.

## Files
- `select_items.py`: picks the 48 items (8 contrast pairs from each of filter_match, log_count_check, state_goal; seed 20261111)
- `run_local.py`: calls the StartLux engine (`startlux-decide serve --backend llamacpp`) at :8090 for each condition
- `run_claude.py`: same items for Claude Haiku 5.5 (reads the key from ~/.config/anthropic/key)
- `analyse.py`: builds `summary.json` (accuracy, pair accuracy, thought rate, timing, calibration, gate sweep)
- `items_selected.jsonl`, `results_local.jsonl` (240 decisions, with every thought), `results_claude.jsonl` (144), `summary.json`

## Sources and licences
- Code: https://github.com/StartLuxLabs/StartLux-Decision (Apache-2.0) · models: https://huggingface.co/startlux-models (CC BY-NC 4.0)
- Items: https://huggingface.co/datasets/startlux-models/DecisionPivot (CC BY 4.0) · report: arXiv 2610.17309
- Caveats: 48 items, 3 of 13 families, level 2 only; GGUF via llama.cpp, not their vLLM/MLX setup.
