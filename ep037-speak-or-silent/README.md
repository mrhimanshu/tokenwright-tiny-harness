# EP037 · Speak or Stay Silent: Claude vs 18 lines of Python

Video: Tokenwright, "Gemini and Claude Lost This AI Test to 18 Lines of Code" (28 Nov 2026).
Benchmark: "Speak or Stay Silent" (arXiv 2603.11409), dataset `ishiki-labs/multi-party-dialogue` (Apache 2.0).

Get the data (not included here):
```
python -c "from huggingface_hub import snapshot_download; snapshot_download('ishiki-labs/multi-party-dialogue', repo_type='dataset', local_dir='data', allow_patterns=['friends/*/*_samples.jsonl','ami/*/*_samples.jsonl','*/stage4_filtered_samples.jsonl','*/test/*'])"
```
- `no_ai.py`: the 18-line script (Friends test, balanced accuracy 74.32)
- `baselines.py`: one-line rules on all three test sets
- `leak.py`: train/test overlap and label conflicts
- `sample.py` + `run.py` + `analyse.py`: Claude Haiku/Sonnet/Opus 5.5 with the paper's prompt (`src/`), 240 stratified test items; `results/` has every answer
- `DATA.md`: all numbers and caveats
