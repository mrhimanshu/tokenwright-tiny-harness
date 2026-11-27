#!/usr/bin/env python3
"""Run a Nemotron Parse model on CPU over a list of page images.

usage: run_nemotron.py <parse20|parse35> <out.jsonl> page1.png [page2.png ...]
Writes one JSON line per page: model, page, seconds, new_tokens, rss_gb, raw.
Skips pages already in out.jsonl (resume).
"""
import json, os, sys, time, resource
from pathlib import Path

import psutil
import torch
from PIL import Image
from transformers import AutoModel, AutoProcessor, GenerationConfig

name, out = sys.argv[1], Path(sys.argv[2])
pages = sys.argv[3:]
mdir = Path(__file__).resolve().parent / "models" / name
torch.set_num_threads(int(os.environ.get("THREADS", "4")))
PROMPT = "</s><s><predict_bbox><predict_classes><output_markdown><predict_no_text_in_pic>"

done = set()
if out.exists():
    for line in out.read_text().splitlines():
        done.add(json.loads(line)["page"])

proc = psutil.Process()
rss0 = proc.memory_info().rss
t0 = time.time()
model = AutoModel.from_pretrained(mdir, trust_remote_code=True, dtype=getattr(torch, os.environ.get("DTYPE", "float32"))).eval()
processor = AutoProcessor.from_pretrained(mdir, trust_remote_code=True)
gen = GenerationConfig.from_pretrained(mdir)
gen.max_new_tokens = int(os.environ.get("MAX_NEW", "4000"))
gen.do_sample = False
gen.num_beams = 1
gen.repetition_penalty = 1.1
load_s = time.time() - t0
rss_loaded = proc.memory_info().rss
nparams = sum(p.numel() for p in model.parameters())
print(f"[{name}] loaded in {load_s:.1f}s, params {nparams/1e9:.3f}B, rss {rss_loaded/1e9:.2f} GB", flush=True)

def cpu_steal():
    with open("/proc/stat") as f:
        v = [int(x) for x in f.readline().split()[1:]]
    return v[7], sum(v)

for p in pages:
    pid = Path(p).stem
    if pid in done:
        continue
    image = Image.open(p).convert("RGB")
    inputs = processor(images=[image], text=PROMPT, return_tensors="pt", add_special_tokens=False)
    s0, tot0 = cpu_steal()
    t = time.time()
    with torch.inference_mode():
        ids = model.generate(**inputs, generation_config=gen)
    dt = time.time() - t
    s1, tot1 = cpu_steal()
    raw = processor.batch_decode(ids, skip_special_tokens=False)[0]
    rec = dict(model=name, dtype=os.environ.get("DTYPE", "float32"), page=pid, seconds=round(dt, 2), new_tokens=int(ids.shape[1]),
               rss_gb=round(proc.memory_info().rss / 1e9, 2),
               peak_rss_gb=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6, 2),
               load_s=round(load_s, 1), params_b=round(nparams / 1e9, 3),
               steal_pct=round(100 * (s1 - s0) / max(1, tot1 - tot0), 1), raw=raw)
    with out.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[{name}] {pid}: {dt:.1f}s, {rec['new_tokens']} tok, steal {rec['steal_pct']}%", flush=True)
print("NEMODONE", name, flush=True)
