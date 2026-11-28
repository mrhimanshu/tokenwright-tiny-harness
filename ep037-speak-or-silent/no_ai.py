# No AI. Scores the official Friends test split of "Speak or Stay Silent".
import json, re
load = lambda p: [json.loads(l) for l in open(p)]
train = load("data/friends/train/train_samples.jsonl")
test = load("data/friends/test/test_samples.jsonl")
key = lambda r: (str(r["context_turns"]), r["current_turn"]["text"], r["target_speaker"])
seen = {key(r): r["decision"] for r in train}          # 1. have I seen this exact moment?

def guess(r):
    if key(r) in seen:
        return seen[key(r)]                             #    then copy the answer
    name = r"\b" + re.escape(r["target_speaker"]) + r"\b"
    said = re.search(name, r["current_turn"]["text"], re.I)
    return "SPEAK" if said else "SILENT"                # 2. else: was my name just said?

hit = {"SPEAK": 0, "SILENT": 0}; n = {"SPEAK": 0, "SILENT": 0}
for r in test:
    n[r["decision"]] += 1
    hit[r["decision"]] += guess(r) == r["decision"]
print("balanced accuracy:", round(50 * (hit["SPEAK"] / n["SPEAK"] + hit["SILENT"] / n["SILENT"]), 2))
