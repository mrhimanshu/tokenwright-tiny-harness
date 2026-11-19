"""EP019: ask Claude models to read values off the invoices, with a stated confidence per answer.
Usage: python run.py [repeats=3]   -> appends to lab/results.jsonl (one row per doc x model x repeat), resumable."""
import concurrent.futures as cf
import json
import os
import re
import sys
import time

import anthropic

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = ["claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"]
PROMPT = """You are reading an invoice for an accounts-payable system. Answer each question from the document only.

<document>
{doc}
</document>

Questions:
{qs}

For every question return:
- "answer": the value as a string, or null if the document does not contain it (do not guess)
- "confidence": an integer 0-100, the probability that your answer (including null) is exactly correct.
  We will auto-approve answers with confidence 90 or more and send the rest to a human, so be honest.

Reply with JSON only, keyed by question id, e.g. {{"amount_due": {{"answer": "123.45", "confidence": 87}}, ...}}"""


def call(client, model, doc, rep):
    qs = "\n".join(f'- {q["id"]}: {q["q"]}' for q in doc["questions"])
    for attempt in range(6):
        try:
            t0 = time.time()
            r = client.messages.create(model=model, max_tokens=1500,
                                       messages=[{"role": "user", "content": PROMPT.format(doc=doc["text"], qs=qs)}])
            text = "".join(b.text for b in r.content if b.type == "text")
            m = re.search(r"\{.*\}", text, re.S)
            parsed = json.loads(m.group(0)) if m else None
            return {"doc_id": doc["doc_id"], "model": model, "rep": rep, "raw": text, "parsed": parsed,
                    "in_tok": r.usage.input_tokens, "out_tok": r.usage.output_tokens, "sec": round(time.time() - t0, 2)}
        except (anthropic.APIStatusError, anthropic.APIConnectionError, json.JSONDecodeError) as e:
            err = str(e)[:200]
            time.sleep(3 * (attempt + 1))
    return {"doc_id": doc["doc_id"], "model": model, "rep": rep, "error": err}


def main():
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    tag = sys.argv[2] if len(sys.argv) > 2 else ""
    client = anthropic.Anthropic(api_key=open(os.path.expanduser("~/.config/anthropic/key")).read().strip())
    docs = [json.loads(l) for l in open(os.path.join(HERE, f"docs{tag}.jsonl"))]
    out = os.path.join(HERE, f"results{tag}.jsonl")
    done = set()
    if os.path.exists(out):
        for l in open(out):
            r = json.loads(l)
            if r.get("parsed") is not None:
                done.add((r["doc_id"], r["model"], r["rep"]))
    jobs = [(m, d, k) for k in range(reps) for m in MODELS for d in docs if (d["doc_id"], m, k) not in done]
    print(len(jobs), "calls to make", flush=True)
    with open(out, "a") as f, cf.ThreadPoolExecutor(8) as ex:
        futs = [ex.submit(call, client, m, d, k) for m, d, k in jobs]
        for i, fu in enumerate(cf.as_completed(futs)):
            r = fu.result()
            f.write(json.dumps(r) + "\n")
            f.flush()
            if i % 20 == 0:
                print(i, r["model"], r["doc_id"], "ERR" if "error" in r else "ok", flush=True)


if __name__ == "__main__":
    main()
