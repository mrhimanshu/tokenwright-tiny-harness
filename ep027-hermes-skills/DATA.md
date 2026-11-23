# EP027 DATA (23 Nov 2026, my runs)

Setup: hermes-agent 0.19.0 (pip, MIT) driven from Python (lab/run_hermes.py), default CLI toolsets, fresh HERMES_HOME per run, Anthropic API. Task: monthly revenue report for a fictional shop from a messy CSV export + fx_rates.json (lab/gen_data.py; ground truth in lab/truth/). Gotchas: duplicate rows, refunded + test orders, 3–4 currencies, decimal commas, email case; plus one non-guessable HOUSE RULE: revenue is reported ex-VAT (prices include 20% VAT). April export drifts: semicolon-delimited + CHF.

Seed (teammate A, January, x3): terse ask → reviewer ('finance') feedback with the 6 rules → redo → Hermes's own skill review (_SKILL_REVIEW_PROMPT, run in the foreground) writes the skill. All 3 seeds: 3/4 on the first pass (missed VAT), 4/4 after one correction (7–8 API calls). Skills written: seed1 'finance-revenue-reporting' (SKILL.md says *ask whether prices include VAT, do not assume*; the hard rule is only in references/), seed2 'monthly-revenue-report' (VAT rule in SKILL.md), seed3 'monthly-revenue-report' + scripts/compute_report.py (comma-only csv.DictReader).

Arms (fresh teammate, no memory): terse_noskill = terse ask; terse_skill = terse ask + one shared skill copied into skills/ (rep k uses seed k%3+1); brief_noskill = terse ask + a 6-line written brief of the same rules. Months Feb/Mar/Apr. Score = 4 fields exact vs truth (revenue ±0.05).

## Claude Haiku 5.5 (n=6 per arm×month, 54 runs)
| arm | month | n | all 4 correct | mean tokens | API calls | tool calls | seconds | cost/run |
|---|---|---|---|---|---|---|---|---|
| terse_noskill | 2026-02 | 6 | 0 | 123,256 | 5.7 | 4.7 | 13.8 | $0.0057 |
| terse_noskill | 2026-03 | 6 | 0 | 118,390 | 5.3 | 4.5 | 12.4 | $0.0055 |
| terse_noskill | 2026-04 | 6 | 0 | 117,970 | 5.5 | 4.5 | 12.6 | $0.0056 |
| terse_noskill | all | 18 | 0 | 119,872 | 5.5 | 4.6 | 12.9 | $0.0056 |
| terse_skill | 2026-02 | 6 | 6 | 108,144 | 4.8 | 5.8 | 13.4 | $0.0053 |
| terse_skill | 2026-03 | 6 | 6 | 113,541 | 5.0 | 5.8 | 12.4 | $0.0054 |
| terse_skill | 2026-04 | 6 | 6 | 123,384 | 5.3 | 6.8 | 16.7 | $0.0060 |
| terse_skill | all | 18 | 18 | 115,023 | 5.1 | 6.2 | 14.2 | $0.0056 |
| brief_noskill | 2026-02 | 6 | 6 | 101,938 | 4.8 | 3.8 | 10.6 | $0.0048 |
| brief_noskill | 2026-03 | 6 | 6 | 105,414 | 5.0 | 4.0 | 10.3 | $0.0048 |
| brief_noskill | 2026-04 | 6 | 6 | 97,149 | 4.7 | 3.7 | 10.7 | $0.0047 |
| brief_noskill | all | 18 | 18 | 101,500 | 4.8 | 3.8 | 10.5 | $0.0048 |

Per skill (Haiku, terse_skill, all months, n=6 each):
- seed_r1: 6/6 correct, 113,613 tokens, 5.2 tool calls
- seed_r2: 6/6 correct, 104,147 tokens, 5.7 tool calls
- seed_r3: 6/6 correct, 127,309 tokens, 7.7 tool calls

## Claude Sonnet 5.5 (n=3 per arm×month, 27 runs, teammates use the Haiku-written skills)
| arm | month | n | all 4 correct | mean tokens | API calls | tool calls | seconds | cost/run |
|---|---|---|---|---|---|---|---|---|
| terse_noskill | 2026-02 | 3 | 0 | 103,893 | 5.0 | 4.0 | 14.6 | $0.0909 |
| terse_noskill | 2026-03 | 3 | 0 | 105,060 | 5.0 | 4.0 | 16.7 | $0.0927 |
| terse_noskill | 2026-04 | 3 | 0 | 120,125 | 5.7 | 4.7 | 15.8 | $0.1012 |
| terse_noskill | all | 9 | 0 | 109,693 | 5.2 | 4.2 | 15.7 | $0.0949 |
| terse_skill | 2026-02 | 3 | 3 | 119,250 | 5.3 | 6.3 | 17.6 | $0.1005 |
| terse_skill | 2026-03 | 3 | 2 | 120,419 | 5.3 | 6.3 | 16.5 | $0.1004 |
| terse_skill | 2026-04 | 3 | 3 | 152,514 | 6.7 | 7.7 | 19.6 | $0.1145 |
| terse_skill | all | 9 | 8 | 130,728 | 5.8 | 6.8 | 17.9 | $0.1051 |
| brief_noskill | 2026-02 | 3 | 3 | 115,890 | 5.7 | 4.7 | 15.1 | $0.0915 |
| brief_noskill | 2026-03 | 3 | 3 | 92,983 | 4.7 | 3.7 | 12.0 | $0.0801 |
| brief_noskill | 2026-04 | 3 | 3 | 86,928 | 4.3 | 3.3 | 12.5 | $0.0805 |
| brief_noskill | all | 9 | 9 | 98,601 | 4.9 | 3.9 | 13.2 | $0.0840 |

## Key findings
- No skill: 0/18 (Haiku) and 0/9 (Sonnet). Every run got orders, customers and top product right but reported revenue incl. VAT (Feb 6,259.72 vs truth 5,216.43, +20%). The guessable rules (dups, refunds, test orders, fx, decimal commas, email case) were found by every run without help.
- Shared skill: 18/18 (Haiku). Sonnet: 9/9 correct values, 1 run saved answer.json to data/report/ instead of report/ (graded 0) → 8/9.
- Written brief: 18/18 and 9/9, and the cheapest arm both times.
- Tokens (Haiku, mean/run): no skill 119,872 · skill 115,023 (−4%) · brief 101,500 (−15% vs no skill, −12% vs skill). Sonnet: 109,693 · 130,728 (+19%) · 98,601. Reading the skill costs 1–2 extra tool calls (skill_view + reference files).
- Script skill (seed3, Haiku): Feb 88,935 / 88,561 tokens (it just ran the script): cheapest skill runs, 13% under the brief's Feb mean (101,938); only 4 brief runs were lower (83–85k). April (semicolons): 194,816 / 139,914 tokens, 12 / 9 tool calls: the agent saw the semicolon, patched scripts/compute_report.py to sniff the delimiter and patched SKILL.md ('Exports may be semicolon-delimited (April 2026 was…)'), then got 4/4. Other skills in April averaged 101,393 tokens.
- Hedged skill (seed1): on Sonnet, 2 of 3 runs called clarify ('I asked whether to remove VAT and got no answer, so I applied the Finance rule from the January report'). A skill that says 'ask' made the agent doubt the rule it carried.
- Cost: Haiku ≈ half a cent per run; Sonnet ≈ 9–11 cents. Whole lab ≈ $3 (list prices; cache read 0.1×, cache write 1.25× input).
- Not tested: Hermes Enterprise's Teams publish/review UI (simulated by copying the skill folder); skill chains over many months; skills from other people's styles; Hermes's curator.
