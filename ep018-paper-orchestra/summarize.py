"""Collect every run into summary.json (runs/*: PaperOrchestra po_1..5, one-call baselines one_gem_1..3, one_son_1..3)."""
import json, glob, os, re, collections
P = {"gemini-3.8-flash": (0.75e-6, 3.75e-6), "claude-sonnet-5-5": (3e-6, 15e-6)}
out = {}
for d in sorted(glob.glob("runs/*/")):
    k = os.path.basename(d.rstrip("/")); r = {}
    meta = json.load(open(d + "run_meta.json"))
    if k.startswith("po_"):
        tex = d + "content_refinement_workdir/final_refined_paper.tex"
        u = [json.loads(l) for l in open(d + "usage.jsonl")]
        r["secs"] = meta["wall_secs"]; r["llm_calls"] = len(u)
        r["usd"] = round(sum(x["inp"] for x in u) * P["gemini-3.8-flash"][0] + sum(x["out"] + x["think"] for x in u) * P["gemini-3.8-flash"][1], 3)
        if os.path.exists(d + "s2_calls.jsonl"):
            s2 = [json.loads(l) for l in open(d + "s2_calls.jsonl")]; r["s2_lookups"] = len(s2); r["s2_status"] = dict(collections.Counter(str(x["status"]) for x in s2))
        import fitz; r["pages"] = len(fitz.open(d + "final_paper.pdf"))
    else:
        tex = d + "latex/template.tex"; u = meta["usage"]; pr = P[meta["model"]]
        r["secs"] = meta["secs"]; r["usd"] = round(u["inp"] * pr[0] + (u["out"] + u.get("think", 0)) * pr[1], 3)
    r["refs"] = dict(collections.Counter(json.loads(l)["status"] for l in open(d + "refs_check.jsonl")))
    r["cites"] = json.load(open(d + "cites.json")) if os.path.exists(d + "cites.json") else None
    r["number_sentences"] = dict(collections.Counter(json.loads(l)["label"] for l in open(d + "nums_check.jsonl")))
    r["rubric"] = {q: v.get("answer") for q, v in json.load(open(d + "rubric.json")).items()}
    t = open(tex).read()
    r["haiku_max_invented"] = bool(re.search(r"Haiku[^\\\n]*&[^\n]*105\.7\s*&\s*[0-9]", t))
    r["memory_invented"] = sorted(set(re.findall(r"\b(\d+)\s?(?:\\,)?(?:\\mathrm\{)?GB", t)))
    out[k] = r
json.dump(out, open("summary.json", "w"), indent=1)
for k, r in out.items(): print(k, r["secs"], r["usd"], r["refs"], r["haiku_max_invented"], r["memory_invented"], r["rubric"]["cites_hoover"])
