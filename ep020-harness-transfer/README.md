# EP020: does a self-improved prompt survive a model switch?

Small replication of Google's "Self-Improvement Memory Enables Continual Recursive Self-Improvement" (arXiv 2611.18856) on a
ticket-routing task with hidden house rules. Video: Tokenwright, "Google Says Tuned Prompts Break on New Models. I Tested It".

- `tasks.py` builds the tickets (labels computed in code). `tasks_v2.json` = main set (40 evolve / 60 held-out), `tasks.json` = easier pilot.
- `sim_lab.py <run>` = source tuning on one model (proposer Claude Sonnet 5.5), transfer snapshot on two other models, then
  harness-only vs SIM-memory continuation. Env: `TASKS`, `OUT`, `SRC`, `TGT`, `EXTRA`, `SKIP_TARGET`.
- Keys are read from `~/.config/anthropic/key` and `~/.config/gemini/key`.
- `v2_runs/` main (Claude Haiku → Gemini Flash / Neon), `rev_runs/` reverse (Gemini Flash → Claude Haiku / Sonnet), `runs/` pilot.
  Each run json holds the final harness, the memory entries and the score trajectory. `*results.jsonl` = every model call.
- `summarize.py` → `summary.json`. Results: DATA.md.

Headline (mean of 3 runs, held-out): 12 of 12 cross-model transfers beat the untuned seed (+16 to +19 on average);
memory vs no memory tied 3 of 3 (nothing left to fix). Total spend ≈ $10.
