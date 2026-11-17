"""EP015: can Claude solve Sudoku-Extreme puzzles by thinking? Same puzzles for every model, adaptive thinking, effort high.
Usage: ../../.venv/bin/python claude_solve.py --model claude-haiku-5-5 --n 10 --workers 5 [--mode think|code]
  think = solve it in its head (answer = 81 digits)
  code  = write a Python solver; we run that code on all 500 test puzzles (see run_codegen in this file)
"""
import argparse, concurrent.futures as cf, json, os, re, subprocess, sys, threading, time
from pathlib import Path
import anthropic

HERE = Path(__file__).resolve().parent
os.environ["ANTHROPIC_API_KEY"] = open(os.path.expanduser("~/.config/anthropic/key")).read().strip()
PRICE = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2, 10), "claude-opus-5-5": (4, 20)}
LOCK = threading.Lock()
TEST = [json.loads(l) for l in open(HERE / "test_sample.jsonl")]

THINK_PROMPT = """Solve this Sudoku puzzle. It is given row by row, 81 characters, '.' means an empty cell.

{grid}

Same puzzle as a 9x9 grid:
{pretty}

Work it out carefully. When you are done, give the full solution as exactly 81 digits (row by row, no spaces) inside <answer></answer>."""

CODE_PROMPT = """Write a Python 3 function `solve(puzzle: str) -> str` that solves any 9x9 Sudoku.
Input: 81 characters row by row, '.' for empty cells. Output: the 81-digit solution string.
It will be run on several hundred of the hardest known Sudokus, so it must be correct and fast. Standard library only.
Reply with one ```python code block containing the full module and nothing else."""


def pretty(q):
    rows = [q[i * 9:(i + 1) * 9] for i in range(9)]
    return "\n".join(" ".join(r) for r in rows)


def valid(q, a):
    if not re.fullmatch(r"[1-9]{81}", a or ""):
        return False
    if any(c != "." and c != a[i] for i, c in enumerate(q)):
        return False
    g = [a[i * 9:(i + 1) * 9] for i in range(9)]
    units = [list(r) for r in g] + [[g[r][c] for r in range(9)] for c in range(9)] + \
            [[g[r][c] for r in range(br, br + 3) for c in range(bc, bc + 3)] for br in (0, 3, 6) for bc in (0, 3, 6)]
    return all(sorted(u) == list("123456789") for u in units)


def call(client, **kw):
    for k in range(6):
        try:
            with client.messages.stream(**kw) as s:
                return s.get_final_message()
        except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
            print("retry", k, type(e).__name__, str(e)[:120], flush=True)
            time.sleep(5 * (k + 1))
    raise RuntimeError("API failed")


def cost(model, u):
    pin, pout = PRICE[model]
    return (u.input_tokens * pin + u.output_tokens * pout) / 1e6


def think_one(client, model, i, max_tokens):
    p = TEST[i]
    t0 = time.time()
    r = call(client, model=model, max_tokens=max_tokens, thinking={"type": "adaptive"}, output_config={"effort": "high"},
             messages=[{"role": "user", "content": THINK_PROMPT.format(grid=p["question"], pretty=pretty(p["question"]))}])
    dt = time.time() - t0
    text = "".join(b.text for b in r.content if b.type == "text")
    m = re.findall(r"<answer>\s*([0-9\s]+?)\s*</answer>", text)
    ans = re.sub(r"\s", "", m[-1]) if m else ""
    cells_right = sum(1 for a, b in zip(ans, p["answer"]) if a == b) if len(ans) == 81 else 0
    blanks = p["question"].count(".")
    blanks_right = sum(1 for k, c in enumerate(p["question"]) if c == "." and len(ans) == 81 and ans[k] == p["answer"][k])
    return dict(mode="think", model=model, puzzle=i, idx=p["idx"], source=p["source"], rating=p["rating"], clues=81 - blanks,
                answer=ans, correct=ans == p["answer"], valid=valid(p["question"], ans), cells_right=cells_right,
                blanks=blanks, blanks_right=blanks_right, stop=r.stop_reason, in_tok=r.usage.input_tokens,
                out_tok=r.usage.output_tokens, cost=round(cost(model, r.usage), 5), secs=round(dt, 1), text_tail=text[-600:])


def code_one(client, model, rep, max_tokens):
    t0 = time.time()
    r = call(client, model=model, max_tokens=max_tokens, thinking={"type": "adaptive"}, output_config={"effort": "high"},
             messages=[{"role": "user", "content": CODE_PROMPT}])
    dt = time.time() - t0
    text = "".join(b.text for b in r.content if b.type == "text")
    m = re.findall(r"```python\n(.*?)```", text, re.S)
    code = m[-1] if m else text
    f = HERE / "gen" / f"{model}-{rep}.py"
    f.parent.mkdir(exist_ok=True)
    f.write_text(code)
    run = run_codegen(f)
    return dict(mode="code", model=model, rep=rep, file=str(f.name), stop=r.stop_reason, in_tok=r.usage.input_tokens,
                out_tok=r.usage.output_tokens, cost=round(cost(model, r.usage), 5), secs=round(dt, 1), code_lines=code.count("\n") + 1,
                **run)


RUNNER = r'''
import importlib.util, json, sys, time
spec = importlib.util.spec_from_file_location("gen", sys.argv[1]); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
for line in sys.stdin:
    q = line.strip(); t = time.perf_counter()
    try: a = m.solve(q)
    except Exception as e: a = "ERR " + type(e).__name__
    print(json.dumps({"a": a, "ms": (time.perf_counter() - t) * 1000}), flush=True)
'''


def run_codegen(f, timeout=600):
    """Run the generated solver on all 500 test puzzles in one process (10 min total cap)."""
    inp = "\n".join(p["question"] for p in TEST) + "\n"
    try:
        r = subprocess.run([sys.executable, "-I", "-c", RUNNER, str(f)], input=inp, capture_output=True, text=True, timeout=timeout)
        out = r.stdout
        err = r.stderr[-300:]
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        err = "TIMEOUT"
    res = [json.loads(l) for l in out.splitlines() if l.startswith("{")]
    ok = sum(1 for p, x in zip(TEST, res) if x["a"] == p["answer"])
    ms = sorted(x["ms"] for x in res) or [0]
    return dict(n_run=len(res), n_ok=ok, n_total=len(TEST), median_ms=round(ms[len(ms) // 2], 2), max_ms=round(ms[-1], 1),
                total_s=round(sum(ms) / 1000, 2), run_err=err)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-haiku-5-5")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--mode", default="think")
    ap.add_argument("--max_tokens", type=int, default=24000)
    ap.add_argument("--out", default="results.jsonl")
    a = ap.parse_args()
    client = anthropic.Anthropic(max_retries=3, timeout=1800)
    fn = think_one if a.mode == "think" else code_one
    with cf.ThreadPoolExecutor(a.workers) as ex:
        futs = [ex.submit(fn, client, a.model, i, a.max_tokens) for i in range(a.start, a.start + a.n)]
        for fu in cf.as_completed(futs):
            try:
                res = fu.result()
            except Exception as e:
                res = dict(mode=a.mode, model=a.model, error=repr(e)[:300])
            with LOCK, open(HERE / a.out, "a") as f:
                f.write(json.dumps(res) + "\n")
            print({k: res.get(k) for k in ("model", "puzzle", "rep", "correct", "valid", "blanks_right", "blanks", "n_ok", "out_tok",
                                            "cost", "secs", "stop", "error")}, flush=True)
