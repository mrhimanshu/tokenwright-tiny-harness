"""EP015: summarise results.jsonl (Claude thinking), code.jsonl (Claude-written solvers), cram_results.jsonl (rebuilt CRAM)."""
import json, statistics as st
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
think = [json.loads(l) for l in open(HERE / "results.jsonl")]
code = [json.loads(l) for l in open(HERE / "code.jsonl")]
cram = [json.loads(l) for l in open(HERE / "cram_results.jsonl")]
out = {}
by = defaultdict(list)
for r in think:
    by[r["model"]].append(r)
for m, rs in by.items():
    rs.sort(key=lambda r: r["puzzle"])
    out[m] = dict(n=len(rs), correct=sum(r["correct"] for r in rs), ran_out=sum(r["stop"] == "max_tokens" for r in rs),
                  wrong_answer=sum((not r["correct"]) and r["stop"] != "max_tokens" for r in rs),
                  cost_total=round(sum(r["cost"] for r in rs), 3), cost_per_puzzle=round(sum(r["cost"] for r in rs) / len(rs), 3),
                  cost_per_solved=round(sum(r["cost"] for r in rs) / max(1, sum(r["correct"] for r in rs)), 3),
                  median_secs=st.median(r["secs"] for r in rs), max_secs=max(r["secs"] for r in rs),
                  median_out_tok=st.median(r["out_tok"] for r in rs),
                  per_puzzle=[(r["puzzle"], r["correct"], r["stop"], r["out_tok"], r["secs"], r["cost"]) for r in rs])
cb = defaultdict(list)
for r in code:
    cb[r["model"]].append(r)
out["code"] = {m: dict(n=len(rs), all_500=sum(r["n_ok"] == 500 for r in rs), solved=[r["n_ok"] for r in rs],
                       median_ms=[r["median_ms"] for r in rs], total_s=[r["total_s"] for r in rs], cost=[r["cost"] for r in rs],
                       lines=[r["code_lines"] for r in rs], write_secs=[r["secs"] for r in rs]) for m, rs in cb.items()}
final = [r for r in cram if r["ntest"] == 500]
out["cram"] = [{k: v for k, v in r.items() if k != "per_puzzle"} for r in final]
# CRAM time on the exact puzzles Claude saw (learned seed 0)
learn0 = next(r for r in final if r["energy"] == "learn" and r["seed"] == 0)
hand = next(r for r in final if r["energy"] == "hand")
out["cram_on_claude_puzzles"] = [(p["i"], p["ok"], p["ms"], h["ms"]) for p, h in zip(learn0["per_puzzle"][:10], hand["per_puzzle"][:10])]
out["spend_total"] = round(sum(r["cost"] for r in think) + sum(r["cost"] for r in code), 2)
json.dump(out, open(HERE / "summary.json", "w"), indent=1)
print(json.dumps(out, indent=1))
