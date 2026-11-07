"""Print a compact view of a run's .transcript.jsonl. Usage: python3 show_transcript.py <run_dir> [reasoning_chars]"""
import json, os, sys

d = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 160
for l in open(os.path.join(d, ".transcript.jsonl")):
    r = json.loads(l)
    calls = [(c, {k: (v[:70] + "…" if isinstance(v, str) and len(v) > 70 else v) for k, v in a.items()}) for c, a in r["calls"]]
    print(r["turn"], calls, "| R:", r["reasoning"][:n].replace("\n", " "), "| C:", r["content"][:120].replace("\n", " "))
