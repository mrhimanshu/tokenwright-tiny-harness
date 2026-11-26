# EP033: Gemma 4 E4B speculative decoding on a plain CPU (Tokenwright, 26 Nov 2026)

Google's litert-community Gemma 4 E4B build for LiteRT-LM adds speculative decoding (a draft model guesses, Gemma checks).
Their model card: Samsung S26 Ultra GPU 21.9 → 49.4 tok/s on code, CPU 17.0 → 29.5 on tone rewrites. What does it do on an x86 CPU?

- `prompts.py`: 15 prompts in Google's 4 task types (summarize, code, rewrite tone, free form) + copy/convert/translate.
- `run_paired.py`: one LiteRT-LM engine (CPU, 4 threads, greedy), each prompt runs off / on / adaptive / lenient(1.0) back to back
  in a shuffled order, 3 rounds, CPU steal logged from /proc/stat → `paired.jsonl` (180 generations).
- `analyse.py` → `summary.json`. `judge.py`: blind Claude Sonnet 5.5 A/B check of lenient vs exact → `judge.jsonl` ($0.21).
- `run_lab.py` + `results_block_aborted.jsonl`: the first block-by-block design, stopped when CPU steal of 26-38% showed up.
- Full write-up: `DATA.md`.

Headline: lossless speculative decoding 1.49× overall (copy 2.23×, code 1.92×, summaries 1.63×, free writing 1.25×,
tone rewrites 1.06×), 45/45 outputs identical, adaptive 1.50×. Lenience 1.0 (accept every drafted token): 2.51× faster,
but the normal answer won the blind check 42/45 (3 ties, 0 lenient wins); lenient code didn't parse, and it invented facts.

Setup: `pip install litert-lm` (0.20.0), download `gemma-4-E4B-it.litertlm` from
huggingface.co/litert-community/gemma-4-E4B-it-litert-lm (3.66 GB, sha256 0b2a8980…52e0) into `model/`, `mkdir cache`,
then `python run_paired.py --reps 3 --arms off,on,adaptive,lenient`. judge.py needs `pip install anthropic` and an API key.
