# EP005 data: same model, same 5 tasks, different harness (runs on 6 Nov 2026, Claude Code 2.1.318)

Prices fitted from Claude Code's costUSD ($/MTok in, out, cache read, cache write): {'claude-haiku-5-5': (np.float64(0.1), np.float64(0.5), np.float64(0.01), np.float64(0.125)), 'claude-sonnet-5-5': (np.float64(2.0), np.float64(10.0), np.float64(0.1), np.float64(2.5))}

| model | harness | runs | passed | avg tokens / task | avg $ / task | avg turns | avg secs | first call (tiny) |
|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | claude_code | 25 | 25/25 | 150,441 | $0.00418 | 9.7 | 13.5 |  |
| claude-haiku-5-5 | tiny | 15 | 12/15 | 17,075 | $0.00192 | 4.0 | 8.0 | 613 |
| claude-haiku-5-5 | tiny2 | 25 | 25/25 | 27,716 | $0.00166 | 4.5 | 6.4 | 726 |
| claude-haiku-5-5 | tiny2_nocache | 15 | 15/15 | 23,381 | $0.00277 | 4.4 | 6.5 | 726 |
| claude-haiku-5-5 | tiny_nocache | 15 | 12/15 | 15,008 | $0.00217 | 4.1 | 7.7 | 613 |
| claude-sonnet-5-5 | claude_code | 10 | 10/10 | 101,772 | $0.04279 | 7.6 | 14.0 |  |
| claude-sonnet-5-5 | tiny2 | 10 | 10/10 | 24,452 | $0.02676 | 4.6 | 9.4 | 726 |

## Per task (avg tokens, pass)

| model | harness | t1_shop | t2_slug | t3_page | t4_cli | t5_rename |
|---|---|---|---|---|---|---|
| claude-haiku-5-5 | claude_code | 297,429 (5/5) | 84,873 (5/5) | 105,693 (5/5) | 106,512 (5/5) | 157,699 (5/5) |
| claude-haiku-5-5 | tiny | 57,560 (0/3) | 6,642 (3/3) | 7,965 (3/3) | 5,576 (3/3) | 7,632 (3/3) |
| claude-haiku-5-5 | tiny2 | 107,591 (5/5) | 6,494 (5/5) | 7,767 (5/5) | 7,085 (5/5) | 9,643 (5/5) |
| claude-haiku-5-5 | tiny2_nocache | 84,904 (3/3) | 6,508 (3/3) | 8,724 (3/3) | 7,601 (3/3) | 9,166 (3/3) |
| claude-haiku-5-5 | tiny_nocache | 46,119 (0/3) | 6,201 (3/3) | 7,384 (3/3) | 6,266 (3/3) | 9,070 (3/3) |
| claude-sonnet-5-5 | claude_code | 142,154 (2/2) | 92,396 (2/2) | 73,390 (2/2) | 72,093 (2/2) | 128,827 (2/2) |
| claude-sonnet-5-5 | tiny2 | 93,357 (2/2) | 5,954 (2/2) | 5,194 (2/2) | 9,146 (2/2) | 8,607 (2/2) |

## The story in numbers (Claude Haiku 5.5, 5 tasks × 5 runs unless noted)
- Claude Code: 25/25 passed · 150,441 tokens per task · $0.00418 per task · 9.7 turns · 13.5 s.
- Tiny harness v2 (5 tools, ~70 lines): 25/25 · 27,716 tokens · $0.00166 · 4.5 turns · 6.4 s → **5.4× fewer tokens, 2.5× cheaper, 2.1× faster**.
- Tiny harness v1 (4 tools, no edit tool): 12/15. Failed t1_shop 3/3: the bug is in an 820-line file; write_file must resend the whole file, so the reply hits the 4,000-token output cap and is cut off. Adding one `edit_file` tool (send only the changed lines) fixed it: 5/5.
- First call: tiny harness 726 tokens (v1: 613); Claude Code ≈17,721 tokens just to reply "OK" (EP003, same version 2.1.318).
- 89% of Claude Code's tokens are cache reads (134,311 of 150,441 per task), billed at $0.01/MTok, which is why 5.4× the tokens is "only" 2.5× the cost.
- Caching off (tiny2_nocache): $0.00277 vs $0.00166 per task → prompt caching cut the tiny harness's bill by 40%.
- Claude Sonnet 5.5 (2 runs × 5 tasks): Claude Code 10/10, 101,772 tokens, $0.0428 per task; tiny v2 10/10, 24,452 tokens, $0.0268 → 4.2× tokens, 1.6× cost.
- Per 1,000 tasks: Haiku $4.18 vs $1.66; Sonnet $42.79 vs $26.76.
- 115 runs in total, under $1 of API spend.
- Caveat: 5 small Python tasks. Claude Code also brings permissions, subagents, compaction, planning, and safer edits that matter on big real repos.
