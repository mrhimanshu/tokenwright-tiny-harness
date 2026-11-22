"""BBC News 2017-01..2025-06 (RealTimeData/bbc_news_alltime), one passage per article
(title + first ~600 chars of the body), embedded with sentence-transformers/all-MiniLM-L6-v2 (384-d, normalised) on CPU, 500 random articles per month.
Also embeds each title alone (used as the search query). Output: data/pass.npy, data/title.npy, data/meta.jsonl"""
import hashlib, json, sys, time, glob, re
import numpy as np, pyarrow.parquet as pq, torch
from huggingface_hub import HfApi, snapshot_download
from sentence_transformers import SentenceTransformer
torch.set_num_threads(4)
LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 0
REPO = "sentence-transformers/all-MiniLM-L6-v2"
PER_MONTH = 500
path = snapshot_download(REPO, local_dir="models/minilm", allow_patterns=["*.json", "*.txt", "model.safetensors", "1_Pooling/*", "modules.json"])
info = HfApi().model_info(REPO, files_metadata=True)
want = {s.rfilename: (s.lfs.sha256 if s.lfs else None) for s in info.siblings}
got = hashlib.sha256(open(f"{path}/model.safetensors", "rb").read()).hexdigest()
assert got == want["model.safetensors"], (got, want["model.safetensors"]); print("model sha256 OK", got[:16], flush=True)

seen, rows = set(), []
for f in sorted(glob.glob("bbc/*.parquet")):
    month = f.split("/")[-1][:7]
    for r in pq.read_table(f, columns=["title", "content", "link", "section"]).to_pylist():
        title = re.sub(r"\s*-\s*BBC (News|Sport)\s*$", "", (r["title"] or "")).strip()
        body = re.sub(r"\s+", " ", r["content"] or "").strip()
        key = r["link"] or title
        if len(title) < 15 or len(body) < 200 or key in seen or title in seen: continue
        seen.add(key); seen.add(title)
        rows.append({"month": month, "title": title, "section": r["section"], "text": body[:600]})
print("articles", len(rows), flush=True)
rng = np.random.default_rng(0); bym = {}
for r in rows: bym.setdefault(r["month"], []).append(r)
rows = []
for mth in sorted(bym):
    g = bym[mth]; idx = sorted(rng.permutation(len(g))[:PER_MONTH]); rows += [g[i] for i in idx]
print("sampled", len(rows), "months", len(bym), flush=True)
if LIMIT: rows = rows[:LIMIT]
m = SentenceTransformer(path, device="cpu"); m.max_seq_length = 128
t0 = time.time()
P = m.encode([r["title"] + ". " + r["text"] for r in rows], batch_size=128, normalize_embeddings=True, convert_to_numpy=True).astype("float32")
print(f"passages {len(P)} in {time.time()-t0:.0f}s", flush=True); t1 = time.time()
T = m.encode([r["title"] for r in rows], batch_size=256, normalize_embeddings=True, convert_to_numpy=True).astype("float32")
print(f"titles in {time.time()-t1:.0f}s", flush=True)
suf = f"_{LIMIT}" if LIMIT else ""
np.save(f"data/pass{suf}.npy", P); np.save(f"data/title{suf}.npy", T)
with open(f"data/meta{suf}.jsonl", "w") as f:
    for r in rows: f.write(json.dumps({"month": r["month"], "title": r["title"], "section": r["section"]}) + "\n")
