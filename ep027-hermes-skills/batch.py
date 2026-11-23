"""Run the teammate arms: months Feb/Mar/Apr x arms x reps, 3 at a time.
rep k uses the skill written by seed_r{(k % 3) + 1}."""
import itertools, subprocess, sys, json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

LAB = Path(__file__).resolve().parent
RUNS = Path("/data/renders/ep027/runs")
MONTHS = ["2026-02", "2026-03", "2026-04"]
ARMS = ["terse_noskill", "terse_skill", "brief_noskill"]
REPS = int(sys.argv[1]) if len(sys.argv) > 1 else 6
MODEL = sys.argv[2] if len(sys.argv) > 2 else "claude-haiku-5-5"
TAG = "" if MODEL == "claude-haiku-5-5" else "_" + MODEL.split("-")[1]

jobs = []
for rep, month, arm in itertools.product(range(REPS), MONTHS, ARMS):
    rid = f"{arm}_{month}_r{rep}{TAG}"
    if (RUNS / rid / "result.json").exists():
        continue
    cmd = [str(LAB / ".venv/bin/python"), str(LAB / "run_hermes.py"), "--run-id", rid, "--month", month, "--arm", arm,
           "--model", MODEL]
    if arm.endswith("_skill"):
        cmd += ["--skill-src", str(RUNS / f"seed_r{rep % 3 + 1}" / "hermes_home" / "skills")]
    jobs.append((rid, cmd))


def run(job):
    rid, cmd = job
    with open(LAB / "logs" / f"{rid}.log", "w") as f:
        p = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, timeout=900)
    return rid, p.returncode


print(f"{len(jobs)} jobs", flush=True)
with ThreadPoolExecutor(3) as ex:
    for rid, rc in ex.map(run, jobs):
        tail = (LAB / "logs" / f"{rid}.log").read_text().strip().splitlines()[-1:]
        print(rid, rc, tail[0][:220] if tail else "", flush=True)
print("BATCH DONE", flush=True)
