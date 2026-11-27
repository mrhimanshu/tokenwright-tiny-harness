#!/usr/bin/env python3
"""RAG answer step: give Claude the retrieved paragraphs, get a short answer.

usage: run_qa.py <model> <cond> <run> [limit]
  cond: k5 | k20 | k70 | gold | k70cot   (retrieval from data/retrieval_q4.json)
appends to results/qa.jsonl (skips done (model,cond,run,id))
"""
import json, sys, time, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import anthropic

L = Path(__file__).parent
D = L / "data"
PRICE = {"claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.10, 0.50)}
model, cond, run = sys.argv[1], sys.argv[2], int(sys.argv[3])
limit = int(sys.argv[4]) if len(sys.argv) > 4 else None

qs = json.loads((D / "questions.json").read_text())[:limit]
corpus = json.loads((D / "corpus.json").read_text())
ret = json.loads((D / "retrieval_q4.json").read_text())
out = L / "results" / "qa.jsonl"
out.parent.mkdir(exist_ok=True)
done = set()
if out.exists():
    for l in out.read_text().splitlines():
        r = json.loads(l)
        done.add((r["model"], r["cond"], r["run"], r["id"]))

PLAIN = ("Answer the question using only the context below. Reply with the short answer only (a name, date, number, "
         "yes or no, or a short phrase), no explanation. If the context does not contain the answer, reply exactly: "
         "not in context\n\n{ctx}\n\nQuestion: {q}")
COT = ("Answer the question using only the context below. The question needs more than one fact. First write the "
       "chain of facts you need as short steps (entity -> relation -> entity), and find each one in the context. "
       "Then write the final short answer (a name, date, number, yes or no, or a short phrase) on the last line as "
       "ANSWER: <answer>. If the context does not contain what you need, write ANSWER: not in context\n\n{ctx}\n\n"
       "Question: {q}")


JOIN = ("Answer the question using only the context below. The answer often needs two facts from two different "
        "paragraphs: combine them. Reply with the short answer only (a name, date, number, yes or no, or a short phrase), "
        "no explanation. Only if a fact you need is truly missing from the context, reply exactly: not in context\n\n{ctx}\n\n"
        "Question: {q}")


def ids_for(q):
    if cond.startswith("gold"):
        return q["gold_ids"]
    k = int(cond[1:].replace("cot", "").replace("join", ""))
    return ret[q["id"]][:k]


def ctx_for(ids):
    # most relevant first, like a normal top-k RAG prompt
    return "\n\n".join(f"[{n+1}] {corpus[i]['title']}\n{corpus[i]['text']}" for n, i in enumerate(ids))


key = Path("~/.config/anthropic/key").expanduser().read_text().strip()
client = anthropic.Anthropic(api_key=key, max_retries=6)
lock = threading.Lock()
spent = [0.0]


def one(q):
    if (model, cond, run, q["id"]) in done:
        return
    ids = ids_for(q)
    prompt = (COT if cond.endswith("cot") else JOIN if cond.endswith("join") else PLAIN).format(ctx=ctx_for(ids), q=q["question"])
    t = time.time()
    msg = client.messages.create(model=model, max_tokens=8000 if cond.endswith("cot") else 4000,
                                 output_config={"effort": "low"},
                                 messages=[{"role": "user", "content": prompt}])
    text = "".join(b.text for b in msg.content if b.type == "text").strip()
    ans = text
    if cond.endswith("cot"):
        lines = [x for x in text.splitlines() if x.strip().upper().startswith("ANSWER:")]
        ans = lines[-1].split(":", 1)[1].strip() if lines else text.splitlines()[-1] if text else ""
    pi, po = PRICE[model]
    cost = msg.usage.input_tokens / 1e6 * pi + msg.usage.output_tokens / 1e6 * po
    rec = dict(model=model, cond=cond, run=run, id=q["id"], ctx_ids=ids, answer=ans, raw=text,
               input_tokens=msg.usage.input_tokens, output_tokens=msg.usage.output_tokens,
               cost_usd=round(cost, 6), seconds=round(time.time() - t, 2), stop_reason=msg.stop_reason,
               stop_details=getattr(msg, "stop_details", None) and str(msg.stop_details),
               thinking_tokens=getattr(getattr(msg.usage, "output_tokens_details", None), "thinking_tokens", None))
    with lock:
        spent[0] += cost
        with out.open("a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


with ThreadPoolExecutor(8) as ex:
    list(ex.map(one, qs))
print(f"QADONE {model} {cond} run{run} ${spent[0]:.3f}", flush=True)
