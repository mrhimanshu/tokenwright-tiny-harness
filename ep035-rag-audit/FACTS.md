# EP035 FACTS (verified 27 Nov 2026, 06:20 UTC)

## The story
- AlphaSignal, Thu 26 Nov 2026 (14:12 UK), Signal #2, 3,088 likes: "KET-RAG Audit Finds 84% of AI Errors Happen After Retrieval".
  AlphaSignal page: https://alphasignal.ai/paper/ket-rag-audit-finds-84-of-ai-errors-happen-after-retrieval (published 26 Nov 2026 03:15 UTC).
- Paper: "The Reasoning Bottleneck in Graph-RAG: Structured Prompting and Context Compression for Multi-Hop QA",
  Yasaman Zarrinkia, Venkatesh Srinivasan, Alex Thomo (University of Victoria). arXiv 2603.14045, v1 14 Mar 2026, v2 18 Mar, v3 24 Nov 2026.
  Findings of EACL 2027. Code: github.com/thomouvic/graph-rag-qa-pub
- Same newsletter, Top Model #3 (3,400 likes): Compendium Labs' BGE Base En v1.5 GGUF, 800,000 downloads, Q4_K_M 66 MB / Q8_0 113 MB / F16 209 MB,
  query prefix "Represent this sentence for searching relevant passages:", 512-token limit. HF: CompendiumLabs/bge-base-en-v1.5-gguf
  (806,476 downloads on 27 Nov 2026; files last modified 17 Feb 2024, so the model is old; the download count is the news).

## Their numbers (paper, KET-RAG, 500 questions per dataset, seed 42)
| | HotpotQA | MuSiQue | 2WikiMHQA |
|---|---|---|---|
| gold answer string in retrieved context | 90.8% | 77.2% | 81.0% |
| accuracy, Llama 8B baseline | 67.0% | 23.6% | 31.4% |
| accuracy, Llama 70B baseline | 78.0% | 35.2% | 48.8% |
| reasoning share of errors, 8B baseline | **84%** | 73% | 80% |
| bridging-entity coverage (stricter) | 88.2% | 69.4% | 66.0% |
- Definitions: retrieval failure = wrong answer AND gold answer string absent from context; reasoning failure = wrong answer while the gold string IS in the context.
- Grading: normalized string match (lowercase, strip articles/punctuation, substring + last-token checks), rest by an LLM judge (Llama-3.1-8B); audited by Claude Opus 4.6 on 102 judgments, 96.1% agreement.
- Context ~10,000 tokens per question (entities, relations, community reports, chunks). Embeddings MiniLM-L6-v2. Groq, temperature 0.3.
- Fixes: SPARQL chain-of-thought prompting +2 to +14 pp; graph-walk compression ~60% less context (10k → 4k), no LLM calls; augmented 8B + routing matches/exceeds unaugmented 70B (HotpotQA 79.8 vs 78.0) at "~12x lower cost" = Groq list price ratio $0.05 vs $0.59 per M tokens, not a measured bill.
- The paper's own caveat: substring coverage can overcount (gold string in a distractor) and undercount (paraphrase). AlphaSignal: "84%" is the top of a 73–84% range.

## Competition (27 Nov 06:15 UTC, youtube_search, published after 20 Nov)
- "RAG errors after retrieval": ~15 generic RAG-failure explainers (Dabeer AI, Skill:RE, Garvit Anand…), none on this paper, none measured the split.
- "Graph RAG reasoning bottleneck": 0 relevant.

## Our setup (see DATA.md)
- HotpotQA dev (distractor), 300 questions sampled seed 42, their 2,956 paragraphs pooled into one corpus (HF hotpotqa/hotpot_qa, validation parquet sha256 c20b6386…).
- Retriever: BGE Base v1.5 GGUF Q4_K_M (sha256 74aebb55… = HF API) via llama-cpp-python 0.3.38 on the 4-vCPU VM; F16 for comparison (sha256 88360fdf…).
- Plain top-k vector RAG, NOT KET-RAG's graph index. Answerers: Claude Haiku 5.5, Sonnet 5.5.
