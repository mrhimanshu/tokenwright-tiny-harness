# EP024 DATA: an LLM as a zip file, on a CPU (21 Nov 2026, Quill cloud computer, 4 CPU threads, no GPU)
Raw: lab/results.jsonl (every run), lab/classic_full.jsonl, lab/summary.json, lab/showcase.json, lab/roundtrip.bin. Code: lab/*.py.
Data: enwik9 (sha256 159b8535…44bc). Slices: offsets 10,000,000 / 300,000,000 / 600,000,000 (n = 3), trimmed to UTF-8 boundaries.

## 1. Full enwik9 (1,000,000,000 bytes), classic tools (one run each; sizes are deterministic)
| tool | bytes out | MB | note |
|---|---|---|---|
| gzip -9 | 322,591,988 | 322.6 | |
| bzip2 -9 | 253,977,891 | 254.0 | |
| xz -9 (single thread) | 213,370,900 | 213.4 | Mahoney lists xz 197.3 MB with other settings |
| zstd -3 (python zstandard) | 311,786,472 | 311.8 | 8.5 s compress, 3.2 s decompress (CPU shared) |
| tufazip v2 (theirs) | 105,388,353 total | 105.4 | 100,958,324 data + 4,430,029 decoder/weights |

## 2. 64 KB slices: bits per byte (mean of 3; per slice)
| method | mean | slices | speed |
|---|---|---|---|
| gzip -9 | 3.050 | 3.029 / 3.117 / 3.003 | |
| zstd -22 | 2.900 | 2.885 / 2.946 / 2.868 | |
| xz -9e | 2.807 | 2.824 / 2.824 / 2.774 | |
| bzip2 -9 | 2.734 | 2.721 / 2.797 / 2.684 | |
| brotli q11 | 2.467 | 2.458 / 2.490 / 2.452 | (has a built-in dictionary) |
| SmolLM2-135M (269 MB bf16) | **0.938** | 0.900 / 0.992 / 0.923 | ~948 B/s scoring |
| SmolLM2-360M (724 MB) | **0.824** | 0.800 / 0.863 / 0.810 | ~424 B/s |
| Qwen2.5-0.5B (988 MB) | **0.878** | 0.849 / 0.909 / 0.877 | ~346 B/s |
| tufazip, whole GB (theirs) | 0.843 | | total incl. decoder |
LLM numbers = ideal arithmetic-code length (sum of −log2 p per token, 1024-token windows, stride 512); tokenizer round-trips exactly on all slices.
xz / LLM-135M = 2.99× on average (2.85–3.14× per slice).

## 3. Real round trip (lab/roundtrip.py, SmolLM2-135M + constriction range coder, token by token)
4,096 bytes (offset 10 MB) → 596 bytes (1.16 bpb incl. 4-byte header and coder overhead) → decoded byte-identical (sha256 8561dfc8… both).
xz -9e on the same 4 KB: 2,080 · gzip 2,050 · brotli 1,646. Encode 94.6 s, decode 95.0 s = 43 B/s.

## 4. Scaling to 1 GB (my extrapolation)
- Size: 0.938 bpb × 1e9 / 8 = 117 MB + 269 MB weights = ~386 MB (gzip 322.6, xz 213.4, tufazip 105.4).
- Time on this CPU: 43 B/s → 2.3e7 s ≈ 269 days ≈ 9 months; scoring path 948 B/s → ≈ 12.2 days. tufazip: 645,748 s ≈ 7.5 days decompress on 2× B200 (theirs).

## 5. Toy tufazip-style online learner (lab/online_zip.py; random init, score chunk then train on it + 6 replays)
Config: byte-level transformer d=128, 2 layers, 0.50M params, ctx 64 + 192 new bytes/row, 8 rows/chunk, Adam lr 1e-2. 1 MB per slice, 1 thread, ~684 s each.
| slice | avg bpb | first ~100 KB | last 100 KB |
|---|---|---|---|
| 10 MB | 3.247 | 4.25 | 2.75 |
| 300 MB | 3.163 | 4.19 | 2.63 |
| 600 MB | 3.270 | 4.29 | 2.61 |
| mean | **3.227** | 4.24 | **2.66** |
Same 1 MB slices: gzip 2.885 · zstd-22 2.460 · xz 2.386 · bzip2 2.341 · brotli 2.304.
Tuning (300 KB, tune.jsonl): 8 configs (d 128–256, 2–4 layers, lr 1e-3–1e-2, replay 1–10) all ended 3.94–4.25 avg; the first 1 MB "base" run (d256, 4 layers, lr 1e-3, 1 replay) averaged 3.89. A 10 MB run was stopped to free the CPU for the render (no result).

## 6. Showcase sentence (lab/showcase.json, SmolLM2-135M, article "Aeon")
" the word [[eon (geology)|eon]] quantitatively refers to a period of time of 1,000,000,000 years." → 71.7 bits for 97 bytes (raw: 776 bits).
"quant"+"itatively" = 15.66 + 5.13 = 20.8 bits; most "0" tokens 0.000–0.013 bits (two at 0.135 and 0.042); " refers" p = 0.28 → 1.83 bits.

## Spend
$0 API. CPU only. Models from official HF repos (sha256 verified), in /data/renders/EP024 (trash after).
