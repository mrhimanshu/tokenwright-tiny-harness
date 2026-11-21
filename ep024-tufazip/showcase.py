# Per-token bits for one real enwik9 sentence (for the "prediction = compression" scene).
import json, math, torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from common import read_slice
P = json.load(open("models.json"))["HuggingFaceTB/SmolLM2-135M"]["path"]
tok = AutoTokenizer.from_pretrained(P); m = AutoModelForCausalLM.from_pretrained(P, dtype=torch.float32).eval()
text = read_slice(10_000_000, 65536).decode()
i = text.find("In [[geology]], the word")
ctx = text[max(0, i - 1500):i]; tgt = text[i:i + 114]
a = tok(ctx, add_special_tokens=False)["input_ids"]; b = tok(tgt, add_special_tokens=False)["input_ids"]
ids = torch.tensor([a + b])
with torch.no_grad(): lp = torch.log_softmax(m(ids).logits[0], -1)
rows = []
for k, t in enumerate(b):
    pos = len(a) + k
    p = lp[pos - 1].exp(); top = int(p.argmax())
    rows.append(dict(tok=tok.decode([t]), bits=round(-lp[pos - 1, t].item() / math.log(2), 3),
                     p=round(p[t].item(), 4), top=tok.decode([top])))
json.dump(dict(text=tgt, rows=rows), open("showcase.json", "w"), indent=1)
for r in rows: print(repr(r["tok"]), r["bits"], r["p"], repr(r["top"]))
