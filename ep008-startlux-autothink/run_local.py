"""Run StartLux-Decision v1.1 4B AutoThink (Q8_0 GGUF, llama.cpp on an M4 Pro) on the 48 selected DecisionPivot items.
Usage: .venv/bin/python run_local.py <cond> [<cond> ...]   cond = never | auto0.6 | auto0.9 | always | always_r2
Appends one line per item to results_local.jsonl (first read-out, read-out after the thought, final answer, thought tokens, ms)."""
import json, os, sys, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
URL = "http://127.0.0.1:8090/v1/systemone"
OUT = os.path.join(HERE, "results_local.jsonl")
ITEMS = [json.loads(l) for l in open(os.path.join(HERE, "items_selected.jsonl"))]
MODES = {"never": {"think_mode": "never"}, "auto0.6": {"think_mode": "auto", "gate": 0.6},
         "auto0.9": {"think_mode": "auto", "gate": 0.9}, "always": {"think_mode": "always"},
         "always_r2": {"think_mode": "always"}}


def ask(item, ctl):
    body = dict(state=item["state"], questions=item["questions"], return_thought=True, **ctl)
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=1800))


for cond in sys.argv[1:]:
    for i, it in enumerate(ITEMS):
        t = time.time()
        try:
            r = ask(it, MODES[cond])
            a = r["answers"]["q"]
            d = a.get("details", {})
            th = d.get("thought") or {}
            rec = {"cond": cond, "id": it["id"], "family": it["family"], "group": it["group"], "gold": it["gold"],
                   "choice": a.get("choice"), "probs": a.get("probabilities"), "confidence": a.get("confidence"),
                   "first": (d.get("first_pass") or {}).get("probabilities"), "first_top": (d.get("first_pass") or {}).get("top"),
                   "after": (d.get("after_thought") or {}).get("probabilities"),
                   "thought_used": th.get("used"), "thought_tokens": th.get("tokens"), "thought_ended": th.get("ended"),
                   "thought_ms": th.get("ms"), "thought_text": th.get("text"), "usage": r.get("usage"), "timing": r.get("timing_ms")}
        except Exception as e:
            rec = {"cond": cond, "id": it["id"], "family": it["family"], "group": it["group"], "gold": it["gold"], "error": repr(e)[:300]}
        rec["secs"] = round(time.time() - t, 2)
        rec["right"] = rec.get("choice") == it["gold"]
        rec["at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        open(OUT, "a").write(json.dumps(rec) + "\n")
        print(cond, i, it["id"], it["gold"], rec.get("choice"), "OK" if rec["right"] else "x", rec.get("thought_tokens"), rec["secs"], flush=True)
