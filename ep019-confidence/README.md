# EP019: Claude says it's 90% sure. I checked 3,780 answers.

Tokenwright episode 19 (19 Nov 2026). Can you route on a chat model's own confidence? Claude Haiku / Sonnet / Opus 5.5 read 6 fields
off 70 synthetic invoices (40 easy, 30 hard two-page statements with traps), each answer with a 0-100 confidence, 3 runs per model.

- `gen.py`, `gen_hard.py`: deterministic invoice generators (seeds 19 / 1919) with exact ground truth -> `docs*.jsonl`
- `run.py [repeats] [_hard]`: calls the Anthropic API (key in ~/.config/anthropic/key) -> `results*.jsonl` (raw replies)
- `analyze.py [_hard]` (+ `SWEEP=1`): scoring, calibration error, auto-approve analysis -> `summary*.json`, `sweep*.json`
- `combine.py`: headline numbers across both sets -> `combined.json`
- `DATA.md`: the write-up with every number used in the video

Headline: 0 of 927 absent fields made up; 32 wrong answers, none at confidence >= 90 (max 85); calibration error 6-9 points, all
under-confidence (said ~92, right 99.2%); 24 of the 32 errors were identical in all 3 runs. Total API spend $4.57.
Context: Liquid AI d1.2 decision models (liquid.ai/blog/d1-2) claim a 0.8-point calibration error on their own benchmarks; not run here.
