"""Fetch a small sample of Sudoku-Extreme (sapientinc/sudoku-extreme, the benchmark used by HRM/TRM/CRAM) via the HF datasets-server.
test_sample.jsonl = 500 test puzzles from 5 seeded random pages; train_sample.jsonl = first 1,000 train puzzles (solutions used for learning)."""
import json, random, urllib.request, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
URL = "https://datasets-server.huggingface.co/rows?dataset=sapientinc/sudoku-extreme&config=default&split={s}&offset={o}&length=100"

def page(split, off):
    for k in range(5):
        try:
            with urllib.request.urlopen(URL.format(s=split, o=off), timeout=60) as r:
                d = json.load(r)
            return d["rows"], d["num_rows_total"]
        except Exception as e:
            print("retry", split, off, e); time.sleep(3 + 3 * k)
    raise SystemExit("fetch failed")

_, n_test = page("test", 0)
random.seed(15)
offs = sorted(random.sample(range(0, n_test - 100), 5))
with open(HERE / "test_sample.jsonl", "w") as f:
    for o in offs:
        rows, _ = page("test", o)
        for r in rows:
            f.write(json.dumps({"idx": r["row_idx"], **r["row"]}) + "\n")
with open(HERE / "train_sample.jsonl", "w") as f:
    for o in range(0, 1000, 100):
        rows, n_train = page("train", o)
        for r in rows:
            f.write(json.dumps({"idx": r["row_idx"], **r["row"]}) + "\n")
print("test total", n_test, "offsets", offs, "train total", n_train)
