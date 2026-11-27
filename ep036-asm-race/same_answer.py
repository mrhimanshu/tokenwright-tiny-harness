#!/usr/bin/env python3
"""Do both engines give the same greedy answer? + peak RAM + engine size on disk.
Same chat-templated prompt (Qwen3 no-think template), temperature 0, 64 tokens, 4 threads."""
import json, os, resource, subprocess, sys, time

M = "/tmp/ep036models"; LL = "/tmp/ep036src/llama.cpp/build-native/bin"
PROMPTS = [
    "Explain the difference between L1, L2, and L3 CPU caches and why cache locality matters.",
    "What is 17 * 23? Answer with the number only.",
    "Write a Python function that reverses a string.",
    "Name three planets in the solar system.",
    "Translate 'good morning' into French and Spanish.",
]
TPL = "<|im_start|>user\n{p}<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"


def peak(cmd):
    before = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    return p, resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss  # KB, running max over children


out = []
for pr in PROMPTS:
    a, rss_a = peak(["/tmp/ep036bin/asm-llm-q8", "-m", f"{M}/qwen3-0.6b-q8_0.asmbin", "-p", pr, "-n", "64", "-t", "4"])
    l, rss_l = peak([f"{LL}/llama-completion", "-m", f"{M}/gguf/Qwen3-0.6B-Q8_0.gguf", "-p", TPL.format(p=pr),
                     "-n", "64", "-t", "4", "--temp", "0", "-no-cnv", "--no-warmup", "-ngl", "0", "--no-display-prompt"])
    ta = a.stdout.strip(); tl = l.stdout.strip()
    wa, wl = ta.split(), tl.split()
    same = 0
    for x, y in zip(wa, wl):
        if x != y: break
        same += 1
    rec = dict(prompt=pr, asm=ta, llama=tl, identical=ta == tl, same_first_words=same,
               words_asm=len(wa), words_llama=len(wl))
    out.append(rec)
    print(json.dumps(rec)[:600], flush=True)

# peak RSS separately (ru_maxrss of children is a running max, so measure each engine in its own subprocess)
def rss(cmd):
    p = subprocess.run(["/usr/bin/python3", "-c",
        "import resource,subprocess,sys;subprocess.run(sys.argv[1:],capture_output=True);"
        "print(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)"] + cmd, capture_output=True, text=True)
    return int(p.stdout.strip())

r_asm = rss(["/tmp/ep036bin/asm-llm-q8", "-m", f"{M}/qwen3-0.6b-q8_0.asmbin", "-p", PROMPTS[0], "-n", "64", "-t", "4"])
r_ll = rss([f"{LL}/llama-completion", "-m", f"{M}/gguf/Qwen3-0.6B-Q8_0.gguf", "-p", TPL.format(p=PROMPTS[0]),
            "-n", "64", "-t", "4", "--temp", "0", "-no-cnv", "-ngl", "0"])
size_ll = sum(os.path.getsize(os.path.join(LL, f)) for f in os.listdir(LL)
              if f.startswith(("libggml", "libllama.so", "libllama-common", "libllama-completion")) and not os.path.islink(os.path.join(LL, f)))
size_ll += os.path.getsize(os.path.join(LL, "llama-completion"))
summary = dict(prompts=out, peak_rss_kb=dict(asm=r_asm, llama=r_ll),
               engine_bytes=dict(asm=os.path.getsize("/tmp/ep036bin/asm-llm-q8"), llama_completion_plus_libs=size_ll))
json.dump(summary, open(sys.argv[1] if len(sys.argv) > 1 else "results/same_answer.json", "w"), indent=1)
print(summary["peak_rss_kb"], summary["engine_bytes"])
