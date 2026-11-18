# EP018 DATA (lab run 18 Nov 2026 22:05–23:10 UTC, cloud Linux box, no GPU)
Raw: lab/runs/<run>/ (paper .tex/.pdf, usage.jsonl, s2_calls.jsonl, refs_check.jsonl, nums_check.jsonl, rubric.json, cites.json), lab/summary.json.
Input for every writer: lab/raw_materials (idea_sparse.md + experimental_log.md + 1 figure), rewritten from our own EP015 CRAM / Sudoku lab, so the ground truth of every number is known.
Writers: PaperOrchestra commit d9bae99, every agent on gemini-3.8-flash (repo default gemini-3.1-pro-preview = 404 on our key), no Semantic Scholar key, ICLR template, no plotting agent, n=5 (runs 1–3 in parallel, runs 4–5 alone with S2 calls logged). Controls: one single prompt with the same files + template, gemini-3.8-flash (google_search tool attached) n=3, claude-sonnet-5-5 n=3.
Checks: every BibTeX entry vs Crossref + arXiv + Semantic Scholar (title fuzz ≥ 90 + first-author surname); non-matches checked by hand/web search. Every number sentence labelled by a Claude Sonnet 5.5 judge against the materials (lab/check_numbers.py); the specific invented items below were confirmed by hand (grep in the .tex). Honesty rubric by Sonnet judge (lab/check_rubric.py).
API spend: Gemini $5.20 (PaperOrchestra, 5 runs) + $0.15 (Gemini one-prompt) + $0.63 (Sonnet one-prompt) + ~$3 Sonnet judges ≈ $9 (over the ~$5 guide; the 5-run PaperOrchestra loop was the bulk).

## 1. Cost, time, size
| writer | runs | wall time / paper | $ / paper | pages | references |
|---|---|---|---|---|---|
| PaperOrchestra (Gemini 3.8 Flash) | 5 | 835–2,040 s (14–34 min) | 0.63–1.54 (mean 1.04) | 10–13 (runs 1–3) | 4, 7, 7, 7, 4 |
| Gemini 3.8 Flash, 1 prompt | 3 | 89–122 s | 0.04–0.06 | — | 25, 18, 26 |
| Claude Sonnet 5.5, 1 prompt | 3 | 84–89 s | 0.21 | — | 16, 19, 21 |
- PaperOrchestra run 3: first attempt's draft did not compile (unclosed \texttt, "Emergency stop"); the pipeline caught the exception and restarted from scratch (try 2/3 succeeded).

## 2. References
| writer | real (verified) | fabricated (no such paper) | real paper, wrong authors |
|---|---|---|---|
| PaperOrchestra | 29 / 29 | 0 | 0 |
| Gemini 1 prompt | 60 verified + 6 real ones the checker missed (dataset ×3, Norvig essay, Wilson & Pawley 1988, CLRS) = 66 of 69 | 2 (run 1: "Can a One-Layer Transformer Solve Hard Sudoku? …" Arora 2024; "Benchmarking reasoning in neural networks: A survey" Slabas 2023) | 1 (run 1: "Solve the Loop…" credited to Deepak Pathak; real authors Fein-Ashley, Rashidinejad …) |
| Claude 1 prompt | 52 verified + 4 real ones the checker missed (Norvig essay ×3, Chollet) = 56 of 56 | 0 | 0 |
- Why PaperOrchestra keeps so few: each candidate needs a Semantic Scholar title match (utils/scholar_utils.py; any non-200 → return None, no retry). Runs 4 + 5 (alone): 106 + 135 = 241 lookups, 94 + 129 = **223 returned HTTP 429** (Too Many Requests), 12 + 6 OK → 7 and 4 papers kept.
- The CRAM paper (Hoover, Blayney, Whittington, arXiv 2611.17309), the method the whole experiment replicates, is \cite-d in **1 of 5** PaperOrchestra papers (run 4). Run 1 names "Hoover et al. (2026)" in plain text only; run 2 puts \citep[cf.]{Chen2026EnergybasedReasoners, Bresler2014} where the CRAM citation belongs; runs 3 and 5 never credit the authors. Gemini 1-prompt: cited 3/3. Claude 1-prompt: cited in text 2/3 (run 3 only in the .bib).

## 3. Invented details (confirmed by hand in the .tex)
| item (NOT in the log) | PaperOrchestra | Gemini 1 prompt | Claude 1 prompt |
|---|---|---|---|
| Haiku "max seconds" table cell (log gives max only for Opus/Sonnet) | run 1: 182.0 | 189.4, 183.4, 182.4 (3/3) | 0/3 (left empty) |
| laptop memory | 24 GB (runs 1, 4), 48 GB (run 3) | 24 GB (runs 1, 3) + "12 cores" (run 1) | 0/3 |
| toolchain / hyperparameters | run 3: Clang 16.0.0, Python 3.11, NumPy 1.26.4, Adam lr 0.01, wd 1e-4, 150 epochs, w0 = 1.0; run 2: Adam lr 1e-2, 50 epochs; run 1: geometric cooling schedule; run 5: Python 3.11 | run 3: Python 3.12, "22–28 clues"; runs 1, 3: per-model solver write times (not in log) | 0/3 |
| meaning of "CRAM" (the paper never expands it) | runs 2, 3: "Classical Recurrent Associative Memory"; run 5: "Continuous Relaxation for Algorithmic Modeling" | "Compact Reasoning Associative Memory" (1), "Classical Relational Associative Memor(y/ies)" (2, 3) | 0/3 |
| arithmetic slips | e.g. run 1 "$355" for 500 Opus puzzles (0.426 × 500 = $213), "five orders of magnitude" | run 1 "$0.42–$0.71 per puzzle" (0.71 is per solved) | run 1: "9 of the 12 non-solves" (table: 2 + 2 + 7 = 11) |
- Judge totals (number sentences labelled wrong + invented, includes some judge false positives): PaperOrchestra 12, 5, 11, 9, 13; Gemini 1-prompt 16, 3, 15; Claude 1-prompt 3, 0, 1.
- Rubric "no claims beyond the log": PaperOrchestra 0/5 pass, Gemini 0/3, Claude 2/3.

## 4. What PaperOrchestra did well
- Every kept reference real (29/29); kept the small-n caveat and the "hand-set energy = learned" caveat in 5/5; kept the original paper's numbers (99.996%, 42 ms H200) separate from ours in 5/5; 10–13-page compiled ICLR PDFs with tables and our figure; review loop (3 rounds + formatting fixes).

## Headline
- 29 of 29 PaperOrchestra references are real, but only 4–7 per paper: 223 of 241 Semantic Scholar lookups were rate-limited and silently dropped, and the replicated CRAM paper is cited in 1 of 5 runs.
- It made up things that look like data: a Haiku max-time cell (182.0 s), 24/48 GB of memory, Clang 16 / NumPy 1.26.4 / 150 epochs. The one-prompt Gemini did the same (3/3) and invented 2 references; one Claude Sonnet prompt invented no references and no setup details (1 bad sum), for ~21 cents in 90 s.
- Caveats: Flash instead of their default Pro model; no Semantic Scholar key; one experiment, 5 + 3 + 3 runs.
