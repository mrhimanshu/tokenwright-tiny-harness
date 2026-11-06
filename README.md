# tokenwright-tiny-harness

A complete coding-agent harness in about 70 lines of Python: a loop, five tools (`list_files`, `read_file`, `write_file`, `edit_file`, `run_tests`), the conversation, and one prompt-cache marker. Built for the Tokenwright video **"I built my own Claude Code in 70 lines, and raced it"** (EP005).

## The race (6 Nov 2026, Claude Haiku 5.5, 5 tasks x 5 runs)

| harness | passed | tokens / task | $ / task | turns | seconds |
|---|---|---|---|---|---|
| Claude Code 2.1.318 | 25/25 | 150,441 | $0.00418 | 9.7 | 13.5 |
| tiny harness v2 (this repo) | 25/25 | 27,716 | $0.00166 | 4.5 | 6.4 |
| tiny harness v1 (no edit tool) | 12/15 | 17,075 | $0.00192 | 4.0 | 8.0 |
| tiny harness v2, caching off | 15/15 | 23,381 | $0.00277 | 4.4 | 6.5 |

- v1 failed the shop task every time: the bug is in an 820-line file, `write_file` has to resend all of it, and the reply hits the 4,000-token output cap. Adding `edit_file` fixed it.
- 89% of Claude Code's tokens are cache reads ($0.01 per million on Haiku 5.5), so 5.4x the tokens is ~2.5x the cost.
- Claude Sonnet 5.5 (2 runs x 5 tasks): Claude Code $0.0428 / task vs $0.0268 (both 10/10).
- Full numbers: `DATA.md`, raw runs: `results.jsonl`. Small tasks only: Claude Code also brings permissions, planning, sub agents and compaction that matter on big repos.

## Run it

```bash
pip install anthropic
export ANTHROPIC_API_KEY=...        # your own key
cd tasks/t3_page && python3 ../../tiny_harness.py "Fix the bugs in pager/paginate.py so all the tests pass."
```

`race.py` reproduces the race (it expects Claude Code at `~/.local/bin/claude` and reads the key from `~/.config/anthropic/key`).

## Further reading
- FrontierHarness Eval: https://frontierharness.org/
- What Does a Harness Buy? Tokens, Mostly (arXiv 2610.04433): https://arxiv.org/abs/2610.04433

Tokenwright: AI news, tested in code. https://www.youtube.com/@Tokenwright
MIT licence.
