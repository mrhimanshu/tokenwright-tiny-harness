"""Run all tests without pytest: python3 run_tests.py"""
import importlib, sys, traceback
sys.path.insert(0, ".")
mod = importlib.import_module("tests.test_main")
fails = 0
for name in [n for n in dir(mod) if n.startswith("test_")]:
    try:
        getattr(mod, name)(); print("PASS", name)
    except BaseException:
        fails += 1; print("FAIL", name); traceback.print_exc(limit=1)
print(f"{fails} failed")
sys.exit(1 if fails else 0)
