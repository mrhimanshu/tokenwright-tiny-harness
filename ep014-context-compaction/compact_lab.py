"""EP014: does a Claude coding agent need its whole history? Same 5-project job, three memory strategies.
  full    = keep every message (prompt caching on, like Claude Code)
  compact = when the context passes THRESH tokens, the agent writes a handoff and restarts from task + handoff
  single  = one action per context: task + the agent's own state note + the last action's result, nothing else
Usage: ../../.venv/bin/python compact_lab.py --models claude-haiku-5-5 --modes full,compact,single --reps 3 --workers 6
"""
import argparse, concurrent.futures as cf, json, os, re, shutil, subprocess, sys, threading, time
from pathlib import Path
import anthropic

HERE = Path(__file__).resolve().parent
os.environ["ANTHROPIC_API_KEY"] = open(os.path.expanduser("~/.config/anthropic/key")).read().strip()
LOCK = threading.Lock()
JOBS = ["shop", "slug", "pager", "report", "store"]
# $/MTok: input, output. Cache write = 1.25x input, cache read = 0.1x input (Anthropic standard).
PRICE = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2, 10), "claude-opus-4-5-20251101": (5, 25),
         "claude-opus-5-5": (4, 20)}

TASK = """This repo has five small projects, each in its own folder with its own tests. Do all five jobs:
1. shop/ : the tests are failing. Find and fix the bugs in the shop package. Keep changes minimal.
2. slug/ : implement slugify in textkit/slug.py so its tests pass.
3. pager/ : fix the bugs in pager/paginate.py.
4. report/ : add a --json flag to report.py that prints the rows as a JSON list of {name, total} objects, respecting --top.
5. store/ : rename calc_total to order_total everywhere in the store package, with no alias.
run_tests runs all five test suites. Stop when every suite passes."""

SYSTEM = "You are a coding agent in the current folder. Make the changes, run the tests, stop when they pass."
SYSTEM_SINGLE = SYSTEM + """
Your memory works differently: each turn you see ONLY the task, the state note you wrote last turn, and the result of
your last action. Everything else is forgotten. So every reply must:
1. First write your updated state inside <state>...</state>: the objective, facts you've established, relevant files and
   what you know about them, changes already made, failed approaches, remaining work, and the immediate next action.
   Fold in anything you need from the last result, because you will not see it again.
2. Then make exactly ONE tool call.
When every suite passes, write the final <state> and the word DONE, with no tool call."""

COMPACT_PROMPT = """Your context is getting long, so it will now be cleared. Write a handoff briefing for a fresh copy of
yourself that will continue this job with only the original task and this briefing. Keep only what the next steps need:
the objective, facts established, relevant files and results, changes already made, failed approaches, remaining work,
and the immediate next action. Be specific (file names, function names, exact remaining failures). No tool calls."""

TOOLS = [
    {"name": "list_files", "description": "List the project's files.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "read_file", "description": "Read a file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "write_file", "description": "Overwrite a file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                      "required": ["path", "content"]}},
    {"name": "edit_file", "description": "Replace one exact snippet in a file (send only the lines that change).",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old": {"type": "string"},
                      "new": {"type": "string"}}, "required": ["path", "old", "new"]}},
    {"name": "run_tests", "description": "Run all five test suites.", "input_schema": {"type": "object", "properties": {}}},
]


def run_tool(d, name, args):
    p = lambda rel: (d / rel).resolve()
    if name == "list_files":
        return "\n".join(str(f.relative_to(d)) for f in sorted(d.rglob("*")) if f.is_file() and "__pycache__" not in str(f))
    if name == "read_file":
        return p(args["path"]).read_text()
    if name == "write_file":
        p(args["path"]).write_text(args["content"])
        return "saved"
    if name == "edit_file":
        src = p(args["path"]).read_text()
        if args["old"] not in src:
            return "error: snippet not found"
        p(args["path"]).write_text(src.replace(args["old"], args["new"], 1))
        return "edited"
    if name == "run_tests":
        r = subprocess.run([sys.executable, "-B", "run_tests.py"], cwd=d, capture_output=True, text=True, timeout=120)
        return (r.stdout + r.stderr)[-4000:]
    return f"error: unknown tool {name}"


def ctx(u):
    return (u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0)


def cost_of(model, u, cached=True):
    pin, pout = PRICE[model]
    if not cached:  # what the same tokens would cost with no prompt caching
        return (ctx(u) * pin + (u.get("output_tokens") or 0) * pout) / 1e6
    return ((u.get("input_tokens") or 0) * pin + (u.get("cache_creation_input_tokens") or 0) * pin * 1.25
            + (u.get("cache_read_input_tokens") or 0) * pin * 0.1 + (u.get("output_tokens") or 0) * pout) / 1e6


def call(client, **kw):
    for attempt in range(6):
        try:
            return client.messages.create(**kw)
        except (anthropic.RateLimitError, anthropic.APIStatusError, anthropic.APIConnectionError) as e:
            if isinstance(e, anthropic.BadRequestError):
                raise
            time.sleep(5 * (attempt + 1))
    return client.messages.create(**kw)


def mark_cache(messages):
    for m in messages:
        if isinstance(m["content"], list):
            for b in m["content"]:
                b.pop("cache_control", None)
    messages[-1]["content"][-1]["cache_control"] = {"type": "ephemeral"}


def text_of(r):
    return "".join(b.text for b in r.content if b.type == "text")


def do_tools(d, r):
    results, actions = [], []
    for b in r.content:
        if b.type == "tool_use":
            try:
                out = run_tool(d, b.name, b.input)
            except Exception as e:
                out = f"error: {e}"
            results.append({"type": "tool_result", "tool_use_id": b.id, "content": out})
            actions.append((b.name, b.input, out))
    return results, actions


def agent_history(client, d, model, mode, thresh, max_steps):
    """full / compact: normal tool loop; compact clears the history at the threshold."""
    calls, compactions = [], 0
    messages = [{"role": "user", "content": [{"type": "text", "text": TASK}]}]
    for step in range(1, max_steps + 1):
        mark_cache(messages)
        r = call(client, model=model, max_tokens=8000, system=SYSTEM, tools=TOOLS, messages=messages)
        u = r.usage.model_dump()
        calls.append(dict(kind="act", ctx=ctx(u), usage=u))
        messages.append({"role": "assistant", "content": [b.model_dump(exclude_none=True) for b in r.content]})
        if r.stop_reason != "tool_use":
            return step, calls, compactions, "done"
        results, _ = do_tools(d, r)
        messages.append({"role": "user", "content": results})
        if mode == "compact" and ctx(u) > thresh:
            messages[-1]["content"].append({"type": "text", "text": COMPACT_PROMPT})
            mark_cache(messages)
            c = call(client, model=model, max_tokens=4000, system=SYSTEM, tools=TOOLS, tool_choice={"type": "none"},
                     messages=messages)
            cu = c.usage.model_dump()
            handoff = text_of(c)
            calls.append(dict(kind="compact", ctx=ctx(cu), usage=cu, handoff_chars=len(handoff)))
            compactions += 1
            messages = [{"role": "user", "content": [{"type": "text", "text":
                         TASK + "\n\nHANDOFF FROM YOUR EARLIER SELF (your earlier context was cleared):\n" + handoff}]}]
    return max_steps, calls, compactions, "max_steps"


def agent_single(client, d, model, max_steps):
    calls, state, last = [], "(nothing yet: this is the first turn)", "(none yet)"
    for step in range(1, max_steps + 1):
        prompt = f"{TASK}\n\nYOUR STATE NOTE (written by you last turn):\n{state}\n\nYOUR LAST ACTION AND ITS RESULT:\n{last}"
        r = call(client, model=model, max_tokens=8000, system=SYSTEM_SINGLE, tools=TOOLS,
                 tool_choice={"type": "auto", "disable_parallel_tool_use": True}, messages=[{"role": "user", "content": prompt}])
        u = r.usage.model_dump()
        calls.append(dict(kind="act", ctx=ctx(u), usage=u))
        txt = text_of(r)
        m = re.search(r"<state>(.*?)</state>", txt, re.S)
        state = (m.group(1) if m else txt).strip()[:12000] or state
        if r.stop_reason != "tool_use":
            return step, calls, 0, "done"
        _, actions = do_tools(d, r)
        last = "\n\n".join(f"{n}({json.dumps(a)[:3000]})\nRESULT:\n{o}" for n, a, o in actions)
    return max_steps, calls, 0, "max_steps"


def jobs_passed(d):
    ok = []
    for j in JOBS:
        r = subprocess.run([sys.executable, "-B", "run_tests.py"], cwd=d / j, capture_output=True, timeout=60)
        ok.append(r.returncode == 0)
    return ok


def run(model, mode, rep, thresh, max_steps):
    d = HERE / "runs" / f"{model}-{mode}-{rep}-{time.time_ns()}"
    shutil.copytree(HERE / "repo", d, ignore=shutil.ignore_patterns("__pycache__"))
    client = anthropic.Anthropic(max_retries=4)
    t0 = time.time()
    try:
        if mode == "single":
            steps, calls, comps, end = agent_single(client, d, model, max_steps)
        else:
            steps, calls, comps, end = agent_history(client, d, model, mode, thresh, max_steps)
        err = None
    except Exception as e:
        steps, calls, comps, end, err = 0, [], 0, "error", repr(e)[:400]
    ok = jobs_passed(d)
    tot = lambda k: sum((c["usage"].get(k) or 0) for c in calls)
    res = dict(model=model, mode=mode, thresh=thresh if mode == "compact" else None, rep=rep, end=end, error=err,
               jobs=dict(zip(JOBS, ok)), n_jobs=sum(ok), all_pass=all(ok), steps=steps, n_calls=len(calls),
               compactions=comps, peak_ctx=max([c["ctx"] for c in calls] or [0]),
               ctx_sum=sum(c["ctx"] for c in calls), out_tok=tot("output_tokens"), in_tok=tot("input_tokens"),
               cache_read=tot("cache_read_input_tokens"), cache_write=tot("cache_creation_input_tokens"),
               cost=round(sum(cost_of(model, c["usage"]) for c in calls), 6),
               cost_nocache=round(sum(cost_of(model, c["usage"], cached=False) for c in calls), 6),
               compact_cost=round(sum(cost_of(model, c["usage"]) for c in calls if c["kind"] == "compact"), 6),
               ctx_trace=[(c["kind"][0], c["ctx"]) for c in calls], secs=round(time.time() - t0, 1),
               ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="claude-haiku-5-5")
    ap.add_argument("--modes", default="full,compact,single")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--rep0", type=int, default=0)
    ap.add_argument("--thresh", type=int, default=16000)
    ap.add_argument("--max-steps", type=int, default=60)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", default="results.jsonl")
    a = ap.parse_args()
    jobs = [(m, mo, r) for r in range(a.rep0, a.rep0 + a.reps) for m in a.models.split(",") for mo in a.modes.split(",")]
    total = 0.0
    with cf.ThreadPoolExecutor(a.workers) as ex:
        futs = [ex.submit(run, m, mo, r, a.thresh, a.max_steps) for m, mo, r in jobs]
        for f in cf.as_completed(futs):
            res = f.result()
            with LOCK, open(HERE / a.out, "a") as fh:
                fh.write(json.dumps(res) + "\n")
            total += res["cost"]
            print(res["model"], res["mode"], res["rep"], f"{res['n_jobs']}/5", res["end"], "steps", res["steps"],
                  "peak", res["peak_ctx"], "comp", res["compactions"], f"${res['cost']:.4f}", f"(nocache ${res['cost_nocache']:.4f})",
                  f"{res['secs']}s", res["error"] or "", f"TOTAL ${total:.3f}", flush=True)


if __name__ == "__main__":
    main()
