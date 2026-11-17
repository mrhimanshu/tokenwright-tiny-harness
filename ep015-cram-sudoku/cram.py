"""EP015: a from-scratch NumPy re-implementation of CRAM (Hoover, Blayney, Whittington, arXiv 2611.17309) on an M4 Pro CPU.
Energy (paper Eq. 1, one-hot boards):  E(x) = 1/2 sum_{i!=j} W[i,x_i,j,x_j] + sum_i B[i,x_i]
  hand  = Hopfield-Tank style rules set by hand: W = 1 for the same digit in two cells that share a row/col/box (paper C.7)
  learn = W, B learned by pseudolikelihood from solved puzzles only. The cells are opaque indices: it is NOT told rows/cols/boxes.
Search (paper C.3.1): 4 chains from random boards; a move picks a random free cell whose local energy is above its
training-solution mean by > 0.45*hbar and samples its digit from softmax(-h/T); T falls geometrically 0.40->0.31*hbar over
524,288 moves then restarts; stop at the first board with E <= tau + 1e-3 (tau = highest training-solution energy).
All chains of all puzzles run together as one NumPy batch (one move per chain per step).
Usage: ../../.venv/bin/python cram.py --energy hand|learn --ntrain 1000 --ntest 500 --seed 0 --budget 600000
"""
import argparse, json, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
D = "123456789"
HBAR_MULT = 1.0
NONNEG = True


def load(name, n):
    rows = [json.loads(l) for l in open(HERE / name)][:n]
    q = np.array([[D.index(c) if c != "." else -1 for c in r["question"]] for r in rows], dtype=np.int64)
    a = np.array([[D.index(c) for c in r["answer"]] for r in rows], dtype=np.int64)
    return rows, q, a


def peers_mask():
    r, c = np.divmod(np.arange(81), 9)
    b = (r // 3) * 3 + c // 3
    m = (r[:, None] == r[None]) | (c[:, None] == c[None]) | (b[:, None] == b[None])
    np.fill_diagonal(m, False)
    return m  # 81x81, 20 True per row


def hand_energy():
    W = np.zeros((81, 9, 81, 9), np.float32)
    pm = peers_mask()
    for a in range(9):
        W[:, a, :, a] = pm
    return W.reshape(729, 729), np.zeros(729, np.float32)


def onehot(x):
    return np.eye(9, dtype=np.float32)[x].reshape(len(x), 729)


def learn_energy(sol, steps=300, lr=0.05, seed=0, l1=0.0):
    """Pseudolikelihood: maximise sum_i log p(x_i | x_-i), p = softmax(-h_i), h = W x + B. Adam, full batch, digit augmentation."""
    rng = np.random.default_rng(seed)
    W = np.zeros((729, 729), np.float32)
    B = np.zeros(729, np.float32)
    blockdiag = np.kron(np.eye(81, dtype=np.float32), np.ones((9, 9), np.float32)).astype(bool)
    mW = np.zeros_like(W); vW = np.zeros_like(W); mB = np.zeros_like(B); vB = np.zeros_like(B)
    b1, b2, eps = 0.9, 0.999, 1e-8
    t0 = time.perf_counter()
    for t in range(1, steps + 1):
        perm = np.stack([rng.permutation(9) for _ in range(len(sol))])  # digit augmentation: relabel 1..9 per puzzle
        xs = np.take_along_axis(perm, sol, 1)
        X = onehot(xs)                                   # N x 729
        H = (X @ W + B).reshape(-1, 81, 9)
        P = np.exp(-(H - H.min(-1, keepdims=True))); P /= P.sum(-1, keepdims=True)
        G = (X - P.reshape(-1, 729)) / len(sol)          # d(-logPL)/dH
        gW = X.T @ G; gW = (gW + gW.T) / 2; gW[blockdiag] = 0
        gB = G.sum(0)
        for p, g, m, v in ((W, gW, mW, vW), (B, gB, mB, vB)):
            m *= b1; m += (1 - b1) * g; v *= b2; v += (1 - b2) * g * g
            p -= lr * (m / (1 - b1 ** t)) / (np.sqrt(v / (1 - b2 ** t)) + eps)
        if l1:
            W[:] = np.sign(W) * np.maximum(np.abs(W) - lr * l1, 0)
        if NONNEG:  # costs can only penalise (a valid board then has energy ~0, as in the paper's tau of about -1e-4)
            np.maximum(W, 0, out=W); np.maximum(B, 0, out=B)
    # a per-cell constant in B changes nothing (softmax is shift-invariant), so drop it: only the threshold tau moves
    B = (B.reshape(81, 9) - B.reshape(81, 9).min(1, keepdims=True)).reshape(729)
    return W, B, time.perf_counter() - t0


def energy_of(W, B, x):
    X = onehot(x)
    return 0.5 * np.einsum("ni,ij,nj->n", X, W, X) + X @ B


def search(W, B, q, sol_train, chains=4, budget=600_000, seed=0, recompute=4096, log_every=0):
    rng = np.random.default_rng(seed)
    n = len(q)
    # statistics from training solutions: mean local energy per cell, scale hbar, threshold tau
    Xt = onehot(sol_train); Ht = (Xt @ W + B).reshape(-1, 81, 9)
    loc = np.take_along_axis(Ht, sol_train[..., None], -1)[..., 0]          # Ntrain x 81
    mu = loc.mean(0)
    srt = np.sort(Ht, -1)
    # hbar = energy scale: the typical size of one learned "conflict" cost (= 1 for the hand-set energy)
    big = np.abs(W[np.abs(W) > 0.1 * np.abs(W).max()])
    hbar = float(np.median(big)) * HBAR_MULT
    tau = float(energy_of(W, B, sol_train).max())
    # batch of chains
    Q = np.repeat(q, chains, 0)
    free = Q < 0
    x = np.where(free, rng.integers(0, 9, Q.shape), Q)
    H = (onehot(x) @ W + B).reshape(-1, 81, 9)
    E = energy_of(W, B, x)
    active = np.ones(len(Q), bool)
    solved_at = np.full(n, -1); answer = [None] * n; moves_used = np.zeros(n, np.int64)
    best_E = E.copy(); best_x = x.copy()
    period = 524_288
    t_start = time.perf_counter()
    for step in range(budget):
        idx = np.flatnonzero(active)
        if len(idx) == 0:
            break
        # stopping test
        hit = idx[E[idx] <= tau + 1e-3]
        for k in hit:
            p = k // chains
            if solved_at[p] < 0:
                solved_at[p] = step; answer[p] = x[k].copy(); moves_used[p] = step * chains
            active[p * chains:(p + 1) * chains] = False
        idx = np.flatnonzero(active)
        if len(idx) == 0:
            break
        T = hbar * 0.40 * (0.31 / 0.40) ** ((step % period) / period)
        h = H[idx]                                                           # a x 81 x 9
        xl = x[idx]
        le = np.take_along_axis(h, xl[..., None], -1)[..., 0]               # local energy of current digit
        focus = free[idx] & (le - mu > 0.45 * hbar)
        anyf = focus.any(1)
        cand = np.where(anyf[:, None], focus, free[idx])
        score = rng.random(cand.shape) * cand
        cell = score.argmax(1)
        hc = h[np.arange(len(idx)), cell]                                    # a x 9
        logits = -(hc - hc.min(1, keepdims=True)) / T
        pr = np.exp(logits); pr /= pr.sum(1, keepdims=True)
        new = (pr.cumsum(1) > rng.random((len(idx), 1))).argmax(1)
        old = xl[np.arange(len(idx)), cell]
        ch = new != old
        if ch.any():
            k = idx[ch]; c = cell[ch]; o = old[ch]; nw = new[ch]
            E[k] += H[k, c, nw] - H[k, c, o]
            H[k] += (W[:, c * 9 + nw] - W[:, c * 9 + o]).T.reshape(-1, 81, 9)
            x[k, c] = nw
        if recompute and step % recompute == recompute - 1:
            H[idx] = (onehot(x[idx]) @ W + B).reshape(-1, 81, 9)
            E[idx] = energy_of(W, B, x[idx])
        better = E < best_E
        best_E[better] = E[better]; best_x[better] = x[better]
        if log_every and step % log_every == 0:
            print(f"step {step} active puzzles {len(idx) // chains} solved {int((solved_at >= 0).sum())} "
                  f"{time.perf_counter() - t_start:.1f}s", flush=True)
    secs = time.perf_counter() - t_start
    for p in range(n):
        if answer[p] is None:
            k = p * chains + int(np.argmin(best_E[p * chains:(p + 1) * chains]))
            answer[p] = best_x[k]; moves_used[p] = budget * chains
    return answer, solved_at, moves_used, secs, dict(hbar=hbar, tau=tau)


def peer_recovery(W):
    """How many of each cell's top-20 partners (by learned same-digit cost) are its true row/col/box peers?"""
    K = W.reshape(81, 9, 81, 9)
    same = np.einsum("iaja->ij", K)                     # trace of each 9x9 block = same-digit cost
    pm = peers_mask()
    top = np.argsort(-same, 1)[:, :20]
    return float(np.mean([pm[i, top[i]].mean() for i in range(81)]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--energy", default="hand")
    ap.add_argument("--ntrain", type=int, default=1000)
    ap.add_argument("--ntest", type=int, default=500)
    ap.add_argument("--test", default="test_sample.jsonl")
    ap.add_argument("--steps", type=int, default=300)
    ap.add_argument("--lr", type=float, default=0.05)
    ap.add_argument("--l1", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--budget", type=int, default=600_000)
    ap.add_argument("--log", type=int, default=20000)
    ap.add_argument("--out", default="cram_results.jsonl")
    ap.add_argument("--hbar_mult", type=float, default=1.0)
    a = ap.parse_args()
    HBAR_MULT = a.hbar_mult
    _, _, sol_tr = load("train_sample.jsonl", a.ntrain)
    rows, q, ans = load(a.test, a.ntest)
    fit = 0.0
    if a.energy == "hand":
        W, B = hand_energy()
    else:
        W, B, fit = learn_energy(sol_tr, a.steps, a.lr, a.seed, a.l1)
    rec = peer_recovery(W)
    nnz = int((np.abs(W) > 1e-3 * np.abs(W).max()).sum() // 2 + (np.abs(B) > 1e-3 * max(np.abs(B).max(), 1e-9)).sum())
    print(f"energy={a.energy} fit={fit:.2f}s peer_recovery={rec:.3f} nnz~{nnz}", flush=True)
    out, solved_at, moves, secs, st = search(W, B, q, sol_tr, budget=a.budget, seed=a.seed, log_every=a.log)
    ok = [bool((o == s).all()) for o, s in zip(out, ans)]
    stopped = int((solved_at >= 0).sum())
    wrong_stop = sum(1 for o, s, sa in zip(out, ans, solved_at) if sa >= 0 and not (o == s).all())
    res = dict(energy=a.energy, ntrain=a.ntrain, steps=a.steps, lr=a.lr, seed=a.seed, ntest=len(q), solved=sum(ok),
               stopped=stopped, wrong_stops=wrong_stop, fit_s=round(fit, 3), search_s=round(secs, 1),
               ms_per_puzzle=round(secs * 1000 / len(q), 2), median_moves=int(np.median(moves)), max_moves=int(moves.max()),
               peer_recovery=round(rec, 3), nnz=nnz, budget=a.budget, **st,
               per_puzzle=[dict(i=i, ok=o, moves=int(m)) for i, (o, m) in enumerate(zip(ok, moves))])
    with open(HERE / a.out, "a") as f:
        f.write(json.dumps(res) + "\n")
    print({k: v for k, v in res.items() if k != "per_puzzle"}, flush=True)
