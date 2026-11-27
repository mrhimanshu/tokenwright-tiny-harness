#!/usr/bin/env python3
"""Summarise results/graded.jsonl per (model, cond): accuracy, error split (paper rule + strict rule), cost."""
import json, statistics as st
from collections import defaultdict
from pathlib import Path

R = Path(__file__).parent / "results"
rows = [json.loads(l) for l in (R / "graded.jsonl").read_text().splitlines()]
g = defaultdict(list)
for r in rows:
    g[(r["model"], r["cond"], r["run"])].append(r)

summary = []
for (m, c, run), rs in sorted(g.items()):
    n = len(rs)
    wrong = [r for r in rs if not r["correct"]]
    reas = [r for r in wrong if r["err"] == "reasoning"]
    strict_reas = [r for r in wrong if r["both_gold_paras"]]
    s = dict(model=m.replace("claude-", ""), cond=c, run=run, n=n,
             acc=round(sum(r["correct"] for r in rs) / n, 4),
             gold_in_ctx=round(sum(r["gold_in_ctx"] for r in rs) / n, 4),
             both_paras=round(sum(r["both_gold_paras"] for r in rs) / n, 4),
             wrong=len(wrong), reasoning_share_paper=round(len(reas) / len(wrong), 3) if wrong else None,
             reasoning_share_strict=round(len(strict_reas) / len(wrong), 3) if wrong else None,
             abstain=sum(r["abstain"] for r in rs), abstain_with_both_paras=sum(r["abstain"] and r["both_gold_paras"] for r in rs),
             judge_rescued=sum(r["how"] == "judge" and r["correct"] for r in rs),
             avg_in_tokens=round(st.mean(r["input_tokens"] for r in rs)),
             cost=round(sum(r["cost_usd"] for r in rs), 3))
    summary.append(s)
    print(s)
(R / "summary_runs.json").write_text(json.dumps(summary, indent=1))
