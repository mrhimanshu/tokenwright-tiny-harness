import torch


def _expm1_minus_x(x: torch.Tensor) -> torch.Tensor:
    """Accurate exp(x) - 1 - x, including for small |x| (avoids cancellation)."""
    small = x.abs() < 0.5
    xs = torch.where(small, x, torch.zeros_like(x))
    # Taylor: x^2 * sum_{k>=0} x^k / (k+2)!
    coeff = 1.0
    facts = [1.0 / 2]
    f = 2.0
    for k in range(1, 12):
        f *= (k + 2)
        facts.append(1.0 / f)
    acc = torch.full_like(xs, facts[-1])
    for c in reversed(facts[:-1]):
        acc = acc * xs + c
    series = xs * xs * acc
    xl = torch.where(small, torch.ones_like(x), x)
    direct = torch.expm1(xl) - xl
    return torch.where(small, series, direct)


class _KLFromLogits(torch.autograd.Function):
    @staticmethod
    def forward(ctx, student_logits, teacher_logits):
        s = student_logits
        t = teacher_logits
        p = torch.softmax(t, dim=-1)
        d = s - t                                   # exact when s ~ t
        c = (p * d).sum(dim=-1, keepdim=True)       # shift (KL is shift invariant)
        dc = d - c
        r = (p * dc).sum(dim=-1, keepdim=True)      # ~0 (rounding residual)
        A = (p * _expm1_minus_x(dc)).sum(dim=-1, keepdim=True)
        m = A + r                                   # E_p[expm1(dc)]
        # KL = log E_p[exp(dc)] - E_p[dc] = log1p(m) - r
        kl = torch.log1p(m) - r
        ctx.save_for_backward(p, dc, m)
        return kl.squeeze(-1)

    @staticmethod
    def backward(ctx, grad_out):
        p, dc, m = ctx.saved_tensors
        # grad wrt student logits = q - p = p * (expm1(dc) - m) / (1 + m)
        g = p * (torch.expm1(dc) - m) / (1.0 + m)
        return grad_out.unsqueeze(-1) * g, None


def kl_from_logits(student_logits: torch.Tensor, teacher_logits: torch.Tensor) -> torch.Tensor:
    """KL(softmax(teacher) || softmax(student)), accurate when the two are nearly equal.

    Differentiable w.r.t. student_logits (teacher is treated as a constant).
    """
    teacher_logits = teacher_logits.detach()
    return _KLFromLogits.apply(student_logits, teacher_logits)
