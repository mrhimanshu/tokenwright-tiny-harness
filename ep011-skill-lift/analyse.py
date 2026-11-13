"""runs/*.jsonl + quality/ → results.jsonl (merged, with setting) + summary.json.
setting "small" = 2 distractor skills listed (pdf, xlsx); "crowd" = all 19 official Anthropic skills listed (runs/crowd_*)."""
import json, re, statistics as st
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
PRICE = {"claude-haiku-5-5": (0.10, 0.50)}  # $/MTok in/out (fitted in EP005)
rows = []
for f in sorted((HERE / "runs").glob("*.jsonl")):
    for l in open(f):
        r = json.loads(l); r["setting"] = "crowd" if f.name.startswith("crowd_") else "small"; rows.append(r)
with open(HERE / "results.jsonl", "w") as f:
    for r in rows:
        f.write(json.dumps(r) + "\n")
q = {}
for d in (HERE / "quality").iterdir():
    s = json.dumps(json.load(open(d / "skillevaluator-quality.json")))
    q[d.name] = float(re.search(r'"overall_score": ([0-9.]+)', s).group(1))
DIS = {p.name for p in (HERE / "distractors").iterdir()}
by = defaultdict(list)
for r in rows:
    by[(r["setting"], r["model"], r["cond"])].append(r)
out = {}
for (sg, m, c), rs in sorted(by.items()):
    sc = [r["score"] / 8 * 100 for r in rs]
    k = f"{sg}|{m}|{c}"
    reps = defaultdict(list)
    for r in rs:
        reps[r["rep"]].append(r["score"] / 8 * 100)
    out[k] = {"setting": sg, "model": m, "cond": c, "n": len(rs), "quality": q.get(c), "score": round(st.mean(sc), 1),
              "sd": round(st.pstdev(sc), 1), "perfect": sum(r["score"] == 8 for r in rs),
              "loaded": sum(any(x not in DIS for x in r["loaded"]) for r in rs),
              "score_if_loaded": round(st.mean([r["score"] / 8 * 100 for r in rs if any(x not in DIS for x in r["loaded"])] or [0]), 1),
              "score_if_not": round(st.mean([r["score"] / 8 * 100 for r in rs if not any(x not in DIS for x in r["loaded"])] or [0]), 1),
              "in_tok": round(st.mean(r["in_tok"] for r in rs)), "out_tok": round(st.mean(r["out_tok"] for r in rs)),
              "secs": round(st.mean(r["secs"] for r in rs), 1), "rep_means": [round(st.mean(v), 1) for _, v in sorted(reps.items())],
              "checks": {ck: sum(r["checks"][ck] for r in rs) for ck in rs[0]["checks"]}}
    if m in PRICE:
        pi, po = PRICE[m]
        out[k]["usd_per_run"] = round(st.mean(r["in_tok"] * pi + r["out_tok"] * po for r in rs) / 1e6, 6)
for k, v in out.items():
    base = out.get(f"{v['setting']}|{v['model']}|none")
    v["lift"] = round(v["score"] - base["score"], 1) if base else None
json.dump(out, open(HERE / "summary.json", "w"), indent=1)
print("runs:", len(rows))
for k, v in out.items():
    print(f"{v['setting']:5} {v['model'][7:]:10} {v['cond']:11} Q={v['quality']}  score={v['score']:5} sd={v['sd']:4} lift={v['lift']:6} "
          f"perfect={v['perfect']:2}/{v['n']} loaded={v['loaded']:2} (if loaded {v['score_if_loaded']}, if not {v['score_if_not']}) "
          f"in={v['in_tok']:5} out={v['out_tok']:4} {v['secs']}s reps={v['rep_means']}")
