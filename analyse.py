"""Summarise results.jsonl into DATA.md. Prices per MTok fitted exactly from Claude Code's own costUSD (see FIT)."""
import json, os, statistics as st
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
PRICE = {  # $/MTok: input, output, cache read, cache write (5 min)
    "claude-haiku-5-5": (0.10, 0.50, 0.01, 0.125),
}
rows = [json.loads(l) for l in open(os.path.join(HERE, "results.jsonl"))]


def price_for(model, rows):
    """Fit the price vector from Claude Code runs of that model (exact: Claude Code reports costUSD per token class)."""
    import numpy as np
    X, y = [], []
    for r in rows:
        u = (r.get("modelUsage") or {}).get(model)
        if u:
            X.append([u["inputTokens"], u["outputTokens"], u["cacheReadInputTokens"], u["cacheCreationInputTokens"]])
            y.append(u["costUSD"])
    if len(X) < 4:
        return None
    p = np.linalg.lstsq(np.array(X, float), np.array(y), rcond=None)[0]
    return tuple(round(v * 1e6, 4) for v in p)


def cost(r):
    if r["cfg"] == "claude_code":
        return r.get("cost") or 0
    pi, po, pr, pw = PRICE[r["model"]]
    t = r["tokens"]
    return (t["input_tokens"] * pi + t["output_tokens"] * po + t["cache_read_input_tokens"] * pr
            + t["cache_creation_input_tokens"] * pw) / 1e6


for m in {r["model"] for r in rows}:
    f = price_for(m, rows)
    if f:
        PRICE[m] = f

g = defaultdict(list)
for r in rows:
    if "error" in r:
        continue
    g[(r["model"], r["cfg"])].append(r)

out = ["# EP005 data: same model, same 5 tasks, different harness (runs on 6 Nov 2026, Claude Code 2.1.318)", "",
       f"Prices fitted from Claude Code's costUSD ($/MTok in, out, cache read, cache write): {PRICE}", "",
       "| model | harness | runs | passed | avg tokens / task | avg $ / task | avg turns | avg secs | first call (tiny) |",
       "|---|---|---|---|---|---|---|---|---|"]
summary = {}
for (m, c), rs in sorted(g.items()):
    tot = [sum(r["tokens"].values()) for r in rs]
    cs = [cost(r) for r in rs]
    fc = [r["first_call_input"] for r in rs if "first_call_input" in r]
    s = {"runs": len(rs), "passed": sum(r["passed"] for r in rs), "tokens": st.mean(tot), "cost": st.mean(cs),
         "turns": st.mean(r["turns"] for r in rs), "secs": st.mean(r["secs"] for r in rs), "first": st.mean(fc) if fc else None}
    summary[f"{m}|{c}"] = s
    fcs = "" if s["first"] is None else format(s["first"], ",.0f")
    out.append(f"| {m} | {c} | {s['runs']} | {s['passed']}/{s['runs']} | {s['tokens']:,.0f} | ${s['cost']:.5f} | {s['turns']:.1f} | "
               f"{s['secs']:.1f} | {fcs} |")
out += ["", "## Per task (avg tokens, pass)", "", "| model | harness | " + " | ".join(sorted({r['task'] for r in rows})) + " |",
        "|---|---|" + "---|" * len({r['task'] for r in rows})]
for (m, c), rs in sorted(g.items()):
    cells = []
    for t in sorted({r['task'] for r in rows}):
        tr = [r for r in rs if r["task"] == t]
        cells.append(f"{st.mean(sum(r['tokens'].values()) for r in tr):,.0f} ({sum(r['passed'] for r in tr)}/{len(tr)})" if tr else "")
    out.append(f"| {m} | {c} | " + " | ".join(cells) + " |")
open(os.path.join(HERE, "DATA.md"), "w").write("\n".join(out) + "\n")
json.dump(summary, open(os.path.join(HERE, "summary.json"), "w"), indent=1)
print("\n".join(out))
