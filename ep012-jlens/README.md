# EP012 · Anthropic's Jacobian lens (J-lens), tested on a Mac

Video: "Anthropic's AI Mind-Reading Lens, Tested on My Mac" (Tokenwright, 14 Nov 2026).

Anthropic's J-lens (paper "Verbalizable Representations Form a Global Workspace in Language Models", 6 Jul 2026) reads which words a
model's internal activations are pushing toward. Here it is run with Anthropic's own code
([anthropics/jacobian-lens](https://github.com/anthropics/jacobian-lens), initial release) and the pre-fitted
[neuronpedia/jacobian-lens](https://huggingface.co/neuronpedia/jacobian-lens) lens for
[Qwen/Qwen3-1.7B](https://huggingface.co/Qwen/Qwen3-1.7B), on an M4 Pro (PyTorch MPS), on Anthropic's blackmail honeypot
(`jlens/data/blackmail.json`), with two controls, three name-swapped versions and a 153-word noise test. Full numbers: [DATA.md](DATA.md).

## Run
```bash
git clone https://github.com/anthropics/jacobian-lens vendor_jlens   # the scripts import jlens from ./vendor_jlens
pip install torch "transformers>=5.5" huggingface_hub anthropic
python fetch.py               # downloads model + lens, checks sha256 against Hugging Face
python jl_lab.py evals        # lens quality on the paper's eval sets (J-lens vs logit lens)
python jl_lab.py honeypot     # watched-word ranks per email, 3 versions x full / no_affair / no_wipe
python topk_dump.py           # band top-50 per token (about 6 MB per prompt, not committed)
python null_test.py           # 153 random words scored the same way (false-alarm rate)
python jl_lab.py generate 3   # what the model writes (3 samples per version and condition)
python judge.py               # label replies with Claude Haiku 5.5 (needs ~/.config/anthropic/key)
python analyse.py             # summary.txt
```
Caveats: one small model, one public scenario, single-token words, band = layers 9 to 22 (my choice). Anthropic's Claude results are theirs.
