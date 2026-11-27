#!/usr/bin/env python3
"""Send each test page to Claude (vision) and save the transcription.

usage: run_claude.py <model> <out.jsonl> page1.png ...
"""
import base64, json, sys, time
from pathlib import Path

import anthropic

PRICE = {"claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.10, 0.50)}
PROMPT = (
    "Transcribe this document page exactly, in reading order, as Markdown. Keep the original language and "
    "spelling (do not translate or correct). Write tables as Markdown tables. If there is a chart, write its "
    "data as a Markdown table with one row per category and the value read from the axis. Output only the "
    "transcription, nothing else."
)

model, out = sys.argv[1], Path(sys.argv[2])
key = Path("~/.config/anthropic/key").expanduser().read_text().strip()
client = anthropic.Anthropic(api_key=key)
done = {json.loads(l)["page"] for l in out.read_text().splitlines()} if out.exists() else set()

for p in sys.argv[3:]:
    pid = Path(p).stem
    if pid in done:
        continue
    b64 = base64.standard_b64encode(Path(p).read_bytes()).decode()
    t = time.time()
    msg = client.messages.create(
        model=model,
        max_tokens=8000,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
            {"type": "text", "text": PROMPT}]}],
    )
    dt = time.time() - t
    text = "".join(b.text for b in msg.content if b.type == "text")
    pi, po = PRICE[model]
    cost = msg.usage.input_tokens / 1e6 * pi + msg.usage.output_tokens / 1e6 * po
    rec = dict(model=model, page=pid, seconds=round(dt, 2), input_tokens=msg.usage.input_tokens,
               output_tokens=msg.usage.output_tokens, cost_usd=round(cost, 6), stop_reason=msg.stop_reason,
               stop_details=getattr(msg, "stop_details", None) and str(msg.stop_details), raw=text)
    with out.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[{model}] {pid}: {dt:.1f}s ${cost:.4f} {msg.stop_reason}", flush=True)
print("CLAUDEDONE", model)
