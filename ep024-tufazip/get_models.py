# Download official small LMs and verify every LFS file's sha256 against the HF API.
import hashlib, json, sys
from huggingface_hub import HfApi, snapshot_download
api = HfApi(); out = {}
for repo in ["HuggingFaceTB/SmolLM2-135M", "HuggingFaceTB/SmolLM2-360M", "Qwen/Qwen2.5-0.5B"]:
    p = snapshot_download(repo, cache_dir="/data/renders/EP024/hf", allow_patterns=["*.json", "*.safetensors", "*.txt", "merges.txt", "vocab.json"])
    info = api.model_info(repo, files_metadata=True)
    res = {}
    for s in info.siblings:
        if s.lfs and s.rfilename.endswith(".safetensors"):
            h = hashlib.sha256(open(f"{p}/{s.rfilename}", "rb").read()).hexdigest()
            res[s.rfilename] = {"sha256": h, "ok": h == s.lfs.sha256, "size": s.size}
    out[repo] = {"path": p, "sha": info.sha, "files": res}
    print(repo, res, flush=True)
json.dump(out, open("models.json", "w"), indent=1)
