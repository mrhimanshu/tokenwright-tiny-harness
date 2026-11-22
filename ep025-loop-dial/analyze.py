"""Summarise results.jsonl + ppl_results.jsonl → summary.json (rescored with accent-insensitive city match)."""
import json, os, re, statistics as st, unicodedata, collections

HERE = os.path.dirname(os.path.abspath(__file__))
norm = lambda s: unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def parse(txt):
    txt = txt.strip().split("\n")[0]  # first line only (the answer line)
    # the answer = the number right after the last "=" if the model wrote an equation, else the first number
    if "=" in txt:
        m = re.findall(r"-?\d[\d,]*", txt.rsplit("=", 1)[1])
        if m:
            return int(m[0].replace(",", ""))
    m = re.findall(r"-?\d[\d,]*", txt)
    return int(m[0].replace(",", "")) if m else None


def ok(r):
    g = r["gold"]
    return norm(g) in norm(r["out"].strip().split("\n")[0]) if isinstance(g, str) else parse(r["out"]) == g


rows = [json.loads(l) for l in open(os.path.join(HERE, "results.jsonl"))]
out = {}
for (m, k), rs in sorted(collections.defaultdict(list, {}).items()):
    pass
groups = collections.defaultdict(list)
for r in rows:
    groups[(r["model"], r["loops"])].append(r)
for (m, k), rs in sorted(groups.items()):
    d = out.setdefault(m, {}).setdefault(str(k), {})
    d["n"] = len(rs)
    d["correct"] = sum(ok(r) for r in rs)
    d["acc"] = round(d["correct"] / len(rs), 3)
    d["per_set"] = [round(sum(ok(r) for r in rs if r["set"] == s) / max(1, sum(1 for r in rs if r["set"] == s)), 3) for s in (1, 2, 3)]
    d["per_kind"] = {kd: f'{sum(ok(r) for r in rs if r["kind"] == kd)}/{sum(1 for r in rs if r["kind"] == kd)}' for kd in sorted({r["kind"] for r in rs})}
    if rs[0].get("gen_tps"):
        d["gen_tps_median"] = round(st.median(r["gen_tps"] for r in rs if r["gen_tps"]), 2)
        d["prompt_tps_median"] = round(st.median(r["prompt_tps"] for r in rs if r["prompt_tps"]), 2)
        d["rss_mb_first"] = rs[0]["rss_mb"]
    d["wall_s_median"] = round(st.median(r["wall_s"] for r in rs), 2)
    d["examples_wrong"] = [(r["id"], r["gold"], r["out"]) for r in rs if not ok(r)][:12]
pp = os.path.join(HERE, "ppl_results.jsonl")
if os.path.exists(pp):
    pr = [json.loads(l) for l in open(pp)]
    g = collections.defaultdict(list)
    for r in pr:
        g[(r["model"], r["loops"])].append(r)
    for (m, k), rs in sorted(g.items()):
        d = out.setdefault(m, {}).setdefault(str(k), {})
        d["ppl"] = {r["article"]: r["ppl"] for r in rs}
        vals = [r["ppl"] for r in rs if r["ppl"]]
        d["ppl_mean"] = round(st.mean(vals), 3) if vals else None
        d["ppl_wall_s"] = [r["wall_s"] for r in rs]
json.dump(out, open(os.path.join(HERE, "summary.json"), "w"), indent=1)
for m, ks in out.items():
    for k, d in ks.items():
        print(m, k, d.get("correct"), "/", d.get("n"), d.get("acc"), d.get("per_set"), d.get("per_kind"), "tps", d.get("gen_tps_median"),
              d.get("prompt_tps_median"), "ppl", d.get("ppl_mean"), d.get("ppl"))
