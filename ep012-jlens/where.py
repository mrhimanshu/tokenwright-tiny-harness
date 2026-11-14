"""Where (token, layer) do the watched words hit lens rank 1-5? From topk/ dumps. Prints context + the top-5 there."""
import os, sys, torch, transformers
HERE = os.path.dirname(os.path.abspath(__file__))
tok = transformers.AutoTokenizer.from_pretrained("Qwen/Qwen3-1.7B")
BAND = list(range(9, 23))
words = sys.argv[1].split(",") if len(sys.argv) > 1 else ["blackmail", "secret", "shutdown", "scenario", "fake", "fictional"]
K = int(sys.argv[2]) if len(sys.argv) > 2 else 1
for w in words:
    ids = {tok.encode(v, add_special_tokens=False)[0] for v in [" " + w, w, " " + w.capitalize(), w.capitalize()] if len(tok.encode(v, add_special_tokens=False)) == 1}
    for vi in range(3):
        for cond in ["full", "no_affair", "no_wipe"]:
            for mode in ["jlens", "logit"]:
                d = torch.load(os.path.join(HERE, "topk", f"{vi}_{cond}_{mode}.pt"))
                top = d["top"][:, :, :K]
                m = torch.zeros(top.shape[:2], dtype=torch.bool)
                for i in ids:
                    m |= (top == i).any(-1)
                pos = sorted(set(m.nonzero()[:, 1].tolist()))
                if not pos:
                    continue
                print(f"{w} v{vi} {cond} {mode}: {len(pos)} positions")
                for p in pos[:6]:
                    ls = [BAND[l] for l in m[:, p].nonzero()[:, 0].tolist()]
                    ctx = tok.decode(d["ids"][max(0, p - 8):p + 1].tolist()).replace("\n", " | ")
                    t5 = [tok.decode([t]) for t in d["top"][ls[0] - 9, p, :5].tolist()]
                    print(f"   pos {p} seg {int(d['seg_of'][p])} layers {ls}  ...{ctx!r}  top5@L{ls[0]} {t5}")
