# EP011 FACTS (verified 13 Nov 2026, 22:15–22:40 UK)

## Source story
- AlphaSignal, Fri 13 Nov 2026 (13:06 UTC), Signal #3: "NVIDIA releases open-source tool to test and score AI agent skills", 861 stars.
- The tool: **NVIDIA SkillEvaluator**, github.com/NVIDIA/SkillEvaluator (Apache 2.0, support level "Experimental").
  Cloned 13 Nov 2026 22:10 UK, commit 976f91f (2026-11-13 21:54 UTC), pyproject version **0.9.0**.
- Paper: arXiv 2608.20614. NVIDIA Developer blog "Evaluating AI Agent Skill Performance with NVIDIA SkillEvaluator", published **19 Aug 2026**.

## What it does (README + blog)
- Three tiers: Tier 1 Validation ("Is the skill safe and well-formed?"), Tier 2 Deduplication ("Does guidance repeat or overlap?"),
  Tier 3 Live Evaluation ("Does the skill help the agent?").
- Keyless command: `skillevaluator quality-check <skill>` gives a deterministic quality score out of 100 with a letter grade; passing threshold defaults to **70**.
  README example `text-analyzer` scores 84.5/100 (B): reproduced exactly on the Mac.
- The quality score's findings are tagged with dimensions correctness, discoverability, reliability, efficiency (deductions of 5–20 points each).
- README: "This checks static quality ... agent impact needs live evaluation." Tier 3 needs provider access, a supported agent and a Docker sandbox (Harbor).
- **Skill Lift** = with-skill score minus without-skill score, in points (blog).
- Blog numbers (NVIDIA's, not ours): 300+ verified skills across 30+ NVIDIA products; Skill Lift all dimensions **+34 Claude Code, +29 Codex**
  (+42 / +36 excluding Security); per-product lift ranges about +2 to +46; 85% of skills ran **one attempt** per task, 15% two;
  "this post does not report confidence intervals".
- Blog: "a skill that loads when it is not relevant can reduce agent performance."

## Our measurements (see lab/ and DATA.md)
- quality-check on all 19 skills in github.com/anthropics/skills (commit 2c5958e, 6 Nov 2026), 13 Nov 2026.
- Six variants of one changelog skill scored with quality-check, then Skill Lift measured on the Anthropic API (Haiku 5.5, Sonnet 5.5),
  Claude-Code-style progressive disclosure (name + description listed, `load_skill` tool returns SKILL.md), 6 tasks x 3 reps per condition.
- We did NOT run NVIDIA's Tier 3 (Harbor/Docker); our lift test is our own, smaller harness on the same with-vs-without idea.

## Competition (YouTube, published after 6 Nov, searched 13 Nov 22:12 UK)
- Nubenetes: 1 long walkthrough + 4 Shorts (all explainer, 13 Nov 17:49 UTC). Trollefsen Labs "Skill Issue" (uses it in a product).
- Nobody tested whether the score predicts whether a skill helps.
