# EP009 · Meta's e-means vs k-means, on a MacBook (CPU only)

Video: Tokenwright, "Meta's New k-means Is 45× Faster? I Tested It on a Mac" (12 Nov 2026).

e-means (Meta FAIR, arXiv 2611.09501, shipped in faiss 1.16 as `faiss.contrib.e_means`) vs scikit-learn KMeans,
scikit-learn MiniBatchKMeans and classic Lloyd k-means in faiss. 298,000 Simple English Wikipedia paragraphs embedded with
BAAI/bge-small-en-v1.5 (384-d), k = 1,024 and 256, 3 seeds each, 60 runs, Apple M4 Pro CPU.

| file | what |
|---|---|
| `embed.py` | builds the dataset (wikimedia/wikipedia 20231101.simple → paragraphs → bge-small embeddings on MPS) |
| `bench.py K seeds…` | trains every method, measures time, loss, IVF recall@10 (nprobe 8), vectors scanned per query |
| `analyse.py` | summary + recall at an equal scan budget (2,500 / 8,000 vectors) → `summary.json` |
| `results.jsonl` | the 60 raw runs |
| `DATA.md` | tables and headline numbers · `FACTS.md` sources |

Headline (k = 1,024): scikit-learn 70.8 s · e-means 5 passes 4.3 s (same loss) · faiss Lloyd-25 6.6 s · e-means beats Lloyd-25
loss at 2–2.5 passes · on the clock 3.1× vs faiss Lloyd-25 (a tie at k = 256) · MiniBatchKMeans: best recall at nprobe 8 but
+46 % vectors scanned; last at equal budget.

```
pip install faiss-cpu scikit-learn sentence-transformers pyarrow
python embed.py 300000 && python bench.py 1024 0 1 2 && python bench.py 256 0 1 2 && python analyse.py
```
