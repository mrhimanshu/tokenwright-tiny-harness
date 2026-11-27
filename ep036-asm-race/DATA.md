# EP036 DATA: llm.asm vs llama.cpp, raced on one CPU (27 Nov 2026, 22:08–22:16 UTC)

Machine: cloud VM, AMD EPYC 9354P (Zen 4, AVX-512 + VNNI), 4 vCPUs, CPU steal median 0.3–3% per run (logged).
Model: Qwen3-0.6B Q8_0 for both (llm.asm .asmbin v2 exported from Qwen/Qwen3-0.6B; llama.cpp = official Qwen/Qwen3-0.6B-GGUF Q8_0). sha256 verified.
Engines: llm.asm e7d4883 FAST_Q8=1 (14,712 B) and FAST_Q8=0 (14,008 B, the pre-25-Nov kernel); llama.cpp v1.1.0 (1715275) native build (AVX-512) and AVX2-only build, llama-bench -r 1 -ngl 0.
Design: 6 rounds; in each round every arm runs back to back per cell in shuffled order. Ratios = median of per-round paired ratios.
Raw: lab/results/race.jsonl (90 runs) · lab/summary.json · lab/results/same_answer.json. Code: lab/run_race.py, lab/analyse.py, lab/same_answer.py. API spend: $0.

## Decode (34-token prompt, 64 generated tokens), tok/s medians
| threads | llm.asm FAST_Q8=1 | llama.cpp native | llama.cpp AVX2-only | llm.asm FAST_Q8=0 (old kernel) | asm ÷ llama native (paired median, range, wins) |
|---|---|---|---|---|---|
| 1 | **32.0** | 19.6 | 19.2 | 11.9 | **1.64×** (1.58–1.65, 6/6) |
| 2 | **57.2** | 31.5 | 30.1 | 22.2 | **1.81×** (1.58–1.89, 6/6) |
| 4 | **80.1** | 51.3 | 48.0 | 37.2 | **1.65×** (1.39–5.5*, 6/6) |
*one llama run hit a steal spike (15 tok/s); medians unaffected.
- Their claim at 4 threads: 1.36× (69.24 vs 51.08 on EPYC 7642). Our llama.cpp at 4T = 51.3, almost exactly their 51.08; our llm.asm is faster (80.1 vs 69.2), so on Zen 4 the gap is BIGGER: +65% not +36%.
- vs the AVX2-only llama.cpp (same instruction set): 1.70× / 1.86× / 1.72×. AVX-512 barely helps llama.cpp decode here (native/AVX2 1.03–1.16×).
- The old FAST_Q8=0 kernel (same assembly, FP32 activations): 0.61× / 0.70× / 0.72× of llama.cpp. FAST_Q8=1 is 2.2–2.7× the old one. Assembly alone was SLOWER than llama.cpp; the 25 Nov INT8×INT8 kernel did it.

## Prefill (reading the prompt), tok/s medians
| | llm.asm | llama.cpp native | asm ÷ llama |
|---|---|---|---|
| 34 tokens, 1T | 41.3 | 87.9 | 0.47× |
| 34 tokens, 4T | 106.8 | 291.3 | 0.39× |
| 426 tokens, 4T | 94.9 | 289.8 | **0.34× (llama 2.9× faster)** |
- 426-token prompt + 64-token answer, 4T: time to first token llm.asm **4.52 s** vs llama.cpp **1.47 s**; whole reply 5.45 s vs 2.98 s (decode at depth 426: asm 72.9, llama 42.8 tok/s).
- Break-even (4T, our medians): llm.asm finishes first only when the prompt is shorter than the answer. 64-token answer → prompt ≤ ~63 tokens; 256 → ~253; 1,000 → ~989.

## Same answers? (5 prompts, greedy, 64 tokens, 4T)
- 4/5 word-for-word identical to llama.cpp (math 17×23=391, Python reverse, planets, French/Spanish). 1/5 (CPU caches) identical for 26 words, then a different but valid continuation ("accessed. Here's a breakdown" vs "accessed by the CPU.").

## Size and memory
- Engine on disk: llm.asm 14,712 bytes vs llama.cpp llama-completion + its libraries 15,608,952 bytes (~1,060×).
- Peak RAM (RSS), 4T, ctx 2048: llm.asm 650 MB vs llama.cpp 925 MB. (llama.cpp at its default context of 40,960: 5.28 GB.)
- Weights: .asmbin 643.5 MB vs GGUF 639.4 MB.

## Caveats (say them)
- One model only: llm.asm runs Qwen3-0.6B and nothing else; tiny models are where per-token overhead matters most.
- llama-bench measures decode from an empty cache (short test) while llm.asm decodes after the 34-token prompt (slightly harder for llm.asm).
- 4 vCPUs on a shared VM; we didn't test 8–40 threads (the author's gap shrinks to 1.18–1.20× at 16–40 threads).
- llama.cpp has batching, many models, GPUs, a server; llm.asm is one hand-tuned path.
