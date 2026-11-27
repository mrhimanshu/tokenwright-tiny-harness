# EP034: NVIDIA Nemotron Parse 2.0 + Nemotron 3.5 Parse on a CPU with no GPU, vs Claude (Tokenwright, 26 Nov 2026)

AlphaSignal's top model on 26 Nov 2026 was Nemotron Parse 2.0 (page image → text, tables, chart data, boxes; "44% → 91%", "under 2 GB").
Its card points to a newer model, Nemotron 3.5 Parse. I ran both on a 4-vCPU cloud VM (no GPU) next to Claude Haiku/Sonnet/Opus 5.5
on 27 pages with known answers.

- `gen_pages.py` / `gen_hard.py` / `gen_ctrl.py`: build the test pages (`pages/`) and answers (`truth.json`). Handwriting lines come from
  Teklia/IAM-line (test split, MIT); download `data/test.parquet` from that dataset and NotoSansDevanagari-Regular.ttf into `data/` first.
- `run_nemotron.py <parse20|parse35> out.jsonl pages...`: Transformers on CPU (`DTYPE=bfloat16`, 4 threads), card settings. Models from
  huggingface.co/nvidia/NVIDIA-Nemotron-Parse-2.0 and huggingface.co/nvidia/Nemotron-3.5-Parse into `models/parse20`, `models/parse35`
  (sha256 in `sha256.txt`). Needs torch, transformers==5.6.1, timm==1.0.22, open_clip_torch==3.2.0, einops, accelerate, psutil.
- `run_claude.py <model> out.jsonl pages...`: same image + one transcription prompt, effort low (needs an Anthropic key).
- `score.py` → `scores.jsonl` + `summary.json`; `report.py` → `report.txt`. Write-up: `DATA.md`.

Headline: English scans and tables near-perfect for both NVIDIA models (2.0: 0/288 wrong cells; 3.5: 1/288), but 70 s (3.5) and 170 s (2.0)
per page on 4 CPU cores vs 1.5 s and $0.0004 for Claude Haiku. Charts: Claude exact 114/114; 3.5 8/38 off by 1–2; 2.0 25/38, up to 7 off.
Handwriting CER: 2.0 9.1%, 3.5 2.4%, Haiku 1.0%, Opus 0.1%. Hindi: 2.0 1.1%, but 3.5 wrote legacy-font style mojibake on 6 of 10 pages
(CER 18.6% on the clean ones); Claude 0%.
