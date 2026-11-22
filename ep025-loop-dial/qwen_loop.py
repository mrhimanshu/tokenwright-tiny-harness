"""Control: loop the middle layers of an ORDINARY model (Qwen2.5-1.5B-Instruct, never trained to loop), same recipe
as SenseNova (first 4 and last 4 layers once, middle block k times, shared weights). Same 60 tasks + perplexity on
the same 3 Wikipedia articles. Usage: qwen_loop.py <loops csv>"""
import copy, json, math, os, re, sys, time
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

HERE = os.path.dirname(os.path.abspath(__file__))
MID = os.environ.get("QWEN", "Qwen/Qwen2.5-1.5B-Instruct")
SYS = "Answer with only the final answer (a number or a city name). No working."
torch.set_num_threads(4)


def parse(txt):
    m = re.findall(r"-?\d[\d,]*", txt)
    return int(m[-1].replace(",", "")) if m else None


def clone(layer, idx):
    # same parameters (shared submodules), but its own layer_idx so the KV cache keeps each visit apart
    L = copy.copy(layer); L._modules = dict(layer._modules)
    att = copy.copy(layer.self_attn); att._modules = dict(layer.self_attn._modules); att.layer_idx = idx
    L._modules["self_attn"] = att
    return L


def set_loops(model, base_layers, k, head=4, tail=4):
    n = len(base_layers)
    order = list(range(head)) + list(range(head, n - tail)) * k + list(range(n - tail, n))
    model.model.layers = torch.nn.ModuleList([clone(base_layers[i], j) for j, i in enumerate(order)])
    model.config.num_hidden_layers = len(order)
    if getattr(model.config, "layer_types", None):
        model.config.layer_types = [model.config.layer_types[0]] * len(order)
    return len(order)


@torch.no_grad()
def ppl(model, tok, path, ctx=512, chunks=3):
    ids = tok(open(path).read(), return_tensors="pt").input_ids[0][: ctx * chunks]
    nll, cnt = 0.0, 0
    for c in range(chunks):
        x = ids[c * ctx:(c + 1) * ctx].unsqueeze(0)
        logits = model(x, use_cache=False).logits[0, :-1].float()
        lp = torch.log_softmax(logits, -1)
        tgt = x[0, 1:]
        # score only the second half of each chunk (like llama-perplexity)
        half = ctx // 2
        nll -= lp[half - 1:].gather(1, tgt[half - 1:, None]).sum().item()
        cnt += len(tgt[half - 1:])
    return math.exp(nll / cnt)


@torch.no_grad()
def answer(model, tok, q):
    msgs = [{"role": "system", "content": SYS}, {"role": "user", "content": q}]
    x = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt")
    if not torch.is_tensor(x):
        x = x["input_ids"]
    out = model.generate(x, max_new_tokens=40, do_sample=False, use_cache=True, stop_strings=["\n"], tokenizer=tok)
    return tok.decode(out[0, x.shape[1]:], skip_special_tokens=True)


def main():
    loops = [int(v) for v in sys.argv[1].split(",")]
    tok = AutoTokenizer.from_pretrained(MID)
    model = AutoModelForCausalLM.from_pretrained(MID, dtype=torch.float32)
    model.eval()
    base = list(model.model.layers)
    tasks = [json.loads(l) for l in open(os.path.join(HERE, "tasks.jsonl"))]
    tag = MID.split("/")[-1].lower()
    for k in loops:
        depth = set_loops(model, base, k)
        for art in ([] if str(k) in os.environ.get("SKIP_PPL", "").split(",") else ("Lighthouse", "Sourdough", "Tardigrade")):
            t0 = time.time()
            p = ppl(model, tok, os.path.join(HERE, "text", f"{art}.txt"))
            row = dict(model=tag, loops=k, depth=depth, article=art, ppl=round(p, 3), wall_s=round(time.time() - t0, 1))
            open(os.path.join(HERE, "ppl_results.jsonl"), "a").write(json.dumps(row) + "\n")
            print(row, flush=True)
        for t in tasks:
            t0 = time.time()
            txt = answer(model, tok, t["q"])
            row = dict(model=tag, loops=k, depth=depth, id=t["id"], set=t["set"], kind=t["kind"], gold=t["a"], out=txt,
                       pred=parse(txt), ok=(t["a"].lower() in txt.lower()) if isinstance(t["a"], str) else parse(txt) == t["a"], wall_s=round(time.time() - t0, 2))
            open(os.path.join(HERE, "results.jsonl"), "a").write(json.dumps(row) + "\n")
            print(k, t["id"], row["ok"], repr(txt[:30]), flush=True)


if __name__ == "__main__":
    main()
