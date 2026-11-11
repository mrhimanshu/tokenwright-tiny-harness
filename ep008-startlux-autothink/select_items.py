"""Pick the test set: 8 contrast pairs at level 2 from each of 3 DecisionPivot core families (48 items), seeded."""
import json, random, collections, os
HERE = os.path.dirname(os.path.abspath(__file__))
FAMS = ["filter_match", "log_count_check", "state_goal"]
rng = random.Random(20261111)
out = []
for fam in FAMS:
    rows = [json.loads(l) for l in open(os.path.join(HERE, "pivot/tasks", fam, "items.jsonl"))]
    groups = collections.defaultdict(list)
    for r in rows:
        groups[r["group"]].append(r)
    ok = [g for g, m in groups.items() if len(m) == 2 and all(x["meta"].get("level") == 2 for x in m)
          and sorted(x["gold"] for x in m) == ["no", "yes"]]
    for g in rng.sample(sorted(ok), 8):
        for r in sorted(groups[g], key=lambda x: x["id"]):
            out.append({"id": r["id"], "family": fam, "group": g, "gold": r["gold"], "state": r["state"],
                        "questions": r["questions"], "level": r["meta"]["level"]})
with open(os.path.join(HERE, "items_selected.jsonl"), "w") as f:
    for r in out:
        f.write(json.dumps(r) + "\n")
print(len(out), collections.Counter(r["family"] for r in out), collections.Counter(r["gold"] for r in out))
