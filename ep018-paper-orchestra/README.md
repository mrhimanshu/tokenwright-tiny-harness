# EP018 · PaperOrchestra, fact-checked (Tokenwright, 18 Nov 2026)
Google's PaperOrchestra (github.com/google-research/paper-orchestra, commit d9bae99) turned our own experiment log (raw_materials/, from EP015) into papers.
We audited every reference and every number. Results: DATA.md and summary.json.
- run_po.py: runs a local copy of PaperOrchestra (not included; clone the repo at d9bae99 into ./po) and logs every Gemini call (usage.jsonl) and Semantic Scholar call (s2_calls.jsonl). Repo default models that our key can't call are mapped to gemini-3.8-flash.
- baseline.py: the one-prompt control (Gemini 3.8 Flash or Claude Sonnet 5.5).
- check_refs.py (Crossref + arXiv + Semantic Scholar), check_numbers.py (Claude judge vs the log), check_rubric.py, check_cites.py.
- runs/: every generated paper (.tex/.bib/.pdf) and every check. LaTeX was compiled with Tectonic 0.17.0 (pdflatex/bibtex shims).
Video: Tokenwright on YouTube.
