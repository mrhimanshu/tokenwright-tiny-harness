#!/usr/bin/env python3
"""Print the headline numbers from scores.jsonl + results (run score.py first)."""
import json, statistics as st
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
S = [json.loads(l) for l in (HERE / "scores.jsonl").read_text().splitlines()]
truth = json.loads((HERE / "truth.json").read_text())
SYS = ["parse20", "parse35", "claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"]

def tier(p): return truth[p]["tier"]

print("system | kind | tier | n | metric")
for s in SYS:
    for kind in ["report", "table", "chart", "handwriting", "hindi"]:
        for t in ["easy", "hard", "all"]:
            L = [x for x in S if x["system"] == s and x["kind"] == kind and (t == "all" or tier(x["page"]) == t)]
            if not L:
                continue
            if kind in ("report", "handwriting", "hindi"):
                m = f"CER {100*st.mean(x['cer'] for x in L):.2f}%  pages {[round(100*x['cer'],1) for x in L]}"
            elif kind == "table":
                wrong = sum(round((1 - x["cell_acc"]) * x["rows"] * 4) for x in L)
                cells = sum(x["rows"] * 4 for x in L)
                m = f"wrong cells {wrong}/{cells}  rows ok {sum(x['rows_ok'] for x in L)}/{sum(x['rows'] for x in L)}  totals {sum(x['total_ok'] for x in L)}/{len(L)}"
            else:
                errs = [e for x in L for e in x["errs"]]
                wrong = sum(1 for e in errs if e is None or e > 0)
                m = f"wrong values {wrong}/{len(errs)}  off by >2: {sum(1 for e in errs if e is None or e > 2)}  MAE {st.mean(e for e in errs if e is not None):.2f}"
            print(f"{s} | {kind} | {t} | {len(L)} | {m}")
print()
R = defaultdict(list)
for f in (HERE / "results").glob("*.jsonl"):
    if f.name.startswith("smoke"):
        continue
    for l in f.read_text().splitlines():
        r = json.loads(l)
        if r["page"] in truth:
            R[r["model"]].append(r)
for s in SYS:
    L = R[s]
    sec = st.median(r["seconds"] for r in L)
    cost = st.mean(r.get("cost_usd", 0) for r in L)
    extra = ""
    if s.startswith("parse"):
        extra = f" peak_rss {max(r['peak_rss_gb'] for r in L)} GB  rss_after {st.median(r['rss_gb'] for r in L)} GB  steal median {st.median(r['steal_pct'] for r in L)}%  sec min/max {min(r['seconds'] for r in L)}/{max(r['seconds'] for r in L)}"
    print(f"{s}: n={len(L)} median {sec:.2f}s/page  mean ${cost:.5f}/page  1000 pages = ${1000*cost:.2f}, {1000*sec/3600:.1f} h{extra}")
tot = sum(r.get("cost_usd", 0) for s in SYS for r in R[s])
print(f"total API spend ${tot:.2f}")
