"""EP033 analysis of paired.jsonl -> summary.json + printed tables."""
import json, os, statistics as st
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
R = [json.loads(l) for l in open(os.path.join(HERE, "paired.jsonl"))]
med = lambda xs: round(st.median(xs), 2) if xs else None
arms = ["off", "on", "adaptive", "lenient"]; tasks = ["summarize", "code", "rewrite", "freeform", "copy"]
by = defaultdict(list)
for r in R:
    by[(r["arm"], r["task"])].append(r); by[(r["arm"], "ALL")].append(r)
S = {"n_generations": len(R), "steal_median": med([r["steal_pct"] for r in R]), "steal_max": max(r["steal_pct"] for r in R),
     "tps": {}, "speedup": {}, "identical": {}, "ttft": {}, "wall": {}}
print(f"{'task':10s}" + "".join(f"{a:>10s}" for a in arms) + "   speedup on/off (median of pairs)  adaptive/off  lenient/off")
pairs = defaultdict(dict)
for r in R:
    pairs[(r["task"], r["prompt"], r["rep"])][r["arm"]] = r
for t in tasks + ["ALL"]:
    row = {a: med([r["decode_tps"] for r in by[(a, t)]]) for a in arms}
    S["tps"][t] = row
    sp = {}
    for a in ["on", "adaptive", "lenient"]:
        xs = [p[a]["decode_tps"] / p["off"]["decode_tps"] for k, p in pairs.items() if (t == "ALL" or k[0] == t) and a in p and "off" in p]
        sp[a] = med(xs)
        # steal-adjusted: tok/s / (1 - steal)
        xa = [(p[a]["decode_tps"] / (1 - p[a]["steal_pct"] / 100)) / (p["off"]["decode_tps"] / (1 - p["off"]["steal_pct"] / 100))
              for k, p in pairs.items() if (t == "ALL" or k[0] == t) and a in p and "off" in p]
        sp[a + "_steal_adj"] = med(xa)
        sp[a + "_min"] = round(min(xs), 2) if xs else None; sp[a + "_max"] = round(max(xs), 2) if xs else None
    S["speedup"][t] = sp
    idn = {a: sum(1 for k, p in pairs.items() if (t == "ALL" or k[0] == t) and a in p and "off" in p and p[a]["out_sha"] == p["off"]["out_sha"])
           for a in ["on", "adaptive", "lenient"]}
    idn["of"] = sum(1 for k, p in pairs.items() if (t == "ALL" or k[0] == t) and "off" in p and "on" in p)
    S["identical"][t] = idn
    S["ttft"][t] = {a: med([r["ttft_s"] for r in by[(a, t)]]) for a in arms}
    S["wall"][t] = {a: med([r["wall_s"] for r in by[(a, t)]]) for a in arms}
    print(f"{t:10s}" + "".join(f"{row[a] if row[a] is not None else '-':>10}" for a in arms) +
          f"   {sp['on']}x ({sp['on_min']}-{sp['on_max']}) adj {sp['on_steal_adj']}x   {sp['adaptive']}x   {sp['lenient']}x   identical on {idn['on']}/{idn['of']}")
print("TTFT", S["ttft"]["ALL"], "wall", S["wall"]["ALL"])
print("steal median", S["steal_median"], "max", S["steal_max"])
# position effect check (is the first arm in a shuffled block slower?)
pos = defaultdict(list)
for r in R:
    if r["arm"] == "off":
        pos[r["pos"]].append(r["decode_tps"])
S["off_by_position"] = {k: med(v) for k, v in sorted(pos.items())}
print("off tok/s by position in block", S["off_by_position"])
json.dump(S, open(os.path.join(HERE, "summary.json"), "w"), indent=1)
