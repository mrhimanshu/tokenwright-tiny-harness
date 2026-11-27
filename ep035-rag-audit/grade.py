#!/usr/bin/env python3
"""Grade results/qa.jsonl like the paper: string match first, then an LLM judge (Sonnet 5.5) for the rest.
Then split every wrong answer into retrieval failure vs reasoning failure (paper rule) and a strict rule.

writes results/graded.jsonl, results/judge.jsonl (cache)
"""
import json, re, string, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import anthropic

L = Path(__file__).parent
D, R = L / "data", L / "results"
qs = {q["id"]: q for q in json.loads((D / "questions.json").read_text())}
corpus = json.loads((D / "corpus.json").read_text())
JUDGE = "claude-sonnet-5-5"


def norm(s):
    s = s.lower()
    s = "".join(ch if ch not in set(string.punctuation) else " " for ch in s)
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    return " ".join(s.split())


def contains(hay, needle):
    return bool(needle) and re.search(r"(^| )" + re.escape(needle) + r"( |$)", hay) is not None


def abstain(a):
    return "not in context" in a.lower()


def string_correct(pred, gold):
    p, g = norm(pred), norm(gold)
    if not p or abstain(pred):
        return False
    if p == g or contains(p, g):
        return True
    # last-token / subset check: every predicted token is in the gold answer (e.g. "Ronan" for "Saoirse Ronan")
    if g not in ("yes", "no") and set(p.split()) <= set(g.split()) and len(p) >= 3:
        return True
    return False


key = Path("~/.config/anthropic/key").expanduser().read_text().strip()
client = anthropic.Anthropic(api_key=key, max_retries=6)
cache_f = R / "judge.jsonl"
cache = {}
if cache_f.exists():
    for l in cache_f.read_text().splitlines():
        r = json.loads(l)
        cache[(r["id"], r["pred_norm"])] = r
lock = threading.Lock()

JP = ("You grade answers to a quiz. Question: {q}\nReference answer: {g}\nCandidate answer: {p}\n"
      "Does the candidate give the same answer as the reference (same entity, date, number or yes/no; extra words or "
      "a more/less specific but equivalent form are fine)? Reply with one word: CORRECT or WRONG.")


def judge(qid, pred):
    k = (qid, norm(pred))
    if k in cache:
        return cache[k]["verdict"]
    q = qs[qid]
    msg = client.messages.create(model=JUDGE, max_tokens=20, output_config={"effort": "low"},
                                 messages=[{"role": "user", "content": JP.format(q=q["question"], g=q["answer"], p=pred)}])
    t = "".join(b.text for b in msg.content if b.type == "text").strip().upper()
    v = "CORRECT" if t.startswith("CORRECT") else "WRONG"
    rec = dict(id=qid, pred_norm=k[1], verdict=v, raw=t, input_tokens=msg.usage.input_tokens,
               output_tokens=msg.usage.output_tokens,
               cost_usd=round(msg.usage.input_tokens * 2e-6 + msg.usage.output_tokens * 1e-5, 6))
    with lock:
        cache[k] = rec
        with cache_f.open("a") as f:
            f.write(json.dumps(rec) + "\n")
    return v


rows = [json.loads(l) for l in (R / "qa.jsonl").read_text().splitlines()]
need = [(r["id"], r["answer"]) for r in rows
        if not string_correct(r["answer"], qs[r["id"]]["answer"]) and not abstain(r["answer"]) and norm(r["answer"])]
uniq = list({(i, norm(a)): (i, a) for i, a in need}.values())
with ThreadPoolExecutor(8) as ex:
    list(ex.map(lambda x: judge(*x), uniq))

out = []
for r in rows:
    q = qs[r["id"]]
    ctx = norm(" ".join(corpus[i]["title"] + " " + corpus[i]["text"] for i in r["ctx_ids"]))
    sc = string_correct(r["answer"], q["answer"])
    if sc:
        how, ok = "string", True
    elif abstain(r["answer"]) or not norm(r["answer"]):
        how, ok = "abstain", False
    else:
        ok = judge(r["id"], r["answer"]) == "CORRECT"
        how = "judge"
    gold_in_ctx = contains(ctx, norm(q["answer"]))
    both = set(q["gold_ids"]) <= set(r["ctx_ids"])
    err = None
    if not ok:
        err = "reasoning" if gold_in_ctx else "retrieval"
    out.append(dict(model=r["model"], cond=r["cond"], run=r["run"], id=r["id"], answer=r["answer"],
                    gold=q["answer"], type=q["type"], correct=ok, how=how, abstain=abstain(r["answer"]),
                    gold_in_ctx=gold_in_ctx, both_gold_paras=both, n_gold_present=len(set(q["gold_ids"]) & set(r["ctx_ids"])),
                    err=err, input_tokens=r["input_tokens"], cost_usd=r["cost_usd"]))
(R / "graded.jsonl").write_text("\n".join(json.dumps(o) for o in out) + "\n")
print("graded", len(out), "judge calls cached", len(cache))
