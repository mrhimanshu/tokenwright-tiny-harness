"""Summarise results.jsonl -> summary.json (+ printed table). Uses the last record per (task, method)."""
import json, os
import numpy as np

H = os.path.dirname(os.path.abspath(__file__))
recs = {}
for line in open(os.path.join(H, "results.jsonl")):
    r = json.loads(line)
    if r.get("n_test", 0) < 100:
        continue
    recs[(r["task"], r["method"])] = r
tasks = sorted({t for t, _ in recs})
methods = ["base", "wanda_only", "random_deletion", "deletion_tuning", "full_finetune"]
out = {"tasks": tasks, "per_task": {}, "mean": {}}
for t in tasks:
    out["per_task"][t] = {}
    for m in methods:
        r = recs.get((t, m))
        if not r:
            continue
        out["per_task"][t][m] = {k: r.get(k) for k in ("acc", "kl", "ret_acc", "train_s", "deleted", "gate_weights", "mask_bytes_zstd",
                                                       "peak_mem_gb", "n_test", "n_train", "weights_changed", "n_params")}
for m in methods:
    accs = [out["per_task"][t][m]["acc"] for t in tasks if m in out["per_task"][t]]
    kls = [out["per_task"][t][m]["kl"] for t in tasks if m in out["per_task"][t]]
    if accs:
        out["mean"][m] = {"acc": float(np.mean(accs)), "acc_min": float(min(accs)), "acc_max": float(max(accs)), "kl": float(np.mean(kls)), "n": len(accs)}
# share of FFT's gain recovered by deletion tuning, per task
out["gain_recovered"] = {}
for t in tasks:
    p = out["per_task"][t]
    if all(k in p for k in ("base", "deletion_tuning", "full_finetune")):
        g_f = p["full_finetune"]["acc"] - p["base"]["acc"]; g_d = p["deletion_tuning"]["acc"] - p["base"]["acc"]
        out["gain_recovered"][t] = g_d / g_f if g_f else None
# example questions: base wrong, deletion right
ex = []
for t in tasks:
    b, d, f = recs.get((t, "base")), recs.get((t, "deletion_tuning")), recs.get((t, "full_finetune"))
    if b and d:
        for i, (pb, pd) in enumerate(zip(b["preds"], d["preds"])):
            ex.append({"task": t, "i": i, "base": pb, "dt": pd, "fft": f["preds"][i] if f else None})
out["flips"] = {t: {"base_wrong_dt_right": None} for t in tasks}
json.dump(out, open(os.path.join(H, "summary.json"), "w"), indent=1)
print(f"{'task':12s}" + "".join(f"{m[:10]:>12s}" for m in methods))
for t in tasks:
    print(f"{t:12s}" + "".join(f"{100*out['per_task'][t][m]['acc']:11.1f}%" if m in out['per_task'][t] else f"{'-':>12s}" for m in methods))
print(f"{'mean':12s}" + "".join(f"{100*out['mean'][m]['acc']:11.1f}%" if m in out['mean'] else f"{'-':>12s}" for m in methods))
print("KL   " + " ".join(f"{m}={out['mean'][m]['kl']:.3f}" for m in out["mean"]))
print("gain recovered", out["gain_recovered"])
for t in tasks:
    p = out["per_task"][t]
    if "deletion_tuning" in p:
        d = p["deletion_tuning"]
        print(t, "deleted", d["deleted"], f"{100*d['deleted']/d['gate_weights']:.3f}% of gate", f"{100*d['deleted']/d['n_params']:.3f}% of model",
              "mask", d["mask_bytes_zstd"], "train_s", d["train_s"], "mem", d["peak_mem_gb"])
    if "full_finetune" in p:
        f = p["full_finetune"]; print(t, "fft train_s", f["train_s"], "mem", f["peak_mem_gb"], "changed", f["weights_changed"])
