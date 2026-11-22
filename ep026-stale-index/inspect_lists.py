"""Which stale lists overgrew, and with what? Seed 0 stale centroids (Lloyd-25 on 2017-2018), corpus to 2025-06."""
import json, numpy as np, faiss, collections, re
P = np.load("data/pass.npy"); meta = [json.loads(l) for l in open("data/meta.jsonl")]
month = np.array([m["month"] for m in meta]); d = P.shape[1]; K = 256
base = np.where(month <= "2018-12")[0]
km = faiss.Kmeans(d, K, niter=25, seed=1, verbose=False, max_points_per_centroid=10**9); km.train(P[base]); C = km.centroids
_, A = faiss.knn(P, C, 1); A = A.ravel()
sizes = np.bincount(A, minlength=K); base_sizes = np.bincount(A[base], minlength=K)
order = np.argsort(-sizes)
out = {"mean_size": float(sizes.mean()), "lists": []}
cov = np.array([bool(re.search(r"covid|coronavirus|lockdown|pandemic|vaccin", m["title"], re.I)) for m in meta])
for j in order[:6]:
    mem = np.where(A == j)[0]
    yrs = collections.Counter(month[mem].astype("U4").tolist())
    old_titles = [meta[i]["title"] for i in mem if month[i] <= "2018-12"][:6]
    new_titles = [meta[i]["title"] for i in mem if month[i] >= "2020-01"]
    rng = np.random.default_rng(0)
    out["lists"].append({"list": int(j), "size": int(sizes[j]), "x_mean": round(float(sizes[j] / sizes.mean()), 2), "size_2018": int(base_sizes[j]),
        "by_year": dict(sorted(yrs.items())), "covid_titles": int(cov[mem].sum()),
        "old_examples": old_titles, "new_examples": [new_titles[i] for i in rng.permutation(len(new_titles))[:8]]})
# covid articles: how many lists hold them, how concentrated
cm = A[cov]; cc = collections.Counter(cm.tolist())
out["covid"] = {"articles": int(cov.sum()), "lists_used": len(cc), "top3_lists_share": round(sum(v for _, v in cc.most_common(3)) / cov.sum(), 3),
                "top_lists": cc.most_common(5)}
# fresh for comparison
km2 = faiss.Kmeans(d, K, niter=25, seed=1, verbose=False, max_points_per_centroid=10**9); km2.train(P); _, A2 = faiss.knn(P, km2.centroids, 1); A2 = A2.ravel()
cc2 = collections.Counter(A2[cov].tolist())
out["covid_fresh"] = {"lists_used": len(cc2), "top3_lists_share": round(sum(v for _, v in cc2.most_common(3)) / cov.sum(), 3), "biggest_list": int(np.bincount(A2, minlength=K).max())}
json.dump(out, open("lists_seed0.json", "w"), indent=1)
print(json.dumps(out, indent=1)[:6000])
