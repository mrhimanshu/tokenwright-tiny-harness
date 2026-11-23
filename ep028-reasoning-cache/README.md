# EP028 · a mini NVIDIA CPU-ARC (reasoning cache) on Claude

Video: Tokenwright EP028 "NVIDIA's AI Reasoning Cache: 47x Cheaper Until It Isn't".
Paper: Belcak et al., NVIDIA, "CPU-ARC: Agentic Reasoning Caching for on-CPU Reasoning Reuse", arXiv 2611.09891 (6 Nov 2026).

- `gen_tasks.py`: 6 problem families × (1 seed + 8 same-shape + 3 shape-shift), with my own reference solvers → `tasks.json`
- `run_lab.py all`: Opus 5.5 fresh (×1), Haiku 5.5 fresh (×3), cache build (Opus turns its seed trace into `solve(**p)`), cache hits (Haiku 5.5 routes + extracts + `fits` flag, CPU runs the code, ×3). Reads the key from `~/.config/anthropic/key` or `ANTHROPIC_API_KEY`.
- `analyse.py` → `summary.json`; `cache.json` = the 6 entries Opus wrote; `results.jsonl` = every call.

Headline (23 Nov 2026, $1.48): same shape 144/144 at 47× cheaper than Opus (but only 2× cheaper than Haiku alone); one extra sentence → 12/54 right with zero errors; the `fits` check flagged 45/54 and 0/144, and falling back to Opus gave 54/54. See DATA.md.
