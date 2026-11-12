# EP009 DATA — e-means vs k-means on a MacBook (my runs, 12 Nov 2026)
Machine: Apple M4 Pro, 12 CPU cores, 24 GB, CPU only (no GPU used for clustering). faiss-cpu 1.16.0 (e-means = faiss.contrib.e_means.NumpyEmeans,
default settings), scikit-learn 1.9.1, numpy 2.5.4. Raw rows: lab/results.jsonl (60 runs) · summary: lab/summary.json · centroids: lab/runs/*.npy.
Data: 300,000 Simple English Wikipedia paragraphs (wikimedia/wikipedia 20231101.simple), embedded with BAAI/bge-small-en-v1.5 (384-d,
normalised) on MPS in 541 s. 2,000 held out as queries, 298,000 clustered. 3 seeds per condition. API spend: $0.

Contenders: scikit-learn KMeans (defaults: k-means++ init, n_init 1, max_iter 300, tol 1e-4) · scikit-learn MiniBatchKMeans (batch 4096) ·
faiss Kmeans = classic Lloyd at 3 / 5 / 25 passes (25 = faiss default) · e-means at 1 / 2 / 2.5 / 3 / 5 passes (5 = default).
Loss = mean squared distance of each vector to its nearest final centre (same code for all). Search = IVF-Flat index built from each set of
centres; recall@10 of the 2,000 held-out queries vs exact search, at nprobe 8 and at an equal budget of vectors scanned per query
(interpolated over nprobe 1–64: 2,500 for k=1024, 8,000 for k=256).

## k = 1,024 clusters ("search index" job) — mean of 3 seeds
| method | passes | time (s) | loss | recall@10, nprobe 8 | vectors scanned / query | recall@10 at 2,500 scanned |
|---|---|---|---|---|---|---|
| scikit-learn KMeans | 109 (101–117) | **70.77** ±0.66 | 0.38482 | 0.888 | 2,181 | 0.898 |
| scikit-learn MiniBatch | 3.9 | 4.46 | **0.39730 (worst)** | **0.896 (best)** | **3,318** | **0.860 (worst)** |
| faiss Lloyd 3 | 3 | 0.82 | 0.39337 | 0.868 | 2,489 | 0.867 |
| faiss Lloyd 5 | 5 | 1.35 | 0.39005 | 0.874 | 2,457 | 0.875 |
| faiss Lloyd 25 | 25 | 6.62 | 0.38587 | 0.887 | 2,437 | 0.889 |
| e-means 1 | 1 | 0.90 | 0.38928 | 0.874 | 2,272 | 0.883 |
| e-means 2 | 2 | 1.75 | 0.38591 | 0.886 | 2,266 | 0.893 |
| e-means 2.5 | 2.5 | **2.16** | **0.38578** (below Lloyd 25) | 0.883 | 2,274 | 0.891 |
| e-means 3 | 3 | 2.58 | 0.38538 | 0.886 | 2,276 | 0.894 |
| e-means 5 | 5 | **4.30** | **0.38482** (= scikit-learn) | 0.887 | 2,276 | 0.895 |

## k = 256 clusters ("topic grouping" job)
| method | passes | time (s) | loss | recall@10 nprobe 8 | recall at 8,000 scanned |
|---|---|---|---|---|---|
| scikit-learn KMeans | 250 | 25.74 | **0.41920 (best)** | 0.937 | 0.925 |
| scikit-learn MiniBatch | 2.9 | 1.65 | 0.42293 | 0.929 | 0.914 |
| faiss Lloyd 3 / 5 / 25 | 3 / 5 / 25 | 0.24 / 0.38 / **1.75** | 0.42721 / 0.42387 / **0.41967** | 0.927 / 0.930 / 0.936 | 0.908 / 0.913 / 0.922 |
| e-means 1 / 2 / 2.5 / 3 / 5 | — | 0.69 / 1.36 / **1.70** / 2.04 / 3.37 | 0.42128 / 0.41987 / **0.41970** / 0.41959 / 0.41945 | 0.933–0.939 | 0.919–0.925 |

## Headline numbers (for the script)
- scikit-learn took **71 s** (≈109 passes) for 1,024 groups; e-means (5 passes, default) reached the **same loss (0.38482) in 4.3 s → 16×**.
- But faiss classic k-means (25 passes) was already **6.6 s → 10.7× faster than scikit-learn** by itself. Much of the "16×" is the library.
- Pass for pass (the paper's real claim): e-means beats Lloyd-25's loss between **2 and 2.5 passes** (2: 0.38591 vs 0.38587, 2.5: 0.38578). Paper: 1.4–2.6. ✓
- After 3 passes classic k-means still has **+1.9 % loss** (0.39337 vs 0.38587).
- Wall clock vs faiss Lloyd-25 at k=1024: **2.16 s vs 6.62 s = 3.1×** (not 10–45×). Per pass: Lloyd 0.265 s, e-means 0.86 s (**3.3× more per pass**: small batches on a CPU).
- At k=256: per pass Lloyd 0.07 s vs e-means 0.67 s (**~10×**), so e-means 2.5 = **1.70 s vs Lloyd-25 1.75 s → a tie**. scikit-learn still had the lowest loss there (0.41920 vs 0.41945 for e-means 5, 0.06 %).
- Search: recall@10 at nprobe 8 spans only 0.868–0.896 at k=1024. MiniBatch looks best (0.896) but scans **3,318 vectors per query vs ~2,270 for e-means (+46 %)** because its clusters are lopsided (largest = 4.95× average). At an equal budget of 2,500 vectors it drops to **0.860, the worst**. e-means 3 (0.894) beats faiss Lloyd-25 (0.889) at equal work.

## Their numbers (not mine)
1.4–2.6 epochs to beat Lloyd at 25 epochs; 10–45× GPU wall-clock on H100 vs Flash-KMeans / Faiss-GPU / cuML; DINO10B: 10 billion vectors,
16 million clusters, 2.5 epochs. README: CPU "convenient for small problems and for trying things out"; GPU recommended when n × k ≥ 1e10
(ours: 3 × 10^8).

## Caveats
One dataset (384-d text embeddings), one machine, CPU only, 3 seeds, two k values. scikit-learn time includes its k-means++ init. e-means
used its defaults (scaling-law batch sizes); no tuning for any method.
