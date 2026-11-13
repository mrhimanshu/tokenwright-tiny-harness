# EP010 DATA: Deletion Tuning vs full fine-tuning on a MacBook (my runs, 12–13 Nov 2026)

Raw: lab/results.jsonl (25 records, one per subject × method, with every test prediction) · summary: lab/summary.json (lab/analyse.py)
Code: lab/dt_lab.py (re-implementation of the official SFT recipe, github.com/agentic-learning-ai-lab/deleting-weights, MIT)

## Setup
- Mac: MacBook Pro, Apple M4 Pro, 24 GB, PyTorch 2.x on MPS, fp32.
- Model: Qwen/Qwen2.5-0.5B-Instruct (494,032,768 weights; model.safetensors sha256 fdf756fa…fb7fe = HF API value, revision 7ae5576).
- Data: TIGER-Lab/MMLU-Pro test split, 5 categories. Per category: seeded shuffle (seed 0), 25% test / 75% train (as the official code).
  Samples longer than 512 tokens dropped (laptop deviation). Train/test sizes: biology 537/180, economics 633/211, health 611/205, philosophy 374/125, psychology 598/200.
- Scoring (as official): each of up to 10 options scored by mean answer-token loss; lowest wins. Chance = 10%.
- Deletion Tuning (official SFT settings): mask over every mlp.gate_proj weight (24 × 4,358,144 = 104,595,456 logits), soft sigmoid(sharpness·G) in training,
  hard G > 0 when evaluated; sharpness 100 → 1000; logits N(0, 0.01²) + Wanda prior ±3 std (init sparsity 1/2048); AdamW lr 5e-4; 400 steps; batch 4;
  regulariser −1e-5·(1 − t/T)·Σ‖W⊙mask‖²; grad clip 1.0.
- Full fine-tuning: all 494M weights, AdamW lr 3e-6, 400 steps, batch 4 (official MMLU-Pro FFT setting); gradient checkpointing on (memory).
- Controls: (a) "starting mask, no training" = the Wanda-initialised mask applied as is; (b) "random deletion" = the same number of gate weights per layer as the
  learned mask deleted, picked at random.
- Drift: mean per-token KL(original ‖ tuned) over 40 held-out MMLU-Pro history answer texts (≤ 256 tokens), full vocabulary.
- n: 5 subjects × 1 seed each = 5 runs per condition (25 runs). No API cost ($0).

## Accuracy on unseen test questions (%)
| subject | original | start mask | random deletion | deletion tuning | full fine-tune |
|---|---|---|---|---|---|
| biology | 14.4 | 13.9 | 12.8 | **20.6** | 23.3 |
| economics | 14.2 | 14.2 | 14.2 | **18.5** | 19.4 |
| health | 11.7 | 11.2 | 12.2 | **37.1** | 39.0 |
| philosophy | 9.6 | 9.6 | 8.0 | **13.6** | 12.8 |
| psychology | 15.0 | 15.0 | 15.0 | **14.0** | 17.0 |
| **mean** | **13.0** | 12.8 | 12.4 | **20.7** | **22.3** |

- Deletion tuning recovered 83% of full fine-tuning's mean gain ((20.74 − 12.99) / (22.32 − 12.99)). Per subject: biology 69%, economics 82%, health 93%,
  philosophy 125% (beat FFT), psychology −50% (no gain: 15.0 → 14.0, inside noise; FFT +2.0).
- Health: 11.7% → 37.1% (deletion) vs 39.0% (FFT): about 3.2× the original.
- Controls: random deletion of the same number of weights 12.4% mean (below the original 13.0%); starting mask 12.8%. Learning which weights matters.
- Noise: ~125–211 test questions per subject, so ±2.3–2.9 points (1 SE) per number; single seed per subject.

## What was deleted / shipped
- Learned masks deleted 1,040,144–1,146,799 gate weights (mean 1,081,742) = 0.99–1.10% of the gate weights = 0.21–0.23% of the whole model.
  The paper reports < 0.05% of the model (0.035–0.046% at Llama scale): on this 0.5B model it deleted about 4–5× more.
  (The starting mask already deletes ~191,500 = 0.04%: Wanda 1/2048 plus logits that start negative from the N(0, 0.01²) init.)
- Mask file (bit-packed + zstd, as the official save_mask): 1.85–1.98 MB, mean 1.90 MB. Full fine-tune = new 988 MB file (bf16) per subject → ~520× smaller.
- Full fine-tuning changed 493,994,138–494,010,272 of 494,032,768 weights (99.99%).

## Drift from the original (KL on held-out text, lower = forgets less)
- mean: start mask 0.003 · random deletion 0.027 · deletion tuning 0.111 · full fine-tune 0.247 → FFT drifted 2.2× as far (1.8–2.7× per subject).
- Prior-task accuracy (60 history questions) was at chance for every method (6.7–13.3%), so it can't show forgetting here; not used in the video.

## Time / memory (not a fair race, reported only)
- Train time per subject: deletion 95–165 s (mean 124 s); FFT 165–268 s (mean 205 s, with gradient checkpointing). Eval ~40–60 s per method.
- First FFT attempt kept a second model copy in memory and hit swap (20 steps in 268 s); rerun as a separate low-memory step. Peak MPS memory ~10.6–15 GB.

## Their numbers (paper, not mine)
- Llama 3 8B GSM8K GRPO: DT 83.55 vs FFT 83.24; mask 8.4 MB vs 30,633 MB. Qwen2.5-0.5B GRPO: base 10.44, FFT 19.01, DT 17.64.
- SFT MMLU-Pro Llama1B: base 10.37 · FFT 16.97 · DT 18.62. Small models recover 90–99% of FFT under GRPO.
