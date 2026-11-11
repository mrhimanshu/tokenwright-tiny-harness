# EP008 FACTS — StartLux-Decision AutoThink ("thinks only when unsure")
Checked 11 Nov 2026, 06:00–06:40 UK, from primary sources.

## Story source
- AlphaSignal, Mon 9 Nov 2026, Signal #5: "StartLux ships decision models from 0.8B to 27B that think only when uncertain" (511 likes).

## Primary sources
- Code: https://github.com/StartLuxLabs/StartLux-Decision (Apache-2.0; cloned at commit a99977d, 23 Oct 2026)
- Models: https://huggingface.co/startlux-models (weights CC BY-NC 4.0, non-commercial)
  - 4B AutoThink repo lastModified 14 Oct 2026; GGUF repo created 11 Oct 2026, 18,250 downloads at check time.
- Technical report: arXiv 2610.17309 (Oct 2026), Zhuang, Su, Pan, Wong, Chen, Kuo (StartLux, HKU, SUSTech).
- Benchmark: DecisionPivot v1.1 (8 Oct 2026), https://huggingface.co/datasets/startlux-models/DecisionPivot, paper arXiv 2610.28522.
  Core track = 13 program-generated families, 7,800 items, CC BY 4.0. Items come in contrast pairs: the same case twice, with ONE
  planted detail that flips the answer. A pair counts only when both answers are right.

## How AutoThink works (model card + docs/api.md)
- One forward pass reads a probability for every option (no text). If the top probability is below the gate, the model writes a
  thought (max 4,096 tokens, temperature 0.6), reads the options again and answers 0.25 × first + 0.75 × second.
- Default gate = 0.6. The published results use gate 0.9.
- Family: 0.8B / 2B / 4B / 9B / 27B Instant, 4B / 9B / 27B AutoThink.

## Their numbers (not ours)
- 4B AutoThink: Decision Index 0.3 public 68.21; DecisionPivot pair accuracy 59.9 (gate 0.9). 4B Instant: 67.88 / 41.5.
- README, 27B AutoThink: moving the gate 0.9 → 0.6 lowers DecisionPivot pair accuracy 88.1% → 68.4% (Decision Index 73.22 → 72.85).
- DecisionPivot T4 table, "4B after the stop step": one pass pair accuracy 14.0 vs with reasoning 61.0; 2,271 thought tokens per item.
- Speed: one H200, vLLM: 25–52 ms per request (Instant). MLX 8-bit on an Apple M5 Pro, 4B, 256-token prompt: 94 ms per read-out.
- 16 Oct 2026: 27B Instant ranked #1 of 174 on the Decision Index 0.3.2 leaderboard (Full 69.12).

## Our setup
- Model: startlux-models/StartLux-Decision-v1.1-4B-AutoThink-GGUF, file Q8_0, 4,482,402,752 bytes,
  sha256 31e0d4e3ceb02cc5ea2db4168a97fe8cd94e70759595154d0a1ebe910ee78213 (matches the HF API).
- Engine: llama-server 0.7.0 (Homebrew build 11669), 16k ctx, q8 KV cache, 1 slot; StartLux engine `--backend llamacpp`.
- Mac: Apple M4 Pro, 24 GB. Claude baseline: claude-haiku-5-5 via the API.
- Test set: 48 items = 8 contrast pairs at level 2 from each of filter_match, log_count_check, state_goal (seed 20261111).

## Competition (YouTube search, 11 Nov 2026)
- "StartLux Decision AutoThink" since 15 Oct: 1 relevant video (Aether Agent, 21 Oct, an explainer) + 1 news clip. Nobody ran it.
