"""Build a real RAG-style embedding set: Simple English Wikipedia (wikimedia/wikipedia 20231101.simple)
split into paragraph passages, embedded with BAAI/bge-small-en-v1.5 (384-d, normalised) on the M4 Pro GPU (MPS).
Output: data/wiki_bge384.npy (float32, N x 384) + data/passages.jsonl (id, title, text[:300])."""
import hashlib, json, sys, time
import numpy as np, pyarrow.parquet as pq, torch
from huggingface_hub import HfApi, snapshot_download
from sentence_transformers import SentenceTransformer

N_MAX = int(sys.argv[1]) if len(sys.argv) > 1 else 300_000
REPO = "BAAI/bge-small-en-v1.5"

# --- model: official BAAI repo, sha256 checked against the HF API ---
path = snapshot_download(REPO, local_dir="models/bge-small", allow_patterns=["*.json", "*.txt", "model.safetensors", "1_Pooling/*"])
info = HfApi().model_info(REPO, files_metadata=True)
want = {s.rfilename: (s.lfs.sha256 if s.lfs else None) for s in info.siblings}
got = hashlib.sha256(open(f"{path}/model.safetensors", "rb").read()).hexdigest()
assert got == want["model.safetensors"], (got, want["model.safetensors"])
print("model sha256 OK", got[:16])

# --- passages: paragraphs of 200-1200 chars ---
t = pq.read_table("data/simplewiki.parquet", columns=["id", "title", "text"]).to_pylist()
passages = []
for row in t:
    for para in row["text"].split("\n"):
        para = para.strip()
        if 200 <= len(para) <= 1200:
            passages.append((row["id"], row["title"], para))
print("articles", len(t), "passages", len(passages))
rng = np.random.default_rng(0)
idx = rng.permutation(len(passages))[:N_MAX]
idx.sort()
passages = [passages[i] for i in idx]

model = SentenceTransformer(path, device="mps")
model.max_seq_length = 256
t0 = time.time()
emb = model.encode([p[2] for p in passages], batch_size=256, normalize_embeddings=True,
                   convert_to_numpy=True, show_progress_bar=False).astype("float32")
print(f"embedded {len(emb)} x {emb.shape[1]} in {time.time()-t0:.0f}s")
np.save("data/wiki_bge384.npy", emb)
with open("data/passages.jsonl", "w") as f:
    for (aid, title, text) in passages:
        f.write(json.dumps({"id": aid, "title": title, "text": text[:300]}) + "\n")
