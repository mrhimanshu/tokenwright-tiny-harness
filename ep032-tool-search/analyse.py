import json, statistics as st
from collections import defaultdict, Counter
from pathlib import Path
H = Path(__file__).parent
R = [json.loads(l) for l in open(H / "results.jsonl")]
S = {"single": {}, "sessions": {}, "spend": 0}
print(f'{"cell":14} {"n":>4} {"acc":>6} {"ctx tok":>8} {"$/task real":>11} {"$/task nocache":>14} {"secs":>5} {"srch":>4}')
for m in ["opus", "sonnet", "haiku"]:
    for a in ["all", "bm25", "regex"]:
        rs = [r for r in R if r["model"] == m and r["arm"] == a]
        if not rs: continue
        ctx = st.mean(r["inp"] + r["cw"] + r["cr"] for r in rs)
        c = dict(n=len(rs), ok=sum(r["ok"] for r in rs), acc=round(sum(r["ok"] for r in rs) / len(rs), 3),
                 ctx=round(ctx), cost=st.mean(r["cost"] for r in rs), cost_nocache=st.mean(r["cost_nocache"] for r in rs),
                 cost_warm=st.mean(r["cost"] for r in rs if r["cw"] == 0) if a == "all" else st.mean(r["cost"] for r in rs),
                 secs=round(st.median(r["secs"] for r in rs), 2), searches=round(st.mean(r["n_search"] for r in rs), 2),
                 none=sum(r["picked"] is None for r in rs), stops=dict(Counter(r["stop"] for r in rs)),
                 misses=Counter(f'{r["task"]}:{r["picked"]}' for r in rs if not r["ok"]).most_common())
        S["single"][f"{m}|{a}"] = c
        print(f'{m+"|"+a:14} {c["n"]:4} {c["acc"]:6.3f} {c["ctx"]:8} {c["cost"]:11.5f} {c["cost_nocache"]:14.5f} {c["secs"]:5} {c["searches"]:4}  warm={c["cost_warm"]:.5f} none={c["none"]} {c["stops"]}')
        for k, v in c["misses"]: print("      miss", k, v)
S["spend"] += sum(r["cost"] for r in R)
REQ = {"crash": ["github_create_issue", "slack_post_message"], "release": ["sentry_create_release", "sentry_create_deploy", "grafana_create_annotation"],
       "latency": ["grafana_query_prometheus", "splunk_", "slack_"], "kafka": ["grafana_search_dashboards", "splunk_create_saved_search", "slack_post_message"]}
REQ2 = {"release": ["github_create_release"]}  # optional: the catalog has no create_release tool for GitHub
p = H / "sessions.jsonl"
if p.exists():
    Q = [json.loads(l) for l in open(p)]
    S["spend"] += sum(q["cost"] for q in Q)
    print("\nsessions")
    for m in ["opus", "sonnet", "haiku"]:
        for a in ["all", "bm25"]:
            qs = [q for q in Q if q["model"] == m and q["arm"] == a]
            if not qs: continue
            done = [all(any(u.startswith(t) for u in q["tools_used"]) for t in REQ[q["chain"]]) for q in qs]
            c = dict(n=len(qs), done=sum(done), cost=st.mean(q["cost"] for q in qs), cost_nocache=st.mean(q["cost_nocache"] for q in qs),
                     ctx=round(st.mean(q["inp"] + q["cw"] + q["cr"] for q in qs)), turns=round(st.mean(q["turns"] for q in qs), 2),
                     calls=round(st.mean(len(q["tools_used"]) for q in qs), 2), searches=round(st.mean(q["n_search"] for q in qs), 2))
            S["sessions"][f"{m}|{a}"] = c
            print(f'{m+"|"+a:14} n={c["n"]} done={c["done"]} $/session={c["cost"]:.4f} nocache={c["cost_nocache"]:.4f} ctx={c["ctx"]} turns={c["turns"]} calls={c["calls"]} searches={c["searches"]}')
            for q, d in zip(qs, done):
                if not d: print("      not done", q["chain"], q["rep"], q["tools_used"])
print("\ntotal spend", round(S["spend"], 3))
json.dump(S, open(H / "summary.json", "w"), indent=1, default=str)
