# ep014-context-compaction

Does a Claude coding agent need its whole history? NVIDIA's paper "You don't need long context" (arXiv 2611.05306) says no.
This lab runs the same 5-project coding job with three memory strategies and prices every run with prompt caching.

- `compact_lab.py`: the harness (full history / compaction at 16K tokens / one action per context), the cost maths, the runner.
- `repo/`: the job (five small Python projects, one `run_tests.py` for all of them).
- `results.jsonl`: all 24 runs (Sonnet 5.5 ×3, Haiku 5.5 ×5 per strategy), with per-request context sizes and token usage.
- `../DATA.md`: the summary.

Run: `python compact_lab.py --models claude-haiku-5-5 --modes full,compact,single --reps 3` (reads the key from ~/.config/anthropic/key).

Headline (15 Nov 2026): every run finished every job; on Sonnet 5.5 compaction cost +15% and one-action-per-context 2.8× more than
full history with prompt caching, because forgetting throws away the cached prefix.
