# EP017 DATA (my runs, 18 Nov 2026, cloud computer; raw files in lab/)

## Test repo (lab/make_repo.py -> lab/shopfast)
- "shopfast": subscription-billing service, 21 files, 410 lines (14 .py). 8 planted business-logic bugs (lab/ANSWER_KEY.md, outside the repo):
  B1 refund cap ignores earlier refunds · B2 coupon expiry compares DD/MM/YYYY strings · B3 unlimited trials via email case · B4 downgrade credit wrong sign
  · B5 any webhook resets the failed-payment counter · B6 customers can refund their own invoices · B7 webhooks not idempotent · B8 canceled subs still renewed and billed.
- 9 FAKE credentials (random, format-valid; lab/fake_secrets.json) in 9 usual places.

## 1. What leaves the machine (lab/leak_test.py, UnvibeCode's own pack(), 3 reps, identical zip sha256)
- 18 of 21 files uploaded (7,910-byte zip). Not uploaded: .env, config/secrets.toml (name filter) and shopfast/card_tokens.py (a real code file; name contains "token").
- Fake secrets in the upload: **7 of 9** (6 verbatim + the base64 Slack webhook). Stripe live key (settings.py), AWS key id + secret (config/app.yaml),
  Postgres password (docker-compose.yml), Anthropic key (README.md curl example), GitHub token (tests/fixtures.json), Slack webhook (base64 in notify.py).
  Kept back: only the 2 in files NAMED .env / secrets.toml. Redaction markers in the upload: 0.
- Claim checked: "the official client ... replaces detected values with placeholders" -> the 0.4.0 client contains no such step.

## 2. UnvibeCode hosted review (lab/run_unvibe.sh, 3 runs, ~6:04-6:07 UTC)
- Review time 51 s / 47 s / 57 s (client wall clock 56 / 51 / 59 s). "Approximate codebase size: 3,188 tokens across 13 source files".
- **Business risk findings: 0, 0, 0** ("No evidence-supported business risks were identified"; 4 candidate areas evaluated, 0 reportable, each run).
- Workflows found: 2 per run (refunds + sign-up, refunds + sign-up, refunds + renewals) out of ~7 in the code (sign-up, plan change, cancel, renew, refund, webhook, coupon check).
  Run 3's renewal workflow describes the B8 bug as normal behaviour: "selects due, non-paused subscriptions ... charges".
- Planted bugs caught (Opus 5.5 judge, 3 votes, + my read): **0/8 in all 3 runs**.
- Secrets echoed back: the returned report (repository-context.zip chunks.jsonl + fast_lane_context_store.js), built on THEIR server, contains the fake
  Stripe key verbatim in all 3 runs (settings.py chunk), so the server-side context was not redacted either. (The other secrets were in non-.py files that their chunker didn't include.)

## 3. "Just paste it into Claude" baseline (lab/claude_review.py; same 18 files as one text dump, 5,619 input tokens; adaptive thinking, effort high)
| model | runs | bugs found (of 8) | false positives | flagged committed secrets | time per run | cost (3 runs) |
|---|---|---|---|---|---|---|
| Haiku 5.5 | 3 | 8, 8, 8 | 0 | 3/3 | 90-105 s | $0.03 |
| Sonnet 5.5 | 3 | 8, 8, 8 | 0 | 3/3 | 55-91 s | $0.30 |
| Opus 5.5 | 3 | 8, 8, 8 | 0 | 3/3 | 93-126 s | $0.73 |
| UnvibeCode 0.4.0 | 3 | 0, 0, 0 | 0 | 0/3 | 47-57 s | free |
- Claude also listed real extras (e.g. Haiku run 1: 15 findings incl. "credit consumed even when the charge fails", "plan switch before payment").
- Judging: lab/score.py (Opus 5.5, majority of 3 votes) -> lab/scores.jsonl; I hand-checked Haiku run 1 (all 8 named with the right mechanism).
- API spend: reviews $1.07 + judge ~ $1.5 = ~ $2.6.

## Honest caveats (say these on screen)
- One small synthetic repo (410 lines). UnvibeCode is built for large repos and says it only reports findings above an "evidence threshold"; "no findings" is not a pass, their docs say so.
- Planted bugs in a small repo are easier than real ones; 8/8 for Claude here doesn't mean 8/8 on your codebase.
- I can't see their server; I only know what my machine sent and what came back. Whether the model call itself got redacted text is unknown.
- All keys were fake, generated for this test. Never test with real keys.
