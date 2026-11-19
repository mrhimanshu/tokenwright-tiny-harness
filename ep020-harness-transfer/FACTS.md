# EP020 FACTS (verified 19 Nov 2026, night run)

## Story
- AlphaSignal, Thu 19 Nov 2026 (14:06 UK), Signal #4: "Google's self-improving agent logs its own changes to score 84.75 on workplace tasks" (1,316 likes).
- Primary source: arXiv 2611.18856, "Self-Improvement Memory Enables Continual Recursive Self-Improvement", Xin Yu, Fei Xia, Jiaqi Pan, Youbao Tang, Chengzhi Liu, Adams Yu, Sicong Jiang, Yanfei Chen, Lingzhou Xue, Ting Yu (Google Cloud AI / Google DeepMind / Google Cloud AI Research / Penn State). v1 submitted 13 Nov 2026. https://arxiv.org/abs/2611.18856 . No code link.

## What the paper says (their numbers)
- Harness = the code/prompt/tools around a fixed model. RSI (recursive self-improvement) = an optimizer agent proposes harness edits, keeps the ones that score better.
- Problem: when the benchmark or the MODEL changes, you either restart from scratch or carry over the evolved harness, which "does not record why earlier edits were made or how they performed".
- Key example (workspace domain): an Opus-evolved harness starts at **68.41 on Gemini, below the untouched seed harness's 73.89**. Source policy Claude Opus 5.5, target policy Gemini 3.8 Flash (Table 6).
- SIM = a structured record for the OPTIMIZER (not the task model): edits grouped by recurring harness problem, with rationale, predicted and observed outcome, evaluation context.
- Workspace: both start 68.41; **Full SIM reaches 84.75, Harness Transfer 73.42** (Problem-only memory 79.22; seed-start target RSI 82.98). The AlphaSignal "84.75" is this number.
- Full SIM finishes highest in all four domains (coding TB2.1→TB4, text classification, workspace, engineering), +3.60 to +11.33 over harness-only continuation (cross-model).
- Ten independent coding source runs: SIM improves 9 of 10 continuations, mean +2.36 points over harness-only (p = 0.003).
- Budget: N = 10 rounds, k = 5 candidate proposals per round, 5 rollouts per task; proposer/selector = Gemini 3.8 Flash. A coding round takes ~4 h.
- Gemini generations table (TB2.1 held-out): 2.5 Flash seed 17.8 / fresh 21.4 / CRSI 22.4 … 4 Argon seed 89.7 / fresh 95.6 / CRSI 94.8.

## Our test (scaled down, our runs)
- Ticket routing with 11 labels and hidden house rules (ground truth from code). Seed harness = label names only.
- Source: Claude Haiku 5.5 (effort low), 4 rounds × 2 candidates; proposer Claude Sonnet 5.5 (effort medium); greedy keep-if-better on the evolve set; held-out set never seen by the optimizer.
- Transfer: seed vs Haiku-evolved harness on Gemini 3.8 Flash (the paper's target model) and on Gemini 4 Neon (released 18 Nov 2026), thinking low.
- Target: Gemini 3.8 Flash, 3 rounds × 2 candidates, two arms from the same start: harness-only vs SIM memory. 3 independent runs.
- Differences from the paper: prompt-only harness (no tools/code), tiny sets, greedy selector, 1 rollout per task, 4+3 rounds not 10.

## Related news same email
- Gemini 4 Neon (Google DeepMind, 18 Nov 2026): $3 / $15 per M tokens, thinking levels low/medium/high/xhigh, model id gemini-4-neon (AlphaSignal 19 Nov, 7,150 likes). Covered by 15+ YouTube videos in 24 h (rejected as main topic).
