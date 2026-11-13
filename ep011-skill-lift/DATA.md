# EP011 DATA (13 Nov 2026, M4 Pro + Anthropic API). Raw: lab/results.jsonl (324 runs), lab/summary.json, lab/quality*/

## 1. NVIDIA SkillEvaluator quality-check (v0.9.0, keyless, deterministic) on the 19 official Anthropic skills
(github.com/anthropics/skills @ 2c5958e). Pass mark 70.
| skill | score | grade |
|---|---|---|
| slack-gif-creator 88.5 B · academy-guide 88.0 B · frontend-design 86.8 B · algorithmic-art 86.0 B · brand-guidelines 84.2 B · doc-coauthoring 84.2 B |
| theme-factory 81.8 B · mcp-builder 81.5 B · webapp-testing 81.5 B · claude-api 79.8 C · discernment-nudge 79.8 C · canvas-design 79.2 C |
| internal-comms 79.2 C · web-artifacts-builder 79.0 C · pptx 77.8 C · skill-creator 77.2 C · docx 74.0 C · pdf 74.0 C · xlsx 71.5 C (lowest) |
- 0 of 19 get an A; 10 of 19 get a C. All 19 pass (≥ 70). Typical deductions: missing `version` / `metadata.tags`, no troubleshooting section,
  description in first/second person (xlsx −15), no "Do NOT use for" line. These are form checks; they don't measure whether the skill works.

## 2. One skill, seven versions (changelog-writer; team convention = 8 rules)
| variant | what it is | words | quality score |
|---|---|---|---|
| A_plain | correct rules + 1 example, no extras | 245 | 87.2 B |
| P_polished | A + version, tags, "Do NOT use", prerequisites, workflow, troubleshooting | 457 | 97.5 A |
| C_outdated | P's polish, but last year's rules (old header, hashes, keep chores, security under bug fixes) | 400 | 97.5 A |
| D_sloppy | correct rules as 8 terse lines, first-person description, no example | 75 | 74.0 C |
| B_bloated | P + ~1,600 words of background, FAQ and a pasted style guide (twice) | 2,039 | 97.5 A |
| E_vague | A with description "Misc team helpers." | 223 | 79.8 C |
| F_hidden | E, and the name changed to team-helpers | 223 | 79.8 C |

## 3. Skill Lift (our harness): score = % of the 8 rules met, 6 release tasks x 3 repeats = 18 runs per cell
Claude-Code-style progressive disclosure: the system prompt lists each skill's name + description; the model must call `load_skill`.
"small" = changelog skill + 2 real distractors (pdf, xlsx). "crowd" = changelog skill + all 19 official Anthropic skills (pdf and xlsx included) = 20 skills.

| Haiku 5.5, small | score | lift | perfect | loaded | input tokens |
|---|---|---|---|---|---|
| no skill | 48.6 | 0 | 0/18 | — | 1,216 |
| A_plain (87 B) | 97.9 | +49.3 | 15/18 | 18/18 | 3,257 |
| P_polished (97.5 A) | 97.9 | +49.3 | 15/18 | 18/18 | 3,702 |
| C_outdated (97.5 A) | **0.0** | **−48.6** | 0/18 | 18/18 | 3,582 |
| D_sloppy (74 C) | 98.6 | +50.0 | 16/18 | 18/18 | 2,774 |
| B_bloated (97.5 A) | 100.0 | +51.4 | 18/18 | 18/18 | **6,521** (2.0x A) |
| E_vague (79.8 C) | 99.3 | +50.7 | 17/18 | 18/18 | 3,156 |
| F_hidden (79.8 C) | 93.1 | +44.5 | 15/18 | 16/18 | 2,993 |

| Sonnet 5.5, small | score | lift | loaded |
|---|---|---|---|
| no skill | 56.2 | 0 | — |
| P_polished | 99.3 | +43.1 | 18/18 |
| C_outdated | **0.0** | **−56.2** | 18/18 |
| B_bloated | 98.6 | +42.4 (6,970 input tok) | 18/18 |
| E_vague | 100.0 | +43.8 | 18/18 |

| Haiku 5.5, crowd (20 skills listed) | score | lift | loaded | score when not loaded |
|---|---|---|---|---|
| no skill | 52.1 | 0 | — | |
| A_plain | 98.6 | +46.5 | 18/18 | |
| P_polished | 99.3 | +47.2 | 18/18 | |
| E_vague (name still changelog-writer) | 97.9 | +45.8 | 18/18 | |
| F_hidden (team-helpers + vague) | 90.3 | +38.2 | **14/18** | 56.2 (4 runs) |

## Takeaways
- The outdated skill got the top grade (97.5 A) and turned a 49% baseline into **0%** on Haiku and 56% into 0% on Sonnet: 36 of 36 runs followed it
  exactly (old header, commit hashes, chores listed, security under "Bug fixes"). Claude trusts a loaded skill completely.
- Grade C (74, sloppy, 75 words) = same lift as grade A (+50.0 vs +49.3). Polishing A (87 → 97.5) added 0.0 points.
- Bloat: same score, 2.0x input tokens per run (Haiku 3,257 → 6,521), and quality-check didn't flag it (97.5 A).
- Description mattered only when the name gave no clue: "changelog-writer" + "Misc team helpers." was loaded 18/18 even among 20 skills;
  "team-helpers" was missed in 4/18 crowded runs (2/18 small); those runs scored like no skill.
- Correlation of quality score with lift across the 7 variants (Haiku small): r = −0.42 (with C), +0.31 (without C). n = 7, so no real signal either way.
- Repeats: per-repeat means within ±2 points for every skill cell except F (77–100), baseline 46–60.
- Cost: Haiku 234 runs $0.20 ($0.10/$0.50 per MTok); Sonnet 90 runs 335k in / 34k out tokens. Wall time per run 3.7–5.5 s.
- NOT done: NVIDIA's own Tier 3 (Harbor + Docker + Claude Code). Our lift harness is ours: one skill, 6 tasks, 8 rule checks, 2 models.
  NVIDIA's own numbers (+34 points on Claude Code, 300+ skills, mostly one attempt) are theirs.
