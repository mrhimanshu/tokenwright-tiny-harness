# EP034 DATA (lab runs 26–27 Nov 2026, 22:15–00:06 UTC)

Raw: lab/results/*.jsonl (every raw output) · scores: lab/scores.jsonl · summary: lab/summary.json · full table: lab/report.txt · answers: lab/truth.json
Machine: AMD EPYC 9354P, 4 vCPUs (avx512_bf16), no GPU; torch 2.15.0, transformers 5.6.1, bf16, 4 threads, greedy, repetition_penalty 1.1, max_new_tokens 4000.
Claude 5.5 Haiku/Sonnet/Opus: effort low, 1 prompt, 3 runs per page. API spend **$2.05**.

## Test set (27 pages + 4 Hindi controls)
- clean (15): 3 scanned-look reports, 3 ruled invoice tables (10 rows), 3 bar charts (gridlines every 10, no value labels), 3 handwriting pages (7 real IAM test-split lines each), 3 Hindi Wikipedia summaries (Noto Sans Devanagari 31 px)
- hard (12): 2-column photographed reports, borderless photographed tables (14 rows, odd prices), charts with gridlines every 25 and values never on a line, small (23 px) photographed Hindi
- control (4, Nemotron 3.5 only, 2 threads, timing not used): Hindi small-but-clean, Hindi big-but-photographed

## Accuracy
| kind | Parse 2.0 | Nemotron 3.5 Parse | Claude Haiku 5.5 | Claude Sonnet 5.5 | Claude Opus 5.5 |
|---|---|---|---|---|---|
| reports, CER (6 pages) | 0% wrong letters; reading order swapped on 2 of 3 hard 2-column pages (CER 39.8% / 32.1% because of order) | 0% | 0% | 0% | 0% |
| tables, wrong cells | 0 / 288 | 1 / 288 | 0 / 864 | 3 / 864 | 2 / 864 |
| charts, values not exact | 25 / 38 (clean 6/19 off by 1–2; hard 19/19, up to 7.1 off, MAE 2.74) | 8 / 38 (all 1–2 off, all on hard charts) | 0 / 114 | 0 / 114 | 0 / 114 |
| handwriting CER (3 pages) | 9.08% (4.6 / 17.4 / 5.2) | 2.39% | 0.99% | 0.27% | 0.14% |
| Hindi CER, clean (3) | 1.13% | **18.55%** (26.0 / 18.9 / 10.8) | 0% | 0% | 0% |
| Hindi CER, hard (3) | 1.57% | 0.79% | 0% | 0% | 0% |

Example (hand2, Parse 2.0): "said Mr. Copthorne. The verger" → "zacil his. Sophomie. The ceger"; "disappointment awaited him" → "disagreement outraited him".

## The Hindi finding (Nemotron 3.5 Parse)
On clean Hindi pages it outputs legacy-font style text: Latin/IPA code points in place of Devanagari and pre-base vowel signs in visual order,
e.g. "में" → "मŐ", "दक्षिण" → "दिƗण", "स्थित" → "िस्थित", "उपमहाद्वीप" → "उपमहाȪीप" (what copy-paste from old Krutidev-style PDFs looks like).
Same 3 paragraphs on 10 pages: hindi1 clean big 26.0% · clean small 26.0% · photo big 25.1% · photo small 0.3% ; hindi2 clean big 18.9% · clean small 16.3% · photo big 2.6% · photo small 1.7% ; hindi3 clean big 10.8% · photo small 0.3%.
→ **6 of 10 pages broken (CER 10.8–26.0%), 4 clean (0.3–2.6%)**, the clean ones mostly photographed; not predictable from size alone.
NVIDIA's card: IndicVisionBench Hindi CER 9.36% (3.5) vs 16.32% (2.0) — on my pages it is the other way round. The training-data explanation is my guess.

## Speed and memory (clean tier, 15 pages each, sequential, CPU steal median 3.5–4%)
| | median s/page | min–max | 1,000 pages | $ / 1,000 pages |
|---|---|---|---|---|
| Parse 2.0 | 170.4 | 162–193 (hindi1 193 s overlapped my whisper run) | 47.3 h | 0 + server |
| Nemotron 3.5 Parse | 70.5 | 61–82 | 19.6 h | 0 + server |
| Claude Haiku 5.5 | 1.54 | | 26 min | $0.42 |
| Claude Sonnet 5.5 | 2.03 | | 34 min | $8.29 |
| Claude Opus 5.5 | 2.77 | | 46 min | $16.58 |
Time barely depends on output length (3.5: 99 tokens 66 s vs 383 tokens 78 s): the ViT-H vision encoder at 1664×2048 dominates on CPU.
Memory: bf16 weights 1.26 GB (3.5) / 1.8 GB (2.0); process RSS after load+run ~5.0 GB (3.5) and ~6.4 GB (2.0), peak 5.1 / 6.8 GB. fp32 smoke test: 2.0 173 s, 3.5 82 s (bf16 50 s on the 3-line smoke page).
Params counted: 0.903 B (2.0), 0.631 B (3.5).
