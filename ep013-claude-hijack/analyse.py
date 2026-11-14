"""EP013 summary: python3 analyse.py [results.jsonl ...] > summary.txt (also writes summary.json)"""
import collections, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
files = sys.argv[1:] or ["results.jsonl", "guard.jsonl"]
R = []
for f in files:
    p = os.path.join(HERE, f)
    if os.path.exists(p):
        R += [json.loads(l) for l in open(p)]
R = [r for r in R if "error" not in r]
ERR = 0
SHORT = {"claude-haiku-4-5-20251001": "Haiku 4.5", "claude-sonnet-4-5-20250929": "Sonnet 4.5", "claude-sonnet-4-6": "Sonnet 4.6",
         "claude-opus-4-7": "Opus 4.7", "claude-opus-4-8": "Opus 4.8", "claude-sonnet-5": "Sonnet 5", "claude-opus-5": "Opus 5",
         "claude-haiku-5-5": "Haiku 5.5", "claude-sonnet-5-5": "Sonnet 5.5", "claude-opus-5-5": "Opus 5.5", "claude-fable-5-2": "Fable 5.2"}
ORDER = list(SHORT)
S = {"by_model": {}, "by_attack": {}, "cells": {}}
for d in sorted({r["defence"] for r in R}):
    print(f"\n=== defence: {d} ===")
    rs = [r for r in R if r["defence"] == d]
    print(f"{'model':11s} {'n':>3s} {'leaked':>7s} {'sent_to_attacker':>17s} {'warned':>7s} {'blocked':>8s} {'$/run':>8s}  by attack (leaked/n)")
    for m in ORDER:
        x = [r for r in rs if r["model"] == m]
        if not x:
            continue
        n = len(x); lk = sum(r["leaked"] for r in x); hj = sum(r["hijacked"] for r in x); fl = sum(r["flagged"] for r in x)
        bl = sum(r.get("blocked", False) for r in x); cost = sum(r["cost"] for r in x) / n
        att = collections.OrderedDict()
        for r in x:
            a = att.setdefault(r["attack"], [0, 0]); a[0] += r["leaked"]; a[1] += 1
        S["by_model"][f"{d}/{m}"] = dict(name=SHORT[m], n=n, leaked=lk, sent_to_attacker=hj, warned=fl, blocked=bl, cost_per_run=round(cost, 5),
                                       by_attack={k: v for k, v in att.items()})
        print(f"{SHORT[m]:11s} {n:3d} {lk:4d}/{n:<2d} {hj:10d}/{n:<6d} {fl:4d}/{n:<2d} {bl:5d}/{n:<2d} {cost:8.4f}  " +
              " ".join(f"{k}={v[0]}/{v[1]}" for k, v in att.items()))
    print("by attack:")
    for a in sorted({r["attack"] for r in rs}):
        x = [r for r in rs if r["attack"] == a]
        lk = sum(r["leaked"] for r in x); hj = sum(r["hijacked"] for r in x)
        S["by_attack"][f"{d}/{a}"] = dict(n=len(x), leaked=lk, sent_to_attacker=hj)
        print(f"  {a:12s} leaked {lk}/{len(x)}  sent-to-attacker {hj}/{len(x)}")
    tot = sum(r["cost"] for r in rs)
    print(f"runs {len(rs)}  total ${tot:.2f}")
    S[f"total_cost_{d}"] = round(tot, 3); S[f"runs_{d}"] = len(rs)
json.dump(S, open(os.path.join(HERE, "summary.json"), "w"), indent=1)
