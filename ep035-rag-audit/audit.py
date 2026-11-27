#!/usr/bin/env python3
"""Audit every wrong answer of one (model, cond): Claude Opus 5.5 reads the question, the reference, the answer and
the two gold paragraphs (with whether each was in the answerer's context) and labels the real cause.

usage: audit.py <model> <cond>   -> results/audit.jsonl (cache by model,cond,id,answer)
"""
import json, re, sys, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import anthropic

L = Path(__file__).parent
D, R = L / "data", L / "results"
model, cond = sys.argv[1], sys.argv[2]
qs = {q["id"]: q for q in json.loads((D / "questions.json").read_text())}
corpus = json.loads((D / "corpus.json").read_text())
qa = {(r["model"], r["cond"], r["run"], r["id"]): r for r in map(json.loads, (R / "qa.jsonl").read_text().splitlines())}
graded = [json.loads(l) for l in (R / "graded.jsonl").read_text().splitlines()]
wrong = [g for g in graded if g["model"] == model and g["cond"] == cond and not g["correct"]]
out = R / "audit.jsonl"
done = set()
if out.exists():
    for l in out.read_text().splitlines():
        r = json.loads(l)
        done.add((r["model"], r["cond"], r["id"], r["answer"]))

P = """You are auditing one wrong answer from a retrieval-augmented QA system (HotpotQA, multi-hop).
Question: {q}
Reference answer (from the dataset): {gold}
System's answer: {ans}
The system was given {n} retrieved paragraphs. The two paragraphs the dataset marks as the evidence are below, each
marked IN CONTEXT or NOT IN CONTEXT (whether the system saw it).

{paras}

Pick the ONE best label for why this answer was scored wrong:
- grading_miss: the system's answer is actually correct or equivalent to the reference (the grader was too strict)
- bad_label: the reference answer is wrong, garbled, or the question is ambiguous/subjective so the system's answer is also defensible
- missing_evidence: a fact needed for the answer was not in the system's context (an evidence paragraph is NOT IN CONTEXT, or the evidence shown does not contain the needed fact)
- over_cautious: the system said "not in context" (or gave no answer) although the evidence it saw does contain everything needed
- reasoning_error: the needed evidence was in context and the system combined or compared it wrongly, or picked the wrong entity
Reply with JSON only: {{"label": "<one label>", "why": "<one short sentence>"}}"""

key = Path("~/.config/anthropic/key").expanduser().read_text().strip()
client = anthropic.Anthropic(api_key=key, max_retries=6)
lock = threading.Lock()


def one(g):
    if (model, cond, g["id"], g["answer"]) in done:
        return
    q = qs[g["id"]]
    r = qa[(g["model"], g["cond"], g["run"], g["id"])]
    paras = "\n\n".join(f"[{'IN CONTEXT' if i in r['ctx_ids'] else 'NOT IN CONTEXT'}] {corpus[i]['title']}\n{corpus[i]['text']}"
                        for i in q["gold_ids"])
    msg = client.messages.create(model="claude-opus-5-5", max_tokens=3000, output_config={"effort": "medium"},
                                 messages=[{"role": "user", "content": P.format(q=q["question"], gold=q["answer"],
                                                                                 ans=g["answer"] or "(empty)", n=len(r["ctx_ids"]), paras=paras)}])
    t = "".join(b.text for b in msg.content if b.type == "text")
    m = re.search(r'"label"\s*:\s*"(\w+)"', t)
    w = re.search(r'"why"\s*:\s*"(.*?)"\s*}', t, re.S)
    rec = dict(model=model, cond=cond, run=g["run"], id=g["id"], answer=g["answer"], gold=g["gold"], paper_err=g["err"],
               both_gold_paras=g["both_gold_paras"], label=m.group(1) if m else "PARSE_FAIL", why=w.group(1) if w else t[:300],
               cost_usd=round(msg.usage.input_tokens * 4e-6 + msg.usage.output_tokens * 2e-5, 6), stop_reason=msg.stop_reason)
    with lock:
        with out.open("a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# one audit per (id, answer): repeated identical wrong answers across runs share a label
uniq = list({(g["id"], g["answer"]): g for g in wrong}.values())
with ThreadPoolExecutor(6) as ex:
    list(ex.map(one, uniq))
print("AUDITDONE", model, cond, len(uniq))
