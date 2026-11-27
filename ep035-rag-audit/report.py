#!/usr/bin/env python3
"""Final numbers for DATA.md: per (model,cond) over all runs; audit labels weighted per wrong answer."""
import json, statistics as st, collections
from pathlib import Path
R = Path(__file__).parent / "results"
G = [json.loads(l) for l in (R / "graded.jsonl").read_text().splitlines() if json.loads(l)["cond"] != "k70"]
A = {(a["model"], a["cond"], a["id"], a["answer"]): a["label"] for a in map(json.loads, (R / "audit.jsonl").read_text().splitlines())}
out = {}
for key in sorted({(g["model"], g["cond"]) for g in G}):
    rs = [g for g in G if (g["model"], g["cond"]) == key]
    runs = sorted({g["run"] for g in rs})
    accs = [sum(g["correct"] for g in rs if g["run"] == r) / sum(1 for g in rs if g["run"] == r) for r in runs]
    wrong = [g for g in rs if not g["correct"]]
    lab = collections.Counter(A.get((g["model"], g["cond"], g["id"], g["answer"]), "unaudited") for g in wrong)
    lab_reas = collections.Counter(A.get((g["model"], g["cond"], g["id"], g["answer"]), "unaudited") for g in wrong if g["err"] == "reasoning")
    d = dict(n_per_run=len(rs) // len(runs), runs=len(runs), acc_runs=[round(a, 4) for a in accs], acc_mean=round(st.mean(accs), 4),
             wrong_total=len(wrong), reasoning_share_paper=round(sum(g["err"] == "reasoning" for g in wrong) / len(wrong), 3),
             retrieval_share_paper=round(sum(g["err"] == "retrieval" for g in wrong) / len(wrong), 3),
             abstain_share_of_wrong=round(sum(g["abstain"] for g in wrong) / len(wrong), 3),
             gold_in_ctx=round(st.mean(g["gold_in_ctx"] for g in rs), 4), both_gold_paras=round(st.mean(g["both_gold_paras"] for g in rs), 4),
             avg_input_tokens=round(st.mean(g["input_tokens"] for g in rs)), cost_usd=round(sum(g["cost_usd"] for g in rs), 3),
             audit_all_wrong=dict(lab), audit_paper_reasoning=dict(lab_reas))
    out[f"{key[0].replace('claude-','')}|{key[1]}"] = d
    print(key, json.dumps(d))
spent = sum(json.loads(l)["cost_usd"] for f in ["qa.jsonl", "qa_cap200_aborted.jsonl", "judge.jsonl", "audit.jsonl"] for l in (R / f).read_text().splitlines())
out["total_api_usd"] = round(spent, 2)
print("TOTAL $", round(spent, 2))
(R.parent / "summary.json").write_text(json.dumps(out, indent=1))
