"""Run one Hermes Agent (hermes-agent 0.19.0) session on a monthly-report task and record usage + score.

Usage:
  run_hermes.py --run-id ID --month 2026-02 --arm terse_skill|terse_noskill|brief_noskill|seed
                [--skill-src DIR] [--model claude-haiku-5-5] [--review]

The agent is built the same way `hermes -z` builds it (hermes_cli.oneshot._run_agent), but kept alive
so that (a) the seed session can take reviewer feedback for several turns and (b) Hermes's own
background skill review (agent.background_review._SKILL_REVIEW_PROMPT) runs to completion in the
foreground instead of in a daemon thread that a one-shot process would kill.
"""
import argparse, json, os, shutil, sys, time
from pathlib import Path

LAB = Path(__file__).resolve().parent
RUNS = Path("/data/renders/ep027/runs")

TERSE = ("Please do the monthly revenue report for {mname}. The order export and the fx rates file are in "
         "./data/. Write report/answer.json with exactly these keys: net_revenue_eur (number, 2 decimals), "
         "orders (int, number of orders that count), unique_customers (int), top_product (string, the product "
         "with the highest net revenue in EUR). Then reply with the four values.")
RULES = ("Finance rules for this report: (1) the export tool sometimes writes the same order twice; count each "
         "order_id once. (2) Only status 'paid' counts; refunded orders and our QA test orders (status 'test') "
         "never count. (3) Prices are in several currencies; convert to EUR with that month's fx_rates.json "
         "(EUR per 1 unit). (4) Some prices use a decimal comma, like 12,50. (5) Count customers by email, "
         "case-insensitive. (6) We report revenue ex-VAT: every price in the export includes 20% VAT, so divide by 1.2.")
FEEDBACK_1 = ("Finance checked this and the numbers don't match theirs. " + RULES +
              " Please redo the report with these rules and overwrite report/answer.json.")
FEEDBACK_N = "Still not matching finance. These fields are wrong: {bad}. Check your work against the rules and fix report/answer.json."
MONTHS = {"2026-01": "January 2026", "2026-02": "February 2026", "2026-03": "March 2026", "2026-04": "April 2026"}

# $ per 1M tokens, Claude API list prices (claude-api skill table, cached 2026-11-03). Cache read = 0.1x input,
# cache write (5-min) = 1.25x input: standard Anthropic multipliers.
PRICES = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.00, 10.00)}


def grade(workdir, month):
    t = json.loads((LAB / "truth" / f"{month}.json").read_text())
    p = workdir / "report" / "answer.json"
    res = {"answer_file": p.exists()}
    try:
        a = json.loads(p.read_text())
    except Exception as e:
        a = {}
        res["parse_error"] = str(e)[:200]
    ok = {
        "net_revenue_eur": isinstance(a.get("net_revenue_eur"), (int, float)) and abs(float(a["net_revenue_eur"]) - t["net_revenue_eur"]) <= 0.05,
        "orders": a.get("orders") == t["orders"],
        "unique_customers": a.get("unique_customers") == t["unique_customers"],
        "top_product": str(a.get("top_product", "")).strip().lower() == t["top_product"].lower(),
    }
    res.update({"answer": a, "fields_ok": ok, "score": sum(ok.values()), "all_correct": all(ok.values())})
    return res


def usage_of(agent, model):
    keys = ["session_input_tokens", "session_output_tokens", "session_cache_read_tokens",
            "session_cache_write_tokens", "session_api_calls"]
    u = {k: getattr(agent, k, None) for k in keys}
    return u


def cost(u, model):
    pi, po = PRICES[model]
    return ((u.get("input", 0) * pi + u.get("cache_read", 0) * pi * 0.1 + u.get("cache_write", 0) * pi * 1.25
             + u.get("output", 0) * po) / 1e6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--month", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--skill-src", default=None)
    ap.add_argument("--model", default="claude-haiku-5-5")
    ap.add_argument("--review", action="store_true")
    ap.add_argument("--max-feedback", type=int, default=3)
    args = ap.parse_args()

    rd = RUNS / args.run_id
    if rd.exists():
        shutil.rmtree(rd)
    work, home = rd / "work", rd / "hermes_home"
    (work / "data").mkdir(parents=True)
    home.mkdir(parents=True)
    for f in (LAB / "exports" / args.month).iterdir():
        shutil.copy(f, work / "data" / f.name)
    if args.skill_src:
        shutil.copytree(args.skill_src, home / "skills", dirs_exist_ok=True)
    os.environ["HERMES_HOME"] = str(home)
    os.environ["ANTHROPIC_API_KEY"] = Path("~/.config/anthropic/key").expanduser().read_text().strip()
    os.environ["HERMES_YOLO_MODE"] = "1"
    os.environ["HERMES_ACCEPT_HOOKS"] = "1"
    os.chdir(work)

    import logging
    logging.disable(logging.CRITICAL)
    from hermes_cli.config import load_config
    from hermes_cli.runtime_provider import resolve_runtime_provider
    from hermes_cli.tools_config import _get_platform_tools
    from hermes_cli import oneshot
    from run_agent import AIAgent
    from tools.thread_context import propagate_context_to_thread  # noqa: F401 (import parity)
    oneshot.declare_stateless_channel()

    cfg = load_config()
    runtime = resolve_runtime_provider(requested="anthropic", target_model=args.model)
    toolsets = sorted(_get_platform_tools(cfg, "cli"))
    session_db = oneshot._create_session_db_for_oneshot()
    agent = AIAgent(api_key=runtime.get("api_key"), base_url=runtime.get("base_url"), provider=runtime.get("provider"),
                    api_mode=runtime.get("api_mode"), model=args.model, enabled_toolsets=toolsets, quiet_mode=True,
                    platform="cli", session_db=session_db, credential_pool=runtime.get("credential_pool"),
                    clarify_callback=oneshot._oneshot_clarify_callback)
    agent.suppress_status_output = True
    agent.stream_delta_callback = None
    agent.tool_gen_callback = None

    prompt = TERSE.format(mname=MONTHS[args.month])
    if args.arm.startswith("brief"):
        prompt = prompt + "\n\n" + RULES
    turns, history, t0 = [], None, time.time()
    totals = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "api_calls": 0, "tool_calls": 0}
    msg = prompt
    for turn in range(1 + (args.max_feedback if args.arm == "seed" else 0)):
        ts = time.time()
        r = agent.run_conversation(msg, conversation_history=history)
        history = r.get("messages")
        tcalls = sum(1 for m in (history or []) if m.get("role") == "tool")
        g = grade(work, args.month)
        turns.append({"turn": turn, "msg": msg[:120], "seconds": round(time.time() - ts, 1), "api_calls": r.get("api_calls"),
                      "final": (r.get("final_response") or "")[:600], "grade": g, "tool_msgs_cum": tcalls,
                      "result_keys": sorted(k for k in r.keys() if k != "messages")})
        for k_src, k in [("input_tokens", "input"), ("output_tokens", "output"), ("cache_read_tokens", "cache_read"),
                         ("cache_write_tokens", "cache_write")]:
            if isinstance(r.get(k_src), int):
                totals[k] = r[k_src]  # session-cumulative in hermes results
        totals["api_calls"] += r.get("api_calls") or 0
        totals["tool_calls"] = tcalls
        if args.arm != "seed" or g["all_correct"]:
            break
        bad = [k for k, v in g["fields_ok"].items() if not v]
        msg = FEEDBACK_1 if turn == 0 else FEEDBACK_N.format(bad=", ".join(bad))
    task_seconds = round(time.time() - t0, 1)
    task_totals = dict(totals)

    review = None
    if args.review:
        from agent.background_review import _run_review_in_thread, _SKILL_REVIEW_PROMPT
        before = {p for p in (home / "skills").rglob("*")} if (home / "skills").exists() else set()
        tr = time.time()
        _run_review_in_thread(agent, list(history), _SKILL_REVIEW_PROMPT)
        after = {p for p in (home / "skills").rglob("*")} if (home / "skills").exists() else set()
        review = {"seconds": round(time.time() - tr, 1),
                  "new_files": sorted(str(p.relative_to(home)) for p in after - before if p.is_file())}

    final_grade = grade(work, args.month)
    out = {"run_id": args.run_id, "month": args.month, "arm": args.arm, "model": args.model, "skill_src": args.skill_src,
           "prompt": prompt, "turns": turns, "task_seconds": task_seconds, "usage": task_totals,
           "usage_after_review": totals, "cost_usd_task": round(cost(task_totals, args.model), 5),
           "agent_attr_usage": usage_of(agent, args.model), "grade": final_grade, "review": review,
           "n_feedback_turns": len(turns) - 1, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (rd / "result.json").write_text(json.dumps(out, indent=2, default=str))
    (rd / "transcript.json").write_text(json.dumps(history, indent=1, default=str))
    with open(LAB / "results.jsonl", "a") as f:
        f.write(json.dumps({k: v for k, v in out.items() if k != "turns"} | {"turns": [{k: t[k] for k in ("turn", "seconds", "api_calls", "tool_msgs_cum")} | {"score": t["grade"]["score"]} for t in turns]}, default=str) + "\n")
    print(json.dumps({"run": args.run_id, "score": final_grade["score"], "all": final_grade["all_correct"],
                      "turns": len(turns), "secs": task_seconds, "usage": task_totals, "cost": out["cost_usd_task"],
                      "review": review}, default=str), flush=True)
    try:
        agent.close()
        session_db.close()
    except Exception:
        pass
    os._exit(0)


if __name__ == "__main__":
    main()
