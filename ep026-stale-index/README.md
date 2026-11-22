# EP026: does a stale RAG index rot? (BBC News 2017–2025)
Video: "I Never Rebuilt My RAG Index. One Box Grew 18×" (Tokenwright). Results: DATA.md.

Run (CPU, ~25 min embedding + ~2 min bench):
```
pip install faiss-cpu==1.16.0 sentence-transformers pyarrow numpy huggingface_hub
python dl.py               # RealTimeData/bbc_news_alltime monthly parquet -> bbc/
python embed.py            # 500 articles/month, all-MiniLM-L6-v2 -> data/
python bench.py            # stale (2017-18 lists) vs fresh Lloyd-25 / e-means, 8 checkpoints x 3 seeds -> results.jsonl
python analyse.py          # -> summary.json
python inspect_lists.py    # which lists overgrew -> lists_seed0.json
```
