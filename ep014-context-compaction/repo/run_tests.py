"""Run all five projects' tests: python3 run_tests.py"""
import os, subprocess, sys

JOBS = ["shop", "slug", "pager", "report", "store"]
HERE = os.path.dirname(os.path.abspath(__file__))
bad = 0
for job in JOBS:
    p = subprocess.run([sys.executable, "-B", "run_tests.py"], cwd=os.path.join(HERE, job),
                       capture_output=True, text=True, timeout=60)
    ok = p.returncode == 0
    bad += not ok
    print(f"=== {job}: {'PASS' if ok else 'FAIL'}")
    if not ok:
        print((p.stdout + p.stderr)[-1200:])
print(f"{bad} of {len(JOBS)} projects failing")
sys.exit(1 if bad else 0)
