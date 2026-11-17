import math
import torch


_COEFFS = [1.0 / math.factorial(j + 2) for j in range(12)]  # 1/2!, 1/3!, ...


def _expm1_minus_x(x):
    """Accurate expm1(x) - x, including for tiny |x| (where it is ~x^2/2)."""
    g = torch.full_like(x, _COEFFS[-1])
    for c in reversed(_COEFFS[:-1]):
        g = g * x + c
    series = x * x * g
    direct = torch.expm1(x) - x
    return torch.where(x.abs() < 0.5, series, direct)


class _KLFromLogits(torch.autograd.Function):
    @staticmethod
    def forward(ctx, s, t):
        # delta = s - t ; KL(p||q) = log E_p[e^{delta}] - E_p[delta]
        p = torch.softmax(t, dim=-1)
        delta = s - t
        m0 = (p * delta).sum()
        d = delta - m0                       # shift-invariant, ~zero p-mean
        ok = bool(torch.isfinite(d).all()) and bool(d.abs().max() <= 10.0)

        if ok:
            m = (p * d).sum()                # tiny residual mean
            r = _expm1_minus_x(d)            # >= 0, accurate
            R = (p * r).sum()
            A = m + R                        # E_p[expm1(d)]
            kl = torch.log1p(A) - m          # errors in m cancel
            grad = p * ((d - m) + (r - R)) / (1.0 + A)   # = q - p
        else:
            # Robust fallback for large / non-finite differences
            lt = torch.log_softmax(t, dim=-1)
            ls = torch.log_softmax(s, dim=-1)
            terms = torch.where(p > 0, p * (lt - ls), torch.zeros_like(p))
            kl = terms.sum()
            grad = torch.softmax(s, dim=-1) - p

        ctx.save_for_backward(grad)
        return kl

    @staticmethod
    def backward(ctx, grad_out):
        (grad,) = ctx.saved_tensors
        return grad * grad_out, None


def kl_from_logits(student_logits, teacher_logits):
    """KL(softmax(teacher) || softmax(student)), scalar, differentiable wrt student.

    Uses a shifted/centered formulation with an accurate expm1(x)-x so that both
    the value and the gradient (q - p) stay accurate in float32 when the
    distributions are nearly identical.
    """
    return _KLFromLogits.apply(student_logits, teacher_logits.detach())
