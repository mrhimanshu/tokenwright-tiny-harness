"""EP033 lab: Gemma 4 E4B (LiteRT-LM) decode speed with speculative decoding off / on / adaptive, on a 4-vCPU x86 Linux box.
Usage: run_lab.py MODE [--reps N] [--tasks a,b] [--threads 4] [--lenience c] [--out results.jsonl] [--max 256]
One engine per process (the drafter loads at engine creation). Greedy decoding (top_k=1) so outputs can be compared across modes.
"""
import argparse, json, os, resource, sys, time, hashlib
sys.path.insert(0, os.path.dirname(__file__))
import litert_lm as L
from litert_lm import interfaces as I
from prompts import PROMPTS

ap = argparse.ArgumentParser()
ap.add_argument("mode", choices=["off", "on", "adaptive"])
ap.add_argument("--reps", type=int, default=1)
ap.add_argument("--tasks", default=",".join(PROMPTS))
ap.add_argument("--prompts", default="0,1,2")
ap.add_argument("--threads", type=int, default=4)
ap.add_argument("--lenience", type=float, default=None)
ap.add_argument("--max", type=int, default=256)
ap.add_argument("--out", default="results.jsonl")
ap.add_argument("--tag", default="")
ap.add_argument("--rep0", type=int, default=0)
a = ap.parse_args()

MODEL = os.path.join(os.path.dirname(__file__), "model", "gemma-4-E4B-it.litertlm")
M = {"off": L.SpeculativeDecodingMode.OFF, "on": L.SpeculativeDecodingMode.ON, "adaptive": L.SpeculativeDecodingMode.ADAPTIVE} \
    if hasattr(L, "SpeculativeDecodingMode") else None
from litert_lm._ffi import SpeculativeDecodingMode as SDM
M = {"off": SDM.OFF, "on": SDM.ON, "adaptive": SDM.ADAPTIVE}
cfg = I.SpeculativeDecodingConfig(mode=M[a.mode], lenience=a.lenience)

t0 = time.time()
eng = L.Engine(MODEL, backend=I.Backend.CPU(thread_count=a.threads), max_num_tokens=2048,
               enable_benchmark=True, speculative_decoding_config=cfg, cache_dir=os.path.join(os.path.dirname(__file__), "cache"))
load_s = time.time() - t0
print(f"engine {a.mode} loaded in {load_s:.1f}s", flush=True)

def text_of(msg):
    if isinstance(msg, dict):
        c = msg.get("content")
    else:
        c = getattr(msg, "content", msg)
    if isinstance(c, list):
        return "".join(x.get("text", "") if isinstance(x, dict) else str(getattr(x, "text", x)) for x in c)
    return str(c)

out = open(os.path.join(os.path.dirname(__file__), a.out), "a")
for rep in range(a.reps):
    for task in a.tasks.split(","):
        for pi in [int(x) for x in a.prompts.split(",")]:
            prompt = PROMPTS[task][pi]
            conv = eng.create_conversation(sampler_config=I.SamplerConfig(top_k=1, temperature=0.0, seed=1),
                                           max_output_tokens=a.max)
            t = time.time()
            msg = conv.send_message(prompt)
            wall = time.time() - t
            bi = conv.get_benchmark_info()
            txt = text_of(msg)
            rec = dict(mode=a.mode, lenience=a.lenience, threads=a.threads, task=task, prompt=pi, rep=rep + a.rep0, tag=a.tag,
                       wall_s=round(wall, 3), load_s=round(load_s, 1),
                       prefill_tps=round(bi.last_prefill_tokens_per_second, 2),
                       decode_tokens=bi.last_decode_token_count,
                       decode_tps=round(bi.last_decode_tokens_per_second, 2),
                       ttft_s=round(getattr(bi, "time_to_first_token_in_second", 0) or 0, 3),
                       maxrss_mb=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024),
                       out_sha=hashlib.sha256(txt.encode()).hexdigest()[:16], out_chars=len(txt), text=txt,
                       ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
            out.write(json.dumps(rec) + "\n"); out.flush()
            print(f"{a.mode:8s} {task:9s} p{pi} r{rep} decode {rec['decode_tps']:6.2f} tok/s  {rec['decode_tokens']} tok  wall {wall:.1f}s  rss {rec['maxrss_mb']} MB", flush=True)
            conv.close()
