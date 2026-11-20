# EP022 · Firecrawl Local, raced (Tokenwright, 20 Nov 2026)

Firecrawl Local (v0.1.1, `cargo install firecrawl-local`) vs trafilatura vs crawl4ai 0.9.6 on 29 real pages (`urls.json`), 3 rounds, on a Linux server (4 cores, no GPU).

- `bench.py <tool> <round>`: runs one tool over every page; memory = PSS summed over the whole process tree (server + Chrome children) every 50 ms. Tools: `fc_cloud` (defaults), `fc_local` (FIRECRAWL_CLOUD=off), `fc_static` (browser never), `trafilatura`, `crawl4ai` (via `worker.py`).
- `make_gold.py`: renders each page in Chromium and asks Claude Sonnet 5.5 for 2 questions from the main content → `gold_qa.jsonl`.
- `qa.py`: Claude Haiku 5.5 answers from each tool's markdown only (3 repeats), Sonnet grades → `qa_results.jsonl`.
- `summarize.py` → `summary.json`. Full write-up in `DATA.md`.

Scraped page copies are not included (they belong to the sites). Video: youtube.com/@Tokenwright
