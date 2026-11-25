# EP032 DATA: does MCP tool search's "over 85% less context" also cut the bill? (my runs, 25 Nov 2026, night)

Setup (lab/): 5 MCP-style servers from Anthropic's own docs example (GitHub, Slack, Sentry, Grafana, Splunk), 148 tools written
like real MCP servers by Sonnet 5.5 (lab/gen_catalog.py, catalog_raw.json; 30/29/30/29/30 tools). 30 user requests, 6 per server,
each with one expected first tool (+ listed equal alternatives). Same system prompt in every arm (names the 5 services).
Arms: all = all 148 definitions in context, prompt-cached (cache_control on the last tool) · bm25 = tool_search_tool_bm25_20251119,
every tool defer_loading · regex = tool_search_tool_regex_20251119. Effort medium on all models. One API call per request
(stop at the first real tool call). Haiku n = 3 reps × 30, Opus/Sonnet n = 1 × 30 per arm.
Part 2 (lab/session.py): 4 multi-step jobs (crash → Sentry/GitHub/Slack; release → GitHub/Sentry/Grafana; latency → Grafana/
Splunk/Slack; kafka → Grafana/Splunk/Slack), fake tool results, up to 12 calls, BOTH arms with automatic prompt caching;
Sonnet and Haiku, n = 3 per job per arm. Total API spend $3.56 (incl. $0.36 catalog generation).

## Context (token counts, Opus 5.5 tokenizer)
- 148 definitions = 37,741 tokens (count_tokens; per server 6.8k–8.9k). Anthropic's docs example: ~55k for the same 5 servers.
- Up front with tool search: 653 tokens (search tool + system), i.e. 98% less before anything is loaded.
- Per request, measured: all = 37,857 · bm25 = 3,318 (Opus) / 3,521 (Sonnet) / 3,306 (Haiku) → **91% less** · regex 5,078–6,260 (83–87% less).
- Whole sessions: Sonnet 145,269 → 30,472 tokens per job (−79%); Haiku 173,787 → 38,774 (−78%).
→ The claim holds: over 85% less context (bm25 91% per request; sessions ~79%).

## Picking the right tool (expected first tool)
| model | all 148 loaded | bm25 search | regex search |
|---|---|---|---|
| Opus 5.5 | 30/30 | 30/30 | 29/30 |
| Sonnet 5.5 | 29/30 | 29/30 | 28/30 |
| Haiku 5.5 | 87/90 (96.7%) | 87/90 (96.7%) | 74/90 (82.2%) |
- No accuracy drop at 148 loaded tools (docs: selection "degrades once you exceed 30–50"). Not seen here.
- Regex hurts the small model: Haiku's 16 regex misses = list-first instead of get (list_saved_searches), wrong neighbour
  (list_prometheus_label_values), one gave up (end_turn).
- Shared misses: "Which alerts fired in the last 24 hours?" (my task didn't name Splunk; models picked Grafana) and
  "get_dashboard_versions" before restore (a reasonable 2-step plan, scored as a miss).
- Searches per request: bm25 1.04–1.17, regex 1.27–1.47.

## Money per request (first tool call, $)
| model | all, NO cache | all, cache expired (write 1.25x) | all, warm cache | bm25 search | bm25 vs warm |
|---|---|---|---|---|---|
| Opus 5.5 | 0.1538 | 0.1915 | **0.0106** | **0.0169** | +59% |
| Sonnet 5.5 | 0.0769 | 0.0957 | 0.0053 | 0.0090 | +70% |
| Haiku 5.5 | 0.0039 | 0.0048 | 0.00047 | 0.00046 | −1% (tie) |
- Why: Opus/Sonnet 5.5 bill cache hits at 0.05x input. 37,673 cached tokens on Opus = $0.0075 ≈ 1,900 fresh tokens.
  Tool search sends ~3,300 FRESH tokens (search tool + 5 loaded definitions + search result) at full price, + more output
  (Opus 182 vs 118 tokens). Haiku 5.5 cache hits are 0.10x → 3,800 equivalent → a tie.
- vs no caching: tool search is 9x cheaper (Opus $0.154 → $0.017); vs a cache that expired: 11x.
- Break-even (one cache write then reads, Opus): all-loaded beats tool search after ~29 requests in a row with < 5 min gaps
  (Sonnet ~25). Haiku: tool search never loses.
- Latency (median, first tool call): Opus 1.48 s → 2.74 s with bm25 (+1.25 s); Sonnet 1.29 → 2.28; Haiku 1.15 → 1.82.

## Whole sessions (both arms cached, $ per job)
| model | all | bm25 | jobs done (all / bm25) | no-cache all / bm25 |
|---|---|---|---|---|
| Sonnet 5.5 | 0.0264 | 0.0292 (+11%) | 12/12 · 12/12 | 0.299 / 0.073 |
| Haiku 5.5 | 0.0029 | 0.0023 (−21%) | 11/12 · 12/12 | 0.018 / 0.0048 |
- In long sessions the gap narrows: the conversation itself is cached in both arms, and loaded tools stay loaded.

## Limits
- My catalog (Claude-written, 37.7k tokens, not 55k), my 30 requests, first call only in part 1, fake tool results in part 2.
- Opus sessions not run (budget). Claude.ai / Claude Code manage caching their own way; this is the API.
- 5-minute cache only; 1-hour cache writes cost 2x.
