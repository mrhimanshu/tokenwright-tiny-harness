"""Download Qwen2.5-0.5B-Instruct (official Qwen repo) + MMLU-Pro, verify safetensors sha256 against the HF API."""
import hashlib, json, os
from huggingface_hub import snapshot_download, HfApi
from datasets import load_dataset

REPO = "Qwen/Qwen2.5-0.5B-Instruct"
path = snapshot_download(REPO, allow_patterns=["*.json", "*.safetensors", "*.txt", "merges.txt", "vocab.json"])
info = HfApi().model_info(REPO, files_metadata=True)
out = {"repo": REPO, "sha": info.sha, "files": {}}
for s in info.siblings:
    if s.rfilename.endswith(".safetensors"):
        expected = s.lfs.sha256 if s.lfs else None
        h = hashlib.sha256()
        with open(os.path.join(path, s.rfilename), "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        got = h.hexdigest()
        out["files"][s.rfilename] = {"expected": expected, "got": got, "ok": got == expected, "bytes": s.size}
print(json.dumps(out, indent=1))
ds = load_dataset("TIGER-Lab/MMLU-Pro")["test"]
from collections import Counter
print(len(ds), Counter(ds["category"]).most_common())
json.dump(out, open("model_verify.json", "w"), indent=1)
