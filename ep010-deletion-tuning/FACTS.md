# EP010 FACTS: Deletion Tuning ("teach an LLM by deleting 0.05% of its weights")
Checked 12 Nov 2026, 22:05–22:30 UK (night run).

## Source chain
- AlphaSignal, Thu 12 Nov 2026 14:19 UTC, "Signals" #3: "NYU method matches full fine-tuning by deleting just 0.05% of LLM weights" (1,760 likes).
- Paper: "The Surprising Effectiveness of Deleting Weights in LLM Post-Training", arXiv 2611.10866 (posted 7 Nov 2026), NeurIPS 2026.
  Authors: Jack Lu*, Zhenbang Yang* (NYU), Mike Lasby, Tejas Pote, Yani Ioannou (U Calgary), Mengye Ren (NYU).
- Project page: https://agenticlearning.ai/deleting-weights/
- Official code (MIT): https://github.com/agentic-learning-ai-lab/deleting-weights (HEAD 94f0340, 10 Nov 2026). Masks on HF: Jacklu0831/deletion-tuning-masks.

## What the method does (from the project page + code)
- Freeze the pretrained model. Give every weight of every MLP **gate projection** one trainable logit G.
- Training: weight multiplied by sigmoid(alpha * G); alpha (sharpness) rises linearly (SFT script: 100 -> 1000).
- Deployment: keep weights with G > 0, set the rest to exactly zero. "Writes no new values." One bit per weight.
- Logits start from Wanda pruning scores (|W| x input-activation norm); SFT script init sparsity 0.00048828125 (= 1/2048, 0.049%), prior strength 3 std.
- SFT settings (scripts/train_sft.sh): 400 steps, batch 4, lr 5e-4 (deletion) vs 3e-6 (full fine-tune), weight_reg 1e-5 decaying to 0.
- Eval on MMLU-Pro: score each option by mean answer-token loss, pick the lowest. 25% of each category held out as test.

## Their numbers (all theirs, not ours)
- Llama 3 8B Instruct, GRPO on GSM8K: Deletion Tuning 83.55% vs full fine-tune 83.24% (base 60.27%).
- Adapter size: mask 8.4 MB vs FFT checkpoint 30,633 MB (fp32) for Llama8B. Qwen0.5B: 0.5 MB vs 1,885 MB.
- Every Deletion Tuning run deletes < 0.05% of the model's weights (0.035–0.046% at the Llama scales).
- Small models trail: "At smaller sizes, Deletion Tuning recovers 90% to 99% of FFT's accuracy, and the gap closes as models grow."
  Qwen2.5-0.5B GRPO: base 10.44 · FFT 19.01 · DT 17.64.
- SFT, MMLU-Pro (mean of 14 categories): Llama1B base 10.37 · FFT 16.97 · DT 18.62; Llama3B base 12.63 · FFT 21.19 · DT 22.28.
- Wanda pruning alone (no training) changes accuracy by at most 2.4 points; learning the mask drives the gains (up to +53.2).
- Forgetting: prior-task accuracy within 1 point of base for DT; FFT −1.3 to −3.1; LoRA/MTH up to −5.4. Forward KL to base ≤ 0.05 (DT) vs 1.0 (FFT Llama1B) / 1.5 (Llama8B).
- An earlier version was called "Bit-Mask Tuning" and reported trailing FFT on 0.5B models (per coverage).

## Competition (YouTube search, published after 5 Nov, 12 Nov 22:10 UK)
- 4 videos on the paper: AI Paper Slop (auto paper read), AI Engineering Topics (explainer), Emergent Mind (paper summary), one Korean explainer. Nobody ran it.

## Other AlphaSignal 12 Nov stories considered
- Grok Bot 1.0 (11,994 likes): product launch, not testable.
- Gemini 4 Carbon (8,425): big launch, not testable via the Anthropic API; will be saturated.
- FAISS e-means (6,832): our EP009.
- Gemini Robotics 2.5 (5,532): not testable.
- Anthropic "inner monologue" tool (753): no runnable artefact checked tonight.
- Zyphra ZONOS3-Mini voice cloning (4,170 downloads): 15+ YouTube videos in 3 days incl. local tests (Run It Local, Rk Runtime, Neural Nexus): saturated.
- Unsloth Qwen3.8-27B Dynamic V3.1 GGUFs (2,522): smallest 1-bit file 6.19 GB, over our 6 GB local-model rule.
