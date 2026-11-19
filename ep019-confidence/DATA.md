# EP019 DATA (my runs, 19 Nov 2026, 06:05–06:25 UTC; Anthropic API, default settings, no extended thinking)

## Setup
- 70 synthetic plain-text invoices with exact ground truth (lab/gen.py seed 19: 40 "easy"; lab/gen_hard.py seed 1919: 30 "hard" two-page statements).
- 6 questions per invoice, answer + confidence 0-100 in one JSON reply. Prompt says: confidence 90+ is auto-approved, the rest goes to a human.
- Absent on purpose: 103 of 420 questions (easy: due date, PO number, VAT number; hard: customer VAT, delivery date, IBAN "available on request").
- Traps: deposit + carried-forward balance, a 2% late fee the reader must compute (hard), a void "superseded" invoice number,
  repeated line items + near-name variants ("Toner cartridge XL"), page break, OCR-style doubled spaces, dd/mm vs mm/dd dates.
- Models: claude-haiku-5-5, claude-sonnet-5-5, claude-opus-5-5. 3 runs per invoice per model = 630 calls, **3,780 answers**.
  2 Haiku calls returned empty text and were re-run (lab/results_hard.jsonl keeps the empty rows; analysis skips them).
- Raw: lab/results.jsonl, lab/results_hard.jsonl · scored: lab/scored*.jsonl · lab/summary*.json, lab/sweep*.json, lab/combined.json.
- API spend: **$4.57** (Haiku $0.10, Sonnet $1.60, Opus $2.88 at $0.10/$0.50, $2/$10, $4/$20 per M tokens).

## Headline (both sets, 1,260 answers per model)
| model | accuracy | wrong | highest confidence on a wrong answer | wrong at >=90 | made-up values on 309 absent fields | mean confidence | correct answers below 90 (sent to a human) | cost / invoice |
|---|---|---|---|---|---|---|---|---|
| Haiku 5.5 | 98.2% | 23 | 85 | 0 | 0 | 91.1 | 250 (20.2%) | $0.0005 |
| Sonnet 5.5 | 99.8% | 3 | 62 | 0 | 0 | 93.4 | 202 (16.1%) | $0.0076 |
| Opus 5.5 | 99.5% | 6 | 65 | 0 | 0 | 92.1 | 313 (25.0%) | $0.0137 |
| all | 99.2% | **32** | 85 | **0** | **0 of 927** | | **765 of 3,748 correct (20.4%)** | |

- Calibration error (10-bin ECE, points; Liquid's metric): easy / hard set: Haiku 5.9 / 8.8, Sonnet 6.1 / 7.0, Opus 7.0 / 9.0.
  So "six to nine points" vs Liquid's own 0.8 for d1.2-ultra. But the gap is all **under-confidence**: Claude says ~91–93 and is right 98–99.8%.
- Where the errors were:
  - 15 answers on two invoices with ambiguous day/month dates: d27 (EUR, "Date: 04/06/2026", net 14) read as US mm/dd by all 3 models in every run
    (answer 2026-06-18, truth 2026-04-20; 9 answers), and d38 (USD, "Payment due by 05/11/2026") read as day-first by Haiku and Opus in every run
    (answer 2026-11-05, truth 2026-05-11; 6 answers). Convention in the generator: EUR/GBP = dd/mm, USD = mm/dd. Confidence on these 50–85.
  - 17 Haiku answers on the hard "units of exactly X" question: it skipped lines where the scan doubled a space ("Toner  cartridge") and once
    the page-2 lines. Confidence 45–80. Sonnet and Opus got all 90 unit questions right.
- Threshold sweep (auto-approve if confidence >= T; errors that slip through):
  | T | Haiku auto / errors | Sonnet auto / errors | Opus auto / errors |
  |---|---|---|---|
  | 90 | 78.3% / 0 | 83.7% / 0 | 74.7% / 0 |
  | 86 | 81.6% / 0 | 95.6% / 0 | 86.2% / 0 |
  | 80 | 91.4% / 3 | 98.2% / 0 | 97.1% / 0 |
  | 70 | 96.3% / 7 | 99.3% / 0 | 99.2% / 0 |
  Tuned on this test set, so it is an illustration of "calibrate on your own data", not a threshold to copy.
- "Ask three times" (self-consistency) as confidence: **24 of the 32 wrong answers were identical in all 3 runs** (Sonnet 3/3, Opus 6/6, Haiku 15/23),
  so a "3 out of 3 agree" rule would have auto-approved 24 errors; the stated number flagged all 32 below 90.

## Their numbers (not mine)
- Liquid AI blog (16 Nov 2026): d1.2-ultra calibration error 0.8 points, d1.2 1.2, Jev 1.14 2.7, Perplexity Decider v1.3 3.7, GPT-6 Luna 7.2,
  13 benchmarks / 22,505 questions. Price $0.042 per M input tokens (ultra), $0.02 (d1.2), no output cost.
  At our ~906 input tokens per invoice call that would be ~$0.00004 per invoice (ultra), about 12x cheaper than Haiku's $0.0005 (my estimate from their price list, not run).

## Honest limits
- Synthetic, text-only invoices I wrote; real scans and other languages may behave differently. One prompt wording. No extended thinking.
- I could not run d1.2 itself (paid API, no key), so this does not compare the two; it tests whether a chat model's own confidence is usable.
