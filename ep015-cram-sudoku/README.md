# EP015: a 1980s energy model (CRAM) vs Claude vs a Claude-written solver, on Sudoku-Extreme

Video: Tokenwright, "A 1980s AI Beat Claude at Sudoku. 100 Lines Beat Both" (17 Nov 2026).
Paper: Hoover, Blayney, Whittington, arXiv 2611.17309 (their code: https://github.com/Prefrontal-AI/CRAM; this is an independent rebuild from the paper).

- `fetch_data.py` – 500 test puzzles + 1,000 train solutions from `sapientinc/sudoku-extreme`
- `claude_solve.py` – `--mode think` (Claude solves in its head) or `--mode code` (Claude writes `solve()`, run on all 500)
- `cram.py` – NumPy energy (hand-set or learned by pseudolikelihood) + reference search; `gibbs.c` + `cram_c.py` – the fast C focused-Gibbs search used for the final numbers (`cc -O3 -o gibbs gibbs.c -lm`)
- `gen/` – the 9 solvers Claude wrote; `*.jsonl` raw results; `summary.json` / `DATA.md` summary
API key read from `~/.config/anthropic/key`. Total spend ~$3.75.
