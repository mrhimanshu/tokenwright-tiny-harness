# EP029: is Claude's writing harder to read? (Tokenwright)

Tests the claim in Clark, Martin & Mahowald, "Why is AI-generated language so hard to understand?" (arXiv 2610.29162)
on Claude Opus 5.5 and Claude Haiku 5.5, using 39 Stack Overflow questions whose accepted human answers predate ChatGPT.

- `fetch_se.py`: pulls the 39 questions + accepted answers (questions.json) and a 356k-word reference corpus of other answers from the public StackExchange API (the corpus isn't committed; re-run to rebuild it)
- `gen.py`: Claude answers each question with no system prompt, "Be concise.", or a plain-English line → gen.jsonl
- `rewrite.py`: control, where Claude rewrites the human answer in its own words (cond=rewrite in gen.jsonl)
- `analyse.py`: spaCy (en_core_web_md) features: dependency length, noun stacks, inanimate subject + animate verb, words/sentence, odd (unattested) word pairs per 1,000 → metrics.jsonl, summary.json
- `DATA.md`: results table and caveats

Headline: odd word pairs per 1,000 = humans 290, Opus 371 (+28%, higher on 32/39), Haiku 344. "Be concise." left Opus at 371. The plain line gave −6% (Opus) and −8% (Haiku). Dependency length and noun stacks were level, and Claude's sentences were shorter.

Human answers are from Stack Overflow, licensed CC BY-SA 4.0. Each item in questions.json links to its source answer (`link`).
Video: https://www.youtube.com/@Tokenwright
