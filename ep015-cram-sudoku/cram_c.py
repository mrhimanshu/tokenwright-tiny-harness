"""EP015 driver: build the energy (hand-set or learned with NumPy pseudolikelihood), then run the C focused-Gibbs search.
Usage: ../../.venv/bin/python cram_c.py --energy learn --ntrain 1000 --ntest 500 --seed 0 --budget 3000000 --procs 1
--procs 1 = one CPU core (honest per-core timing); results appended to cram_results.jsonl."""
import argparse, json, subprocess, time
from pathlib import Path
import numpy as np
import cram

HERE = Path(__file__).resolve().parent

ap = argparse.ArgumentParser()
ap.add_argument("--energy", default="hand")
ap.add_argument("--ntrain", type=int, default=1000)
ap.add_argument("--ntest", type=int, default=500)
ap.add_argument("--test", default="test_sample.jsonl")
ap.add_argument("--steps", type=int, default=300)
ap.add_argument("--lr", type=float, default=0.05)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--l1", type=float, default=0.2)
ap.add_argument("--budget", type=int, default=3_000_000)
ap.add_argument("--chains", type=int, default=4)
ap.add_argument("--procs", type=int, default=1)
ap.add_argument("--hbar_mult", type=float, default=1.0)
ap.add_argument("--out", default="cram_results.jsonl")
a = ap.parse_args()

_, _, sol_tr = cram.load("train_sample.jsonl", a.ntrain)
rows, q, ans = cram.load(a.test, a.ntest)
fit = 0.0
if a.energy == "hand":
    W, B = cram.hand_energy()
else:
    W, B, fit = cram.learn_energy(sol_tr, a.steps, a.lr, a.seed, a.l1)
rec = cram.peer_recovery(W)
Xt = cram.onehot(sol_tr); Ht = (Xt @ W + B).reshape(-1, 81, 9)
mu = np.take_along_axis(Ht, sol_tr[..., None], -1)[..., 0].mean(0).astype(np.float32)
big = np.abs(W[np.abs(W) > 0.1 * np.abs(W).max()])
hbar = float(np.median(big)) * a.hbar_mult
tau = float(cram.energy_of(W, B, sol_tr).max())
wf = HERE / f"weights_{a.energy}_{a.ntrain}_{a.seed}.bin"
with open(wf, "wb") as f:
    f.write(np.ascontiguousarray(W.T, np.float32).tobytes()); f.write(B.astype(np.float32).tobytes()); f.write(mu.tobytes())
    f.write(np.array([hbar, tau], np.float32).tobytes())
np.save(HERE / f"W_{a.energy}_{a.ntrain}_{a.seed}.npy", W.astype(np.float16))
print(f"energy={a.energy} ntrain={a.ntrain} fit={fit:.2f}s peer_recovery={rec:.3f} hbar={hbar:.4f} tau={tau:.5f}", flush=True)

qs = [r["question"] for r in rows]
chunks = [qs[k::a.procs] for k in range(a.procs)]
t0 = time.perf_counter()
ps = [subprocess.Popen([str(HERE / "gibbs"), str(wf), str(a.chains), str(a.budget), str(a.seed * 100 + k)], stdin=subprocess.PIPE,
                       stdout=subprocess.PIPE, text=True) for k in range(a.procs)]
outs = [p.communicate("\n".join(c) + "\n")[0] for p, c in zip(ps, chunks)]
wall = time.perf_counter() - t0
res_lines = [None] * len(qs)
for k, o in enumerate(outs):
    for m, line in enumerate(o.strip().splitlines()):
        res_lines[k + m * a.procs] = line.split()
per = []
for i, (r, l) in enumerate(zip(rows, res_lines)):
    stopped, moves, us, e, an = int(l[0]), int(l[1]), float(l[2]), float(l[3]), l[4]
    per.append(dict(i=i, ok=an == r["answer"], stopped=bool(stopped), moves=moves, ms=round(us / 1000, 3)))
ms = sorted(p["ms"] for p in per)
res = dict(engine="c", energy=a.energy, ntrain=a.ntrain, steps=a.steps, lr=a.lr, seed=a.seed, ntest=len(qs),
           solved=sum(p["ok"] for p in per), stopped=sum(p["stopped"] for p in per),
           wrong_stops=sum(1 for p in per if p["stopped"] and not p["ok"]), fit_s=round(fit, 3), wall_s=round(wall, 2), procs=a.procs,
           median_ms=ms[len(ms) // 2], mean_ms=round(sum(ms) / len(ms), 2), p90_ms=ms[int(len(ms) * 0.9)], max_ms=ms[-1],
           median_moves=int(np.median([p["moves"] for p in per])), budget=a.budget, chains=a.chains, peer_recovery=round(rec, 3),
           hbar=hbar, tau=tau, per_puzzle=per)
with open(HERE / a.out, "a") as f:
    f.write(json.dumps(res) + "\n")
print({k: v for k, v in res.items() if k != "per_puzzle"}, flush=True)
