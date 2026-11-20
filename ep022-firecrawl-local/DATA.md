# EP022 DATA (my runs, 20 Nov 2026, Quill cloud computer: Linux x86_64, 4 vCPU visible, no GPU; UK broadband-class datacentre link)

Raw: lab/results.jsonl (one row per page per run), lab/mem.jsonl (memory per run), lab/qa_results.jsonl (agent answers), lab/summary.json, lab/md/ (every markdown output).
Page set: lab/urls.json, 29 real pages (Wikipedia ×3, Python/MDN/Rust/FastAPI/Anthropic docs, GitHub READMEs + an issue, arXiv abstract + PDF, BBC, The Verge, 2 blogs, Stack Overflow, toscrape practice sites incl. 2 JavaScript-only pages, react.dev, Hugging Face, PyPI, npm, crates.io).
Install: `cargo install firecrawl-local` (v0.1.1) took 487 s on this machine; binary 23.9 MB.

## Tools (each scrapes all 29 pages one after another, 3 rounds, order rotated)
- fc_cloud = Firecrawl Local `serve`, defaults (FIRECRAWL_CLOUD=auto, browser auto)
- fc_local = same, FIRECRAWL_CLOUD=off (nothing leaves the machine)
- fc_static = browser never, cloud off
- trafilatura 2.x + requests (Python, no browser)
- crawl4ai 0.9.6 (Python + Playwright headless Chromium, its defaults)
Memory = PSS summed over the whole process tree (server + every Chrome child), sampled every 50 ms. Idle = 5 s after ready.

## Memory + speed (3 runs each)
| tool | idle MB | peak MB | 29 pages, s | median page s | pages with content (of 29) |
|---|---|---|---|---|---|
| fc_cloud (default) | 15.5–15.7 | 215–226 | 8.9 / 5.3 / 7.2 | 0.08 | 26 |
| fc_local (cloud off) | 15.5–15.7 | 220–228 | 4.7 / 7.2 / 6.1 | 0.10 | 24 |
| fc_static | 15.5–15.7 | 139–153 | 4.4 / 3.7 / 3.5 | 0.07 | 24 |
| trafilatura | 34.9 | 103 | 8.9 / 7.8 / 8.4 | 0.17 | 23 |
| crawl4ai | 331–332 | 866–892 | 29.7 / 32.1 / 31.1 | 0.69 | 26 |
- Idle: Firecrawl Local 15.6 MB vs their "11 MB idle" (their machine/metric unknown; ours is Linux PSS). Close to the claim.
- Under load memory rises ~14× to ~220 MB (Chrome start attempts + big pages). Still ~4× under crawl4ai's peak; crawl4ai idles 21× higher (331 vs 15.6 MB).
- Speed: ~6 s vs ~31 s for crawl4ai (≈5×), median page 0.10 vs 0.69 s (≈7×). vs trafilatura ≈1.4×.
- NOT tested: the "37× vs self-hosted" and "230× less memory" baselines (the old 5-service Docker stack: no Docker on this machine). 11 MB × 230 ≈ 2.5 GB = the old stack's reported idle. Their numbers.

## Twist 1: the browser and the sandbox
On this server (container, user namespaces blocked) Firecrawl Local refused to start Chrome without its sandbox ("Firecrawl Local does not run Chrome without its sandbox"). JavaScript pages came back as just a title + a warning: quotes.toscrape.com/js → 94 characters; js-delayed → 94; crates.io → 0. crawl4ai launches Chromium with --no-sandbox by default (its browser_manager.py: "The default keeps --no-sandbox"), so it rendered quotes/js (1,666 chars). Same machine, same pages.

## Twist 2: pages that leave your machine
With the default FIRECRAWL_CLOUD=auto, 2 of 29 pages (Stack Overflow 403, npm 403 Cloudflare) were fetched by Firecrawl Cloud instead: no warning, only "source": "firecrawl-cloud" in the JSON. With cloud off, those two come back empty with a 403 warning. (README documents this: blocked pages go to the cloud; calls carry an install ID.)

## Agent test (does the markdown let an AI answer?)
Claude Sonnet 5.5 wrote 2 questions per page from a real-Chromium render (independent of every tool), 28 pages (npm excluded: its render was a Cloudflare check) = 56 questions. Claude Haiku 5.5 answered from each tool's markdown only, 3 repeats (identical scores all 3 times); Sonnet graded vs the gold answer.
| tool | correct (of 56) | % | doc tokens for 28 pages | non-JS pages (44 q) | JS pages (12 q) |
|---|---|---|---|---|---|
| fc_cloud (default) | 46 | 82.1 | 494,659 | 42 | 4 |
| crawl4ai | 46 | 82.1 | 594,088 | 40 | 6 |
| fc_local (cloud off) | 44 | 78.6 | 444,751 | 40 | 4 |
| trafilatura | 38 | 67.9 | 185,032 | 34 | 4 |
- trafilatura is the cheapest (185k tokens, 2.4× fewer than Firecrawl) but misses the most (no PDFs, cut the Anthropic models table, BBC list).
- Firecrawl misses: wiki "d_emb 768" (table), BBC second story, the JS pages.
- API spend for gold + answers + grading ≈ $3.
