#!/usr/bin/env python3
"""EP036 race: llm.asm (pure assembly) vs llama.cpp on the same CPU, same model (Qwen3-0.6B Q8_0).

Paired + shuffled design (cloud VM has CPU steal): every round runs every arm back to back
for each (test, threads) cell in random order, and logs CPU steal from /proc/stat per run.

Tests
  short : 34-token prompt (the README prompt) + 64 generated tokens  -> decode tok/s (their headline) + prefill
  long  : 426-token prompt + 64 generated tokens                       -> prefill tok/s / time to first token
"""
import json, os, random, re, subprocess, sys, time

ROUNDS = int(os.environ.get("ROUNDS", 5))
THREADS = [int(x) for x in os.environ.get("THREADS", "1,2,4").split(",")]
OUT = sys.argv[1] if len(sys.argv) > 1 else "results/race.jsonl"
M = "/tmp/ep036models"
ASMBIN = f"{M}/qwen3-0.6b-q8_0.asmbin"
GGUF = f"{M}/gguf/Qwen3-0.6B-Q8_0.gguf"
LL = "/tmp/ep036src/llama.cpp"
HERE = os.path.dirname(os.path.abspath(__file__))
SHORT_PROMPT = "Explain the difference between L1, L2, and L3 CPU caches and why cache locality matters."
LONG_PROMPT = open(os.path.join(HERE, "long_prompt.txt")).read().strip()
PTOK = {"short": 34, "long": 426}  # chat-templated token counts printed by asm-llm --print-tokens

ARMS = {
    "asm_q8": ("asm", "/tmp/ep036bin/asm-llm-q8"),
    "asm_fp32act": ("asm", "/tmp/ep036bin/asm-llm-fp32act"),
    "llama_native": ("llama", f"{LL}/build-native/bin/llama-bench"),
    "llama_avx2": ("llama", f"{LL}/build-avx2/bin/llama-bench"),
}


def steal():
    with open("/proc/stat") as f:
        v = [int(x) for x in f.readline().split()[1:]]
    return v[7], sum(v)


def run_asm(binary, test, t):
    prompt = SHORT_PROMPT if test == "short" else LONG_PROMPT
    p = subprocess.run([binary, "-m", ASMBIN, "-p", prompt, "-n", "64", "-t", str(t), "--print-tokens"],
                       capture_output=True, text=True, timeout=900)
    err = p.stderr
    pf = re.search(r"prefill: (\d+) tok in ([\d.]+) ms \(([\d.]+) tok/s\)", err)
    dc = re.search(r"decode : (\d+) tok in ([\d.]+) ms \(([\d.]+) tok/s", err)
    gen = re.search(r"GEN_TOKENS:([\d,]+)", err)
    return dict(prompt_tokens=int(pf.group(1)), prefill_ms=float(pf.group(2)), prefill_tps=float(pf.group(3)),
                gen_tokens=int(dc.group(1)), decode_ms=float(dc.group(2)), decode_tps=float(dc.group(3)),
                gen_ids=gen.group(1) if gen else None, text=p.stdout[:400])


def run_llama(binary, test, t):
    n_p = PTOK[test]
    res = {}
    # prefill (pp) and decode (tg). For the long test, decode runs at depth n_p (KV cache already holding the prompt).
    cmds = [("pp", ["-p", str(n_p), "-n", "0"]),
            ("tg", ["-p", "0", "-n", "64"] + (["-d", str(n_p)] if test == "long" else []))]
    for kind, extra in cmds:
        p = subprocess.run([binary, "-m", GGUF, "-t", str(t), "-r", "1", "-ngl", "0", "-o", "json"] + extra,
                           capture_output=True, text=True, timeout=900)
        try:
            j = json.loads(p.stdout)[0]
        except Exception:
            raise RuntimeError(p.stderr[-2000:])
        res[kind] = j
    return dict(prompt_tokens=n_p, prefill_tps=res["pp"]["avg_ts"], prefill_ms=1000 * n_p / res["pp"]["avg_ts"],
                gen_tokens=64, decode_tps=res["tg"]["avg_ts"], decode_ms=1000 * 64 / res["tg"]["avg_ts"],
                build=res["tg"].get("build_commit"), cpu_info=res["tg"].get("cpu_info"),
                backends=res["tg"].get("backends"))


def main():
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    cells = [("short", t) for t in THREADS] + [("long", 4)]
    with open(OUT, "a") as f:
        for r in range(ROUNDS):
            for test, t in cells:
                arms = [a for a in ARMS if not (a == "asm_fp32act" and test == "long")]
                random.shuffle(arms)
                for a in arms:
                    kind, binary = ARMS[a]
                    s0, tot0 = steal(); w0 = time.time()
                    out = run_asm(binary, test, t) if kind == "asm" else run_llama(binary, test, t)
                    s1, tot1 = steal()
                    rec = dict(round=r, test=test, threads=t, arm=a, wall_s=round(time.time() - w0, 2),
                               steal_pct=round(100 * (s1 - s0) / max(1, tot1 - tot0), 2),
                               ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **out)
                    f.write(json.dumps(rec) + "\n"); f.flush()
                    print(r, test, t, a, f"decode {out['decode_tps']:.1f}", f"prefill {out['prefill_tps']:.1f}",
                          f"steal {rec['steal_pct']}%", flush=True)


if __name__ == "__main__":
    main()
