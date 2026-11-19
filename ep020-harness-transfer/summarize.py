"""Summarize EP020 lab: python summarize.py -> summary.json + prints"""
import json, os, statistics as st
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
PRICE = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2, 10), "gemini-4-neon": (3, 15),
         "gemini-3.8-flash": (0.75, 3.75), "proposer": (2, 10)}


def load(prefix):
    runs = []
    for i in range(3):
        p = os.path.join(HERE, f"{prefix}runs/run{i}.json")
        if os.path.exists(p):
            runs.append(json.load(open(p)))
    recs = [json.loads(l) for l in open(os.path.join(HERE, f"{prefix}results.jsonl"))]
    return runs, recs


def cost(recs):
    c = defaultdict(float); n = defaultdict(int)
    for r in recs:
        m = r.get("model", "proposer")
        pi, po = PRICE[m]
        u = r["usage"]
        c[m] += u.get("inp", 0) / 1e6 * pi + u.get("out", 0) / 1e6 * po; n[m] += 1
    return {m: dict(calls=n[m], usd=round(c[m], 2)) for m in c}


def noise(recs):
    """same harness, same model, held-out set scored more than once -> spread"""
    g = defaultdict(list)
    for r in recs:
        if r.get("tag", "").endswith("_held") or r.get("stage") == "transfer":
            g[(r["run"], r["model"], r["h"], r["stage"], r["tag"])].append(r["ok"])
    by = defaultdict(list)
    for (run, m, h, stage, tag), oks in g.items():
        by[(run, m, h)].append(round(100 * sum(oks) / len(oks), 2))
    return [dict(run=k[0], model=k[1], h=k[2], scores=v) for k, v in by.items() if len(v) > 1 and len(set(v)) > 1]


out = {}
for prefix, name in (("", "v1_easy"), ("v2_", "v2_main"), ("rev_", "v2_reverse")):
    if not os.path.exists(os.path.join(HERE, f"{prefix}results.jsonl")):
        continue
    runs, recs = load(prefix)
    d = dict(cost=cost(recs), total_usd=round(sum(v["usd"] for v in cost(recs).values()), 2), runs=[])
    for r in runs:
        row = dict(run=r["run"], src_seed_held=r["traj_src"][0]["held"], src_final_held=r["traj_src"][-1]["held"],
                   src_traj=r["traj_src"], transfer=r.get("transfer"))
        for arm in ("harness", "sim"):
            if f"tgt_{arm}" in r:
                row[f"tgt_{arm}"] = r[f"tgt_{arm}"]["traj"]
                row[f"tgt_{arm}_kept"] = sum(e["kept"] for e in r[f"tgt_{arm}"]["entries"])
        row["src_edits_kept"] = sum(e["kept"] for e in r["mem_src"])
        row["src_harness_chars"] = len(r["h_src"])
        d["runs"].append(row)
    if runs and runs[0].get("transfer"):
        for m in runs[0]["transfer"]:
            se = [r["transfer"][m]["seed"] for r in runs]; ev = [r["transfer"][m]["evolved"] for r in runs]
            d.setdefault("transfer_mean", {})[m] = dict(seed=round(st.mean(se), 2), evolved=round(st.mean(ev), 2),
                                                       seeds=se, evolveds=ev)
    d["noise_same_harness"] = noise(recs)
    out[name] = d
    print("==", name, "cost", d["total_usd"], d["cost"])
    for row in d["runs"]:
        print(" run", row["run"], "src held", row["src_seed_held"], "->", row["src_final_held"], "| transfer", row["transfer"],
              "| tgt harness", [t["held"] for t in row.get("tgt_harness", [])], "kept", row.get("tgt_harness_kept"),
              "| tgt sim", [t["held"] for t in row.get("tgt_sim", [])], "kept", row.get("tgt_sim_kept"))
    print(" transfer mean", d.get("transfer_mean"))
    print(" noise", d["noise_same_harness"][:6])
json.dump(out, open(os.path.join(HERE, "summary.json"), "w"), indent=1)
