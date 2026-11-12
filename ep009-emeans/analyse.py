"""Summarise results.jsonl -> summary.json (+ print). Also: recall@10 at a fixed search budget (equal vectors scanned),
from the saved centroids in runs/, sweeping nprobe per centroid set and interpolating at BUDGET vectors per query."""
import json, collections, statistics as st
import numpy as np, faiss

rows = [json.loads(l) for l in open("results.jsonl")]
g = collections.defaultdict(list)
for r in rows:
    g[(r["k"], r["method"])].append(r)

X = np.load("data/wiki_bge384.npy"); Q, XT = np.ascontiguousarray(X[:2000]), np.ascontiguousarray(X[2000:])
flat = faiss.IndexFlatL2(XT.shape[1]); flat.add(XT); _, GT = flat.search(Q, 10)


def budget_recall(C, budget):
    C = np.ascontiguousarray(C)
    quant = faiss.IndexFlatL2(C.shape[1]); ivf = faiss.IndexIVFFlat(quant, C.shape[1], C.shape[0])
    quant.add(C); ivf.is_trained = True; ivf.add(XT)
    sizes = np.bincount(faiss.knn(XT, C, 1)[1].ravel(), minlength=C.shape[0])
    _, P = faiss.knn(Q, C, 64)
    pts = []
    for npb in (1, 2, 4, 6, 8, 12, 16, 24, 32, 48, 64):
        ivf.nprobe = npb; _, I = ivf.search(Q, 10)
        rec = sum(len(set(a) & set(b)) for a, b in zip(I, GT)) / GT.size
        pts.append((float(sizes[P[:, :npb]].sum(axis=1).mean()), rec))
    xs, ys = zip(*pts)
    return float(np.interp(budget, xs, ys))


summary = {}
for (k, m), rs in sorted(g.items()):
    secs = [r["secs"] for r in rs]; loss = [r["loss"] for r in rs]; rec = [r["recall10_nprobe8"] for r in rs]
    scan = [r.get("scanned_per_query", 0) for r in rs]
    B = 2500 if k == 1024 else 8000
    brec = [budget_recall(np.load(f"runs/{m}_k{k}_s{r['seed']}.npy"), B) for r in rs]
    summary[f"{k}/{m}"] = {"k": k, "method": m, "n": len(rs), "secs_mean": st.mean(secs), "secs_sd": st.pstdev(secs),
                           "loss_mean": st.mean(loss), "loss_sd": st.pstdev(loss), "loss_min": min(loss), "loss_max": max(loss),
                           "recall_nprobe8": st.mean(rec), "scanned_nprobe8": st.mean(scan), "imbalance": st.mean(r["imbalance"] for r in rs),
                           "budget": B, "recall_at_budget": st.mean(brec), "epochs": st.mean(float(r["epochs"]) for r in rs)}
    s = summary[f"{k}/{m}"]
    print(f"k={k:5d} {m:18s} n={s['n']} {s['secs_mean']:7.2f}s ±{s['secs_sd']:.2f}  loss {s['loss_mean']:.5f} [{s['loss_min']:.5f}-{s['loss_max']:.5f}]"
          f"  rec8 {s['recall_nprobe8']:.3f} scan {s['scanned_nprobe8']:6.0f}  rec@{B} {s['recall_at_budget']:.3f}  imb {s['imbalance']:.2f} ep {s['epochs']:.1f}")
json.dump(summary, open("summary.json", "w"), indent=1)
