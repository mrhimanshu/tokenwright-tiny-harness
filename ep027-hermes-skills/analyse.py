"""Summarise /data/renders/ep027/runs/*/result.json -> summary.json + printed table."""
import json, statistics as st, sys
from pathlib import Path
from collections import defaultdict

RUNS = Path("/data/renders/ep027/runs")
LAB = Path(__file__).resolve().parent
suffix = sys.argv[1] if len(sys.argv) > 1 else ""   # "" = haiku, "_sonnet" etc.

rows = []
for p in sorted(RUNS.glob("*/result.json")):
    d = json.loads(p.read_text())
    if d["arm"] == "seed":
        continue
    if not d["run_id"].endswith(suffix) if suffix else any(d["run_id"].endswith(s) for s in ("_sonnet", "_opus")):
        continue
    u = d["usage"]
    tokens = u["input"] + u["output"] + u["cache_read"] + u["cache_write"]
    seed = None
    if d.get("skill_src"):
        seed = Path(d["skill_src"]).parent.parent.name
    # did the agent load the skill / run the skill script?
    tr = json.loads((p.parent / "transcript.json").read_text())
    txt = json.dumps(tr)
    rows.append({"run": d["run_id"], "arm": d["arm"], "month": d["month"], "seed": seed, "score": d["grade"]["score"],
                 "all": d["grade"]["all_correct"], "fields": d["grade"]["fields_ok"], "answer": d["grade"]["answer"],
                 "tokens": tokens, "output": u["output"], "api_calls": u["api_calls"], "tool_calls": u["tool_calls"],
                 "secs": d["task_seconds"], "cost": d["cost_usd_task"],
                 "skill_viewed": "skill_view" in txt, "ran_skill_script": "compute_report.py" in txt,
                 "asked_clarify": '"clarify"' in txt})

def agg(rs):
    if not rs:
        return None
    m = lambda k: round(st.mean(r[k] for r in rs), 4)
    md = lambda k: st.median(r[k] for r in rs)
    return {"n": len(rs), "all_correct": sum(r["all"] for r in rs), "rate": round(sum(r["all"] for r in rs) / len(rs), 3),
            "revenue_ok": sum(r["fields"]["net_revenue_eur"] for r in rs),
            "mean_tokens": m("tokens"), "median_tokens": md("tokens"), "mean_output": m("output"),
            "mean_api_calls": m("api_calls"), "mean_tool_calls": m("tool_calls"), "mean_secs": m("secs"),
            "mean_cost": m("cost"), "skill_viewed": sum(r["skill_viewed"] for r in rs),
            "ran_skill_script": sum(r["ran_skill_script"] for r in rs)}

S = {}
groups = defaultdict(list)
for r in rows:
    groups[(r["arm"], r["month"])].append(r)
    groups[(r["arm"], "all")].append(r)
    groups[(r["arm"], "feb+mar")].append(r) if r["month"] != "2026-04" else None
    if r["seed"]:
        groups[(r["arm"] + "|" + r["seed"], "all")].append(r)
        groups[(r["arm"] + "|" + r["seed"], r["month"])].append(r)
for k, rs in sorted(groups.items()):
    S[f"{k[0]}|{k[1]}"] = agg(rs)
    a = S[f"{k[0]}|{k[1]}"]
    print(f"{k[0]:28s} {k[1]:8s} n={a['n']:2d} correct={a['all_correct']:2d} rev_ok={a['revenue_ok']:2d} "
          f"tok={a['mean_tokens']:>9.0f} api={a['mean_api_calls']:.1f} tools={a['mean_tool_calls']:.1f} "
          f"secs={a['mean_secs']:.1f} cost=${a['mean_cost']:.4f} viewed={a['skill_viewed']} script={a['ran_skill_script']}")
out = LAB / f"summary{suffix}.json"
out.write_text(json.dumps({"groups": S, "rows": rows}, indent=1))
print("wrote", out, len(rows), "runs")
