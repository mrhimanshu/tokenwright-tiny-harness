"""EP026: does a stale IVF index rot as the corpus drifts?
Corpus = BBC News, 500 articles/month, 2017-01..2025-06 (data/pass.npy, time ordered).
STALE  = centroids trained once on 2017-2018 (faiss Lloyd, 25 passes), every later article just appended to its nearest list.
FRESH  = re-cluster the whole corpus at the checkpoint: faiss Lloyd-25 and e-means (faiss 1.16 NumpyEmeans, default 5 passes).
Queries = titles of 300 random articles from the 6 months before the checkpoint ("what people search now");
control = 300 titles from 2017-2018. Ground truth = exact top-10 over the whole corpus at that checkpoint.
k = 256 lists for every index. 3 seeds. Writes results.jsonl (one row per checkpoint x method x seed x query set)."""
import json, time, sys
import numpy as np, faiss
from faiss.contrib.e_means import NumpyEmeans
faiss.omp_set_num_threads(4)
P = np.load("data/pass.npy"); T = np.load("data/title.npy")
meta = [json.loads(l) for l in open("data/meta.jsonl")]
month = np.array([m["month"] for m in meta]); d = P.shape[1]; K = 256
NPROBES = [1, 2, 4, 8, 16, 32]
CHECKS = ["2018-12", "2019-12", "2020-12", "2021-12", "2022-12", "2023-12", "2024-12", "2025-06"]
out = open(sys.argv[1] if len(sys.argv) > 1 else "results.jsonl", "w")

def lloyd(X, seed):
    km = faiss.Kmeans(d, K, niter=25, seed=seed + 1, verbose=False, max_points_per_centroid=10**9); km.train(X); return km.centroids

def emeans(X, seed):
    C, _ = NumpyEmeans(d, K, nepochs=5, seed=seed + 1).train(X); return np.ascontiguousarray(C, dtype="float32")

def evaluate(C, X, Q, GT, own):
    C = np.ascontiguousarray(C, dtype="float32")
    quant = faiss.IndexFlatL2(d); quant.add(C)
    ivf = faiss.IndexIVFFlat(quant, d, K); ivf.is_trained = True; ivf.add(X)
    D1, A = faiss.knn(X, C, 1)
    sizes = np.bincount(A.ravel(), minlength=K)
    res = {"loss": float(D1.mean()), "imbalance": float(sizes.max() / sizes.mean()), "empty": int((sizes == 0).sum()),
           "top10pct_share": float(np.sort(sizes)[::-1][:K // 10].sum() / sizes.sum()),
           "cv": float(sizes.std() / sizes.mean()), "per": {}}
    _, PL = faiss.knn(Q, C, max(NPROBES))
    for npb in NPROBES:
        ivf.nprobe = npb
        _, I = ivf.search(Q, 10)
        rec = sum(len(set(a) & set(b)) for a, b in zip(I, GT)) / GT.size
        hit = float(np.mean([o in set(a) for o, a in zip(own, I)]))
        scanned = float(sizes[PL[:, :npb]].sum(axis=1).mean())
        res["per"][npb] = {"recall10": rec, "own_hit10": hit, "scanned": scanned}
    return res

rng0 = np.random.default_rng(123)
base = np.where(month <= "2018-12")[0]
for seed in range(3):
    t = time.time(); C_stale = lloyd(P[base], seed); t_base = time.time() - t
    for chk in CHECKS:
        idx = np.where(month <= chk)[0]; X = P[idx]
        y, mo = int(chk[:4]), int(chk[5:])
        lo = f"{y - (1 if mo <= 6 else 0)}-{(mo - 6) % 12 + 1:02d}"   # 6 months back
        recent = idx[month[idx] >= lo]; old = base
        r = np.random.default_rng(1000 + seed + int(chk[:4]))
        sets = {"recent": r.choice(recent, 300, replace=False), "old": r.choice(old, 300, replace=False)}
        flat = faiss.IndexFlatIP(d); flat.add(X)
        fits = {"stale": (C_stale, t_base)}
        if chk != "2018-12":
            t = time.time(); C = lloyd(X, seed); fits["fresh_lloyd25"] = (C, time.time() - t)
            t = time.time(); C = emeans(X, seed); fits["fresh_emeans"] = (C, time.time() - t)
        for name, (C, secs) in fits.items():
            for qs, qi in sets.items():
                Q = np.ascontiguousarray(T[qi]); _, GT = flat.search(Q, 10)
                own = qi.tolist()   # positions in X equal global ids because X = P[:len] (time ordered)
                ev = evaluate(C, X, Q, GT, own)
                row = {"seed": seed, "checkpoint": chk, "n": int(len(X)), "method": name, "queries": qs, "train_s": round(secs, 3), **ev}
                out.write(json.dumps(row) + "\n"); out.flush()
                p8 = ev["per"][8]
                print(seed, chk, len(X), name, qs, f"rec={p8['recall10']:.3f} hit={p8['own_hit10']:.3f} scan={p8['scanned']:.0f} imb={ev['imbalance']:.2f} t={secs:.2f}", flush=True)
