"""EP033: blind quality check of the "lenient" arm (lenience=1.0, accept every drafted token) vs the exact output.
For each prompt (rep 0), Claude Sonnet 5.5 sees the prompt + two answers in random order (A/B) and says which is better
or "tie", plus whether either has an error (wrong fact/number, broken code, repetition, cut-off garbage). Run 3 times per pair
with swapped order. Also counts how many tokens differ (first divergence char) between lenient and exact.
Run with the Tokenwright venv: /data/projects/Tokenwright/.venv/bin/python judge.py"""
import json, os, random, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ep032-tool-search"))
from common import client, cost
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prompts import PROMPTS

HERE = os.path.dirname(os.path.abspath(__file__))
R = [json.loads(l) for l in open(os.path.join(HERE, "paired.jsonl"))]
exact = {(r["task"], r["prompt"]): r["text"] for r in R if r["arm"] == "off" and r["rep"] == 0}
len_ = {(r["task"], r["prompt"]): r["text"] for r in R if r["arm"] == "lenient" and r["rep"] == 0}
SYS = ("You compare two answers to the same request, written by a small on-device model with a 256-token output cap "
       "(so both may stop mid-sentence at the end; do not penalise that). Judge correctness first (facts and numbers kept from the "
       "source text, working code, following the instruction), then clarity. Reply with JSON only: "
       '{"better": "A" | "B" | "tie", "errors_A": [short strings], "errors_B": [short strings], "why": "one sentence"}')
rng = random.Random(7); out = open(os.path.join(HERE, "judge.jsonl"), "w"); spend = 0
for key in sorted(exact):
    if key not in len_:
        continue
    e, l = exact[key], len_[key]
    div = next((i for i, (x, y) in enumerate(zip(e, l)) if x != y), min(len(e), len(l)))
    for trial in range(3):
        swap = (trial % 2 == 1) if trial < 2 else rng.random() < .5
        A, B = (l, e) if swap else (e, l)
        msg = client.messages.create(model="claude-sonnet-5-5", max_tokens=600, system=SYS, messages=[{"role": "user", "content":
              f"REQUEST:\n{PROMPTS[key[0]][key[1]]}\n\nANSWER A:\n{A}\n\nANSWER B:\n{B}"}])
        spend += cost("sonnet", msg.usage)
        txt = msg.content[0].text
        m = re.search(r"\{.*\}", txt, re.S)
        try:
            j = json.loads(m.group(0))
        except Exception:
            j = {"better": "parse_error", "raw": txt}
        b = j.get("better")
        winner = "tie" if b == "tie" else ("lenient" if (b == "A") == swap else "exact") if b in ("A", "B") else b
        err_len = j.get("errors_A" if swap else "errors_B", []); err_ex = j.get("errors_B" if swap else "errors_A", [])
        rec = dict(task=key[0], prompt=key[1], trial=trial, swap=swap, winner=winner, err_lenient=err_len, err_exact=err_ex,
                   why=j.get("why"), first_diff_char=div, len_exact=len(e), len_lenient=len(l))
        out.write(json.dumps(rec) + "\n"); out.flush()
        print(key, trial, winner, "| lenient errs:", err_len, "| exact errs:", err_ex)
print("spend $%.3f" % spend)
