# EP010: Deletion Tuning vs full fine-tuning on a MacBook

Video: Tokenwright, "Deleting Weights vs Fine-Tuning: I Tested It on a Mac".

A compact re-implementation of the supervised fine-tuning recipe from *The Surprising Effectiveness of Deleting Weights in LLM Post-Training*
(arXiv 2611.10866; official code, MIT: https://github.com/agentic-learning-ai-lab/deleting-weights), run on an Apple M4 Pro (24 GB, MPS)
with Qwen/Qwen2.5-0.5B-Instruct on 5 MMLU-Pro subjects.

| method (mean of 5 subjects) | accuracy |
|---|---|
| original | 13.0% |
| starting mask (Wanda, no training) | 12.8% |
| random deletion (same count) | 12.4% |
| **deletion tuning** | **20.7%** |
| full fine-tuning | 22.3% |

Mask ≈ 1.9 MB per subject (bit-packed + zstd) vs a 988 MB fine-tuned model. Full details, caveats and the paper's own numbers: DATA.md.

Run: `python fetch.py` (downloads + sha256-checks the model), then `python dt_lab.py --task health --methods base,wanda,dt,random` and
`python dt_lab.py --task health --methods fft`; `python analyse.py` → summary.json. Needs torch, transformers, datasets, zstandard.
