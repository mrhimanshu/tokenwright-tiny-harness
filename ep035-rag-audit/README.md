# EP035: "84% of RAG errors happen after retrieval", replicated and audited (Tokenwright, 27 Nov 2026)

AlphaSignal (26 Nov 2026) covered arXiv 2603.14045, "The Reasoning Bottleneck in Graph-RAG" (Findings of EACL 2027): on HotpotQA,
84% of KET-RAG's wrong answers had the gold answer string in the retrieved context ("reasoning failures").
I rebuilt the measurement on a plain vector RAG: 300 HotpotQA dev questions (seed 42), their 2,956 paragraphs pooled,
BGE Base v1.5 GGUF Q4_K_M (66 MB, CompendiumLabs/bge-base-en-v1.5-gguf) on 4 CPU cores, Claude Haiku 5.5 answering, 3 runs per condition.

- `prep.py 300 <gguf> <tag>`: sample questions, pool paragraphs, embed (llama-cpp-python), write `data/retrieval_<tag>.json`.
  Get `hotpot_val.parquet` from huggingface.co/datasets/hotpotqa/hotpot_qa (distractor/validation) and the GGUF into `data/` first.
- `run_qa.py <model> <k5|k20|k50|gold|k50cot|k50join|goldjoin> <run> [limit]` → `results/qa.jsonl` (Anthropic key needed).
  Use max_tokens of a few thousand: Haiku 5.5 thinks adaptively, and a 200-token cap returned empty answers (`qa_cap200_aborted.jsonl`).
- `grade.py`: string match, then a Claude Sonnet 5.5 judge; paper's retrieval-vs-reasoning split → `results/graded.jsonl`.
- `audit.py <model> <cond>`: Claude Opus 5.5 labels each wrong answer (bad key, grader miss, missing evidence, over-cautious, reasoning error).
- `report.py` → `summary.json`. Write-up: `DATA.md`.

Headline (Haiku, top 50 ≈ 11k tokens, 900 answers): 88.9% right; 85 of 100 errors are "after retrieval" by the paper's rule (paper: 84%).
Audit of the 100: 41 answer key/question broken, 26 a needed fact missing, 20 over-cautious "not in context", 6 grader too strict,
7 real reasoning errors. Only the 2 right paragraphs: 90.3%. Top 5: 77.8% and the "after retrieval" share falls to 51%.
One prompt sentence ("the answer often needs two facts from two paragraphs: combine them"): 88.9% → 92.0% (1 run).
HotpotQA is CC BY-SA 4.0.
