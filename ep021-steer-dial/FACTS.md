# EP021 FACTS — Spaceship IDE ("steer LLM output as you write")

Checked 20 Nov 2026 (morning run).

## The story
- AlphaSignal 19 Nov 2026, Signal #6: "MIT researcher builds a real-time tool to steer LLM output as you write" (2,335 likes).
  AlphaSignal news page: https://alphasignal.ai/news/mit-s-spaceship-ide-lets-developers-steer-ai-text-like-a-live-control-surface
- Project: **Spaceship IDE** by **Chuanqi Sun (MIT Media Lab)**, https://github.com/chuanqisun/spaceship (MIT licence,
  ~956 stars, 100 forks when checked 20 Nov). Demo: https://chuanqisun.github.io/spaceship/. CITATION.cff date-released 2026-11-16.
  Author's demo Short: youtube.com/shorts/3WmNLWUmcnY (16 Nov).
- README features: focus monitor, attention lock, **"Future Vector Steering: decompose the task into eigenvectors, tune each
  independently, re-compose to influence incoming text"**, realtime re-generation (scrubbing). Conjecture: "LLM and Decision
  Models will reach 60 FPS interactivity". README says most of it was written with Claude Code.

## What the code actually does (repo cloned 20 Nov, last commit 2026-11-19)
- Live mode calls **Cerebras `gpt-oss-120b`** (src/llm/cerebras.ts), temperature 0.9 for the story.
- A knob's position (0–1) becomes one of **5 phrases** (src/text/dimension.ts `gradeIndexOf` / `valueOf`):
  `<0.2` "very LOW", `<0.4` "somewhat LOW", `≤0.6` "midway between LOW and HIGH", `≤0.8` "somewhat HIGH", else "very HIGH".
- Knob strength (distance) becomes one of **3 words**: `<1/3` slight, `<2/3` moderate, else strong (`strengthLevelOf`).
- These go into a **system prompt** as text ("tension: very strained (strong)") in src/text/live-completion.ts
  (STEERED_SYSTEM_PROMPT). So the "vector steering" in Spaceship is **prompt-compiled**: 5 × 3 = **15 distinct settings**
  per knob, no hidden-state vectors.
- Axis catalog (live-dimension.ts) includes tension: relaxed | strained, fortune: worsens | improves, pace, distance, surprise…
- Story openings: 16 fixed openings in src/story/openings.ts ("The alarm went off, but", …).

## Related (for context)
- Harish Kotra, "steer" (DEV, 17 Nov 2026; github.com/harishkotra/steer): independent re-implementation with REAL
  activation steering on Qwen2.5-3B-Instruct (MLX, layer 19/36, unit vector from contrast prompts, scale = fraction of mean
  activation norm, default 0.10). His sweep: 0.04 / 0.08 change register, 0.16 readable, **0.28 "collapses into meta-text"**.
  His blind test: 1 of 3 rounds "a real gap" on the real model. These are HIS numbers.
- Competition (youtube_search 20 Nov, last 7 days, "Spaceship IDE steer LLM"): 2 videos (LookOnThisGit walkthrough 18 Nov;
  the author's own Short). Nobody measured whether the dial works.

## Our test setup facts
- No Cerebras key here → Spaceship's exact system prompt + user message format run on Claude Haiku 5.5 and Gemini 3.8 Flash.
- Activation steering: Qwen/Qwen2.5-1.5B-Instruct (official repo, model.safetensors sha256 verified vs HF API, 2.9 GB), CPU.
