#!/usr/bin/env python3
"""Sample HotpotQA dev questions, pool their paragraphs into one corpus, embed with BGE Base GGUF, retrieve.

usage: prep.py <n_questions> <gguf> <tag>
writes data/questions.json, data/corpus.json, data/emb_<tag>.npy, data/retrieval_<tag>.json
"""
import json, random, sys, time
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
from llama_cpp import Llama

D = Path(__file__).parent / "data"
N, GGUF, TAG = int(sys.argv[1]), sys.argv[2], sys.argv[3]
QPREFIX = "Represent this sentence for searching relevant passages: "

qfile, cfile = D / "questions.json", D / "corpus.json"
if not qfile.exists():
    rows = pq.read_table(D / "hotpot_val.parquet").to_pylist()
    random.Random(42).shuffle(rows)
    rows = rows[:N]
    corpus, idx = [], {}
    qs = []
    for r in rows:
        titles = r["context"]["title"]
        for t, sents in zip(titles, r["context"]["sentences"]):
            if t not in idx:
                idx[t] = len(corpus)
                corpus.append({"title": t, "text": "".join(sents).strip()})
        gold = sorted(set(r["supporting_facts"]["title"]))
        qs.append({"id": r["id"], "question": r["question"], "answer": r["answer"], "type": r["type"],
                   "level": r["level"], "gold_titles": gold, "gold_ids": [idx[t] for t in gold]})
    qfile.write_text(json.dumps(qs, indent=1))
    cfile.write_text(json.dumps(corpus, indent=1))
qs, corpus = json.loads(qfile.read_text()), json.loads(cfile.read_text())
print(len(qs), "questions,", len(corpus), "paragraphs")

llm = Llama(model_path=GGUF, embedding=True, n_ctx=512, n_batch=512, n_threads=4, verbose=False)


def emb(texts):
    out = []
    for t in texts:
        v = np.array(llm.embed(t, truncate=True), dtype=np.float32)
        if v.ndim > 1:
            v = v[0]
        out.append(v / np.linalg.norm(v))
    return np.stack(out)


t0 = time.time()
E = emb([f"{c['title']}\n{c['text']}" for c in corpus])
t1 = time.time()
Q = emb([QPREFIX + q["question"] for q in qs])
t2 = time.time()
np.save(D / f"emb_{TAG}.npy", E)
S = Q @ E.T
order = np.argsort(-S, axis=1)[:, :200]
ret = {q["id"]: order[i].tolist() for i, q in enumerate(qs)}
(D / f"retrieval_{TAG}.json").write_text(json.dumps(ret))
for k in (2, 5, 10, 20, 50):
    both = np.mean([set(q["gold_ids"]) <= set(ret[q["id"]][:k]) for q in qs])
    one = np.mean([bool(set(q["gold_ids"]) & set(ret[q["id"]][:k])) for q in qs])
    print(f"{TAG} k={k}: both gold paras {both:.3f}  at least one {one:.3f}")
print(json.dumps({"tag": TAG, "paragraphs": len(corpus), "embed_corpus_s": round(t1 - t0, 1),
                  "embed_queries_s": round(t2 - t1, 1), "dim": int(E.shape[1])}))
