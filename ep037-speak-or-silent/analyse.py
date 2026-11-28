import json, collections, re, statistics, random
S = {r["decision_point_id"]: r for r in json.load(open("data/sample.json"))}
seen = set(); R = []
for l in open("results/results.jsonl"):
    x = json.loads(l); k = (x["model"], x["arm"], x["run"], x["id"])
    if k in seen: continue
    seen.add(k); R.append(x)
def bal(rows, key="pred"):
    n = collections.Counter(); ok = collections.Counter()
    for r in rows:
        n[r["label"]] += 1; ok[r["label"]] += (r[key] == r["label"])
    return 50 * (ok["SPEAK"] / max(1, n["SPEAK"]) + ok["SILENT"] / max(1, n["SILENT"]))
def cat_rec(rows):
    n = collections.Counter(); ok = collections.Counter()
    for r in rows: n[r["category"]] += 1; ok[r["category"]] += (r["pred"] == r["label"])
    return {k: round(100 * ok[k] / n[k], 1) for k in sorted(n)}
def name_rule(s):
    return "SPEAK" if re.search(r"\b" + re.escape(s["target_speaker"].lower()) + r"\b", s["current_turn"]["text"].lower()) else "SILENT"
def prev_rule(s):
    ct = s["context_turns"]; return "SPEAK" if ct and ct[-1]["speaker"] == s["target_speaker"] else "SILENT"
summary = {"cells": {}, "rules_on_sample": {}}
for corpus in ["friends", "ami"]:
    rows = [dict(label=s["decision"], category=s["category"], pred=name_rule(s), pred2=prev_rule(s)) for s in S.values() if s["corpus"] == corpus]
    summary["rules_on_sample"][corpus] = {"name_in_last_line": round(bal(rows), 2), "spoke_turn_before": round(bal(rows, "pred2"), 2), "name_cats": cat_rec(rows)}
groups = collections.defaultdict(list)
for x in R: groups[(x["model"], x["arm"], x["run"])].append(x)
for (m, a, run), rows in sorted(groups.items()):
    d = {"n": len(rows), "missing_pred": sum(r["pred"] is None for r in rows), "cost": round(sum(r["cost"] for r in rows), 3),
         "stop": dict(collections.Counter(r["stop_reason"] for r in rows)),
         "speak_rate": round(100 * sum(r["pred"] == "SPEAK" for r in rows) / len(rows), 1)}
    for corpus in ["friends", "ami"]:
        cr = [r for r in rows if r["corpus"] == corpus]
        if cr: d[corpus] = {"balacc": round(bal(cr), 2), "n": len(cr), "cats": cat_rec(cr)}
    d["both"] = round(bal(rows), 2)
    summary["cells"][f"{m}|{a}|{run}"] = d
summary["total_cost"] = round(sum(x["cost"] for x in R), 3)
json.dump(summary, open("summary.json", "w"), indent=1)
print(json.dumps(summary["rules_on_sample"]))
for k, d in summary["cells"].items():
    print(f"{k:32s} n={d['n']:3d} miss={d['missing_pred']} fr={d.get('friends',{}).get('balacc')} ami={d.get('ami',{}).get('balacc')} both={d['both']} speak%={d['speak_rate']} ${d['cost']}")
    print("      fr", d.get("friends", {}).get("cats"), " ami", d.get("ami", {}).get("cats"))
print("total $", summary["total_cost"])
