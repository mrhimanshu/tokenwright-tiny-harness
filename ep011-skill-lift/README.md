# EP011: Does NVIDIA's skill score tell you if a Claude skill helps?

Video: Tokenwright, "NVIDIA Graded My Claude Skill an A. It Scored Zero" (14 Nov 2026).

- `skills/`: 7 versions of one changelog-writer skill (plain, polished, outdated, sloppy, bloated, vague description, vague name).
- `quality/`, `quality_anthropic/`: NVIDIA SkillEvaluator 0.9.0 `quality-check` reports (our 7 + Anthropic's 19 official skills).
- `run.py`: Claude-Code-style progressive disclosure harness (skills listed by name + description, `load_skill` tool). `DISTRACTORS=all` lists all 19 Anthropic skills.
- `grade.py`: deterministic 8-rule grader. `tasks.json`: 6 release tasks.
- `runs/`, `results.jsonl`: all 324 runs (Haiku 5.5, Sonnet 5.5). `analyse.py` → `summary.json`. Summary in `DATA.md`.

Run: `OUT=out.jsonl python run.py claude-haiku-5-5 P_polished 3` (needs an Anthropic API key).
