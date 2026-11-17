"""Accurate KL(p || q) from logits when p and q are nearly equal (float32-safe), ported to PyTorch from
Brandon Amos, "On numerical issues of divergences between nearly equal distributions", arXiv:2611.18511 (reformulations 1 + 2).
p = softmax(z_ref) is the fixed teacher/reference, q = softmax(z) is the student. Last dim = vocabulary.
Only valid when the two are close (the paper's guard: max(z - z_ref) - min(z - z_ref) <= 0.5); fall back to the usual formula otherwise.
"""
import math
import torch
import torch.nn.functional as F


def e2(x, degree=12, cutoff=0.5):
    """exp(x) - 1 - x without cancellation: Taylor series x^2 (1/2 + x/6 + ...) near 0."""
    poly = torch.full_like(x, 1 / math.factorial(degree))
    for k in range(degree - 1, 1, -1):
        poly = 1 / math.factorial(k) + x * poly
    return torch.where(x.abs() < cutoff, x * x * poly, torch.expm1(x) - x)


class _KLFixed(torch.autograd.Function):
    @staticmethod
    def forward(ctx, z, z_ref):
        p, q = F.softmax(z_ref, -1), F.softmax(z, -1)
        d = z - z_ref                                    # logit difference: exact when z ~ z_ref
        d = d - d[..., :1]
        d = d - (p * d).sum(-1, keepdim=True)
        s = d - torch.log1p((p * torch.expm1(d)).sum(-1, keepdim=True))   # log q - log p, rebuilt
        u = p * torch.expm1(s)                           # = q - p, without subtracting two softmaxes
        ctx.save_for_backward(u - q * u.sum(-1, keepdim=True))
        return (p * e2(s)).sum(-1)                       # every term >= 0: nothing cancels

    @staticmethod
    def backward(ctx, g):
        (grad,) = ctx.saved_tensors
        return g[..., None] * grad, None


def kl_fixed(z, z_ref, limit=0.5):
    """KL(softmax(z_ref) || softmax(z)) per row. Raises if the logits are not close enough for the reformulation."""
    span = (z - z_ref).amax(-1) - (z - z_ref).amin(-1)
    if not bool(torch.isfinite(span).all() and (span <= limit).all()):
        raise ValueError("kl_fixed needs nearly equal logits (span of z - z_ref <= 0.5); use the standard formula here")
    return _KLFixed.apply(z, z_ref.detach())


if __name__ == "__main__":
    torch.manual_seed(0)
    zr = 3 * torch.randn(32000)
    z = (zr + 1e-4 * torch.randn(32000)).requires_grad_(True)
    print("fixed    ", kl_fixed(z, zr).item())
    lp, lq = F.log_softmax(zr, -1), F.log_softmax(z, -1)
    print("textbook ", (lp.exp() * (lp - lq)).sum().item())
    zz = zr.clone().requires_grad_(True); kl_fixed(zz, zr).backward(); print("grad at identical logits:", zz.grad.abs().max().item())
