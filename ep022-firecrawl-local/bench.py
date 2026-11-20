"""EP022 bench: scrape the same pages with each tool, sequentially, N rounds (tool order rotated per round).
Memory = PSS summed over the tool's whole process tree (server + any Chrome it starts), sampled every 50 ms.
Idle = PSS 5 s after the tool reports ready, before the first request.
usage: python bench.py <tool> <round>   -> results.jsonl (one row per page) + mem.jsonl (one row per run)
tools: fc_local (firecrawl-local serve, browser auto, cloud off) · fc_static (browser never, cloud off)
       fc_cloud (browser auto, FIRECRAWL_CLOUD=auto = default) · trafilatura · crawl4ai
"""
import os, sys, json, time, subprocess, threading, signal
import psutil, requests

HERE = os.path.dirname(os.path.abspath(__file__))
URLS = json.load(open(os.path.join(HERE, "urls.json")))
FC = os.path.expanduser("~/.cargo/bin/firecrawl-local")
CHROME = "/opt/ms-playwright/chromium-1254/chrome-linux64/chrome"
PY = os.path.join(HERE, ".venv/bin/python")
os.makedirs(os.path.join(HERE, "md"), exist_ok=True)


def tree_pss(p):
    tot = 0
    try:
        procs = [p] + p.children(recursive=True)
    except psutil.NoSuchProcess:
        return 0, 0
    for q in procs:
        try:
            tot += q.memory_full_info().pss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return tot, len(procs)


class Sampler(threading.Thread):
    def __init__(self, p):
        super().__init__(daemon=True); self.p = p; self.peak = 0; self.maxprocs = 0; self.stop = False; self.series = []

    def run(self):
        t0 = time.time()
        while not self.stop:
            m, n = tree_pss(self.p)
            self.peak = max(self.peak, m); self.maxprocs = max(self.maxprocs, n)
            self.series.append((round(time.time() - t0, 2), m))
            time.sleep(0.05)


def run_fc(tool, rnd):
    env = dict(os.environ, FIRECRAWL_CHROME_PATH=CHROME, FIRECRAWL_LOCAL_HOME="/tmp/fclocal_home")
    env["FIRECRAWL_CLOUD"] = "auto" if tool == "fc_cloud" else "off"
    env["FIRECRAWL_LOCAL_BROWSER"] = "never" if tool == "fc_static" else "auto"
    t_start = time.time()
    proc = subprocess.Popen([FC, "serve", "--port", "3102"], env=env, stdout=subprocess.DEVNULL, stderr=open(f"/tmp/fc_{tool}.err", "w"))
    p = psutil.Process(proc.pid)
    for _ in range(300):
        try:
            if requests.get("http://127.0.0.1:3102/health", timeout=1).ok:
                break
        except Exception:
            time.sleep(0.05)
    ready = time.time() - t_start
    time.sleep(5)
    idle, idle_n = tree_pss(p)
    s = Sampler(p); s.start()
    rows = []
    t_all = time.time()
    for u in URLS:
        t = time.time()
        try:
            r = requests.post("http://127.0.0.1:3102/v2/scrape", json={"url": u["url"], "formats": ["markdown"], "timeout": 45000}, timeout=90)
            j = r.json(); d = j.get("data") or {}
            md = d.get("markdown") or ""
            meta = d.get("metadata") or {}
            extra = {"http": r.status_code, "warning": d.get("warning") or j.get("warning") or j.get("error"),
                     "source": d.get("source") or meta.get("source"), "blocked": d.get("blocked"),
                     "status": meta.get("statusCode")}
        except Exception as e:
            md = ""; extra = {"error": repr(e)[:300]}
        dt = time.time() - t
        rows.append(dict(tool=tool, round=rnd, id=u["id"], kind=u["kind"], secs=round(dt, 3), chars=len(md), **extra))
        open(os.path.join(HERE, "md", f"{tool}__{u['id']}__r{rnd}.md"), "w").write(md)
    total = time.time() - t_all
    time.sleep(1)
    s.stop = True; s.join()
    after, _ = tree_pss(p)
    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(10)
    except Exception:
        proc.kill()
    return rows, dict(tool=tool, round=rnd, ready_s=round(ready, 3), idle_mb=idle / 2**20, idle_procs=idle_n,
                      peak_mb=s.peak / 2**20, max_procs=s.maxprocs, after_mb=after / 2**20, total_s=total, series=s.series[::10])


def run_py(tool, rnd):
    proc = subprocess.Popen([PY, os.path.join(HERE, "worker.py"), tool, str(rnd)], stdout=subprocess.PIPE, text=True,
                            env=dict(os.environ, PLAYWRIGHT_BROWSERS_PATH="/tmp/pw-browsers"))
    p = psutil.Process(proc.pid)
    t_start = time.time()
    line = proc.stdout.readline()
    assert line.strip() == "READY", line
    ready = time.time() - t_start
    time.sleep(5)
    idle, idle_n = tree_pss(p)
    s = Sampler(p); s.start()
    t_all = time.time()
    proc.stdout.readline()  # GO ack
    rows = []
    for line in proc.stdout:
        if line.startswith("{"):
            rows.append(json.loads(line))
        if line.strip() == "DONE":
            break
    total = time.time() - t_all
    s.stop = True; s.join()
    after, _ = tree_pss(p)
    proc.wait(60)
    return rows, dict(tool=tool, round=rnd, ready_s=round(ready, 3), idle_mb=idle / 2**20, idle_procs=idle_n,
                      peak_mb=s.peak / 2**20, max_procs=s.maxprocs, after_mb=after / 2**20, total_s=total, series=s.series[::10])


if __name__ == "__main__":
    tool, rnd = sys.argv[1], int(sys.argv[2])
    rows, mem = (run_fc if tool.startswith("fc_") else run_py)(tool, rnd)
    with open(os.path.join(HERE, "results.jsonl"), "a") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    with open(os.path.join(HERE, "mem.jsonl"), "a") as f:
        f.write(json.dumps(mem) + "\n")
    ok = sum(1 for r in rows if r["chars"] > 200)
    print(f"{tool} r{rnd}: ready {mem['ready_s']:.2f}s idle {mem['idle_mb']:.1f} MB peak {mem['peak_mb']:.0f} MB "
          f"procs {mem['max_procs']} total {mem['total_s']:.1f}s ok {ok}/{len(rows)}", flush=True)
