"""EP021 summary: python summarize.py -> summary.json + prints"""
import json, os, statistics as st
from itertools import combinations

HERE = os.path.dirname(os.path.abspath(__file__))
rows = [json.loads(l) for l in open(os.path.join(HERE, "judged.jsonl"))]
rows = [r for r in rows if r["tension"] is not None]
S = {}


def m(xs):
    return round(st.mean(xs), 1) if xs else None


def sd(xs):
    return round(st.pstdev(xs), 1) if len(xs) > 1 else 0.0


def spearman(x, y):
    def rank(v):
        o = sorted(range(len(v)), key=lambda i: v[i]); r = [0] * len(v); i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[o[j + 1]] == v[o[i]]:
                j += 1
            for k in range(i, j + 1):
                r[o[k]] = (i + j) / 2
            i = j + 1
        return r
    rx, ry = rank(x), rank(y)
    mx, my = st.mean(rx), st.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return round(num / den, 3) if den else None


def separable(a, b):
    """fraction of cross pairs ordered correctly (AUC): 1.0 = always tell b above a"""
    wins = sum((y > x) + 0.5 * (y == x) for x in a for y in b)
    return round(wins / (len(a) * len(b)), 2)


# ---------- arm A: Spaceship prompt knob on API models ----------
for model in sorted({r["model"] for r in rows if r["arm"] == "prompt" and r["model"] != "qwen2.5-1.5b"}):
    R = [r for r in rows if r["arm"] == "prompt" and r["model"] == model]
    base = [r["tension"] for r in R if r["grade"] is None]
    out = dict(unsteered=dict(mean=m(base), sd=sd(base), n=len(base)), grid={})
    for s in ["slight", "moderate", "strong"]:
        out["grid"][s] = {}
        for g in range(5):
            xs = [r["tension"] for r in R if r["grade"] == g and r["strength"] == s]
            out["grid"][s][g] = dict(mean=m(xs), sd=sd(xs), n=len(xs), min=min(xs), max=max(xs))
    steered = [r for r in R if r["grade"] is not None]
    out["spearman_grade_vs_tension"] = spearman([r["grade"] for r in steered], [r["tension"] for r in steered])
    # adjacent-grade separability per strength
    out["adjacent_auc"] = {s: [separable([r["tension"] for r in R if r["grade"] == g and r["strength"] == s],
                                          [r["tension"] for r in R if r["grade"] == g + 1 and r["strength"] == s]) for g in range(4)]
                           for s in ["slight", "moderate", "strong"]}
    # does strength change anything? spread between very relaxed and very strained per strength
    out["range_by_strength"] = {s: round(out["grid"][s][4]["mean"] - out["grid"][s][0]["mean"], 1) for s in out["grid"]}
    # how many of the 15 settings are distinguishable from their neighbours: count distinct levels (greedy, AUC >= 0.9)
    cells = sorted([(st.mean([r["tension"] for r in R if r["grade"] == g and r["strength"] == s]), g, s,
                     [r["tension"] for r in R if r["grade"] == g and r["strength"] == s]) for g in range(5) for s in ["slight", "moderate", "strong"]])
    levels, cur = 1, cells[0][3]
    for c in cells[1:]:
        if separable(cur, c[3]) >= 0.9:
            levels += 1; cur = c[3]
    out["distinct_levels_auc90"] = levels
    out["coherence_mean"] = m([r["coherence"] for r in R])
    words = [len(r["text"].split()) for r in R]
    out["words_mean"] = m(words)
    tok_out = [r["usage"].get("out", 0) for r in R]; tok_in = [r["usage"].get("inp", 0) for r in R]
    out["tokens"] = dict(inp=sum(tok_in), out=sum(tok_out))
    S[model] = out

# ---------- arm B: Qwen 1.5B, vector vs prompt ----------
Q = [r for r in rows if r["model"] == "qwen2.5-1.5b"]
if Q:
    vec = {}
    for g in sorted({r["gain"] for r in Q if r["arm"] == "vector"}):
        xs = [r for r in Q if r["arm"] == "vector" and r["gain"] == g]
        vec[g] = dict(tension=m([r["tension"] for r in xs]), tension_sd=sd([r["tension"] for r in xs]),
                      coherence=m([r["coherence"] for r in xs]), n=len(xs),
                      tok_s=m([r["tok"] / r["sec"] for r in xs]))
    pr = {}
    for g in range(5):
        xs = [r for r in Q if r["arm"] == "prompt" and r["grade"] == g]
        pr[g] = dict(tension=m([r["tension"] for r in xs]), tension_sd=sd([r["tension"] for r in xs]),
                     coherence=m([r["coherence"] for r in xs]), n=len(xs))
    V = [r for r in Q if r["arm"] == "vector"]
    S["qwen_vector"] = dict(by_gain=vec, spearman_gain_vs_tension=spearman([r["gain"] for r in V], [r["tension"] for r in V]))
    P = [r for r in Q if r["arm"] == "prompt"]
    S["qwen_prompt"] = dict(by_grade=pr, spearman_grade_vs_tension=spearman([r["grade"] for r in P], [r["tension"] for r in P]))

json.dump(S, open(os.path.join(HERE, "summary.json"), "w"), indent=1)
print(json.dumps(S, indent=1))
