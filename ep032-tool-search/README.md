# EP032: MCP tool search vs prompt caching (Tokenwright, 25 Nov 2026)

Does Claude's tool search ("cuts context by over 85% in multi-server setups") also cut the bill?

- `gen_catalog.py` writes 148 MCP-style tools for GitHub, Slack, Sentry, Grafana, Splunk + 30 tasks (`catalog_raw.json`).
- `run_lab.py` runs each task 3 ways: all tools loaded (prompt-cached), `tool_search_tool_bm25_20251119`, `tool_search_tool_regex_20251119`.
- `session.py` runs 4 multi-step agent jobs (fake tool results), both arms with automatic prompt caching.
- `analyse.py` → `summary.json` / `analyse.out`. Full write-up: `DATA.md`.

Headline: 91% less context (37,857 → 3,318 tokens), same tool-pick accuracy, but with a warm cache tool search cost
59% more per request on Opus 5.5 (1.06 vs 1.69 cents) and 70% more on Sonnet 5.5; a tie on Haiku 5.5. Without caching
(or with an expired cache) tool search is 9-11x cheaper. Break-even on Opus: ~29 requests in a row, each < 5 min apart.

Needs `pip install anthropic` and a key in `~/.config/anthropic/key` (or ANTHROPIC_API_KEY). Spend for everything: $3.56.
