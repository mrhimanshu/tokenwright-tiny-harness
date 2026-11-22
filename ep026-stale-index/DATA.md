# EP026 DATA: does a stale RAG index rot? (my runs, 22 Nov 2026)
Machine: Quill cloud computer, 4 CPU threads (shared), no GPU. faiss-cpu 1.16.0 (Lloyd = faiss.Kmeans niter 25; e-means =
faiss.contrib.e_means.NumpyEmeans, default 5 passes), sentence-transformers all-MiniLM-L6-v2 (384-d, normalised; safetensors sha256 checked
against the HF API). API spend: $0. Raw rows: lab/results.jsonl (132 rows) · means: lab/summary.json · list autopsy: lab/lists_seed0.json.

## Setup
- Corpus: RealTimeData/bbc_news_alltime, every month 2017-01 .. 2025-06 (102 months), deduped, 500 random articles per month
  (2025: 6 months) = **50,744 articles**. One passage per article = title + first 600 characters. Real time order = real topic drift.
- Index: IVF-Flat, **256 lists** (k fixed for every index), nprobe 8 = search 8 of 256 lists (~3%).
- **Stale** = lists trained ONCE on 2017–2018 (12,000 articles), every later article only appended to its nearest list (what happens when
  you "add documents without re-clustering").
- **Fresh** = re-cluster everything at the checkpoint: faiss Lloyd 25 passes, and e-means (5 passes).
- Checkpoints: end of 2018 (training day), 2019, 2020, 2021, 2022, 2023, 2024, June 2025.
- Queries: 300 article titles from the 6 months before the checkpoint ("what people search now"); control: 300 titles from 2017–2018.
  Ground truth = exact top 10 over the whole corpus at that checkpoint. recall@10 = share of the true top 10 the index returns.
  "own hit" = the query's own article is in the top 10. 3 seeds per condition (clustering seed + query sample).

## Headline (June 2025, 6.5 years after the stale index was trained; recent queries; mean of 3 seeds)
| index | recall@10 (nprobe 8) | own article found | vectors scanned / query | biggest list ÷ average | top 10% of lists hold | rebuild time |
|---|---|---|---|---|---|---|
| stale (2018 lists) | **79.2%** ±0.8 | 89.9% | **2,088** | **5.07×** | **27.3%** of all docs | 0 (never) |
| fresh Lloyd-25 | **83.8%** ±0.4 | 93.3% | 1,731 | 2.83× | 18.4% | **1.47 s** |
| fresh e-means | **84.4%** ±0.8 | 94.6% | 1,901 | 3.16× | 19.5% | **1.46 s** |
- Stale = **−4.6 points** of recall while scanning **+21% more vectors** per query.
- Old (2017–18) queries on the stale index: 85.2% (fresh 84.0–85.0%): **no loss** for the topics it was trained on. The rot only hits NEW topics.
- To match fresh recall (83.8%), the stale index has to search ~twice the lists: nprobe 16 gives 87.7% at 3,991 vectors; interpolated
  ~3,100 vectors for 83.8% ≈ **1.8× the work**. At the end of 2020: fresh 85.4% at 966 vectors; stale needs nprobe 16 (85.5% at 2,002) = **2.1× the work**.

## Over time (recent queries, recall@10 at nprobe 8, stale vs best fresh)
| end of | articles | stale | fresh Lloyd | fresh e-means | gap | stale biggest list |
|---|---|---|---|---|---|---|
| 2018 (train) | 12,000 | 82.5% | – | – | – | 3.19× |
| 2019 | 18,000 | 80.1% | 82.8% | 84.0% | −2.7 to −3.9 | 3.55× |
| **2020 (COVID)** | 24,000 | **76.0%** | 85.4% | 85.2% | **−9.4** | 4.71× |
| 2021 | 30,000 | 79.1% | 84.4% | 85.6% | −5.3 to −6.5 | **6.26× (peak)** |
| 2022 (Ukraine) | 36,000 | 80.9% | 85.4% | 85.8% | −4.5 to −4.9 | 5.97× |
| 2023 | 42,000 | 80.5% | 84.4% | 85.7% | −3.9 to −5.2 | 5.58× |
| 2024 | 48,000 | 80.3% | 83.4% | 83.6% | −3.1 to −3.3 | 5.21× |
| Jun 2025 | 50,744 | 79.2% | 83.8% | 84.4% | −4.6 to −5.2 | 5.07× |
At equal work (4% of the corpus scanned): end of 2020 stale 73.7% vs fresh 85.2% (−11.5); June 2025 78.5% vs 84.8%.

## List autopsy (seed 0, stale lists, June 2025; average list = 198 articles)
- List #100, trained on 51 "Trump / Russia / kompromat / Putin" stories (2017–18) → **937** articles (4.7× average). **425 of them from 2022**:
  the Ukraine war ("Ukraine invasion: Missiles hit Kyiv…", "UK targets Russian military with further sanctions").
- List #7, trained on 76 "NHS pressure / A&E / beds" stories → **920**; **527 are COVID** titles ("Coronavirus lockdown restrictions eased in Wales").
- List #198, 74 "NHS / doctors" stories → **817**; **471 COVID**.
- COVID (4,231 titles mentioning covid/coronavirus/lockdown/pandemic/vaccine): the 3 biggest stale lists hold **30.1%** of them;
  after a fresh re-cluster, **20.3%**, and the biggest fresh list is 506 articles.

## e-means vs plain k-means (the AlphaSignal angle)
- At 50k vectors and 256 lists on CPU, re-clustering takes **~1.5 s with either**: e-means 1.46 s, Lloyd-25 1.47 s. Recall within 1 point
  (e-means slightly higher recall, but it scans ~10% more vectors per query: lists a bit less even, 3.16× vs 2.83×).
- So at this size the fix is "re-cluster at all", not "re-cluster with e-means". e-means' speed-up matters at millions of vectors / GPU
  (their numbers; EP009 measured 3.1× vs Lloyd-25 at 298k vectors × 1,024 lists on a Mac CPU).

## Their numbers (not mine)
AlphaSignal 22 Nov 2026: stale clusters → "lopsided", "higher latency and lower recall"; e-means 8–15× faster than Faiss on CPU, 10–45×
on GPU; teams delay rebuilds "for months". Paper arXiv 2611.09501 (Meta FAIR + ENPC, 6 Nov 2026).

## Caveats
One corpus (BBC News, one passage per article), one small embedding model, 50k vectors, 256 lists, titles as queries, 3 seeds.
Real vector DBs often rebalance or split lists on their own (managed DBs hide this). Stale lists were trained once with Lloyd-25.
