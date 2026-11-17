"""EP016 lab 1: how wrong are everyday FP32 KL / JSD implementations when two distributions are nearly equal?
Reference = mpmath (40-80 digits) on the exact same float32-stored logits (as in Amos, arXiv 2611.18511, App. A).
Writes lab/audit.jsonl (one row per case x h x impl) and prints a summary.
"""
import json, math, sys, time
import numpy as np
import torch, torch.nn.functional as F
import mpmath as mp
import scipy, scipy.stats, scipy.special
from scipy.spatial.distance import jensenshannon

torch.set_num_threads(4)
OUT = None  # opened in __main__ only (importing this module must not touch the results file)


# ---------- reference (high precision) ----------
def ref(zr32, z32, dps):
    mp.mp.dps = dps
    zr = [mp.mpf(float(x)) for x in zr32]; z = [mp.mpf(float(x)) for x in z32]
    def lsm(v):
        m = max(v); lse = m + mp.log(mp.fsum(mp.e ** (x - m) for x in v)); return [x - lse for x in v]
    lp, lq = lsm(zr), lsm(z)
    p = [mp.e ** x for x in lp]; q = [mp.e ** x for x in lq]
    kl = mp.fsum(pi * (a - b) for pi, a, b in zip(p, lp, lq))           # KL(p||q)
    m_ = [(a + b) / 2 for a, b in zip(p, q)]
    jsd = mp.fsum(pi * mp.log(pi / mi) for pi, mi in zip(p, m_)) / 2 + mp.fsum(qi * mp.log(qi / mi) for qi, mi in zip(q, m_)) / 2
    grad = [float(b - a) for a, b in zip(p, q)]                          # d KL(p||q) / dz = q - p
    return float(kl), float(jsd), np.array(grad)


# ---------- the fix (paper, reformulation 1 + 2, ported from its JAX listings to torch) ----------
def e2(x, degree=12, cutoff=0.5):
    poly = torch.full_like(x, 1 / math.factorial(degree))
    for k in range(degree - 1, 1, -1):
        poly = 1 / math.factorial(k) + x * poly
    return torch.where(x.abs() < cutoff, x * x * poly, torch.expm1(x) - x)


def categorical(z, zr):
    lp, lq = F.log_softmax(zr, -1), F.log_softmax(z, -1)
    p, q = lp.exp(), lq.exp()
    d = z - zr; d = d - d[..., :1]
    d = d - (p * d).sum(-1, keepdim=True)
    s = d - torch.log1p((p * torch.expm1(d)).sum(-1, keepdim=True))
    return p, q, s


class FwdKLFixed(torch.autograd.Function):
    @staticmethod
    def forward(ctx, z, zr):
        p, q, s = categorical(z, zr)
        u = p * torch.expm1(s)
        ctx.save_for_backward(u - q * u.sum(-1, keepdim=True))
        return (p * e2(s)).sum(-1)

    @staticmethod
    def backward(ctx, g):
        (gr,) = ctx.saved_tensors
        return g[..., None] * gr, None


def jsd_fixed(z, zr, beta=0.5):
    p, q, s = categorical(z, zr)
    hq = -torch.log1p(beta * torch.expm1(-s))
    return (beta * p * e2(s - hq) + (1 - beta) * q * e2(-hq)).sum(-1)


# ---------- everyday implementations (what people actually write / call) ----------
def kl_naive(z, zr):           # textbook: sum p (log p - log q) with log_softmax
    lp, lq = F.log_softmax(zr, -1), F.log_softmax(z, -1)
    return (lp.exp() * (lp - lq)).sum(-1)

def kl_torch_logtarget(z, zr):  # F.kl_div(input=log q, target=log p, log_target=True)
    return F.kl_div(F.log_softmax(z, -1), F.log_softmax(zr, -1), reduction="sum", log_target=True)

def kl_torch_probtarget(z, zr):  # the classic distillation line: F.kl_div(log_softmax(student), softmax(teacher))
    return F.kl_div(F.log_softmax(z, -1), F.softmax(zr, -1), reduction="sum")

def kl_torch_dist(z, zr):
    return torch.distributions.kl_divergence(torch.distributions.Categorical(logits=zr), torch.distributions.Categorical(logits=z))

def kl_naive_bf16(z, zr):
    return kl_naive(z.bfloat16(), zr.bfloat16()).float()

def kl_fixed(z, zr):
    return FwdKLFixed.apply(z, zr)

def jsd_naive(z, zr):
    p, q = F.softmax(zr, -1), F.softmax(z, -1); m = (p + q) / 2
    return 0.5 * (p * (p.log() - m.log())).sum(-1) + 0.5 * (q * (q.log() - m.log())).sum(-1)

KL_IMPLS = {"naive_fp32": kl_naive, "torch_kl_div_logtarget": kl_torch_logtarget, "torch_kl_div_probtarget": kl_torch_probtarget,
            "torch_distributions": kl_torch_dist, "naive_bf16": kl_naive_bf16, "fixed_fp32": kl_fixed}


def scipy_kl(z, zr):  # scipy on the float32 probabilities a PyTorch pipeline hands it
    p = F.softmax(zr, -1).numpy(); q = F.softmax(z, -1).numpy()
    return float(scipy.stats.entropy(p, q))

def scipy_jsd(z, zr):
    p = F.softmax(zr, -1).numpy(); q = F.softmax(z, -1).numpy()
    return float(jensenshannon(p, q)) ** 2


def run_case(case, zr, z, h, dps):
    kl_t, jsd_t, g_t = ref(zr.numpy(), z.numpy(), dps)
    rows = []
    for name, fn in KL_IMPLS.items():
        zz = z.clone().requires_grad_(True)
        v = fn(zz, zr); v.backward()
        g = zz.grad.numpy().astype(np.float64)
        gerr = float(np.linalg.norm(g - g_t) / np.linalg.norm(g_t)) if np.linalg.norm(g_t) > 0 else float(np.linalg.norm(g))
        rows.append(dict(case=case, h=h, kind="kl", impl=name, value=float(v), true=kl_t, grad_rel_err=gerr))
    rows.append(dict(case=case, h=h, kind="kl", impl="scipy_entropy", value=scipy_kl(z, zr), true=kl_t, grad_rel_err=None))
    for name, fn in {"naive_fp32": jsd_naive, "fixed_fp32": jsd_fixed}.items():
        rows.append(dict(case=case, h=h, kind="jsd", impl=name, value=float(fn(z, zr)), true=jsd_t, grad_rel_err=None))
    rows.append(dict(case=case, h=h, kind="jsd", impl="scipy_jensenshannon_sq", value=scipy_jsd(z, zr), true=jsd_t, grad_rel_err=None))
    for r in rows:
        r["rel_err"] = abs(r["value"] - r["true"]) / r["true"] if r["true"] > 0 else abs(r["value"])
        r["negative"] = r["value"] < 0
        OUT.write(json.dumps(r) + "\n")
    OUT.flush()
    return rows


if __name__ == "__main__":
    OUT = open(sys.argv[1] if len(sys.argv) > 1 else "lab/audit.jsonl", "w")
    t0 = time.time()
    print("torch", torch.__version__, "scipy", scipy.__version__)
    HS = [1e-1, 3e-2, 1e-2, 3e-3, 1e-3, 3e-4, 1e-4, 3e-5, 1e-5, 3e-6, 1e-6]
    # case A: the paper's toy (3 categories), z = (-1, h, 1) vs z_ref = (-1, 0, 1)
    zr = torch.tensor([-1.0, 0.0, 1.0])
    for h in HS + [1e-7, 1e-8]:
        run_case("toy3", zr, torch.tensor([-1.0, h, 1.0]), h, 80)
    # case B: LLM-sized: 32,000-token vocabulary, teacher logits ~ N(0, 3^2), student = teacher + h * noise; 3 seeds
    for seed in range(3):
        g = torch.Generator().manual_seed(seed)
        zr = (3 * torch.randn(32000, generator=g)).float()
        noise = torch.randn(32000, generator=g)
        for h in HS:
            run_case(f"vocab32k_s{seed}", zr, (zr + h * noise).float(), h, 40)
        print("seed", seed, "done", round(time.time() - t0), "s", flush=True)
    # case C: identical logits (true KL = 0, true gradient = 0): what do the gradients say?
    for seed in range(3):
        g = torch.Generator().manual_seed(100 + seed)
        zr = (3 * torch.randn(32000, generator=g)).float()
        for name, fn in KL_IMPLS.items():
            zz = zr.clone().requires_grad_(True); v = fn(zz, zr); v.backward()
            OUT.write(json.dumps(dict(case=f"identical32k_s{seed}", h=0, kind="kl", impl=name, value=float(v), true=0.0,
                                      grad_norm=float(zz.grad.norm()), grad_max=float(zz.grad.abs().max()),
                                      grad_nonzero=int((zz.grad != 0).sum()))) + "\n")
    OUT.close()
    print("done", round(time.time() - t0), "s")
