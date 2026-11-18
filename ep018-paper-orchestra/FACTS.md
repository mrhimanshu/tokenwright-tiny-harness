# EP018 FACTS (checked 18 Nov 2026, night run, 22:00–22:40 UTC)

## Source story
- AlphaSignal, Wed 18 Nov 2026 14:14 UTC ("OpenAI GPT-6.2 Astra, Anthropic Claude Code Mode"), Signal #3 (2,960 stars):
  "Google Cloud releases multi-agent tool that writes full research papers from raw notes".
- AlphaSignal article (datePublished 2026-11-17): "Outputs compilable LaTeX targeting CVPR or ICLR templates from idea summaries and
  experiment logs"; "Semantic Scholar API grounds citations to reduce hallucinated references in the generated lit review";
  "14 to 38 percent overall win margin against autonomous baselines, still trailing humans".

## Primary sources
- Repo: https://github.com/google-research/paper-orchestra (Apache 2.0). We ran commit d9bae997 (2026-11-15 10:08 -0800).
  "This is not an officially supported Google product."
- Paper: arXiv 2604.05018, "PaperOrchestra: A Multi-Agent Framework for Automated AI Research Paper Writing", Yiwen Song, Yale Song,
  Tomas Pfister, Jinsung Yoon (Google Cloud AI Research), v1 6 Apr 2026. Abstract: literature-review win-rate margin 50%–68% and
  overall manuscript margin 14%–38% over autonomous baselines; PaperWritingBench built from 200 top-tier AI conference papers.
- Pipeline in the code: Outline agent → Literature Review agent (Gemini + Google Search tool to find candidates, then
  Semantic Scholar title search, fuzzy match > 70, date before the cutoff) → Section Writing agent → Content Refinement agent
  (simulated peer review + formatting review on the compiled PDF, pdflatex + bibtex). Plotting agent optional.
- Defaults: writer/reflection model "gemini-3.1-pro-preview" (not served to our key on 18 Nov 2026: 404); we used gemini-3.8-flash
  for every agent. Literature search is Gemini-only (google_search tool), so it can't run on Claude without a rewrite.
- Dataset (PaperWritingBench) "not included ... will be released separately".

## Our setup notes
- No TeX on the cloud computer and no root: pdflatex/bibtex are shims onto Tectonic 0.17.0 (official GitHub release binary,
  sha256 8533d07f…a3b7 checked), which runs bibtex itself.
- No Semantic Scholar API key (README says optional); the unauthenticated S2 API is rate-limited.
- Raw materials = our own EP015 CRAM / Sudoku experiment log (lab/raw_materials), so we know the ground truth of every number.

## Competition check (YouTube, published since 4 Nov 2026, 18 Nov 22:20 UTC)
- "PaperOrchestra": ~10 videos (CLI Stack, Alex Hitt, Prince Gupta, paper2video, Next Horizon, Repo Radar AI, Open Source AI Trends,
  2 Korean, a Gource). All explain or demo it; none checks the numbers or citations in what it writes. Our angle is new.

## Rejected stories from the same email (18 Nov)
- GPT-6.2 Astra / Sol (46,727 likes): no OpenAI key in the pipeline; crowded.
- Claude Code "Code Mode" (6,247 likes): 15+ videos since 13 Nov incl. measured on/off tests (DanManREAL 12 sessions, "30% cheaper").
- OpenAI outside safety teams (4,323): policy news, not testable.
- Uncensored Qwen image model 4.4 GB (3,990): "uncensored" image generator, off-brand; CPU image gen.
- MiHoYo game agent (866): not released / no games here. Sarvam India inference (3,923): no key.
- Noisy-teacher distillation (arXiv 2611.11598, 279): needs pretraining runs; effect 0.02 nats, below what a CPU-scale test can resolve.
