# EP014 DATA: does a Claude coding agent need its whole history? (my runs, 15 Nov 2026, 22:27–22:36 UTC)

Code: lab/compact_lab.py · task repo: lab/repo · raw: lab/results.jsonl (24 runs) · smoke: lab/smoke.jsonl (3 runs, not counted)
Spend: about $2.03 in total (Haiku $0.20, Sonnet $1.80, smoke $0.03).

## Setup
- One job, five small projects in one repo (the five EP005 tasks): fix bugs in shop/ (one file, inventory.py, is 52 KB ≈ 28k tokens),
  implement slugify, fix the pager, add a --json flag to a CLI, rename calc_total → order_total. run_tests runs all five suites.
- Tools: list_files, read_file, write_file, edit_file, run_tests. Up to 60 model calls. Scored by running each project's tests afterwards.
- Three memory strategies (the paper's three):
  - FULL: keep every message; prompt caching on (one cache marker on the newest message, like Claude Code).
  - COMPACT: once a request's context passes 16,000 tokens (the paper's threshold), the agent writes a handoff with the paper's fields
    (objective, facts, relevant files + results, changes made, failed approaches, remaining work, next action), then restarts with
    only the original task + that handoff. Caching stays on.
  - SINGLE: one action per context. Each call sees only the task, its own state note from last turn, and the result of its last action.
    Parallel tool calls disabled. The prompt changes every call, so nothing can be cached.
- Models: Claude Haiku 5.5 (n=5 per strategy), Claude Sonnet 5.5 (n=3 per strategy), API defaults.
- Prices ($/MTok in/out): Haiku 5.5 0.10/0.50, Sonnet 5.5 2/10; cache write 1.25×, cache read 0.1× input.

## Results
| model | strategy | runs | finished all 5 jobs | $/run | $/run if no caching | calls | median context per call | peak context | output tokens | secs |
|---|---|---|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | full | 3 | 3/3 | **0.1199** | 0.1652 | 4 | 16,810 | 34,237 | 2,773 | 18.7 |
| Sonnet 5.5 | compact | 3 | 3/3 | **0.1375** (+15%) | 0.1850 | 6 (incl. 1 handoff) | 1,934 | 34,332 | 3,918 | 30.8 |
| Sonnet 5.5 | single | 3 | 3/3 | **0.3408** (2.84×) | 0.3408 | 34 | 1,770 | 29,148 | 16,462 | 152.7 |
| Haiku 5.5 | full | 5 | 5/5 | **0.00628** | 0.01252 | 5 | 32,653 | 35,507 | 3,894 | 19.7 |
| Haiku 5.5 | compact | 5 | 5/5 | **0.00654** (+4%) | 0.01049 (−16% vs full) | 6.4 | 2,196 | 35,470 | 5,773 | 27.8 |
| Haiku 5.5 | single | 5 | 5/5 | **0.02768** (4.4×) | 0.02768 | 48.6 | 1,725 | 29,102 | 28,791 | 140.7 |

## The story in numbers
- Accuracy: **24 of 24 runs finished all five jobs (120/120)** with every strategy. NVIDIA's accuracy claim held on this job.
- Even "single" (forget everything after every action) finished everything: Sonnet in 31–38 calls, Haiku in 29–60.
  Two Haiku single runs never said "done" and hit my 60-call cap; their tests were green when the cap stopped them.
- Cost went the other way. Sonnet 5.5: compact **+15%** ($0.120 → $0.138), single **2.84×** ($0.341). Haiku 5.5: compact +4%, single 4.4×.
- Where compaction's extra cost comes from (Sonnet): the handoff call itself, $0.0221 per run (it re-reads ~34k tokens and writes a
  briefing at the output price), plus a fresh cache write for the new prompt. That is more than the whole difference ($0.0176).
- Where single's cost comes from: 34 calls instead of 4, and 6× the output tokens (16,462 vs 2,773; it rewrites its state note every
  turn, and output costs 5× input). No cache can help, because every prompt is different.
- Context did shrink: median context per call Sonnet 16,810 → 1,934 (compact) → 1,770 (single), about 9× smaller.
  Peak didn't: one read of the 52 KB inventory.py is ~28k tokens by itself.
- Caching is the reason: FULL re-reads its history at 10% of the input price. Without caching, Haiku's compaction would have SAVED 16%
  ($0.0125 → $0.0105); with caching on, the saving disappears (+4%). Sonnet full without caching would be $0.165 (caching saves 27%).
- Speed: compact ~1.5× slower (30.8 s vs 18.7 s Sonnet); single ~8× slower (152.7 s vs 18.7 s).
- Same direction as the paper's own caveat: GPT-5.6 Sol on SWE-bench Verified, $167.68 → $203.12 at standard API prices (+21%).

## Caveats
- One job, five small Python projects, 4–6 steps for the full-history agent. SWE-bench-style tasks run dozens of steps, where the
  full history keeps growing and compaction has more room to win. This is a spot check of the bill, not a benchmark.
- Haiku's cheaper reps (full rep 4, compact reps 3–4) got cache hits from other runs' identical prefixes; that is how the real API
  behaves, so I kept them.
- I didn't run Opus 4.5 (the paper's model) to stay under budget; the paper's accuracy numbers are theirs.
