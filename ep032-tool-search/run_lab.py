"""EP032 lab: tool search vs loading all 148 MCP tools.
Arms: all (every definition in context, prompt-cached), bm25 / regex (tool search, every tool defer_loading).
One API call per task (plus pause_turn continuations); we stop at the first call to a real tool and score its name.
Usage: python run_lab.py --models opus,sonnet,haiku --arms all,bm25,regex --reps 1"""
import json, time, argparse, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from common import client, cost, MODELS, PRICE
HERE = Path(__file__).parent
cat = json.load(open(HERE / "catalog_raw.json"))
TOOLS = [t for s in cat for t in cat[s]["tools"]]
TASKS = [dict(k, server=s, id=f"{s}_{i}") for s in cat for i, k in enumerate(cat[s]["tasks"])]
SYS = ("You are an engineering assistant for the Acme platform team. You can work with GitHub, Slack, Sentry, Grafana "
       "and Splunk through tools. Do the user's request by calling the right tool; don't ask questions first.")
LOCK = threading.Lock()

def tools_for(arm):
    if arm == "all":
        t = [dict(x) for x in TOOLS]
        t[-1] = dict(t[-1], cache_control={"type": "ephemeral"})
        return t
    st = {"bm25": {"type": "tool_search_tool_bm25_20251119", "name": "tool_search_tool_bm25"},
          "regex": {"type": "tool_search_tool_regex_20251119", "name": "tool_search_tool_regex"}}[arm]
    return [st] + [dict(x, defer_loading=True) for x in TOOLS]

def run(model, arm, task, rep):
    tools = tools_for(arm)
    msgs = [{"role": "user", "content": task["prompt"]}]
    t0 = time.time(); tot = dict(inp=0, cw=0, cr=0, out=0, cost=0.0); calls = 0; searches = []; picked = None; stop = None; details = None
    for _ in range(4):
        m = client.messages.create(model=MODELS[model], max_tokens=16000, system=SYS, tools=tools, messages=msgs,
                                   output_config={"effort": "medium"})
        calls += 1; u = m.usage
        tot["inp"] += u.input_tokens; tot["cw"] += u.cache_creation_input_tokens or 0
        tot["cr"] += u.cache_read_input_tokens or 0; tot["out"] += u.output_tokens; tot["cost"] += cost(model, u)
        stop = m.stop_reason; details = str(getattr(m, "stop_details", None)) if stop == "refusal" else None
        for b in m.content:
            if b.type == "server_tool_use": searches.append(b.input)
            if b.type == "tool_search_tool_result":
                c = b.content
                searches[-1] = dict(searches[-1], found=[r.tool_name for r in getattr(c, "tool_references", []) or []])
            if b.type == "tool_use" and picked is None: picked = b.name
        if stop == "pause_turn":
            msgs = msgs + [{"role": "assistant", "content": m.content}]; continue
        break
    i = PRICE[model][0]
    r = dict(model=model, arm=arm, task=task["id"], server=task["server"], rep=rep, target=task["target"],
             also_ok=task["also_ok"], picked=picked, ok=picked in [task["target"]] + task["also_ok"],
             stop=stop, stop_details=details, api_calls=calls, searches=searches, n_search=len(searches),
             secs=round(time.time() - t0, 2), **tot,
             cost_nocache=(tot["inp"] + tot["cw"] + tot["cr"]) * i / 1e6 + tot["out"] * PRICE[model][1] / 1e6)
    with LOCK:
        open(HERE / "results.jsonl", "a").write(json.dumps(r) + "\n")
        print(f'{model:6} {arm:5} {task["id"]:10} r{rep} {str(picked):40} {"OK " if r["ok"] else "XX "} in={tot["inp"]} cw={tot["cw"]} cr={tot["cr"]} out={tot["out"]} ${tot["cost"]:.4f} {r["secs"]}s s={len(searches)}', flush=True)
    return r

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="haiku"); ap.add_argument("--arms", default="all,bm25,regex")
    ap.add_argument("--reps", type=int, default=1); ap.add_argument("--only", default="")
    a = ap.parse_args()
    tasks = [t for t in TASKS if not a.only or t["id"] in a.only.split(",")]
    for model in a.models.split(","):
        for arm in a.arms.split(","):
            jobs = [(model, arm, t, r) for r in range(a.reps) for t in tasks]
            if arm == "all":  # warm the cache with the first job, then run the rest in parallel within the 5 min TTL
                run(*jobs[0]); jobs = jobs[1:]
            with ThreadPoolExecutor(6) as ex:
                list(ex.map(lambda j: run(*j), jobs))
