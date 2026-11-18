"""Run PaperOrchestra (pinned copy in ./po, commit d9bae99) and log every Gemini call's token usage.
usage: run_po.py <out_dir> <model> ; env GEMINI_API_KEY set by caller"""
import sys, os, json, time, threading
HERE = os.path.dirname(os.path.abspath(__file__))
out_dir, model = sys.argv[1], sys.argv[2]
os.makedirs(out_dir, exist_ok=True)
sys.path.insert(0, os.path.join(HERE, "po"))
os.chdir(os.path.join(HERE, "po"))
from google.genai import models as gm
_orig = gm.Models.generate_content
lock = threading.Lock()
logf = os.path.join(out_dir, "usage.jsonl")
MAP = {"gemini-3.1-pro-preview": model, "gemini-3-flash-preview": model}  # repo defaults that our key can't call (404 on 18 Nov 2026)
def patched(self, *a, **k):
    asked = k.get("model")
    if asked in MAP: k["model"] = MAP[asked]
    t = time.time(); r = _orig(self, *a, **k)
    u = r.usage_metadata
    rec = dict(t=t, secs=round(time.time()-t, 2), model=k.get("model"), asked=asked,
               inp=u.prompt_token_count or 0, out=(u.candidates_token_count or 0), think=(u.thoughts_token_count or 0),
               tool=(u.tool_use_prompt_token_count or 0),
               search=bool(getattr(r.candidates[0], "grounding_metadata", None) and r.candidates[0].grounding_metadata.web_search_queries) if r.candidates else False)
    with lock, open(logf, "a") as f: f.write(json.dumps(rec) + "\n")
    return r
gm.Models.generate_content = patched
import requests as _rq
_rget = _rq.get
s2log = os.path.join(out_dir, "s2_calls.jsonl")
def rget(url, *a, **k):
    r = None
    try:
        r = _rget(url, *a, **k); return r
    finally:
        if "semanticscholar" in str(url):
            with lock, open(s2log, "a") as f:
                f.write(json.dumps(dict(t=time.time(), q=(k.get("params") or {}).get("query"), status=getattr(r, "status_code", None),
                                        n=(len(r.json().get("data", [])) if r is not None and r.status_code == 200 else None))) + "\n")
_rq.get = rget
sys.argv = ["paper_writing_cli.py", "--raw_materials_dir", os.path.join(HERE, "raw_materials"),
            "--latex_template_dir", os.path.join(HERE, "po/templates/iclr2025"), "--output_dir", out_dir,
            "--writer_model_name", model, "--reflection_model_name", model, "--research_cutoff", "2026-12"]
t0 = time.time()
import runpy
try:
    runpy.run_path("paper_writing_cli.py", run_name="__main__")
finally:
    json.dump({"wall_secs": round(time.time()-t0, 1), "model": model}, open(os.path.join(out_dir, "run_meta.json"), "w"))
