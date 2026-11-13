"""EP010 lab: Deletion Tuning vs full fine-tuning on a Mac (Qwen2.5-0.5B-Instruct, MMLU-Pro SFT, Apple MPS).

A compact re-implementation of the paper's SFT recipe (arXiv 2611.10866; official code
github.com/agentic-learning-ai-lab/deleting-weights, MIT licence, scripts/train_sft.sh):
- mask = one fp32 logit per gate_proj weight, soft sigmoid(sharpness * logit) while training,
  hard (logit > 0) at eval; sharpness 100 -> 1000 linearly; logits ~ N(0, 0.01^2) shifted by
  +-3 std from Wanda scores so 0.0488% start deleted; AdamW lr 5e-4, 400 steps, batch 4;
  regulariser - 1e-5 * (1 - t/T) * sum ||W * mask||^2; grad clip 1.0.
- FFT baseline: every weight trains, AdamW lr 3e-6, 400 steps, batch 4 (paper's MMLU-Pro setting).
- Data: MMLU-Pro test split, per category 25% test / 75% train after a seeded shuffle;
  sample = "{question}\n{answer text}", loss on the answer tokens only; evaluation scores every
  option by its mean answer-token loss and picks the lowest.
Deviations (laptop): Qwen2.5-0.5B-Instruct instead of Llama-3.2-1B; fp32 instead of bf16 autocast;
samples longer than 512 tokens dropped; right padding.
"""
import argparse, json, math, os, random, time
import numpy as np
import torch, torch.nn as nn, torch.nn.functional as F
import zstandard as zstd
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
DEV = "mps"
MAX_LEN = 512
HERE = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------- data
def load_splits(tok, task, seed, eval_ratio=0.25):
    ds = load_dataset("TIGER-Lab/MMLU-Pro")["test"]
    qs = [{"q": d["question"], "opts": d["options"], "ans": d["options"][d["answer_index"]], "qid": d["question_id"]}
          for d in ds if d["category"] == task]
    random.seed(seed); random.shuffle(qs)
    n_test = math.ceil(len(qs) * eval_ratio)
    test, train = qs[:n_test], qs[n_test:]
    random.seed(seed); random.shuffle(train)
    delim = tok("\n", add_special_tokens=False)["input_ids"]

    def enc(q, a):
        p = tok(q, add_special_tokens=False, truncation=True, max_length=1024)["input_ids"] + delim
        a = tok(a, add_special_tokens=False, truncation=True, max_length=1024)["input_ids"]
        if len(p) + len(a) > MAX_LEN or len(a) == 0:
            return None
        return {"ids": p + a, "n_prompt": len(p)}

    train_s = [s for s in (enc(x["q"], x["ans"]) for x in train) if s]
    test_items = []
    for x in test:
        opts = [enc(x["q"], o) for o in x["opts"]]
        if None in opts:
            continue
        test_items.append({"qid": x["qid"], "opts": opts, "correct": x["opts"].index(x["ans"]), "texts": x["opts"],
                           "question": x["q"]})
    return train_s, test_items


def collate(samples, pad_id):
    L = max(len(s["ids"]) for s in samples)
    ids = torch.full((len(samples), L), pad_id, dtype=torch.long)
    att = torch.zeros((len(samples), L), dtype=torch.long)
    lab = torch.full((len(samples), L), -100, dtype=torch.long)
    for i, s in enumerate(samples):
        n = len(s["ids"])
        ids[i, :n] = torch.tensor(s["ids"]); att[i, :n] = 1
        lab[i, s["n_prompt"]:n] = torch.tensor(s["ids"][s["n_prompt"]:])
    return ids.to(DEV), att.to(DEV), lab.to(DEV)


def answer_token_losses(model, ids, att, lab):
    """Per-sample mean CE over answer tokens, computing lm_head only at answer positions."""
    h = model.model(input_ids=ids, attention_mask=att).last_hidden_state  # [B, L, d]
    tgt = lab[:, 1:]
    sel = tgt != -100
    hs = h[:, :-1][sel]                     # [N, d]
    logits = model.lm_head(hs).float()
    ce = F.cross_entropy(logits, tgt[sel], reduction="none")
    row = sel.nonzero()[:, 0]
    sums = torch.zeros(ids.shape[0], device=ids.device).index_add_(0, row, ce)
    cnt = torch.zeros(ids.shape[0], device=ids.device).index_add_(0, row, torch.ones_like(ce))
    return sums / cnt


# ---------------------------------------------------------------- mask
class MaskedLinear(nn.Module):
    def __init__(self, lin, s0, s1, total):
        super().__init__()
        self.weight = nn.Parameter(lin.weight.data, requires_grad=False)
        self.gate = nn.Parameter(torch.randn(lin.weight.shape, device=lin.weight.device, dtype=torch.float32) * 0.01)
        self.s0, self.s1, self.total, self.step_i = s0, s1, total, 0
        self.hard = False
        self.reg = None
        self.collect = None  # Wanda activation norms

    def sharp(self):
        return self.s0 + (self.s1 - self.s0) * min(self.step_i / self.total, 1.0)

    def forward(self, x):
        if self.collect is not None:
            self.collect += x.detach().float().pow(2).sum(dim=tuple(range(x.dim() - 1))).sqrt()
            return F.linear(x, self.weight)
        if self.hard:
            return F.linear(x, self.weight * (self.gate > 0).to(self.weight.dtype))
        m = torch.sigmoid(self.gate * self.sharp())
        if torch.is_grad_enabled():
            self.reg = (self.weight.detach() * m).pow(2).sum()
        return F.linear(x, self.weight * m)


def masked_layers(model):
    return [m for m in model.modules() if isinstance(m, MaskedLinear)]


def convert(model, s0, s1, total):
    for layer in model.model.layers:
        layer.mlp.gate_proj = MaskedLinear(layer.mlp.gate_proj, s0, s1, total)
    return masked_layers(model)


def wanda_init(model, layers, train_s, pad_id, init_sparsity, prior):
    for m in layers:
        m.collect = torch.zeros(m.weight.shape[1], device=DEV)
    with torch.no_grad():
        for s in train_s:  # one at a time = no padding in the norms
            ids, att, _ = collate([s], pad_id)
            model.model(input_ids=ids, attention_mask=att)
    for m in layers:
        score = (m.weight.detach().float().abs() * m.collect.unsqueeze(0)).flatten().cpu()
        k = max(1, int(score.numel() * init_sparsity))
        thr = score.kthvalue(k).values.item()
        dele = (score < thr).view(m.weight.shape).to(DEV)
        sign = torch.where(dele, -1.0, 1.0)
        with torch.no_grad():
            m.gate += sign * m.gate.std() * prior
        m.collect = None


def mask_stats(layers):
    masks = [(m.gate > 0).cpu() for m in layers]
    total = sum(x.numel() for x in masks)
    deleted = sum(int((~x).sum()) for x in masks)
    cctx = zstd.ZstdCompressor(level=3)
    comp = sum(len(cctx.compress(np.packbits(x.numpy().ravel()).tobytes())) for x in masks)
    return {"gate_weights": total, "deleted": deleted, "mask_bytes_zstd": comp}, masks


# ---------------------------------------------------------------- eval
@torch.no_grad()
def evaluate(model, items, pad_id, bs=20):
    model.eval()
    flat = [(i, j, o) for i, it in enumerate(items) for j, o in enumerate(it["opts"])]
    flat.sort(key=lambda t: len(t[2]["ids"]))
    losses = {}
    for b in range(0, len(flat), bs):
        chunk = flat[b:b + bs]
        ids, att, lab = collate([c[2] for c in chunk], pad_id)
        l = answer_token_losses(model, ids, att, lab).cpu().tolist()
        for (i, j, _), v in zip(chunk, l):
            losses[(i, j)] = v
    preds = []
    for i, it in enumerate(items):
        ls = [losses[(i, j)] for j in range(len(it["opts"]))]
        preds.append(int(np.argmin(ls)))
    acc = float(np.mean([p == it["correct"] for p, it in zip(preds, items)]))
    return acc, preds


@torch.no_grad()
def kl_to_base(model, base, texts_ids, pad_id):
    """Mean per-token KL(base || model) over held-out text (full-vocab next-token distributions)."""
    model.eval()
    tot, n = 0.0, 0
    for s in texts_ids:
        ids = torch.tensor([s], device=DEV)
        lp = F.log_softmax(model(input_ids=ids).logits.float(), -1)
        lq = F.log_softmax(base(input_ids=ids).logits.float(), -1)
        kl = (lq.exp() * (lq - lp)).sum(-1)
        tot += kl.sum().item(); n += kl.numel()
    return tot / n


# ---------------------------------------------------------------- train
def train(model, params, train_s, pad_id, steps, bs, lr, seed, layers=None, weight_reg=0.0, log=None):
    opt = torch.optim.AdamW(params, lr=lr, weight_decay=0.0)
    rng = random.Random(seed)
    order = []
    model.train()
    t0 = time.time(); hist = []
    for step in range(steps):
        if len(order) < bs:
            order += rng.sample(range(len(train_s)), len(train_s))
        batch = [train_s[order.pop()] for _ in range(bs)]
        ids, att, lab = collate(batch, pad_id)
        ce = answer_token_losses(model, ids, att, lab).mean()
        loss = ce
        if layers and weight_reg > 0:
            loss = loss - weight_reg * (1 - step / steps) * sum(m.reg for m in layers)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step(); opt.zero_grad(set_to_none=True)
        if layers:
            for m in layers:
                m.step_i += 1
        if (step + 1) % 20 == 0:
            hist.append({"step": step + 1, "ce": round(ce.item(), 4), "t": round(time.time() - t0, 1)})
            if log:
                log(f"  step {step+1}/{steps} ce={ce.item():.4f} t={time.time()-t0:.0f}s")
    model.eval()
    return time.time() - t0, hist


def load_model():
    m = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float32).to(DEV)
    for p in m.parameters():
        p.requires_grad_(False)
    m.eval()
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--retention_task", default="history")
    ap.add_argument("--steps", type=int, default=400)
    ap.add_argument("--methods", default="base,wanda,dt,random,fft")
    ap.add_argument("--max_test", type=int, default=0)
    ap.add_argument("--out", default=os.path.join(HERE, "results.jsonl"))
    a = ap.parse_args()

    torch.manual_seed(a.seed)
    tok = AutoTokenizer.from_pretrained(MODEL)
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    train_s, test_items = load_splits(tok, a.task, a.seed)
    _, ret_items = load_splits(tok, a.retention_task, 0)
    if a.max_test:
        test_items = test_items[:a.max_test]
    ret_items = ret_items[:60]
    kl_texts = [it["opts"][it["correct"]]["ids"][:256] for it in ret_items[:40]]
    logf = open(os.path.join(HERE, f"log_{a.task}_s{a.seed}.txt"), "a")

    def log(msg):
        print(msg, flush=True); logf.write(msg + "\n"); logf.flush()

    def emit(rec):
        rec.update({"task": a.task, "seed": a.seed, "model": MODEL, "n_train": len(train_s), "n_test": len(test_items),
                    "retention_task": a.retention_task, "n_retention": len(ret_items), "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        with open(a.out, "a") as f:
            f.write(json.dumps(rec) + "\n")
        log("RESULT " + json.dumps({k: v for k, v in rec.items() if k not in ("preds", "ret_preds", "hist")}))

    log(f"== {a.task} seed {a.seed}: train {len(train_s)} test {len(test_items)} retention {len(ret_items)}")
    methods = a.methods.split(",")
    base = load_model()
    n_params = sum(p.numel() for p in base.parameters())

    if "base" in methods:
        t = time.time(); acc, preds = evaluate(base, test_items, pad); r_acc, r_preds = evaluate(base, ret_items, pad)
        emit({"method": "base", "acc": acc, "ret_acc": r_acc, "kl": 0.0, "eval_s": round(time.time() - t, 1),
              "preds": preds, "ret_preds": r_preds, "n_params": n_params})

    dt_deleted_per_layer = None
    if any(x in methods for x in ("wanda", "dt", "random")):
        model = load_model()
        layers = convert(model, 100.0, 1000.0, a.steps)
        torch.manual_seed(a.seed)
        for m in layers:
            m.gate.data = torch.randn_like(m.gate) * 0.01
        t = time.time()
        wanda_init(model, layers, train_s, pad, 0.00048828125, 3.0)
        log(f"wanda init {time.time()-t:.0f}s")
        for m in layers:
            m.hard = True
        if "wanda" in methods:
            st, _ = mask_stats(layers)
            acc, preds = evaluate(model, test_items, pad); r_acc, r_preds = evaluate(model, ret_items, pad)
            emit({"method": "wanda_only", "acc": acc, "ret_acc": r_acc, "kl": kl_to_base(model, base, kl_texts, pad),
                  "preds": preds, "ret_preds": r_preds, **st, "n_params": n_params})
        if "dt" in methods:
            for m in layers:
                m.hard = False
                m.gate.requires_grad_(True)
            params = [m.gate for m in layers]
            if DEV == "mps":
                torch.mps.empty_cache()
            secs, hist = train(model, params, train_s, pad, a.steps, 4, 5e-4, a.seed, layers=layers, weight_reg=1e-5, log=log)
            for m in layers:
                m.hard = True
                m.gate.requires_grad_(False)
            st, masks = mask_stats(layers)
            dt_deleted_per_layer = [int((~x).sum()) for x in masks]
            acc, preds = evaluate(model, test_items, pad); r_acc, r_preds = evaluate(model, ret_items, pad)
            emit({"method": "deletion_tuning", "acc": acc, "ret_acc": r_acc, "kl": kl_to_base(model, base, kl_texts, pad),
                  "train_s": round(secs, 1), "hist": hist, "preds": preds, "ret_preds": r_preds, **st,
                  "trainable": sum(p.numel() for p in params), "n_params": n_params,
                  "peak_mem_gb": round(torch.mps.driver_allocated_memory() / 1e9, 2)})
            torch.save({"masks_packed": [np.packbits(x.numpy().ravel()) for x in masks]},
                       os.path.join(HERE, "runs", f"mask_{a.task}_s{a.seed}.pt")) if os.path.isdir(os.path.join(HERE, "runs")) else None
        if "random" in methods and dt_deleted_per_layer is not None:
            g = torch.Generator().manual_seed(1000 + a.seed)
            for m, k in zip(layers, dt_deleted_per_layer):
                idx = torch.randperm(m.gate.numel(), generator=g)[:k]
                gate = torch.ones(m.gate.numel())
                gate[idx] = -1.0
                m.gate.data = gate.view(m.gate.shape).to(DEV)
            st, _ = mask_stats(layers)
            acc, preds = evaluate(model, test_items, pad); r_acc, r_preds = evaluate(model, ret_items, pad)
            emit({"method": "random_deletion", "acc": acc, "ret_acc": r_acc, "kl": kl_to_base(model, base, kl_texts, pad),
                  "preds": preds, "ret_preds": r_preds, **st, "n_params": n_params})
        del model, layers
        torch.mps.empty_cache()

    if "fft" in methods:
        # Memory (24 GB Mac, other apps open): the first version kept the base model resident during FFT and
        # swapped (20 steps took 268 s). Now: free the base copy, train with gradient checkpointing, reload base after.
        del base
        torch.mps.empty_cache()
        model = load_model()
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        model.config.use_cache = False
        params = list(model.parameters())
        for p in params:
            p.requires_grad_(True)
        secs, hist = train(model, params, train_s, pad, a.steps, 4, 3e-6, a.seed, log=log)
        peak = round(torch.mps.driver_allocated_memory() / 1e9, 2)
        for p in params:
            p.requires_grad_(False)
        del params
        torch.mps.empty_cache()
        acc, preds = evaluate(model, test_items, pad); r_acc, r_preds = evaluate(model, ret_items, pad)
        base = load_model()
        with torch.no_grad():
            changed = sum(int((p != q).sum()) for p, q in zip(model.parameters(), base.parameters()))
        emit({"method": "full_finetune", "acc": acc, "ret_acc": r_acc, "kl": kl_to_base(model, base, kl_texts, pad),
              "train_s": round(secs, 1), "hist": hist, "preds": preds, "ret_preds": r_preds,
              "trainable": n_params, "weights_changed": changed, "n_params": n_params,
              "ckpt_bytes_bf16": n_params * 2, "ckpt_bytes_fp32": n_params * 4, "grad_checkpointing": True,
              "peak_mem_gb": peak})


if __name__ == "__main__":
    main()
