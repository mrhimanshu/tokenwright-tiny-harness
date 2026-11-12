# EP009 FACTS — e-means (Meta FAIR) vs k-means, tested on a MacBook
Checked 12 Nov 2026 (morning run, 06:00 UK).

## Source chain
- AlphaSignal, Wed 11 Nov 2026 14:10 UTC, Signal #4: "New clustering algorithm beats k-means with up to 45x GPU speedup" (4,203 likes).
- Paper: arXiv 2611.09501, "e-means: outperforming k-means (in one-tenth the epochs)", submitted Fri 6 Nov 2026.
  Authors: Swann Bessa, Pierre-Emmanuel Mazaré, Gergely Szilvasy, Hugo Touvron, David Picard, Matthijs Douze, Hervé Jégou (Meta FAIR). Licence CC BY 4.0.
  https://arxiv.org/abs/2611.09501
- Code: inside faiss, github.com/facebookresearch/faiss/tree/main/contrib/e_means (pip faiss-cpu 1.16.0 ships it:
  `from faiss.contrib.e_means import NumpyEmeans`). Website e-means.github.io (browser playground).

## Their claims (abstract + README, verbatim numbers)
- Exponential-moving-average mini-batch update for k-means; batch size and step size from scaling laws, "no hyperparameter sweep".
- "beats the loss of Lloyd k-means at 25 epochs in 1.4 to 2.6 epochs"
- "10-45x GPU wall-clock speedups compared to state-of-the-art k-means implementations" (H100; baselines Flash-KMeans, Faiss-GPU, cuML)
- "converges to lower losses, frequently even beating k-means++" (e-means uses random init)
- DINO10B: 10 billion embeddings into 16 million clusters in 2.5 epochs, loss below Lloyd at 25 epochs.
- README: "~10x speedup in epochs and wall-clock"; default nepochs = 5; "on CPU … convenient for small problems and for trying things out. GPUs are much faster" (recommended when n x k > 1e10).
- Update rule: N_j = (1-a)N_j + a n_j ; S_j = (1-a)S_j + a s_j ; c_j = S_j / N_j; cosine-decayed step to a tenth; dead-cluster revival by splitting; exact closing mean at the end.

## What THEY did not test (our angle)
- Their wall-clock numbers are on H100 GPUs. Most builders cluster on a laptop/CPU with scikit-learn.
- We run it on Apple M4 Pro (12 cores, 24 GB, CPU only) on real RAG embeddings, against scikit-learn KMeans, scikit-learn MiniBatchKMeans and faiss Lloyd, and check whether the loss gap changes retrieval recall (IVF index).

## Our setup
- Data: wikimedia/wikipedia 20231101.simple (parquet sha256 31bded16…e6f0 verified), paragraphs 200–1,200 chars → 351,634 passages,
  random 300,000 kept; embedded with BAAI/bge-small-en-v1.5 (384-d, normalised; safetensors sha256 verified against HF API) on MPS.
- First 2,000 vectors held out as queries; 298,000 train vectors.
- Software: faiss-cpu 1.16.0, scikit-learn 1.9.1, numpy 2.5.4, Python 3.12.

## Competition (YouTube, published after 5 Nov, checked 12 Nov 06:20 UK)
6 on-topic videos, all explainers/paper summaries (Jia-Bin Huang "70-Year-Old K-means Just Got 10× Faster", AI Paper Slop,
AI Morning Brief, AI Research Roundup, peb aryan, 2 Korean). None runs it against scikit-learn on a laptop. ≥5 → allowed only
because our measured angle (CPU/laptop vs the k-means people actually use + recall) is new.
Rejected the same morning: Obscura Rust browser (10+ videos this week; old April 2026 project), Weight-edited Qwen 27B (too big locally),
OpenCode Browse (would drive his real browser), smart-home MCP server (no devices).
