# EP037 DATA (lab runs 28 Nov 2026, 06:20–07:10 UTC)

Benchmark: "Speak or Stay Silent" (arXiv 2603.11409 v2, 24 Nov 2026), dataset ishiki-labs/multi-party-dialogue (official test splits).
Metric: balanced accuracy (mean of SPEAK and SILENT recall), random = 50.

## 1. Claude on the paper's exact zero-shot prompt (lab/run.py, results/results.jsonl)
Sample: 240 test items (120 Friends + 120 AMI, seed 37, test category mix kept within each label, 60 SPEAK / 60 SILENT per corpus).
Prompt: Appendix B system prompt + instruction verbatim (lab/src/), transcript with "[MOST RECENT]", last 40 context turns. effort low, max_tokens 4000, 0 missing decisions, all end_turn.

| model | arm | run | Friends | AMI |
|---|---|---|---|---|
| Haiku 5.5 | paper | 1 / 2 / 3 | 59.17 / 60.00 / 58.33 | 51.67 / 52.50 / 51.67 |
| Sonnet 5.5 | paper | 1 | 59.17 | 58.33 |
| Opus 5.5 | paper | 1 | 59.17 | 62.50 |
| Haiku 5.5 | predict | 1 / 2 / 3 | 57.50 / 60.83 / 58.33 | 52.50 / 51.67 / 51.67 |
| Sonnet 5.5 | predict | 1 | 57.50 | 61.67 |
| Opus 5.5 | predict | 1 | 60.83 | 64.17 |
"predict" = "predict whether X is the very next person to speak" (not what's polite).
Haiku on the FULL test sets (results/full_haiku.jsonl): Friends paper 59.60, predict 60.48 (n=1,287). AMI: see summary in analyse_full below.
Weakest category: Friends SILENT_ref (target was in the conversation, label silent): Opus 20.5%, Sonnet 18.2%, Haiku 25–29% correct.
Their numbers for comparison (Table 2): gemini-3.1-pro Friends 60.54 / AMI 61.03 / SPGI 64.45; gpt-5.2 55.41 / 59.21 / 56.94. Humans (Friends, 360 items): 60.31 / 64.81 / 66.13.
Spend: $4.08 on the sample (Opus paper $1.83, Opus predict $0.70, Sonnet $0.95 + $0.34, Haiku ~$0.20) + Haiku full test ~$0.5.

## 2. One-line rules, full official test sets (lab/baselines.py)
- "SPEAK if the target's name is in the most recent line": Friends **65.99**, AMI 49.52, SPGI 50.00 (AMI speakers are letters A–D, SPGI numbers, so it can't fire there).
- "SPEAK if the target spoke the turn before": AMI 55.51.

## 3. Train/test overlap (lab/leak.py → leak.json)
- Friends: 1,242 of 1,287 test items come from a conversation clip (sequence_id) that also has items in train. 368 (28.6%) are word-for-word identical to a train item (same context, same line, same target): 347 with the same label, **21 with the opposite label**.
- AMI: 1,321 of 1,410 test items share a clip with train; 583 share the exact moment (other target); 1 identical with the same target.
- Test sequence ids: Friends 1,147 of 1,287 test items carry "train_…" sequence ids.

## 4. No-AI script (lab/no_ai.py, 18 non-blank lines; lab/cheat.py variants)
- Friends: copy the train label if this exact moment is in train, else the name rule → **74.32**. (Matching only the last 3 / last 1 context turns: 75.34 / 77.32.)
- Their best fine-tuned models on Friends (Table 3): Llama 3.1 8B 72.52, Mistral 7B 71.50, Qwen3-8B 69.29. Combined training avg (all corpora) 71.73.
- AMI: lookup on the last context turn + "spoke before" rule 67.10 (vs fine-tuned 71.5–72.3), exact lookup barely fires (55.51).

## 5. Window-end labels (Friends test)
- Clips are 5 lines (711 items) or 8 lines (576). 67 test items sit on the LAST line of a clip: all 67 labelled SILENT (0 SPEAK), 61 are two-person scenes, 28 end on a question, 11 contain the target's name.
- Example (test_5turns? no: sequence train_5turns_6647, turn 4): Monica: "Oh my God, what are you gonna do?!" → target Joey, label SILENT, clip ends.
- Haiku (full test, paper prompt) said SPEAK on 51 of the 67.

## Caveats
- 240-item sample: ±~4.5 points per corpus cell (one run). Haiku's 3 runs spread 1.7 points.
- I did not re-run SPGI (long earnings-call contexts, ids instead of names).
- I can't show that the paper's fine-tuned models memorised; only that a lookup table beats them on Friends.
- Human scores are on a 360-item Friends subset, not the full test.
