"""Summarise results.jsonl -> summary.json + printed table."""
import json, statistics as st
from pathlib import Path
HERE = Path(__file__).parent
R = [json.loads(l) for l in (HERE / "results.jsonl").read_text().splitlines()]
S = {"groups": {}, "total_spend": sum(r["cost"] for r in R), "n_runs": len(R),
     "api_calls": sum(r["n_rounds"] for r in R)}
for m in ["opus", "sonnet", "haiku"]:
    for a in ["panasonic_named", "panasonic_blind", "brandx"]:
        rs = sorted([r for r in R if r["model"] == m and r["arm"] == a], key=lambda r: r["rep"])
        if not rs: continue
        g = dict(n=len(rs), first_test=[r["first_test"] for r in rs], final_test=[r["final_test"] for r in rs],
                 final_train=[r["final_train"] for r in rs], rounds=[r["n_rounds"] for r in rs],
                 cracked=sum(r["final_test"] == r["n_test"] for r in rs),
                 cracked_first=sum(r["first_test"] == r["n_test"] for r in rs),
                 mean_final_pct=100 * st.mean(r["final_test"] / r["n_test"] for r in rs),
                 mean_first_pct=100 * st.mean(r["first_test"] / r["n_test"] for r in rs),
                 cost=sum(r["cost"] for r in rs), mean_cost=st.mean(r["cost"] for r in rs),
                 mean_min=st.mean(r["secs"] for r in rs) / 60)
        S["groups"][f"{m}|{a}"] = g
        print(f"{m:6} {a:16} cracked {g['cracked']}/{g['n']} (first try {g['cracked_first']}) "
              f"first {g['first_test']} final {g['final_test']} train {g['final_train']} rounds {g['rounds']} "
              f"${g['cost']:.2f} {g['mean_min']:.1f} min")
print("total spend $%.2f over %d runs, %d calls" % (S["total_spend"], len(R), S["api_calls"]))
json.dump(S, open(HERE / "summary.json", "w"), indent=1)
