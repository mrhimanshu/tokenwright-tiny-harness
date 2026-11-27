# EP036: llm.asm vs llama.cpp, raced on one CPU

Video: Tokenwright, "14 KB of Assembly vs llama.cpp: I Raced Them 90 Times" (28 Nov 2026).

An independent re-run of the llm.asm README benchmark (github.com/alesha-pro/llm.asm, commit e7d4883) against llama.cpp v1.1.0,
same model (Qwen3-0.6B Q8_0), on an AMD EPYC 9354P cloud VM with 4 vCPUs. Results in DATA.md; all 90 raw runs in results/race.jsonl.

Reproduce:
1. Build llm.asm: `make inference FAST_Q8=1` (copy to /tmp/ep036bin/asm-llm-q8) and `make inference FAST_Q8=0` (asm-llm-fp32act); export weights with its scripts/export_weights.py --scale-dtype fp16.
2. Build llama.cpp twice with build_llama.sh (native + AVX2-only), download Qwen/Qwen3-0.6B-GGUF Qwen3-0.6B-Q8_0.gguf.
3. `ROUNDS=6 python3 run_race.py results/race.jsonl`, then `python3 analyse.py` and `python3 same_answer.py`.
Paths are hard-coded to /tmp/ep036*; edit the constants at the top of run_race.py.
