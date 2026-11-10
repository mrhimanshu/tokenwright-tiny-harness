# EP007: a 570 MB local translator vs Claude

PLaMo 3 Translate (Preferred Networks; 0.8B / 2B / 8B Q4_K_M GGUF via llama.cpp on an M4 Pro) vs Claude Haiku 5.5 and Sonnet 5.5.
English → Hindi, Japanese, Spanish, German, Arabic, Chinese; the same 40 WMT24++ sentences per language (google/wmt24pp, Apache-2.0);
chrF++ (sacrebleu 2.6.0) against the human references. 1,200 translations in total.

| system | avg chrF++ | s / sentence | $ for 240 |
|---|---|---|---|
| PLaMo 0.8B (0.57 GB) | 41.1 | 0.30 | 0 |
| PLaMo 2B | 43.4 | 0.69 | 0 |
| PLaMo 8B | 43.9 | 1.80 | 0 |
| Claude Haiku 5.5 | 43.9 | 1.21 | 0.014 |
| Claude Sonnet 5.5 | 45.1 | 1.78 | 0.265 |

Per-language scores: `DATA.md`. Every source, reference and output: `results.jsonl`.
4 of Haiku's 240 outputs contained its own self-corrections ("Wait, the target language is Japanese…"); 0 of PLaMo's 720 did.
Caveats: one automatic metric, 240 sentences, public test set. PLaMo is under the PLaMo Community License (free non-commercial).

```bash
llama-server -m plamo-3-translate-0.8b-Q4_K_M.gguf -c 8192 --port 8000 --jinja --no-prefill-assistant
python bench.py plamo08 40   # then: python bench.py haiku 40 ; python score.py
```
