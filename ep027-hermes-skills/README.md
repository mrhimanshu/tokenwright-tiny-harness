# EP027 · Hermes Agent skills vs a 6-line note

Video: Tokenwright, "Hermes Agent Taught Its Team 18/18. A 6-Line Note Did Too" (23 Nov 2026).

Claim tested (Nous Research, Hermes Enterprise, 18 Nov 2026): Collective Wisdom turns one employee's successful approach into a
reusable skill, so workflows "use less inference and become more reliable over time".

- `gen_data.py`: messy monthly order exports for a made-up shop (duplicates, refunds, test orders, currencies, decimal commas,
  email case, and one house rule: revenue is ex-VAT). April drifts to semicolons + CHF. Ground truth in `truth/`.
- `run_hermes.py`: runs one real hermes-agent 0.19.0 session on Claude (Anthropic API), built like `hermes -z`, kept alive so the
  seed session takes finance feedback and Hermes's own skill review (`agent.background_review._SKILL_REVIEW_PROMPT`) finishes.
- `batch.py`: teammate arms (no skill / shared skill / written brief) × Feb/Mar/Apr × reps. `analyse.py`: summaries.
- `skills_written_by_hermes/`: the 3 skills Hermes wrote after the January session. `patched_by_agent_april/`: the script skill
  after an agent patched it for April's semicolons.
- `results/results.jsonl`: every run (usage, grade, answer). `DATA.md`: tables and findings.

Needs: `pip install hermes-agent==0.19.0`, `~/.config/anthropic/key`. Whole lab ≈ $3 at list prices.
Not tested: the Hermes Enterprise Teams publish/review UI (the skill folder is copied into each teammate's HERMES_HOME).
