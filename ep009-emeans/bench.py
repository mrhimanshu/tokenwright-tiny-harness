"""e-means vs k-means on a MacBook (M4 Pro, 12 CPU cores, no NVIDIA GPU).
Data: 300k Simple-Wikipedia passages embedded with bge-small (384-d). First 2,000 rows = held-out queries.
Every method trains on the same 298k vectors; loss is recomputed the same way for all (mean squared distance
to the nearest final centroid, via faiss.knn). Then each set of centroids is used as the coarse quantizer of an
IVF-Flat index and we measure recall@10 of 2,000 held-out queries at nprobe 8 (the RAG use case).
Usage: python bench.py K seeds... (appends to results.jsonl)"""
import json, sys, time, platform
import numpy as np, faiss
from faiss.contrib.e_means import NumpyEmeans
from sklearn.cluster import KMeans, MiniBatchKMeans

K = int(sys.argv[1]) if len(sys.argv) > 1 else 1024
SEEDS = [int(s) for s in sys.argv[2:]] or [0, 1, 2]
ONLY = None  # set by env for partial reruns
import os
ONLY = os.environ.get("ONLY")
SKIP = set((os.environ.get("SKIP") or "").split(","))

X = np.load("data/wiki_bge384.npy")
Q, XT = np.ascontiguousarray(X[:2000]), np.ascontiguousarray(X[2000:])
n, d = XT.shape
print(f"train {n} x {d}, k={K}, seeds={SEEDS}, faiss threads={faiss.omp_get_max_threads()}", flush=True)

# exact top-10 neighbours of the queries (ground truth for recall)
flat = faiss.IndexFlatL2(d); flat.add(XT)
_, GT = flat.search(Q, 10)


def loss_of(C):
    D, _ = faiss.knn(XT, np.ascontiguousarray(C, dtype="float32"), 1)
    return float(D.mean())


def recall_of(C, nprobe=8):
    quant = faiss.IndexFlatL2(d)
    ivf = faiss.IndexIVFFlat(quant, d, C.shape[0])
    quant.add(np.ascontiguousarray(C, dtype="float32"))
    ivf.is_trained = True
    ivf.add(XT)
    ivf.nprobe = nprobe
    _, I = ivf.search(Q, 10)
    hits = sum(len(set(a) & set(b)) for a, b in zip(I, GT))
    sizes = np.bincount(faiss.knn(XT, np.ascontiguousarray(C, dtype="float32"), 1)[1].ravel(), minlength=C.shape[0])
    _, P = faiss.knn(Q, np.ascontiguousarray(C, dtype="float32"), nprobe)   # lists each query probes
    scanned = float(sizes[P].sum(axis=1).mean())                            # vectors compared per query
    return hits / GT.size, int((sizes == 0).sum()), float(sizes.max() / sizes.mean()), scanned


def run_sklearn(seed):
    m = KMeans(n_clusters=K, init="k-means++", n_init=1, max_iter=300, tol=1e-4, random_state=seed)
    m.fit(XT)
    return m.cluster_centers_, {"epochs": int(m.n_iter_)}


def run_minibatch(seed):
    m = MiniBatchKMeans(n_clusters=K, batch_size=4096, random_state=seed, n_init=1, max_iter=100)
    m.fit(XT)
    return m.cluster_centers_, {"epochs": float(m.n_steps_ * 4096 / n)}


def run_faiss(seed, niter):
    km = faiss.Kmeans(d, K, niter=niter, seed=seed + 1, verbose=False, max_points_per_centroid=10**9)
    km.train(XT)
    return km.centroids, {"epochs": niter}


def run_emeans(seed, T):
    em = NumpyEmeans(d, K, nepochs=T, seed=seed + 1)
    C, _ = em.train(XT)
    return C, {"epochs": T, "batch": em.recipe.get("batch_size"), "alpha0": em.recipe.get("alpha0"), "splits": int(getattr(em, "n_splits", 0) or 0)}


METHODS = [
    ("emeans_1", lambda s: run_emeans(s, 1)),
    ("emeans_2", lambda s: run_emeans(s, 2)),
    ("emeans_2.5", lambda s: run_emeans(s, 2.5)),
    ("emeans_3", lambda s: run_emeans(s, 3)),
    ("emeans_5", lambda s: run_emeans(s, 5)),
    ("lloyd_3", lambda s: run_faiss(s, 3)),
    ("lloyd_5", lambda s: run_faiss(s, 5)),
    ("lloyd_25", lambda s: run_faiss(s, 25)),
    ("minibatch_sklearn", run_minibatch),
    ("kmeans_sklearn", run_sklearn),
]

with open("results.jsonl", "a") as f:
    for seed in SEEDS:
        for name, fn in METHODS:
            if (ONLY and name not in ONLY.split(",")) or name in SKIP:
                continue
            t0 = time.perf_counter()
            C, extra = fn(seed)
            secs = time.perf_counter() - t0
            L = loss_of(C)
            rec, empty, imb, scanned = recall_of(C)
            np.save(f"runs/{name}_k{K}_s{seed}.npy", np.asarray(C, dtype="float32"))
            row = {"method": name, "k": K, "seed": seed, "n": n, "d": d, "secs": round(secs, 3), "loss": L,
                   "recall10_nprobe8": rec, "empty_clusters": empty, "imbalance": round(imb, 3), "scanned_per_query": round(scanned, 1),
                   "machine": platform.machine(), "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **extra}
            f.write(json.dumps(row) + "\n"); f.flush()
            print(f"{name:18s} seed {seed}  {secs:8.2f}s  loss {L:.5f}  recall {rec:.3f}  scanned {scanned:7.0f}  imb {imb:.2f}  ep {extra['epochs']}", flush=True)
