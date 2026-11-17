# EP016 DATA (my runs, 17 Nov 2026, cloud CPU, PyTorch 2.15.0, SciPy 1.18.1; API spend $0.93)
Raw: lab/audit.jsonl, lab/drift.jsonl, lab/claude_gen.jsonl, lab/claude_eval.jsonl, generated code in lab/gen/. Summary: lab/summary.json.
Reference values: mpmath (80 digits toy, 40 digits 32k vocab) on the exact same float32-stored logits.

## Lab 1: everyday FP32 KL / JSD on nearly equal distributions (lab/audit.py)
"h" = how far the student's logits are from the teacher's (student = teacher + h * noise).
Case "32k vocab": teacher logits ~ N(0, 3²) over 32,000 tokens, 3 seeds. Numbers = median over 3 seeds.

| implementation | h = 1e-3 | h = 1e-4 | h = 3e-5 |
|---|---|---|---|
| true KL | 4.5e-7 | 4.5e-9 | 4.1e-10 |
| textbook sum p(log p − log q) | 0.75× true | **23× too big** | **negative (3 of 3)** |
| `F.kl_div(log q, log p, log_target=True)` | same as textbook (identical numbers) | 23× | negative |
| `F.kl_div(log_softmax(student), softmax(teacher))` (classic distillation line) | | 21× | negative |
| `torch.distributions.kl_divergence(Categorical…)` | | 97× | negative |
| `scipy.stats.entropy(p, q)` on the float32 probs | | negative (−14×) | |
| BF16 textbook | already negative at h = 0.1 (2 of 3 seeds) and h = 0.01 | | |
| **fixed (Amos reformulation 1+2, ported to PyTorch)** | exact | exact | exact (still exact at 1e-6: ratio 1.0000003) |

- First h where an implementation is > 10% off in all 3 seeds: textbook / F.kl_div / torch.distributions = 1e-3; SciPy = 3e-4; BF16 = 1e-1; fixed = never (down to 1e-6).
- Toy case (paper's z = (-1, h, 1)): at h = 1e-4 true KL = 9.2e-10, textbook FP32 says 6.0e-8 (**65× too big**); fixed says 9.24e-10.
- JSD: textbook FP32 JSD negative at h = 1e-4 (2 of 3 seeds); **`scipy.spatial.distance.jensenshannon` returned NaN** (sqrt of a negative number) at h = 3e-5 in 2 of 3 seeds and at h = 3e-4, 3e-5, 1e-5 in the toy case.
- Gradients (FP32): only 0.3% off at h = 1e-4, 2% at 3e-5, 9–42% at 1e-6. BF16 gradient 24% off even at h = 0.1.
- **Identical logits** (true KL = 0, true gradient = 0), 32,000 tokens, 3 seeds: every standard implementation returns a NONZERO gradient on **all 32,000 of 32,000** entries
  (FP32 norm ~4e-8, BF16 ~3e-4). The fix: exactly 0 on all entries.

## Lab 2: does it matter in training? (lab/drift.py)
Distillation, student = exact copy of the teacher (MLP 64 → 256 → 32,000 logits). True gradient = 0, so the student should never move.
Adam lr 1e-3 (default eps 1e-8), batch 32, 300 steps, 3 seeds.

| loss | gradient at step 0 | weights moved after 300 steps | true KL after 300 steps (was 0) |
|---|---|---|---|
| FP32 `F.kl_div` | 4.7e-9 (should be 0) | **2.7%** (2.66–2.71%) | 1.8e-5 |
| BF16 `F.kl_div` | 2.6e-4 | **51%** (49–54%) | 3.3e-4 |
| fixed FP32 | 0 | 0 | 0 |

- Drift starts right away: FP32 1.0% after 10 steps, 2.2% after 30; BF16 1.9% after ONE step, 7% after 10.
- Why: Adam divides by the gradient's own size, so a 1e-9 rounding gradient becomes a full-size lr step.
- Caveat: outputs barely change (KL 1.8e-5 is tiny); real training also has other loss terms and an SGD-style optimizer would ignore 1e-9 gradients. This shows wasted, random movement, not a ruined model.

## Lab 3: does Claude write the bug? (lab/claude_kl.py)
Same task, Haiku / Sonnet / Opus 5.5, adaptive thinking, effort high, n = 5 each. Tested on the 32k-vocab case.
"Accurate" = < 1% error at h = 1e-1, 1e-3, 1e-4, 1e-5 AND gradient norm < 1e-12 at identical logits.

| prompt | Haiku | Sonnet | Opus | total |
|---|---|---|---|---|
| plain ("write KL(teacher‖student) from logits for distillation") | 0/5 | 0/5 | 0/5 | **0/15** |
| warned (+ "often nearly identical… must stay accurate in float32, value AND gradient") | 5/5 | 5/5 | 5/5 | **15/15** |

- Plain: all 15 wrote the textbook log_softmax formula (2 Haiku used F.kl_div); every one gave the SAME wrong numbers as the textbook: 37× the true value at h = 1e-4 on seed 0 (error 3,624%), nonzero gradient at identical logits.
- Warned: Haiku 4/5 upcast to float64 (1/5 used expm1). All 10 Sonnet + Opus answers stayed in float32 and used the paper's family of tricks on their own (exp(x)−1−x remainder via expm1 and/or a Taylor series, plus log1p; 8 of 10 with a custom autograd gradient).
- Code size: plain median 23–37 lines; warned 28 (Haiku), 60 (Sonnet), 84 (Opus).
- Cost per answer: plain $0.0004 (Haiku) / $0.0045 (Sonnet) / $0.032 (Opus); warned $0.0013 / $0.041 / $0.107. Total $0.93.
- Read: Claude knows the fix. It only uses it when you tell it the distributions will be close.
