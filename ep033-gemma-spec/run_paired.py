"""EP033 lab (paired): Gemma 4 E4B on LiteRT-LM, x86 Linux CPU. For every prompt, run each arm back to back in a
shuffled order, so the cloud VM's CPU steal hits all arms alike. Logs CPU steal % during each generation.
Arms: off / on / adaptive (lenience 0 = lossless) and optionally "lenient" (on, lenience=1.0).
Usage: run_paired.py [--reps 2] [--arms off,on,adaptive] [--threads 4] [--tasks ...] [--out paired.jsonl] [--tag main]
Greedy decoding (top_k=1) so outputs can be compared across arms."""
import argparse, hashlib, json, os, random, resource, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import litert_lm as L
from litert_lm import interfaces as I
from litert_lm._ffi import SpeculativeDecodingMode as SDM
from prompts import PROMPTS

ap = argparse.ArgumentParser()
ap.add_argument("--reps", type=int, default=2)
ap.add_argument("--arms", default="off,on,adaptive")
ap.add_argument("--tasks", default=",".join(PROMPTS))
ap.add_argument("--threads", type=int, default=4)
ap.add_argument("--max", type=int, default=256)
ap.add_argument("--out", default="paired.jsonl")
ap.add_argument("--tag", default="main")
ap.add_argument("--seed", type=int, default=33)
a = ap.parse_args()
MODEL = os.path.join(HERE, "model", "gemma-4-E4B-it.litertlm")
ARMS = {"off": (SDM.OFF, None), "on": (SDM.ON, None), "adaptive": (SDM.ADAPTIVE, None), "lenient": (SDM.ON, 1.0)}
arms = a.arms.split(",")

# One engine with the drafter loaded (mode ON); each conversation overrides the mode/lenience.
t0 = time.time()
eng = L.Engine(MODEL, backend=I.Backend.CPU(thread_count=a.threads), max_num_tokens=2048, enable_benchmark=True,
               speculative_decoding_config=I.SpeculativeDecodingConfig(mode=SDM.ON), cache_dir=os.path.join(HERE, "cache"))
print(f"engine loaded {time.time() - t0:.1f}s", flush=True)


def cpu():
    v = list(map(int, open("/proc/stat").readline().split()[1:]))
    return sum(v), v[7]  # total, steal


def text_of(msg):
    c = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", msg)
    if isinstance(c, list):
        return "".join(x.get("text", "") if isinstance(x, dict) else str(getattr(x, "text", x)) for x in c)
    return str(c)


rng = random.Random(a.seed)
out = open(os.path.join(HERE, a.out), "a")
jobs = [(rep, t, p) for rep in range(a.reps) for t in a.tasks.split(",") for p in range(len(PROMPTS[t]))]
for k, (rep, task, pi) in enumerate(jobs):
    order = arms[:]; rng.shuffle(order)
    for arm in order:
        mode, len_ = ARMS[arm]
        conv = eng.create_conversation(sampler_config=I.SamplerConfig(top_k=1, temperature=0.0, seed=1), max_output_tokens=a.max,
                                       speculative_decoding_config=I.SpeculativeDecodingConfig(mode=mode, lenience=len_))
        c0, s0 = cpu(); t = time.time()
        msg = conv.send_message(PROMPTS[task][pi])
        wall = time.time() - t; c1, s1 = cpu()
        bi = conv.get_benchmark_info(); txt = text_of(msg)
        rec = dict(arm=arm, threads=a.threads, task=task, prompt=pi, rep=rep, tag=a.tag, pos=order.index(arm),
                   wall_s=round(wall, 3), ttft_s=round(bi.time_to_first_token_in_second, 3),
                   prefill_tokens=bi.last_prefill_token_count, prefill_tps=round(bi.last_prefill_tokens_per_second, 2),
                   decode_tokens=bi.last_decode_token_count, decode_tps=round(bi.last_decode_tokens_per_second, 2),
                   steal_pct=round(100 * (s1 - s0) / max(1, c1 - c0), 1),
                   maxrss_mb=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024),
                   out_sha=hashlib.sha256(txt.encode()).hexdigest()[:16], out_chars=len(txt), text=txt,
                   ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        out.write(json.dumps(rec) + "\n"); out.flush()
        print(f"[{k + 1}/{len(jobs)}] {arm:8s} {task:9s} p{pi} r{rep} {rec['decode_tps']:6.2f} tok/s {rec['decode_tokens']:3d} tok "
              f"steal {rec['steal_pct']:4.1f}% sha {rec['out_sha']}", flush=True)
        conv.close()
print("PAIRED DONE", flush=True)
