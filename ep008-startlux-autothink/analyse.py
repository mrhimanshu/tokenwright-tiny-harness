"""Summaries for DATA.md: per condition accuracy, pair accuracy, think rate, thought tokens, seconds; plus gates derived from the
'always' run (first read-out + read-out after the thought, mixed 0.25/0.75 as the engine does). Writes summary.json."""
import json, os, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
L = [json.loads(l) for l in open(os.path.join(HERE, "results_local.jsonl"))]
C = [json.loads(l) for l in open(os.path.join(HERE, "results_claude.jsonl"))] if os.path.exists(os.path.join(HERE, "results_claude.jsonl")) else []
HAIKU = (0.10, 0.50)  # $/MTok in/out (fitted in EP005/EP007)


def pairs(rows):
    g = collections.defaultdict(list)
    for r in rows:
        g[r["group"]].append(r["right"])
    return sum(all(v) for v in g.values()), len(g)


def summ(rows):
    n = len(rows)
    right = sum(r["right"] for r in rows)
    pr, pn = pairs(rows)
    th = [r for r in rows if r.get("thought_used")]
    fam = {}
    for f in sorted({r["family"] for r in rows}):
        fr = [r for r in rows if r["family"] == f]
        a, b = pairs(fr)
        fam[f] = {"acc": round(100 * sum(r["right"] for r in fr) / len(fr), 1), "pairs": f"{a}/{b}"}
    return {"n": n, "right": right, "acc": round(100 * right / n, 1), "pairs_right": pr, "pairs": pn,
            "pair_acc": round(100 * pr / pn, 1), "thought_rate": round(100 * len(th) / n, 1),
            "thought_tokens_mean": round(st.mean([r["thought_tokens"] for r in th]), 0) if th else 0,
            "secs_mean": round(st.mean(r["secs"] for r in rows), 2), "secs_total_min": round(sum(r["secs"] for r in rows) / 60, 1),
            "errors": sum(1 for r in rows if "error" in r), "by_family": fam}


def top(p):
    p = {k: v for k, v in (p or {}).items() if k in ("yes", "no")}
    return max(p, key=p.get) if p else None


out = {"local": {}, "derived_from_always": {}, "claude": {}}
for cond in ["never", "auto0.6", "auto0.9", "always", "always_r2"]:
    rows = [r for r in L if r["cond"] == cond]
    if len(rows) == 48:
        out["local"][cond] = summ(rows)

# derive every gate from the 'always' run: think only if first top < gate, answer = 0.25 first + 0.75 after
alw = [r for r in L if r["cond"] == "always"]
if len(alw) == 48:
    for gate in [0.0, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.01]:
        rows = []
        for r in alw:
            f, a = r["first"], r["after"]
            ft = max(v for k, v in f.items())
            if ft >= gate:
                ch, thought = top(f), False
            else:
                mix = {k: 0.25 * f.get(k, 0) + 0.75 * a.get(k, 0) for k in ("yes", "no")}
                ch, thought = top(mix), True
            rows.append({"group": r["group"], "family": r["family"], "right": ch == r["gold"], "thought_used": thought,
                         "thought_tokens": r["thought_tokens"], "secs": r["secs"] if thought else 1.5})
        s = summ(rows)
        out["derived_from_always"][str(gate)] = {k: s[k] for k in ("acc", "pair_acc", "pairs_right", "thought_rate")}
    # confident-and-wrong in one pass
    cw = [r for r in alw if top(r["first"]) != r["gold"] and max(r["first"].values()) >= 0.6]
    out["one_pass_wrong_but_above_0.6"] = [{"id": r["id"], "first_top": round(max(r["first"].values()), 3),
                                            "after_right": top(r["after"]) == r["gold"]} for r in cw]
    out["one_pass_calibration"] = {}
    for lo, hi in [(0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.01)]:
        b = [r for r in alw if lo <= max(r["first"].values()) < hi]
        if b:
            out["one_pass_calibration"][f"{lo}-{min(hi, 1.0)}"] = {"n": len(b), "acc": round(100 * sum(top(r["first"]) == r["gold"] for r in b) / len(b), 1)}

for m in sorted({r["model"] for r in C}):
    rows = [r for r in C if r["model"] == m]
    per = []
    for run in sorted({r["run"] for r in rows}):
        rr = [r for r in rows if r["run"] == run]
        if len(rr) == 48:
            s = summ([dict(r, thought_used=False) for r in rr])
            s["usd"] = round(sum(r.get("in_tokens", 0) * HAIKU[0] + r.get("out_tokens", 0) * HAIKU[1] for r in rr) / 1e6, 4)
            s["out_tokens_mean"] = round(st.mean(r.get("out_tokens", 0) for r in rr))
            per.append(s)
    out["claude"][m] = per
json.dump(out, open(os.path.join(HERE, "summary.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
