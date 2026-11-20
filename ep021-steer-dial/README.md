# EP021 — Does MIT's Spaceship IDE steering knob actually steer?

Video: Tokenwright EP021 ("MIT's AI Steering Knob Has 15 Settings. Claude Hears 3").

Spaceship IDE (github.com/chuanqisun/spaceship) compiles each knob into 5 grade phrases × 3 strength words in the system prompt.
This folder runs all 15 settings with Spaceship's exact prompt (`spaceship_system_prompt.txt`) on Claude Haiku 5.5 and Gemini 3.8 Flash,
blind-judges tension with Claude Sonnet 5.5, and compares REAL activation steering on Qwen2.5-1.5B-Instruct (CPU).

- `gen_prompt.py` → `prompt_results.jsonl` (288 stories)
- `steer.py <qwen dir>` → `steer_results.jsonl` (vector gains −0.7…+1.4, plus prompt knob on the same model)
- `judge.py *.jsonl` → `judged.jsonl` (each passage judged twice)
- `summarize.py` → `summary.json`; results in `DATA.md`, sources in `FACTS.md`

Keys are read from `~/.config/anthropic/key` and `~/.config/gemini/key`. Needs `anthropic google-genai torch transformers`.
