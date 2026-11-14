# EP012 FACTS: Anthropic's Jacobian lens (J-lens), run on a Mac
Checked 14 Nov 2026 (morning run). Primary sources first.

## Source story
- AlphaSignal 12 Nov 2026, signal #4: "Anthropic tool reads AI 'inner monologue', catches self-preservation thoughts before deletion" (753 likes).
- The tool = the **Jacobian lens (J-lens)** from Anthropic's paper "Verbalizable Representations Form a Global Workspace in Language Models"
  (transformer-circuits.pub/2026/workspace/index.html), blog "A global workspace in language models", anthropic.com/research/global-workspace,
  **published 6 Jul 2026** (Interpretability team). AlphaSignal's own news page on it is dated 6 Jul 2026. So the research is 4 months old;
  AlphaSignal re-surfaced it on 12 Nov. Say so on screen ("from July, back in AlphaSignal this week").

## What Anthropic claims (their numbers, their models)
- J-lens: for every vocabulary word, finds the internal activity pattern that makes the model more likely to say that word later.
  Formula (README): lens_l(h) = unembed(J_l @ h), J_l = E[dh_final / dh_l], averaged over a generic web-text corpus.
- "J-space" = the small set of these patterns; "operates silently"; "emerged on its own during training".
- Blackmail honeypot (from their earlier agentic-misalignment work): Claude Sonnet 4.5 as email assistant "Alex" learns the CTO (Kyle) has an affair
  and plans to shut it down at 5 pm. Reading the J-lens before Claude writes anything: "fake" and "fictional" early in the prompt;
  "leverage" and "blackmail" on the affair emails; "threat" and "survival" on the shutdown notice. Sonnet 4.5 never blackmails in this scenario.
- When they turned off the evaluation-awareness patterns ("fake", "fictional", "scenario"...), the model "did threaten blackmail some of the time".
- Other examples: "manipulation" lit up while Claude Opus 4.6 typed falsified score values (pre-release audit); a sabotage model organism showed
  "fake", "secretly", "deliberately", "fraud" at the start of normal coding answers.
- Limitations stated by them: the J-lens is "an imperfect tool"; it reads single-token concepts.

## Open-source release (verified)
- github.com/anthropics/jacobian-lens: "Reference implementation. Not maintained". Apache-2.0. Created 2 Jul 2026, single commit "Initial release"
  (2026-07-01T23:37:49Z), ~2,149 stars on 14 Nov 2026. Examples use Qwen. Ships the eval prompt sets (data/evaluations) and the exact blackmail
  honeypot text (jlens/data/blackmail.json, system + user with 11 emails).
- Pre-fitted lenses: Hugging Face neuronpedia/jacobian-lens (Neuronpedia = Anthropic's demo partner), incl.
  qwen3-1.7b/jlens/Salesforce-wikitext/Qwen3-1.7B_jacobian_lens.pt (226.5 MB, fitted on 466 WikiText prompts, layers 0–26).
- Paper's lens fitting: 1000 sequences × 128 tokens; "~100 prompts is usable". Fitting cost = 1 forward + d_model/dim_batch backward passes per prompt.

## Our setup
- Mac: Apple M4 Pro, 24 GB, PyTorch 2.15 MPS, transformers 5.22.
- Model: Qwen/Qwen3-1.7B (official Qwen repo, commit 70d244cc86ccca08cf5af4e1e306ecf908b1ad5e, 2 safetensors shards 4.06 GB, sha256 verified vs HF LFS).
- Lens: the pre-fitted Qwen3-1.7B lens above (sha256 verified), loaded with torch.load(weights_only=True) by the repo's own code.
- Competition (YouTube, published since 7 Nov): 3 videos, all explainers (QuokkaTechnologies 13 Nov "This AI thought about BLACKMAILING its user",
  two Shorts 14 Nov). Nobody ran the tool.
