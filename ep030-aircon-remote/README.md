# EP030: can Claude crack an air-con remote from raw IR captures? (Tokenwright)

AlphaSignal (24 Nov 2026) ran a story about a hobbyist who had Claude reverse-engineer an old Panasonic AC protocol.
This lab tests the idea with Claude Opus 5.5, Sonnet 5.5 and Haiku 5.5 on simulated infrared captures.

- `protocols.py`: ground-truth simulator. `panasonic` = the real PANASONIC_AC 216-bit protocol (layout from IRremoteESP8266),
  `brandx` = an invented 14-byte protocol made up for this test (exists nowhere online). Raw mark/space µs with ±7% jitter,
  plus a generic pulse-distance decoder used for scoring. `python protocols.py` self-tests it.
- `run_lab.py`: 12 labelled captures → the model writes `encode(settings) -> list[int]`. Up to 3 rounds with training-only feedback,
  scored bit-exact on 60 held-out settings. 3 models × 3 arms (Panasonic named / brand hidden / Brand X) × 3 reps. Needs ANTHROPIC_API_KEY.
- `analyse.py` → `summary.json`; `results.jsonl` has every round, including each model's full code.
- `DATA.md`: results and caveats.

Headline: Opus cracked 9/9, including Brand X 3/3 on the first reply (~$0.60, under 4 min each). Sonnet 0/3 on Brand X;
one run passed all 12 training captures and then got 33/60 new settings wrong (a hand-fitted checksum). Haiku 0/3 on Brand X
(it put the captured checksums in a lookup table). Total spend $10.39.
Video: https://www.youtube.com/@Tokenwright
