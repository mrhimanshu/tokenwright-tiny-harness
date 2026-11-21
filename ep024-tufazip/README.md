# EP024: an LLM as a zip file, on a CPU (vs tufazip)

Video: "An AI Zipped Wikipedia 3x Smaller. Then It Lost to gzip" (Tokenwright, 22 Nov 2026).
Story: Tufa Labs' tufazip compresses enwik9 (1 GB of Wikipedia) to 105,388,353 bytes with one transformer ([write-up](https://tufalabs.ai/research/tufazip/), [code](https://github.com/Tufalabs/tufazip)).

What's here (CPU only, no GPU, $0 API):
- `llm_bpb.py`: small pretrained LMs (SmolLM2-135M/360M, Qwen2.5-0.5B) as compressors: ideal arithmetic-code length in bits per byte on 3 × 64 KB slices of enwik9.
- `classic_slices.py`, `classic_full.sh`: gzip / bzip2 / xz / zstd / brotli on the same slices and on the full 1 GB.
- `roundtrip.py`: a real compressor (SmolLM2-135M + [constriction](https://github.com/bamler-lab/constriction) range coder): encode → file → decode, byte-identical check.
- `online_zip.py`: tufazip's idea at toy scale: a byte-level transformer from random weights that learns while it compresses.
- `showcase.py`: per-token bit costs for one sentence.
- Results: `results.jsonl` (every run), `summary.json`, `DATA.md`.

Headline: SmolLM2-135M 0.94 bits/byte vs xz -9e 2.81 (≈3× smaller), but counting its 269 MB of weights, a 1 GB archive would be ~386 MB, more than gzip (322.6 MB). Real decoder speed: 43 bytes/s.

Setup: `pip install torch transformers constriction zstandard brotli numpy huggingface-hub`; put enwik9 (http://mattmahoney.net/dc/enwik9.zip) where `common.py` points; `python get_models.py`.
