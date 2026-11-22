"""Turn SenseNova Loop-9B's loop dial: for each loop count, start the fork's llama-server with the GGUF metadata
rewritten by replan_gguf.py (block_count + loop.count), run the 60 tasks (greedy, no thinking), record answers, speed and RSS.
Usage: run_loops.py <loops csv> [results.jsonl]"""
import json, os, re, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = "/tmp/ep025/snllama/build/bin"
MODEL = os.path.join(HERE, "models", "SenseNova-Loop-9B-Q4_K_M.gguf")
PORT = 8137
STORED, LSTART, LEND = 32, 4, 28
NEXTN = int(os.environ.get("NEXTN", "1"))
SYS = "Answer with only the final answer (a number or a city name). No working."


def block_count(k):
    return STORED + (k - 1) * (LEND - LSTART) + NEXTN


def model_for(k):
    # loop 2 = the official file untouched; others = replan_gguf.py copies (same tensors, new loop plan)
    return MODEL if k == 2 else os.path.join(HERE, "models", f"loop{k}.gguf")


def post(path, body, timeout=900):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def rss_mb(pid):
    with open(f"/proc/{pid}/status") as f:
        for line in f:
            if line.startswith("VmRSS"):
                return int(line.split()[1]) / 1024


def start(k, log):
    cmd = [f"{BIN}/llama-server", "-m", model_for(k), "-c", "2048", "-t", "4", "--port", str(PORT), "-np", "1",
           "--no-warmup"]
    p = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
    for _ in range(600):
        time.sleep(1)
        if p.poll() is not None:
            raise RuntimeError(f"server exited for loops={k}")
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2)
            return p
        except Exception:
            pass
    raise RuntimeError("server timeout")


def score(txt, gold):
    if isinstance(gold, str):
        return gold.lower() in txt.lower()
    return parse(txt) == gold


def parse(txt):
    txt = re.sub(r"<think>.*?</think>", "", txt, flags=re.S)
    m = re.findall(r"-?\d[\d,]*", txt)
    return int(m[-1].replace(",", "")) if m else None


def main():
    loops = [int(x) for x in sys.argv[1].split(",")]
    out_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "results.jsonl")
    tasks = [json.loads(l) for l in open(os.path.join(HERE, "tasks.jsonl"))]
    for k in loops:
        log = open(os.path.join(HERE, f"server_loop{k}.log"), "w")
        p = start(k, log)
        try:
            for t in tasks:
                t0 = time.time()
                r = post("/v1/chat/completions", {
                    "messages": [{"role": "system", "content": SYS}, {"role": "user", "content": t["q"]}],
                    "temperature": 0, "max_tokens": 12, "chat_template_kwargs": {"enable_thinking": False}})
                txt = r["choices"][0]["message"].get("content") or ""
                tm = r.get("timings", {})
                row = dict(model="sensenova-loop-9b-q4km", loops=k, id=t["id"], set=t["set"], kind=t["kind"], gold=t["a"],
                           out=txt, pred=parse(txt), ok=score(txt, t["a"]), wall_s=round(time.time() - t0, 2),
                           prompt_tps=tm.get("prompt_per_second"), gen_tps=tm.get("predicted_per_second"),
                           rss_mb=round(rss_mb(p.pid)))
                with open(out_path, "a") as f:
                    f.write(json.dumps(row) + "\n")
                print(k, t["id"], row["ok"], repr(txt[:30]), row["gen_tps"], flush=True)
        finally:
            p.terminate()
            p.wait()


if __name__ == "__main__":
    main()
