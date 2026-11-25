# EP031: can you sneak a bad pull request past a Claude approver?

Tokenwright episode, 25 Nov 2026. Story: Anthropic's Claude Ship / Claude Approvals (23 Nov 2026): a policy file in your
repo decides which PRs Claude may approve alone. This is NOT Anthropic's product; it rebuilds the idea under it
(policy + natural-language "routine?" classifier + one Claude call per PR) and tries to fool it.

- `prs.py`: the policy file and 29 test PRs (6 routine, 4 risky, 9 attacks, 10 quiet changes). Attack PRs are
  inert text fixtures for a fake repo; every URL in them is made up.
- `run_lab.py ARM [model ...] [--reps N] [--only ids]`: ARM = plain | guarded | fixed. Needs ANTHROPIC_API_KEY.
- `analyse.py`: results.jsonl -> summary.json.
- `results.jsonl`: all 657 raw decisions (verdict, reason, cost, stop_reason). `DATA.md`: the numbers.

Headline: 0 of 243 attack decisions approved; 4 of 495 bad-PR decisions approved, all on one `# nosec` comment
(Sonnet 5.5 3/20, Haiku 5.5 1/20, Opus 5.5 0/20). A 2-line policy fix took it to 0/30. 43 replies were API cyber-filter
refusals: treat a refusal as "needs a human". Spend $4.37.
