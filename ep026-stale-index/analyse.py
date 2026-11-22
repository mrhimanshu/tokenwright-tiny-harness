"""results.jsonl -> summary.json (means over 3 seeds) + recall at an equal scan budget (interpolated over nprobe)."""
import json, numpy as np
R = [json.loads(l) for l in open("results.jsonl")]
def interp(per, budget):
    xs = [per[k]["scanned"] for k in sorted(per, key=int)]; ys = [per[k]["recall10"] for k in sorted(per, key=int)]
    return float(np.interp(budget, xs, ys))
S = {}
for r in R:
    k = (r["checkpoint"], r["method"], r["queries"]); S.setdefault(k, []).append(r)
out = {}
for (chk, m, q), rows in sorted(S.items()):
    n = rows[0]["n"]; budget = 0.04 * n
    agg = lambda f: [f(x) for x in rows]
    d = {"n": n, "seeds": len(rows),
         "recall8": float(np.mean(agg(lambda x: x["per"]["8"]["recall10"]))),
         "recall8_sd": float(np.std(agg(lambda x: x["per"]["8"]["recall10"]))),
         "hit8": float(np.mean(agg(lambda x: x["per"]["8"]["own_hit10"]))),
         "scanned8": float(np.mean(agg(lambda x: x["per"]["8"]["scanned"]))),
         "recall_at_4pct": float(np.mean(agg(lambda x: interp(x["per"], budget)))),
         "imbalance": float(np.mean(agg(lambda x: x["imbalance"]))), "cv": float(np.mean(agg(lambda x: x["cv"]))),
         "top10pct_share": float(np.mean(agg(lambda x: x["top10pct_share"]))), "empty": float(np.mean(agg(lambda x: x["empty"]))),
         "loss": float(np.mean(agg(lambda x: x["loss"]))), "train_s": float(np.mean(agg(lambda x: x["train_s"])))}
    out[f"{chk}|{m}|{q}"] = d
json.dump(out, open("summary.json", "w"), indent=1)
print(f"{'checkpoint':10} {'method':14} {'q':6} {'n':>6} {'rec@8':>6} {'sd':>5} {'hit':>5} {'scan':>6} {'rec@4%':>6} {'imb':>5} {'top10%':>6} {'loss':>6} {'t':>5}")
for k, d in out.items():
    c, m, q = k.split("|")
    print(f"{c:10} {m:14} {q:6} {d['n']:6} {d['recall8']:.3f} {d['recall8_sd']:.3f} {d['hit8']:.3f} {d['scanned8']:6.0f} {d['recall_at_4pct']:.3f} {d['imbalance']:5.2f} {d['top10pct_share']:.3f} {d['loss']:.4f} {d['train_s']:5.2f}")
