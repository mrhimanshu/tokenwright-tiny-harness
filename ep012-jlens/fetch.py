import hashlib, json, os, sys
from huggingface_hub import hf_hub_download, HfApi
api = HfApi()
out = {}
def get(repo, fname, revision=None):
    info = api.get_paths_info(repo, [fname], revision=revision, expand=True)[0]
    exp = info.lfs.sha256 if info.lfs else None
    p = hf_hub_download(repo, fname, revision=revision)
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''): h.update(b)
    got = h.hexdigest()
    out[f"{repo}:{fname}"] = dict(expected=exp, got=got, ok=(exp is None or exp == got), bytes=os.path.getsize(p), path=p, revision=revision)
    print(fname, got == exp, flush=True)
repo = "Qwen/Qwen3-1.7B"
for f in ["config.json","generation_config.json","tokenizer.json","tokenizer_config.json","vocab.json","merges.txt","model.safetensors.index.json","model-00001-of-00002.safetensors","model-00002-of-00002.safetensors"]:
    get(repo, f)
get("neuronpedia/jacobian-lens", "qwen3-1.7b/jlens/Salesforce-wikitext/Qwen3-1.7B_jacobian_lens.pt", revision="main")
out["qwen_sha"] = api.model_info(repo).sha
json.dump(out, open("model_verify.json","w"), indent=1)
print("DONE")
