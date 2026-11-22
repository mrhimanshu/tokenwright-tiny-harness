"""Perplexity of SenseNova Loop-9B at loop counts 1-4 on the same 3 Wikipedia articles (llama-perplexity, ctx 512,
1 chunk per article; it scores the second half of each chunk). Appends to ppl_results.jsonl."""
import json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from run_loops import model_for, BIN

for k in [int(x) for x in sys.argv[1].split(",")]:
    for art in ("Lighthouse", "Sourdough", "Tardigrade"):
        t0 = time.time()
        out = subprocess.run([f"{BIN}/llama-perplexity", "-m", model_for(k), "-f", os.path.join(HERE, "text", f"{art}.txt"),
                              "-c", "512", "--chunks", "1", "-t", "4", "-b", "512"], capture_output=True, text=True).stdout
        out += ""
        m = re.search(r"Final estimate: PPL = ([\d.]+)", out) or re.search(r"\[1\]([\d.]+)", out)
        row = dict(model="sensenova-loop-9b-q4km", loops=k, depth=32 + (k - 1) * 24, article=art,
                   ppl=float(m.group(1)) if m else None, wall_s=round(time.time() - t0, 1))
        open(os.path.join(HERE, "ppl_results.jsonl"), "a").write(json.dumps(row) + "\n")
        print(row, flush=True)
