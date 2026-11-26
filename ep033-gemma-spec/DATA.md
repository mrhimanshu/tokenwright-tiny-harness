# EP033 DATA — Gemma 4 E4B speculative decoding on a plain x86 CPU (my runs, 26 Nov 2026)

Setup: litert-community/gemma-4-E4B-it-litert-lm, gemma-4-E4B-it.litertlm (3.66 GB, sha256 verified), LiteRT-LM 0.20.0 (pip),
CPU backend, 4 threads (= the model card's CPU setting), Quill cloud VM (x86-64, 4 vCPU, no GPU). Greedy decoding (top_k=1), max 256
output tokens, 2048-token KV cache. 15 prompts = 5 task types × 3 (summarize, code, rewrite tone, free form, copy/convert/translate).
**Paired design:** one engine, every prompt runs all 4 arms back to back in a shuffled order, 3 reps → 45 pairs × 4 arms = 180 generations
(lab/paired.jsonl). Arms: off · on (lossless, lenience 0) · adaptive · lenient (on + lenience 1.0 = accept every drafted token).
CPU steal on this shared VM: median 19.1% per generation, max 49.3% → numbers are noisy; the paired median ratio is the headline.
(A first block-by-block run was stopped after 16 generations when steal of 26-38% showed up: results_block_aborted.jsonl, not used.)

## Decode speed (median tok/s) and speedup vs off (median of per-pair ratios)
| task | off | on | adaptive | lenient | on/off | (range) | adaptive/off | lenient/off |
|---|---|---|---|---|---|---|---|---|
| summarize | 8.9 | 14.0 | 14.8 | 24.9 | 1.63× | 0.51–2.40 | 1.79× | 2.87× |
| code | 8.5 | 17.7 | 14.8 | 19.0 | **1.92×** | 1.27–2.32 | 1.97× | 2.21× |
| rewrite tone | 11.0 | 12.8 | 13.1 | 29.0 | **1.06×** | 0.87–2.06 | 1.38× | 2.52× |
| free form | 10.7 | 10.9 | 10.4 | 26.4 | 1.25× | 0.81–1.87 | 1.11× | 2.49× |
| copy / translate | 9.6 | 21.2 | 18.7 | 27.5 | **2.23×** | 1.06–3.19 | 1.71× | 2.69× |
| **all 45 pairs** | 9.5 | 14.2 | 14.3 | 25.7 | **1.49×** | 0.51–3.19 | 1.50× | 2.51× |
- Steal-adjusted (tok/s ÷ (1 − steal)) on/off all: 1.49× (same). Aggregate throughput (sum tokens / sum decode time): off 9.14, on 13.24 (1.45×), adaptive 13.02, lenient 21.91 tok/s.
- Wall time for all 45 prompts: off 19.1 min, on 13.4 min (−30%), adaptive 13.7, lenient 8.6.
- On was slower than off in 6/45 pairs (summarize p2 ×2, free form ×3, rewrite ×1; worst 0.51×).
- Adaptive ≈ on (1.50× vs 1.49×); it didn't rescue the slow tasks on this machine.
- Prefill median: off 100, on 91 tok/s (~109-token prompts). TTFT ~1.2 s all arms. Memory: pilot off 2,805 MB vs on 2,864 MB RSS (+59 MB, drafter); max RSS in the paired run 3,284 MB.

## Is it lossless?
- on vs off, greedy: **45/45 identical outputs** (same sha256); adaptive 45/45 identical.
- lenient vs off: 44/45 differ (median first difference at character 9).

## The lenient switch (lenience = 1.0): blind quality check
- Claude Sonnet 5.5 judged exact vs lenient, A/B order randomised/swapped, 3 trials × 15 prompts (lab/judge.jsonl, $0.21).
- **Exact won 42/45, tie 3/45 (verbatim copy only), lenient won 0.**
- Code 9/9 exact: lenient code doesn't parse (`const debounce(fn, ms) => {`, `CREATE DATABASE LibraryDatabase();`, garbled regex).
- Rewrite: lenient invented facts ("dropped by a third" → "31%", invented dates "October 26, 2023", "unanimously").
- Caps conversion: "SHIPIPP", "DROPP". French translation: "chaque boulanger" (baker) for "block".
- LiteRT-LM's own docstring: "WARNING: any c > 0 gives up the quality guarantee of speculative decoding."

## Their numbers (model card, S26 Ultra; 1024 prefill / 256 decode; CPU 4 threads)
- CPU: baseline 17.0 → summarize 27.5 (1.62×), code 26.2 (1.54×), rewrite 29.5 (1.74×), free form 21.1 (1.24×).
- GPU: 21.9 → code 49.4 (2.26×), rewrite 47.5 (2.17×), summarize 46.0 (2.10×), free form 36.7 (1.68×).
- Linux Arm CPU baseline 17.5 tok/s; no desktop speculative numbers published.

## Read
- Lossless speculative decoding is real and free on a plain CPU: 1.49× overall, output identical, +59 MB.
- It is task-shaped: copy/translate 2.2×, code 1.9×, but tone rewrite only 1.06× (Google's best CPU task, 1.74×) and free form 1.25×.
- The 2× headline is a phone GPU number. On my CPU, the only arm that beat 2× everywhere was lenient, and it broke the output 42/45.
- Caveats: one shared cloud VM with 19% median CPU steal; 15 prompts, greedy only, 256 output tokens; no phone, no GPU, no Arm; quality judged by Claude, not humans.
