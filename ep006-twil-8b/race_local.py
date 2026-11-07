"""EP006 race: TwIL-8B on this Mac inside the EP005 harness, same 5 tasks and prompts as EP005.
Usage: python3 race_local.py [runs] [tag]   (needs llama-server on :8080). Appends to results.jsonl."""
import json, os, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import local_harness

EP5 = os.path.join(HERE, "..", "..", "EP005-agent-harness", "lab")
sys.path.insert(0, EP5)
from race import TASKS   # identical task prompts to EP005

OUT = os.path.join(HERE, "results.jsonl")


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    tag = sys.argv[2] if len(sys.argv) > 2 else "twil8b"
    only = os.environ.get("ONLY", "").split(",") if os.environ.get("ONLY") else list(TASKS)
    start = int(os.environ.get("START", "0"))
    for i in range(start, start + runs):
        for task in only:
            d = os.path.join(HERE, "runs", f"{tag}-{task}-{i}-{time.time_ns()}")
            shutil.copytree(os.path.join(EP5, "tasks", task), d, ignore=shutil.ignore_patterns("__pycache__"))
            t = time.time(); cwd = os.getcwd(); os.chdir(d)
            try:
                turns, usage = local_harness.agent(TASKS[task])
                r = {"turns": turns, "per_call": usage}
            except Exception as e:
                r = {"error": repr(e)[:400]}
            finally:
                os.chdir(cwd)
            ok = subprocess.run([sys.executable, "-B", "run_tests.py"], cwd=d, capture_output=True).returncode == 0
            pc = r.get("per_call", [])
            r.update(cfg=tag, task=task, run=i, secs=round(time.time() - t, 1), passed=ok,
                     prompt_tokens=sum(u.get("prompt_tokens", 0) for u in pc), completion_tokens=sum(u.get("completion_tokens", 0) for u in pc),
                     at=time.strftime("%Y-%m-%d %H:%M:%S"))
            open(OUT, "a").write(json.dumps(r) + "\n")
            print(tag, task, i, "pass" if ok else "FAIL", r.get("turns"), r["secs"], "s", r["prompt_tokens"], r["completion_tokens"],
                  r.get("error", ""), flush=True)


if __name__ == "__main__":
    main()
