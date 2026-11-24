# EP030 DATA: can Claude crack an air-con remote from raw IR captures? (my runs, 24–25 Nov 2026)

## Setup
- Simulator (lab/protocols.py, my code, ground truth never from a model):
  - **panasonic** = the real PANASONIC_AC protocol (IRremoteESP8266 layout): 2 sections (8 + 19 bytes), LSB first,
    3456/1728 µs header, 432 µs mark, 432/1296 µs spaces. Checksum = 0xF4 + sum. Quirk: fan-only mode always sends 27 °C.
  - **brandx** = an invented protocol made up for this test, so it exists nowhere online: 14 bytes, MSB first, 6000/2400 header,
    byte 9 = NOT byte 4, checksum = (XOR of bytes 0–12) + 0x37. Quirk: dry mode always sends fan = auto.
- Each run gets **12 captures**: the settings shown on the display + raw mark/space µs with ±7% jitter. They cover every mode,
  fan speed and vane position, and include both quirks. 439 values per Panasonic capture, 227 per Brand X capture.
- Task: write `encode(settings) -> list[int]` (raw timings). Scored **bit-exact on 60 held-out settings** it never saw
  (a generic pulse-distance decoder compares the bits; header within 25%).
- Up to 3 rounds: after each answer I run the code on the 12 training captures and report which ones mismatch (training data only).
- Arms: Panasonic named ("Panasonic CS-NE9PKE") · Panasonic blind ("brand unknown") · Brand X. Models: Opus 5.5, Sonnet 5.5,
  Haiku 5.5, all at effort high, max 48,000 output tokens per reply. n = 3 per cell (different capture sets per rep).
- 27 runs, 50 API calls, **$10.39** total (Sonnet on Brand X alone was $4.51, because it hit the 48k token cap round after round).

## Results (cracked = 60/60 held-out settings exactly right)
| model | Panasonic named | Panasonic blind | Brand X (invented) |
|---|---|---|---|
| Opus 5.5 | 3/3 (all first try) | 3/3 (2 first try; 1 missed the fan-mode 27 °C quirk, fixed after feedback) | **3/3, all first try** |
| Sonnet 5.5 | 3/3 (first try) | 3/3 (first try) | **0/3** |
| Haiku 5.5 | 2/3 (0 first try) | 2/3 (0 first try) | **0/3** |

- Opus on Brand X: 60/60 in all 3 reps, first reply, avg $0.60 and 3.7 min per run (~27k output tokens). It found the byte
  map, the NOT byte, the dry-mode quirk and the XOR + 0x37 checksum. Its own note: "an empirical fit".
- Panasonic: Opus and Sonnet both cost about $0.25–0.35 and 1.3–3.4 min. In the blind arm, Opus said "Panasonic-style" in 3/3 runs
  (it recognises the protocol), Sonnet in 2/3.
- **Sonnet on Brand X, rep 2: passed all 12 training captures, then got 33 of 60 new settings wrong (27/60).** Every miss was byte 13,
  the checksum: it fitted a hand-made formula (`0x5D + 4 + G[fan] + mode − vane`) that matches the 12 captures and nothing else.
  Reps 0 and 1 never produced code (48k token cap ×3; rep 1 was then stopped twice by the API safety filter, stop_reason "refusal").
- **Haiku on Brand X**: every field right except the checksum. Rep 0 hard-coded a lookup table of the captured checksums and wrote
  "B13 (checksum) is NOT derived. Only observed combinations are supported" → 10/12 training, 0/60 new. Rep 1: 8-entry table + a
  placeholder → 0/60. Rep 2: token cap, then 2 safety-filter refusals.
- Haiku on Panasonic: first reply always hit the 48k cap; with the "no code" nudge it cracked 4 of 6 runs, at about $0.06 per run.
- Where the cheaper models produced code for Brand X, the checksum was the wall: Sonnet rep 2's 33 misses are all byte 13 only;
  Haiku rep 1's 60 misses are byte 13 (48) or bytes 7 + 13 (12); Haiku rep 0 raised "checksum not derived" on all 60.

## Caveats (say on screen)
- Captures come from my simulator (real Panasonic layout, my own jitter), not a real receiver: no glitches, no repeats, no noise bursts.
- The 12 captures were chosen to cover every value. With a random 12 some values could be missing.
- 48k output-token cap per reply: Sonnet/Haiku might get further with more budget. Same cap for every model.
- 4 replies (2 Sonnet, 2 Haiku) ended with stop_reason "refusal"; I counted them as fails.
- I couldn't find the original hobbyist post, so this isn't a replication of their setup.
