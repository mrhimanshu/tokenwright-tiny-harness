"""Generate 3 seeded task sets (n=3 per condition): multi-step arithmetic word problems + variable-chain tracking.
Answers are integers, checked exactly. Writes tasks.jsonl."""
import json, random, sys

NAMES = ["Mara", "Ben", "Ivy", "Omar", "Lena", "Raj", "Tess", "Kofi"]
ITEMS = ["pens", "apples", "bolts", "books", "cards", "jars"]


def word_problem(r):
    n, it = r.choice(NAMES), r.choice(ITEMS)
    a, b = r.randint(12, 39), r.randint(11, 29)
    c = r.randint(20, a * b - 30)
    d = r.randint(2, 6)
    total = a * b - c
    # make total divisible by d
    total -= total % d
    c = a * b - total
    q = (f"{n} has {a} boxes with {b} {it} in each box. {n} gives away {c} {it}, "
         f"then shares the rest equally among {d} friends. How many {it} does each friend get?")
    return q, total // d, "word"


def chain(r, hops):
    vars_ = list("pqrstuvwxyz")
    r.shuffle(vars_)
    v0 = r.randint(2, 9)
    lines = [f"{vars_[0]} = {v0}"]
    val = v0
    for i in range(1, hops + 1):
        op = r.choice(["+", "-", "*"]) if i < hops else r.choice(["+", "-"])
        k = r.randint(2, 9) if op != "*" else r.randint(2, 3)
        val = val + k if op == "+" else val - k if op == "-" else val * k
        lines.append(f"{vars_[i]} = {vars_[i-1]} {op} {k}")
    # shuffle presentation order so the model must track dependencies
    shown = lines[:]
    r.shuffle(shown)
    q = "; ".join(shown) + f". What is {vars_[hops]}?"
    return q, val, f"chain{hops}"


def main():
    out = []
    for seed in (1, 2, 3):
        r = random.Random(1000 + seed)
        for i in range(8):
            q, a, kind = word_problem(r)
            out.append(dict(set=seed, id=f"s{seed}_w{i}", kind=kind, q=q, a=a))
        for hops in (3, 5, 7):
            for i in range(4):
                q, a, kind = chain(r, hops)
                out.append(dict(set=seed, id=f"s{seed}_c{hops}_{i}", kind=kind, q=q, a=a))
    with open(sys.argv[1] if len(sys.argv) > 1 else "tasks.jsonl", "w") as f:
        for t in out:
            f.write(json.dumps(t) + "\n")
    print(len(out), "tasks")


if __name__ == "__main__":
    main()
