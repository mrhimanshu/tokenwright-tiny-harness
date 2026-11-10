"""Score results.jsonl with chrF++ (sacrebleu) per system x language; write DATA.md + summary.json."""
import json, os, statistics as st
from collections import defaultdict
import sacrebleu

HERE = os.path.dirname(os.path.abspath(__file__))
rows = [json.loads(l) for l in open(os.path.join(HERE, "results.jsonl"))]
PRICE = {"haiku": (0.10, 0.50), "sonnet": (2.0, 10.0)}  # $/MTok in, out (fitted from Claude Code's costUSD, EP005)
TOK = {"zh_CN": "zh", "ja_JP": "ja-mecab"}
g = defaultdict(list)
for r in rows:
    g[(r["system"], r["lang"])].append(r)
langs = ["hi_IN", "ja_JP", "es_MX", "de_DE", "ar_SA", "zh_CN"]
systems = [s for s in ["plamo08", "plamo2", "plamo8", "haiku", "sonnet"] if any(k[0] == s for k in g)]
S = {}
for s in systems:
    S[s] = {}
    for l in langs:
        rs = g[(s, l)]
        hyp = [r["hyp"] for r in rs]; ref = [r["ref"] for r in rs]
        chrf = sacrebleu.corpus_chrf(hyp, [ref], word_order=2).score
        S[s][l] = {"chrf": round(chrf, 1), "n": len(rs), "secs_mean": round(st.mean(r["secs"] for r in rs), 3),
                   "empty": sum(1 for r in rs if not r["hyp"].strip())}
    allr = [r for k, v in g.items() if k[0] == s for r in v]
    S[s]["avg_chrf"] = round(st.mean(S[s][l]["chrf"] for l in langs), 1)
    S[s]["secs_per_sentence"] = round(st.mean(r["secs"] for r in allr), 3)
    S[s]["sentences"] = len(allr)
    if s in PRICE:
        pi, po = PRICE[s]
        S[s]["usd_total"] = round(sum(r["in_tokens"] * pi + r["out_tokens"] * po for r in allr) / 1e6, 4)
        S[s]["out_tokens_mean"] = round(st.mean(r["out_tokens"] for r in allr))
json.dump(S, open(os.path.join(HERE, "summary.json"), "w"), indent=1)
out = ["# EP007 data: English → 6 languages, 40 WMT24++ sentences each (same sentences for every system), chrF++ vs human reference", "",
       "| system | " + " | ".join(langs) + " | avg | s / sentence | $ for 240 |", "|---|" + "---|" * (len(langs) + 3)]
for s in systems:
    out.append(f"| {s} | " + " | ".join(str(S[s][l]["chrf"]) for l in langs) + f" | **{S[s]['avg_chrf']}** | {S[s]['secs_per_sentence']} | {S[s].get('usd_total', 0)} |")
open(os.path.join(HERE, "DATA.md"), "w").write("\n".join(out) + "\n")
print("\n".join(out))
for s in systems:
    print(s, {l: S[s][l]["empty"] for l in langs})
