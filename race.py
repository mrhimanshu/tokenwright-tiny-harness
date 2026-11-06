"""Race: same model, same 5 tasks, different harnesses. Appends to results.jsonl.
Usage: ../../.venv/bin/python race.py <config> [runs] [model]   config = claude_code | tiny | tiny_nocache"""
import json, os, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tiny_harness

KEY = open(os.path.expanduser("~/.config/anthropic/key")).read().strip()
os.environ["ANTHROPIC_API_KEY"] = KEY
CLAUDE = os.path.expanduser("~/.local/bin/claude")
CLEAN_CFG = os.path.join(HERE, "cfg_clean")
OUT = os.path.join(HERE, "results.jsonl")
TASKS = {
    "t1_shop": "The tests in run_tests.py are failing. Find and fix the bugs in the shop package so all tests pass. Keep changes minimal.",
    "t2_slug": "Implement slugify in textkit/slug.py so all the tests pass. Check with python3 run_tests.py.",
    "t3_page": "Fix the bugs in pager/paginate.py so all the tests pass. Check with python3 run_tests.py.",
    "t4_cli": "Add a --json flag to report.py that prints the rows as a JSON list of {name, total} objects, respecting --top. Check with python3 run_tests.py.",
    "t5_rename": "Rename calc_total to order_total everywhere in the store package, with no alias. Check with python3 run_tests.py.",
}
TOK = ["input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens"]


def fresh(task, cfg, i):
    d = os.path.join(HERE, "runs", f"{cfg}-{task}-{i}-{time.time_ns()}")
    shutil.copytree(os.path.join(HERE, "tasks", task), d, ignore=shutil.ignore_patterns("__pycache__"))
    return d


def passed(d):
    return subprocess.run([sys.executable, "-B", "run_tests.py"], cwd=d, capture_output=True).returncode == 0


def claude_code(prompt, d, model):
    env = dict(os.environ, CLAUDE_CONFIG_DIR=CLEAN_CFG, PATH=os.path.expanduser("~/.local/bin") + ":" + os.environ["PATH"])
    os.makedirs(CLEAN_CFG, exist_ok=True)
    cmd = [CLAUDE, "-p", prompt, "--model", model, "--output-format", "json", "--strict-mcp-config", "--mcp-config",
           json.dumps({"mcpServers": {}}), "--permission-mode", "acceptEdits", "--allowedTools", "Bash(python3 run_tests.py)",
           "--max-budget-usd", "2"]
    p = subprocess.run(cmd, cwd=d, env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=900)
    j = json.loads(p.stdout.strip().splitlines()[-1])
    mu = j.get("modelUsage", {})
    tok = {k: j.get("usage", {}).get(k, 0) for k in TOK}
    return {"turns": j.get("num_turns"), "tokens": tok, "cost": j.get("total_cost_usd"), "modelUsage": mu}


def tiny(prompt, d, model, cache=True, v2=True):
    cwd = os.getcwd()
    os.chdir(d)
    try:
        turns, usage = tiny_harness.agent(prompt, model=model, cache=cache,
                                          tools=tiny_harness.TOOLS_V2 if v2 else tiny_harness.TOOLS)
    finally:
        os.chdir(cwd)
    tok = {k: sum((u.get(k) or 0) for u in usage) for k in TOK}
    return {"turns": turns, "tokens": tok, "first_call_input": sum((usage[0].get(k) or 0) for k in TOK[:3]), "per_call": usage}


def main():
    cfg = sys.argv[1]
    runs = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    model = sys.argv[3] if len(sys.argv) > 3 else "claude-haiku-5-5"
    for i in range(runs):
        for task, prompt in TASKS.items():
            d = fresh(task, cfg, i)
            t = time.time()
            try:
                if cfg == "claude_code":
                    r = claude_code(prompt, d, model)
                else:
                    # tiny / tiny_nocache = v1 (4 tools, results from the first race); tiny2 / tiny2_nocache = v2 (+ edit_file)
                    r = tiny(prompt, d, model, cache=not cfg.endswith("nocache"), v2=cfg.startswith("tiny2"))
            except Exception as e:
                r = {"error": repr(e)[:400]}
            r.update(cfg=cfg, task=task, run=i, model=model, secs=round(time.time() - t, 1), passed=passed(d),
                     at=time.strftime("%Y-%m-%d %H:%M:%S"))
            open(OUT, "a").write(json.dumps(r) + "\n")
            print(cfg, task, i, "pass" if r["passed"] else "FAIL", r.get("tokens"), r.get("cost"), r.get("turns"), r["secs"], flush=True)


if __name__ == "__main__":
    main()
