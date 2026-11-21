# tufazip's core idea at toy scale: a byte-level transformer that starts from RANDOM weights and learns
# while it compresses. Each chunk is first scored with the current weights (= its arithmetic-code length,
# which a decoder running the same steps can reproduce), then the model trains on it (+1 replay step).
# Usage: online_zip.py <slice_bytes> <tag> [offsets...]
import sys, time, math, json, random, torch, torch.nn as nn, torch.nn.functional as F
from common import OFFSETS, read_slice, log
torch.set_num_threads(4); torch.manual_seed(0); random.seed(0)
N = int(sys.argv[1]); TAG = sys.argv[2]; offs = [int(x) for x in sys.argv[3:]] or OFFSETS
import os
CTX, NEW, B = 64, 192, int(os.environ.get("B", 16))   # each row: 64 bytes of earlier context + 192 new bytes to code
LR = float(os.environ.get("LR", 1e-3)); REPLAY = int(os.environ.get("REPLAY", 1)); OUT = os.environ.get("OUT", "results.jsonl")
torch.set_num_threads(int(os.environ.get("THREADS", 4)))
D, LAYERS, HEADS = int(os.environ.get("D", 256)), int(os.environ.get("LAYERS", 4)), 4
class Block(nn.Module):
    def __init__(s):
        super().__init__(); s.n1 = nn.LayerNorm(D); s.att = nn.MultiheadAttention(D, HEADS, batch_first=True)
        s.n2 = nn.LayerNorm(D); s.mlp = nn.Sequential(nn.Linear(D, 4 * D), nn.GELU(), nn.Linear(4 * D, D))
    def forward(s, x, mask):
        h = s.n1(x); x = x + s.att(h, h, h, attn_mask=mask, need_weights=False)[0]; return x + s.mlp(s.n2(x))
class Net(nn.Module):
    def __init__(s):
        super().__init__(); s.emb = nn.Embedding(257, D); s.pos = nn.Embedding(CTX + NEW + 1, D)
        s.blocks = nn.ModuleList(Block() for _ in range(LAYERS)); s.out = nn.Linear(D, 256); s.nf = nn.LayerNorm(D)
    def forward(s, x):
        T = x.shape[1]; mask = torch.triu(torch.ones(T, T, dtype=torch.bool), 1)
        h = s.emb(x) + s.pos(torch.arange(T))
        for b in s.blocks: h = b(h, mask)
        return s.out(s.nf(h))
def rows(data, start):  # build B rows of new bytes starting at `start`
    X, Y = [], []
    for r in range(B):
        a = start + r * NEW
        if a >= len(data): break
        ctx = data[max(0, a - CTX):a]; new = data[a:a + NEW]
        seq = [256] + list(ctx) + list(new)          # 256 = start symbol
        X.append(seq[:-1]); Y.append((len(ctx), list(new)))
    L = max(len(x) for x in X)
    Xp = torch.full((len(X), L), 256, dtype=torch.long); Tgt = torch.full((len(X), L), -100, dtype=torch.long)
    for i, (x, (c, new)) in enumerate(zip(X, Y)):
        Xp[i, :len(x)] = torch.tensor(x); Tgt[i, c:c + len(new)] = torch.tensor(new)
    return Xp, Tgt
for off in offs:
    data = read_slice(off, N); net = Net(); opt = torch.optim.Adam(net.parameters(), lr=LR)
    params = sum(p.numel() for p in net.parameters())
    bits = 0.0; t0 = time.time(); curve = []; seen = []; pos = 0; step = 0
    while pos < len(data):
        X, T = rows(data, pos); n_new = int((T != -100).sum())
        net.eval()
        with torch.no_grad():
            cb = F.cross_entropy(net(X).reshape(-1, 256), T.reshape(-1), reduction="sum").item() / math.log(2)
        bits += cb; net.train()
        for (Xs, Ts) in [(X, T)] + (random.sample(seen, min(REPLAY, len(seen))) if seen else []):   # learn: this chunk + 1 replay
            loss = F.cross_entropy(net(Xs).reshape(-1, 256), Ts.reshape(-1)); opt.zero_grad(); loss.backward(); opt.step()
        seen.append((X, T)); pos += n_new; step += 1
        if step % 10 == 0 or pos >= len(data): curve.append([pos, round(cb / n_new, 4), round(bits / pos, 4)])
    dt = time.time() - t0
    rec = dict(method="online_from_scratch", tag=TAG, D=D, layers=LAYERS, B=B, lr=LR, replay=REPLAY, params=params, offset=off, bytes=len(data), bits=bits,
               bpb=bits / len(data), seconds=dt, bytes_per_s=len(data) / dt, curve=curve)
    log(OUT, rec); print(json.dumps({k: v for k, v in rec.items() if k != "curve"}), flush=True)
