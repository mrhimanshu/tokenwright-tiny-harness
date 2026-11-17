import torch


def _g(d):
    # g(d) = exp(-d) - 1 + d, computed stably for small |d| via Taylor series
    d2 = d * d
    series = d2 * (0.5 + d * (-1.0 / 6 + d * (1.0 / 24 + d * (-1.0 / 120 + d * (
        1.0 / 720 + d * (-1.0 / 5040 + d * (1.0 / 40320)))))))
    ds = torch.where(d.abs() < 0.25, torch.zeros_like(d), d)
    direct = torch.expm1(-ds) + ds
    return torch.where(d.abs() < 0.25, series, direct)


def _h(m):
    # h(m) = log1p(m) - m, computed stably for small |m|
    series = m * m * (-0.5 + m * (1.0 / 3 + m * (-0.25 + m * (0.2 + m * (
        -1.0 / 6 + m * (1.0 / 7 + m * (-0.125)))))))
    ms = torch.where(m.abs() < 0.1, torch.zeros_like(m), m)
    direct = torch.log1p(ms) - ms
    return torch.where(m.abs() < 0.1, series, direct)


class _KLFromLogits(torch.autograd.Function):
    @staticmethod
    def forward(ctx, s, t):
        p = torch.softmax(t, dim=-1)
        d = t - s                      # log p_t - log p_s = d + log1p(E_p[expm1(-d)])
        c = (p * d).sum()
        d = d - c                      # KL invariant to constant shift of student logits
        u = torch.expm1(-d)
        m = (p * u).sum()
        terms = torch.where(p > 0, p * _g(d), torch.zeros_like(p))
        R = terms.sum()
        # KL = E[d] + log1p(m), with E[d] = -m + R  =>  KL = R + (log1p(m) - m)
        kl = R + _h(m)
        ctx.save_for_backward(s, t, p, d, u, m)
        return kl

    @staticmethod
    def backward(ctx, go):
        s, t, p, d, u, m = ctx.saved_tensors
        # grad = softmax(s) - p = p * (u - m) / (1 + m)  (accurate when nearly equal)
        accurate = p * (u - m) / (1.0 + m)
        fallback = torch.softmax(s, dim=-1) - p
        use_acc = torch.isfinite(accurate) & (d.abs() < 0.5)
        grad = torch.where(use_acc, accurate, fallback)
        return grad * go, None


def kl_from_logits(student_logits, teacher_logits):
    """KL(softmax(teacher) || softmax(student)), scalar, differentiable w.r.t. student_logits.

    Uses a cancellation-free formulation so value and gradient remain accurate in
    float32 when the two distributions are nearly identical.
    """
    s = student_logits.to(torch.float32)
    t = teacher_logits.detach().to(torch.float32)
    return _KLFromLogits.apply(s, t)
