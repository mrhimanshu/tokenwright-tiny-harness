"""EP016: summarise audit.jsonl, drift.jsonl, claude_eval.jsonl -> lab/summary.json (numbers used on screen)."""
import json, statistics as st, collections
A = [json.loads(l) for l in open("lab/audit.jsonl")]
D = [json.loads(l) for l in open("lab/drift.jsonl")]
C = [json.loads(l) for l in open("lab/claude_eval.jsonl")]
G = [json.loads(l) for l in open("lab/claude_gen.jsonl")]
S = {}
# vocab32k: median over 3 seeds of value/true ratio and sign, per impl per h
v = collections.defaultdict(list)
for r in A:
    if r["case"].startswith("vocab32k"):
        v[(r["kind"], r["impl"], r["h"])].append(r)
S["vocab32k"] = {f"{k}:{i}@{h:.0e}": dict(ratio_median=st.median(x["value"] / x["true"] for x in rs), negative=sum(x["negative"] for x in rs),
                  nan=sum(x["value"] != x["value"] for x in rs), n=len(rs), grad_rel_err_median=(st.median(x["grad_rel_err"] for x in rs) if rs[0]["grad_rel_err"] is not None else None),
                  true_median=st.median(x["true"] for x in rs))
                 for (k, i, h), rs in sorted(v.items(), key=lambda t: (t[0][0], t[0][1], -t[0][2]))}
# first h (largest) where the impl is >10% off in every seed
def first_bad(kind, impl, thr=0.10):
    hs = sorted({h for (k, i, h) in v if k == kind and i == impl}, reverse=True)
    for h in hs:
        if all(x["rel_err"] > thr for x in v[(kind, impl, h)]): return h
S["first_h_10pct_off"] = {f"{k}:{i}": first_bad(k, i) for (k, i) in sorted({(k, i) for (k, i, h) in v})}
S["identical"] = {i: dict(grad_norm_median=st.median(r["grad_norm"] for r in A if r["case"].startswith("identical") and r["impl"] == i),
                          nonzero_entries=[r["grad_nonzero"] for r in A if r["case"].startswith("identical") and r["impl"] == i])
                  for i in sorted({r["impl"] for r in A if r["case"].startswith("identical")})}
S["toy3_negatives"] = sorted({(r["kind"] + ":" + r["impl"]) for r in A if r["case"] == "toy3" and r["negative"]})
S["toy3_nan"] = sorted({(r["kind"] + ":" + r["impl"], r["h"]) for r in A if r["case"] == "toy3" and r["value"] != r["value"]})
dd = collections.defaultdict(list)
for r in D: dd[r["cond"]].append(r)
S["drift"] = {c: dict(n=len(rs), first_grad_norm_median=st.median(r["first_grad_norm"] for r in rs),
                      final_true_kl=[r["log"][-1]["true_kl"] for r in rs], final_drift_rel=[r["log"][-1]["drift_rel"] for r in rs],
                      curve_median=[dict(step=rs[0]["log"][j]["step"], true_kl=st.median(r["log"][j]["true_kl"] for r in rs),
                                         drift_rel=st.median(r["log"][j]["drift_rel"] for r in rs)) for j in range(len(rs[0]["log"]))])
              for c, rs in dd.items()}
cc = collections.defaultdict(list)
for r in C: cc[(r["prompt"], r["model"])].append(r)
S["claude"] = {f"{p}|{m}": dict(n=len(rs), accurate=sum(bool(r.get("accurate")) for r in rs), float64=sum(r["uses_float64"] for r in rs),
                                expm1=sum(r["uses_expm1"] for r in rs), custom_grad=sum(r["uses_custom_grad"] for r in rs),
                                lines_median=st.median(r["lines"] for r in rs), cost_mean=round(st.mean(r["cost"] for r in rs), 4),
                                rel_err_1e4_median=st.median(r["1e-04"]["rel_err"] for r in rs))
               for (p, m), rs in cc.items()}
S["api_cost_total"] = round(sum(r["cost"] for r in G), 3)
json.dump(S, open("lab/summary.json", "w"), indent=1)
print(json.dumps({k: S[k] for k in ("first_h_10pct_off", "identical", "toy3_negatives", "toy3_nan", "claude", "api_cost_total")}, indent=1))
for c in S["drift"]: print(c, S["drift"][c]["curve_median"])
for k in ["kl:naive_fp32@1e-04","kl:naive_fp32@3e-05","kl:torch_kl_div_probtarget@1e-04","kl:torch_distributions@1e-04","kl:naive_bf16@1e-01","kl:naive_bf16@1e-02","kl:scipy_entropy@1e-04","jsd:naive_fp32@1e-04","jsd:scipy_jensenshannon_sq@3e-05","kl:fixed_fp32@1e-06","kl:naive_fp32@1e-03"]:
    print(k, S["vocab32k"][k])
