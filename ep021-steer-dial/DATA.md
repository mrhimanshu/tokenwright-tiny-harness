# EP021 DATA — does Spaceship IDE's steering knob actually steer? (my runs, 20 Nov 2026)

Raw: lab/prompt_results.jsonl (288 generations), lab/steer_results.jsonl (114 Qwen generations), lab/judged.jsonl (402 rows,
each judged twice), lab/summary.json. Scripts: lab/gen_prompt.py, lab/steer.py, lab/judge.py, lab/summarize.py.

## Setup
- Axis: Spaceship's own catalog axis **tension: relaxed | strained**. Openings: 3 of Spaceship's 16
  ("The alarm went off, but" · "They told us never to open the door to" · "In the quiet hours just before dawn,").
- Arm A (Spaceship's real mechanism): its exact steered system prompt (lab/spaceship_system_prompt.txt) + "CONTROLS\ntension:
  <grade> (<strength>)" for all **15** settings the knob can send (5 grades × slight/moderate/strong), plus the unsteered prompt.
  Models: Claude Haiku 5.5 (effort low) and Gemini 3.8 Flash (temp 0.9, thinking low) — no Cerebras key for gpt-oss-120b.
  3 openings × 3 repeats = 9 passages per setting per model. 288 passages, generated in 99 s.
- Judge: Claude Sonnet 5.5, blind (sees opening + passage only), tension 0–100 + coherence 0–10, 2 independent calls each.
  The two calls differ by 1.2 points on average (median 0), so judge noise is small next to the effects below.
- Arm B (real activation steering, CPU): Qwen2.5-1.5B-Instruct, layer 15 of 28, unit vector = mean hidden state of 8 tense
  sentences − 8 calm ones; added at every position, scale = gain × mean activation norm (60.7). 14 gains −0.7 … +1.4,
  3 openings × 2 samples = 6 per gain. Same model with the knob phrase in the prompt ("Tension: <grade> (strong).") 5 grades × 6.
  CPU speed 5–12 tokens/s (4 threads).

## Arm A results — mean judged tension (0–100), n = 9 per cell
| Claude Haiku 5.5 | very relaxed | somewhat relaxed | midway | somewhat strained | very strained |
|---|---|---|---|---|---|
| slight   | 16.7 | 26.0 | 62.2 | 70.2 | 79.0 |
| moderate | 19.5 | 18.2 | 63.6 | 76.7 | 76.3 |
| strong   | 16.4 | 21.6 | 62.9 | 79.0 | 84.5 |
| no knob (unsteered) | 73.8 | | | | |

| Gemini 3.8 Flash | very relaxed | somewhat relaxed | midway | somewhat strained | very strained |
|---|---|---|---|---|---|
| slight   | 6.2 | 12.8 | 37.7 | 61.8 | 69.3 |
| moderate | 6.8 | 6.9 | 42.4 | 83.2 | 90.1 |
| strong   | 7.9 | 4.6 | 43.8 | 88.4 | 92.6 |
| no knob (unsteered) | 69.4 | | | | |

- **The knob does steer direction**: Spearman (grade vs tension) 0.81 Haiku, 0.90 Gemini. Coherence stays high (8.8 / 9.0).
- **15 settings, few real levels.** Greedy count of settings separable from the previous level with AUC ≥ 0.9:
  **Haiku 3 of 15, Gemini 6 of 15.**
- **"very" vs "somewhat" barely matters:** Haiku very relaxed 18 vs somewhat relaxed 22; somewhat strained 75 vs very 80.
  Gemini 7 vs 8 and 78 vs 84. Adjacent-grade AUC very↔somewhat relaxed: 0.48–0.69 (0.5 = coin flip).
- **Strength (the knob's distance) does almost nothing on Claude:** very relaxed → very strained range = 62 slight, 57 moderate,
  68 strong. On Gemini it matters: 63 slight vs 83–85 moderate/strong. "Slight" is the only distinct strength on Gemini.
- **No knob ≠ middle:** with no knob the stories are already tense (Haiku 74, Gemini 69); "midway" pulls them DOWN (63 / 43).
  Setting a knob to the middle changes the story.
- **The opening fights back (Haiku):** "very relaxed" on "They told us never to open the door to" still averaged 42; 9 of 54
  relaxed-side Haiku passages scored ≥ 40 (Gemini 0 of 54). Example (strong, very relaxed, judged 36.5): "…nobody had said what to
  do when the knocking came from inside the walls. Dana pressed her back against the cupboard and let the kettle cool…".
- Tokens: Haiku 104k in / 42k out; Gemini 74k in / 37k out (incl. thinking). Spaceship regenerates on every knob move.

## Arm B results — real vector on Qwen2.5-1.5B (n = 6 per gain)
| gain | −0.7 | −0.4 | −0.16 | 0 | +0.16 | +0.28 | +0.4 | +0.6 | +0.8 | +1.0 | +1.4 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tension | 10.9 | 19.7 | 30.0 | 29.8 | 34.2 | 55.3 | 48.7 | 55.4 | 72.3 | 77.5 | 61.8 |
| coherence | 5.9 | 7.2 | 7.3 | 7.2 | 6.4 | 6.2 | 6.0 | 4.8 | 3.5 | 3.1 | 2.2 |
(−0.28: 21.9 / 7.0 · −0.08: 38.6 / 6.8 · +0.08: 32.6 / 6.5)
- Spearman gain vs tension 0.76. It is a true continuous dial — but **±0.16 moves nothing** (30 → 34), and tension above ~70 only
  comes at gain 0.8+ where coherence falls to 3.5 / 3.1 / 2.2 (looping, broken grammar: "Let me go, don't getit").
- The calm side works better: −0.4 to −0.7 gives calm, readable text (tension 20 → 11, coherence 7.2 → 5.9).
- Same model, knob phrase in the prompt: very relaxed 34, somewhat relaxed 28, midway 45, somewhat strained 46, very strained 57
  (Spearman 0.51), coherence 6.5–6.7. On a 1.5B model the prompt knob is weak too.
- Compare: the frontier models with the prompt knob reach 85–93 tension at coherence ~9. To push the small model to 77, the
  vector had to wreck the text (coherence 3.1).
- Harish Kotra's numbers (their numbers, Qwen2.5-3B on MLX): 0.16 readable, 0.28 "collapses into meta-text". Our 1.5B at layer
  15 held up to ~0.4 and fell apart from 0.8.

## Caveats (say on screen)
- Judge is a Claude model; Gemini outputs were also judged by Claude. Judge noise is small (1.2 pts) but bias can't be ruled out.
- gpt-oss-120b on Cerebras (Spaceship's actual model) not tested: no key. Results are for Haiku 5.5 / Gemini 3.8 Flash.
- One axis (tension), 3 openings. Vector arm is a 1.5B model on CPU, not a frontier model.
