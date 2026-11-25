"""EP032 lab part 2: whole agent sessions (multi-step chains across servers), fake tool results.
Arms: all (148 tools in context) vs bm25 (tool search). BOTH arms use top-level automatic prompt caching, like a
real agent loop. Up to 12 model calls per session. Usage: python session.py --models haiku,sonnet --reps 3"""
import json, time, argparse, threading, hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from common import client, cost, MODELS, PRICE
from run_lab import TOOLS, SYS, tools_for
HERE = Path(__file__).parent
LOCK = threading.Lock()
CHAINS = {
 "crash": "Checkout is crashing in production. In Sentry (org acme, project web) find the newest unresolved issue about checkout, "
          "read its details, open a GitHub issue in acme/web-frontend summarising the stack trace, then post the new issue's link "
          "in Slack channel C01INC.",
 "release": "We just shipped version 2.15.0 of acme/web-frontend. Create the GitHub release v2.15.0, create the matching Sentry "
            "release 2.15.0 for org acme project web and record a production deploy for it, then add an annotation "
            "'deploy 2.15.0' on the Grafana dashboard with uid web-overview.",
 "latency": "The checkout p95 latency alert fired. Query Prometheus (Grafana datasource uid prom1) for the p95 of "
            "http_request_duration_seconds{service=\"checkout\"} over the last hour, search Splunk index=web for HTTP 500s by host "
            "over the same hour, and reply with a short summary in the Slack thread 1714600000.123456 in channel C04ABC123.",
 "kafka": "Find the Grafana dashboard about Kafka consumer lag, get a quick summary of its panels, create a Splunk saved search "
          "called 'kafka lag errors' for index=streaming error over the last 15 minutes, then post both to Slack channel C02DATA.",
}
TOPIC = {"crash": "TypeError: Cannot read properties of undefined (reading 'total') at submitOrder (checkout/submit.ts:88)",
         "release": "web-frontend 2.15.0", "latency": "checkout p95 1.84 s (normal 0.42 s); host web-7 has 412 of 455 HTTP 500s",
         "kafka": "Kafka Consumer Lag (uid kafka-lag-01): panels lag by group, lag by partition, consumer throughput"}
def fake(chain, name, args):
    h = hashlib.md5((name + json.dumps(args, sort_keys=True)).encode()).hexdigest()[:8]
    return json.dumps({"ok": True, "tool": name, "id": f"ID-{h}", "url": f"https://acme.example/{name.split('_')[0]}/{h}",
                       "result": [{"id": f"ID-{h}-{i}", "summary": TOPIC[chain], "status": "ok"} for i in range(2)]})

def run(model, arm, chain, rep):
    tools = tools_for(arm)
    msgs = [{"role": "user", "content": CHAINS[chain]}]
    tot = dict(inp=0, cw=0, cr=0, out=0, cost=0.0); used = []; n_search = 0; t0 = time.time(); stop = None
    for turn in range(12):
        m = client.messages.create(model=MODELS[model], max_tokens=16000, system=SYS + " Carry the whole request through to the last step; tool results come from the live systems.", tools=tools, messages=msgs,
                                   output_config={"effort": "medium"}, cache_control={"type": "ephemeral"})
        u = m.usage
        tot["inp"] += u.input_tokens; tot["cw"] += u.cache_creation_input_tokens or 0
        tot["cr"] += u.cache_read_input_tokens or 0; tot["out"] += u.output_tokens; tot["cost"] += cost(model, u)
        stop = m.stop_reason
        msgs.append({"role": "assistant", "content": m.content})
        calls = [b for b in m.content if b.type == "tool_use"]
        n_search += sum(1 for b in m.content if b.type == "server_tool_use")
        if stop == "pause_turn": continue
        if not calls: break
        used += [b.name for b in calls]
        msgs.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": b.id, "content": fake(chain, b.name, b.input)} for b in calls]})
    i, o, _ = PRICE[model]
    r = dict(model=model, arm=arm, chain=chain, rep=rep, turns=turn + 1, tools_used=used, n_search=n_search, stop=stop,
             secs=round(time.time() - t0, 1), **tot,
             cost_nocache=(tot["inp"] + tot["cw"] + tot["cr"]) * i / 1e6 + tot["out"] * o / 1e6)
    with LOCK:
        open(HERE / "sessions.jsonl", "a").write(json.dumps(r) + "\n")
        print(f'{model:6} {arm:5} {chain:8} r{rep} turns={r["turns"]} tools={used} s={n_search} in={tot["inp"]} cw={tot["cw"]} cr={tot["cr"]} out={tot["out"]} ${tot["cost"]:.4f} nocache ${r["cost_nocache"]:.4f}', flush=True)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--models", default="haiku"); ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--arms", default="all,bm25"); ap.add_argument("--only", default="")
    a = ap.parse_args()
    for model in a.models.split(","):
        for arm in a.arms.split(","):
            jobs = [(model, arm, c, r) for r in range(a.reps) for c in CHAINS if not a.only or c in a.only.split(",")]
            run(*jobs[0])  # warm caches
            with ThreadPoolExecutor(4) as ex: list(ex.map(lambda j: run(*j), jobs[1:]))
