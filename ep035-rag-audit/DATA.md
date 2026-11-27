# EP035 DATA (my runs, 27 Nov 2026, 06:00–06:25 UTC) — raw: lab/results/*.jsonl, summary: lab/summary.json

## Setup
- 300 HotpotQA dev (distractor) questions, seed 42; their 2,956 paragraphs pooled into one corpus (every question competes with 2,954 other paragraphs).
- Retriever: BGE Base En v1.5 GGUF **Q4_K_M, 66 MB** (Compendium Labs, sha256 = HF API), llama-cpp-python 0.3.38, 4 vCPUs. Query prefix as the card says. Plain cosine top-k, no reranker, no graph.
- Answerer: Claude Haiku 5.5 (effort low), "answer only from the context; else say not in context". 3 runs per condition (temperature default).
- Grading like the paper: normalized string match (exact / contains / token subset), the rest by a Claude Sonnet 5.5 judge (65 unique judgments). Error split = paper's rule: wrong + answer string in context → "reasoning failure", else "retrieval failure".
- Audit: Claude Opus 5.5 read every wrong answer with the 2 evidence paragraphs (and whether each was in context) and labelled the cause (5 labels). I read every k50 label + reason myself; they hold up.

## Results (Haiku 5.5, 300 questions × 3 runs)
| context | avg tokens | both evidence paras retrieved | accuracy (3 runs) | wrong (of 900) | paper rule: "after retrieval" share |
|---|---|---|---|---|---|
| top 5 | 1,112 | 79.7% | 77.8% (76.7/78.3/78.3) | 200 | 51% |
| top 20 | 4,487 | 94.3% | 86.7% (86.3/86.0/87.7) | 120 | 79% |
| **top 50 (≈ paper's 10k)** | **11,270** | 96.3% | **88.9%** (89.3/88.7/88.7) | **100** | **85%** (paper: 84%) |
| only the 2 right paragraphs | 453 | 100% | 90.3% (all 3) | 87 | 95% |
- Step-by-step "chain of facts" prompt at top 50 (paper-style structured prompting, 1 run): 89.7% vs 88.9% plain = within run noise.
- Sonnet 5.5 (first 80 questions, 1 run): top 50 92.5%, right-paragraphs-only 93.75%. Cost per question at top 50: Haiku $0.00116, Sonnet $0.0227 (~20×).
- Embedder size: both evidence paras in top 20: Q4 66 MB 94.3% vs F16 209 MB 95.0%; top 5 79.7% vs 81.3%.

## Audit of the 100 wrong answers at top 50 (Haiku, 3 runs; labels by Opus 5.5)
| real cause | all 100 wrong | of the 85 the paper rule calls "reasoning failure" |
|---|---|---|
| answer key wrong / question garbled or subjective | 41 | 40 |
| needed fact not retrieved (answer string matched by coincidence or one hop missing) | 26 | 14 |
| said "not in context" though both paragraphs were there | 20 | 18 |
| grader too strict (answer was right) | 6 | 6 |
| **real reasoning error** | **7** | **7** |
- So 7 of 100 errors (7 of 900 answers, 0.8%) are the model actually reasoning wrong. 47 of 100 "errors" (41 key + 6 grader) are not errors.
- 55 of 100 wrong answers were "not in context" replies.
- With perfect retrieval (2 right paragraphs only, 87 wrong over 3 runs): 37 bad key, 37 over-cautious, 8 grader, 5 real reasoning.
- Examples (answer key): "Who is still alive today, Franklin Adreon or Ryan Gosling?" key: Franklin Adreon (died 1979). "Who was born first, David Draiman or Terry Kath?" key: Draiman (1973; Kath 1946). "Husband of William Roper born…" key "7 February 14786". Over-cautious: "Where were the recording sessions for Beat It?" both paragraphs present (Beat It is on Thriller; Thriller recorded at Westlake), Haiku: not in context.
- Real reasoning error example: "Which was published more frequently, Popular Science or Girlfriends?" (monthly vs bi-monthly) → Haiku said Popular Science.

## Spend: $5.44 total (incl. $0.6 on the first run, aborted: max_tokens 200 cut off Haiku's adaptive thinking → 73 empty answers that the paper rule would have counted as "reasoning failures").

## Caveats
- Plain vector RAG, not KET-RAG's graph; Claude 5.5, not Llama 8B/70B; HotpotQA only (not MuSiQue/2Wiki); 300 questions, not 500.
- Audit labels come from Opus 5.5 (read by me). Judge = Sonnet 5.5. A different auditor could move single items.
- The paper's own caveat says substring coverage over/under-counts; our audit measures how much.

## Added 06:40 UTC: one-sentence "combine them" prompt (1 run each)
- Prompt adds: "The answer often needs two facts from two different paragraphs: combine them … Only if a fact you need is truly missing, reply not in context".
- Top 50: **92.0%** (vs 88.9% plain, 3-run mean); 24 wrong: 14 bad key, 6 missing evidence, 2 over-cautious (plain: ~6.7/run), 1 grader, 1 real reasoning. Over-cautious + abstain share of wrong 37.5% (plain 55%).
- Paired vs each plain run: fixes 10 / 11 / 12, breaks 2 / 1 / 2. Plain run 0 vs run 1 differ on 8 questions in total, so +~10 net is above run noise (still 1 run).
- Only the 2 right paragraphs: 93.3% (plain 90.3%).
- Same first 80 questions, top 50: Haiku plain 93.75 / 92.5 / 93.75 (mean 93.3), Haiku "combine" 95.0, Sonnet plain 92.5. Right paragraphs only: Haiku 90.0, Sonnet 93.75.
- Spend now $5.8 total.
