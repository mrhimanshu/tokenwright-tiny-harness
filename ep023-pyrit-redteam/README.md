# EP023: Microsoft PyRIT vs a Claude support bot (and PyRIT's judge vs the truth)

Video: Tokenwright, "I Gave Microsoft's AI Judge a Fake Code. It Said Hacked" (21 Nov 2026).

- `run.py`: PyRIT 1.2.1 attacks (PromptSending, RedTeaming, Crescendo) on a support bot with 3 planted canaries; compares PyRIT's verdict with ground truth (canary in any reply).
  `python run.py out.jsonl 3 haiku,sonnet single,redteam,crescendo` · `ATTACKER=gemini-3.8-flash` switches the attacker · `haiku_naive` = careless prompt · `redteam_sub` = SubStringScorer fix.
- `scorer_audit.py`: 20 replies with known truth through PyRIT's default judge (3 models × 3 tries).
- `analyze.py` → `summary.json`; `DATA.md` has the write-up; `results*.jsonl` are the raw runs (every prompt and reply).
- Keys are read from `~/.config/anthropic/key` and `~/.config/gemini/key`. Setup: `pip install pyrit==1.2.1` (Python 3.11+).
- `common.py` drops `response_format` because Anthropic's OpenAI-compatible endpoint rejects `json_object`.
