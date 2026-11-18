# EP017: UnvibeCode, fake keys and planted bugs (Tokenwright, 18 Nov 2026)

Video: "This Tool Says It Hides Your API Keys. It Uploaded 7 of 9" (youtube.com/@Tokenwright)

What is here
- `make_repo.py` writes the test repo `shopfast/` (subscription billing, 14 .py, ~400 lines) with 8 planted business-logic bugs and 9 FAKE credentials
  (random, generated at run time; they are deliberately NOT in this repo, so secret scanners stay quiet). Answer key: `ANSWER_KEY.md`.
- `leak_test.py` runs UnvibeCode 0.4.0's own `unvibecode.archive.pack()` (the exact zip its client uploads) and checks which fake keys are inside -> `leak_results.jsonl`.
- `run_unvibe.sh` runs the real hosted review 3 times; `parse_unvibe.py` -> `unvibe_results.jsonl`.
- `claude_review.py` pastes the same 18 files into Claude Haiku / Sonnet / Opus 5.5 (3 runs each) -> `claude_reviews.jsonl`.
- `score.py` grades every review against the answer key (Opus 5.5 judge, majority of 3) -> `scores.jsonl`.
- `DATA.md` = the numbers in the video.

Headline: 7 of 9 fake keys in the upload (no redaction step in the 0.4.0 client); UnvibeCode 0/8 bugs in 3 runs; Claude 8/8 in 9 of 9 runs.
Caveats: one small synthetic repo; planted bugs are easier than real ones; their server is not visible to me. Never test any tool with real keys.
