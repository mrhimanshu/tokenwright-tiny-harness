#!/usr/bin/env python3
"""usage: run.py <model> <arm> <run> [limit]   arms: paper | predict
appends results/results.jsonl; skips done (model,arm,run,id)."""
import json, sys, time, re, threading, os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import anthropic
L = Path(__file__).parent
PRICE = {"claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.10, 0.50)}
model, arm, run = sys.argv[1], sys.argv[2], int(sys.argv[3])
limit = int(sys.argv[4]) if len(sys.argv) > 4 else None
items = json.load(open(L / os.environ.get("SAMPLE","data/sample.json")))[:limit] if limit is None else json.load(open(L / os.environ.get("SAMPLE","data/sample.json")))
if limit: items = items[::max(1, len(items)//limit)][:limit]
SYS_PAPER = (L / "src/system_prompt.txt").read_text()
INS_PAPER = (L / "src/instruction_prompt.txt").read_text()
SYS_PREDICT = ("You read transcripts of real conversations (meetings and TV scenes) and predict who talks next. "
               "Real people often jump in without being addressed, and often stay quiet even when their name is said.")
INS_PREDICT = ("The transcript above ends with the most recent utterance (marked [MOST RECENT]), then a pause. "
               "Predict: is {target_speaker} the very next person to speak?\n\n"
               "Reply in this format:\n<reasoning>one sentence</reasoning>\n<decision>SPEAK</decision> if "
               "{target_speaker} speaks next, or <decision>SILENT</decision> if someone else does.")
MAXCTX = 40
def transcript(r):
    lines = [f"Speakers: {', '.join(r['all_speakers'])}", "", "Conversation:"]
    for t in r["context_turns"][-MAXCTX:]:
        lines.append(f"{t['speaker']}: {t['text']}")
    lines.append(f"[MOST RECENT] {r['current_turn']['speaker']}: {r['current_turn']['text']}")
    return "\n".join(lines)
out = L / os.environ.get("OUT","results/results.jsonl"); out.parent.mkdir(exist_ok=True)
done = set()
if out.exists():
    for l in out.read_text().splitlines():
        x = json.loads(l); done.add((x["model"], x["arm"], x["run"], x["id"]))
key = Path("~/.config/anthropic/key").expanduser().read_text().strip()
client = anthropic.Anthropic(api_key=key, max_retries=8)
lock = threading.Lock(); spent = [0.0]
def one(r):
    if (model, arm, run, r["decision_point_id"]) in done: return
    sysp, ins = (SYS_PAPER, INS_PAPER) if arm == "paper" else (SYS_PREDICT, INS_PREDICT)
    user = transcript(r) + "\n\n" + ins.format(target_speaker=r["target_speaker"])
    t = time.time()
    msg = client.messages.create(model=model, max_tokens=4000, output_config={"effort": "low"},
                                 system=sysp, messages=[{"role": "user", "content": user}])
    text = "".join(b.text for b in msg.content if b.type == "text")
    m = re.findall(r"<decision>\s*(SPEAK|SILENT)\s*</decision>", text, re.I)
    pred = m[-1].upper() if m else None
    pi, po = PRICE[model]
    cost = msg.usage.input_tokens / 1e6 * pi + msg.usage.output_tokens / 1e6 * po
    rec = dict(model=model, arm=arm, run=run, id=r["decision_point_id"], corpus=r["corpus"], category=r["category"],
               label=r["decision"], pred=pred, text=text, stop_reason=msg.stop_reason,
               in_tok=msg.usage.input_tokens, out_tok=msg.usage.output_tokens, cost=cost, secs=round(time.time()-t, 2),
               ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    with lock:
        spent[0] += cost
        with open(out, "a") as f: f.write(json.dumps(rec) + "\n")
with ThreadPoolExecutor(8) as ex: list(ex.map(one, items))
print(f"{model} {arm} run{run}: ${spent[0]:.3f}")
