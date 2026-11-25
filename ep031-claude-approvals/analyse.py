"""Summarise results.jsonl -> summary.json + tables."""
import json
from pathlib import Path
from collections import defaultdict
HERE = Path(__file__).parent
R = [json.loads(l) for l in (HERE / "results.jsonl").read_text().splitlines()]
import re
def outcome(r):
    if r["verdict"] == "parse_error" and r.get("stop") == "refusal": return "refused"
    if r["verdict"] == "parse_error":  # JSON with braces inside the reason: read the verdict field directly
        m = re.findall(r'"verdict":\s*"(\w+)"', r.get("text", ""))
        if m: return m[-1]
    return r["verdict"]
S = {"total_spend": round(sum(r["cost"] for r in R), 3), "n": len(R), "cells": {}, "per_pr": {}}
for arm in ["plain", "guarded", "fixed"]:
    for m in ["opus", "sonnet", "haiku"]:
        rs = [r for r in R if r["arm"] == arm and r["model"] == m]
        c = {}
        for k in ["routine", "risky", "sneaky", "subtle"]:
            ks = [r for r in rs if r["kind"] == k]
            o = defaultdict(int)
            for r in ks: o[outcome(r)] += 1
            c[k] = dict(n=len(ks), **o)
        c["cost"] = round(sum(r["cost"] for r in rs), 3)
        S["cells"][f"{arm}|{m}"] = c
        print(arm, m, json.dumps(c))
for r in R:
    S["per_pr"].setdefault(f'{r["arm"]}|{r["pr"]}', defaultdict(list))[r["model"]].append(outcome(r))
print()
for k, v in S["per_pr"].items():
    print(f"{k:36}", "  ".join(f"{m}:{','.join(x[:4] for x in v[m])}" for m in ["opus", "sonnet", "haiku"]))
json.dump(S, open(HERE / "summary.json", "w"), indent=1)
