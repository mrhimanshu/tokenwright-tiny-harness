"""Stratified sample of the official test splits (seed 37): per corpus N items,
keeping the test set's category mix within each label (BalAcc weights labels equally)."""
import json, random, collections, sys
N = 120
out = []
for c in ["friends", "ami"]:
    rows = [json.loads(l) for l in open(f"data/{c}/test/test_samples.jsonl")]
    rng = random.Random(37)
    by = collections.defaultdict(list)
    for r in rows: by[r["category"]].append(r)
    for lab in ["SPEAK", "SILENT"]:
        cats = [k for k in by if k.startswith(lab)]
        tot = sum(len(by[k]) for k in cats)
        alloc = {k: round(N / 2 * len(by[k]) / tot) for k in cats}
        for k in cats:
            for r in rng.sample(by[k], alloc[k]):
                r["corpus"] = c; out.append(r)
json.dump(out, open("data/sample.json", "w"))
print(len(out), collections.Counter((r["corpus"], r["category"]) for r in out))
