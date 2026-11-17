# EP016: KL / JSD divergence bugs when two distributions are nearly equal (PyTorch, SciPy, Claude-written code)

Video: Tokenwright, "Claude Wrote My KL Loss 15 Times. All 15 Had the Bug" (18 Nov 2026).
Paper: Brandon Amos, "On numerical issues of divergences between nearly equal distributions", arXiv 2611.18511 (13 Nov 2026).

- `kl_fixed.py` – **the fix in PyTorch**: `kl_fixed(z, z_ref)` = KL(softmax(z_ref) ‖ softmax(z)), accurate in float32 near equality (paper reformulations 1 + 2, with the paper's closeness guard). `python kl_fixed.py` runs a demo.
- `audit.py` – lab 1: textbook / `F.kl_div` (log and prob target) / `torch.distributions` / bf16 / SciPy `entropy` + `jensenshannon` vs an mpmath reference (40–80 digits) on the same float32 logits; toy case + 32,000-token vocab, 3 seeds → `audit.jsonl`
- `drift.py` – lab 2: distillation with the student starting as an exact copy of the teacher (Adam, 300 steps, 3 seeds) → `drift.jsonl`
- `claude_kl.py` – lab 3: Claude Haiku / Sonnet / Opus 5.5 write `kl_from_logits` (plain vs warned prompt, n = 5 each), then each file is tested → `claude_gen.jsonl`, `claude_eval.jsonl`, code in `gen/`
- `summarize.py` → `summary.json`; `DATA.md` = the numbers used in the video
Requires torch, scipy, mpmath, numpy (+ anthropic for lab 3; key read from `~/.config/anthropic/key`). Total API spend $0.93. Run from the folder above `lab/` paths as written, or adjust the output paths.
