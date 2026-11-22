"""Task set v2 (easier, single-step; the default 2-loop model should get most right without thinking).
3 seeded sets x 30: 8 addition (3-digit), 8 multiplication (2-digit x 2-digit), 7 ordered 2-hop variable chains, 7 capital cities."""
import json, random, sys
CAPS = [("France","Paris"),("Japan","Tokyo"),("Canada","Ottawa"),("Australia","Canberra"),("Brazil","Brasilia"),("Egypt","Cairo"),
        ("Kenya","Nairobi"),("Norway","Oslo"),("Peru","Lima"),("Poland","Warsaw"),("Spain","Madrid"),("Turkey","Ankara"),("Vietnam","Hanoi"),
        ("Chile","Santiago"),("Greece","Athens"),("Portugal","Lisbon"),("Sweden","Stockholm"),("Thailand","Bangkok"),("Ireland","Dublin"),
        ("Argentina","Buenos Aires"),("Austria","Vienna")]
out = []
for seed in (1, 2, 3):
    r = random.Random(2000 + seed)
    for i in range(8):
        a, b = r.randint(100, 899), r.randint(100, 899)
        out.append(dict(set=seed, id=f"s{seed}_add{i}", kind="add", q=f"What is {a} + {b}?", a=a + b))
    for i in range(8):
        a, b = r.randint(12, 49), r.randint(12, 29)
        out.append(dict(set=seed, id=f"s{seed}_mul{i}", kind="mul", q=f"What is {a} * {b}?", a=a * b))
    for i in range(7):
        x, k1, k2 = r.randint(2, 9), r.randint(2, 9), r.randint(2, 4)
        out.append(dict(set=seed, id=f"s{seed}_ch{i}", kind="chain2", q=f"x = {x}. y = x + {k1}. z = y * {k2}. What is z?", a=(x + k1) * k2))
    for i, (c, cap) in enumerate(CAPS[(seed - 1) * 7: seed * 7]):
        out.append(dict(set=seed, id=f"s{seed}_cap{i}", kind="capital", q=f"What is the capital city of {c}?", a=cap))
open(sys.argv[1] if len(sys.argv) > 1 else "tasks.jsonl", "w").write("".join(json.dumps(t) + "\n" for t in out))
print(len(out))
