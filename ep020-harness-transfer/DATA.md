# EP020 DATA (my runs, 19 Nov 2026, 22:00–22:30 UTC)

Raw: lab/v2_results.jsonl (main), lab/rev_results.jsonl (reverse), lab/results.jsonl (v1 pilot, easier rules), lab/*runs/run*.json (harnesses, memory, trajectories), lab/summary.json.
Task: 100 synthetic support tickets (lab/tasks_v2.json, seed 1), 11 labels, 9 hidden house rules computed in code. 40 evolve (optimizer sees failures) / 60 held-out (never shown to the optimizer). Seed harness = 3 lines: role, label names, "reply with one label".
Optimizer (proposer) = Claude Sonnet 5.5 effort medium, 2 candidates per round, keep the best if it beats the current harness on the evolve set. Policies at low effort/thinking. 1 rollout per ticket.

## 1. Tune on Claude Haiku 5.5, then move to Gemini (paper's direction: Claude → Gemini). 3 independent runs.
| | run 0 | run 1 | run 2 | mean |
|---|---|---|---|---|
| Haiku, seed harness (held-out) | 63.3 | 63.3 | 63.3 | 63.3 |
| Haiku, after 4 rounds | 91.7 | 86.7 | 88.3 | 88.9 |
| Gemini 3.8 Flash, seed | 71.7 | 71.7 | 75.0 | 72.8 |
| Gemini 3.8 Flash, Haiku-tuned harness | 91.7 | 90.0 | 86.7 | **89.4 (+16.7)** |
| Gemini 4 Neon, seed | 70.0 | 68.3 | 70.0 | 69.4 |
| Gemini 4 Neon, Haiku-tuned harness | 88.3 | 90.0 | 86.7 | **88.3 (+18.9)** |

## 2. Reverse: tune on Gemini 3.8 Flash, move to Claude. 3 runs.
| | run 0 | run 1 | run 2 | mean |
|---|---|---|---|---|
| Flash seed → tuned (held-out) | 71.7 → 86.7 | 73.3 → 85.0 | 70.0 → 83.3 | 71.7 → 85.0 |
| Claude Haiku 5.5 seed → Flash-tuned | 63.3 → 83.3 | 65.0 → 76.7 | 63.3 → 80.0 | 63.9 → **80.0 (+16.1)** |
| Claude Sonnet 5.5 seed → Flash-tuned | 65.0 → 83.3 | 65.0 → 83.3 | 66.7 → 83.3 | 65.6 → **83.3 (+17.8)** |

=> 12 of 12 cross-model transfers scored HIGHER than the untouched seed (v1 pilot: 6 of 6 more, +10 to +15). The paper's "tuned harness starts below the seed" (68.41 vs 73.89) did not show up here.

## 3. Continue tuning on Gemini Flash: harness-only vs SIM memory (3 rounds each, same start)
| run | start | harness-only final | SIM final | edits kept (harness / SIM) |
|---|---|---|---|---|
| 0 | 91.7 | 91.7 | 91.7 | 0 / 0 |
| 1 | 91.7 | 98.3 | 98.3 | 1 / 2 |
| 2 | 86.7 | 86.7 | 86.7 | 0 / 0 |
=> a tie in 3 of 3. Reason: the transferred harness already scored 97.5–100% on the 40 evolve tickets, so there were almost no failures left to learn from. This test can't confirm or refute the memory claim (the paper: 10 rounds × 5 candidates × 5 rollouts, ~4 h per coding round, mean +2.36 over 10 runs).

## 4. What the tuned harness learned (and didn't)
- Each run grew the 3-line seed into a ~1,800–2,000-character rule list (rules in order, refund thresholds, digital vs physical windows, data loss = bug_critical, missing digital download = account).
- Blind spot carried everywhere: the 40 evolve tickets had only 3 Enterprise tickets (2 cancel charges, 1 feature request), so all 3 runs wrote "Enterprise complaint, billing problem or feature request → priority". On held-out, Enterprise refunds and bugs were routed as normal refunds/bugs. Same mistakes on Gemini Flash and Neon (e.g. "Plan: Enterprise … refund $15" → refund_review; gold priority).
- Two rules were never learned in any run: Free-plan refund limit $20 (no example in the evolve set) and Team-plan data loss → priority (0 in evolve, 1 in held-out).
- Rejected candidate (run 0, round 2): the optimizer proposed that "unusually formal or letter-style wording" sends a refund to review, from one ticket that started "To whom it may concern" (real cause: digital + 28 days). Scored +0, not kept.

## 5. Noise
- Same harness, same 60 held-out tickets, Claude Haiku 5.5 at low effort, scored 3 times: 81.7, 93.3, 85.0 (11.7-point swing). Gemini 3.8 Flash repeats moved ≤ 2.5 points.
- So a single run can't see a 2-point effect; the paper's 2.36 mean needed 10 paired runs (p = 0.003).

## 6. Cost per 1,000 tickets (measured tokens × list price)
| model | avg in/out tokens | $ per 1,000 tickets | held-out with tuned harness |
|---|---|---|---|
| Claude Haiku 5.5 | 583 / 17 | $0.07 | 88.9 (own tune) / 80.0 (Flash's tune) |
| Gemini 3.8 Flash | 437 / 90 | $0.67 | 89.4 (Haiku's tune) |
| Claude Sonnet 5.5 | 402 / 13 | $0.93 | 83.3 (Flash's tune) |
| Gemini 4 Neon (thinking low) | 315 / 208 | $4.06 | 88.3 (Haiku's tune) |
- Prompt mattered more than model: seed → tuned = +16 to +19 points on every model; Flash → Neon with the same prompt = −1 point at 6× the price.

## Spend
- Total $10.36 (v1 pilot $3.65, main $4.83, reverse $1.88), 12,774 API calls, 0 API errors, 0 unparsable answers. Over the ~$5 guide because of the pilot + reverse direction.
