import torch


class _KLFromLogits(torch.autograd.Function):
    """KL(softmax(t) || softmax(s)) with accurate value and gradient for s ~= t.

    Notation: p = softmax(t), q = softmax(s), delta = t - s, and
    x = log(p/q) = delta - c, where c = log sum_j q_j exp(delta_j).

    Since sum p = sum q = 1:
        KL = sum_j q_j * f(x_j),  f(x) = x*e^x - expm1(x) >= 0  (~ x^2/2 for small x).
    Every term is non-negative and second order in x, so nothing cancels.
    The gradient with respect to s is q - p = -q * expm1(x).
    """

    @staticmethod
    def forward(ctx, student_logits, teacher_logits):
        s = student_logits
        t = teacher_logits
        delta = t - s  # nearly exact when s ~= t

        log_q = torch.log_softmax(s, dim=-1)
        q = log_q.exp()
        p = torch.softmax(t, dim=-1)

        # c = log E_q[exp(delta)], computed accurately via log1p/expm1 when delta is small
        dc = delta.clamp(-20.0, 20.0)
        c_small = torch.log1p((q * torch.expm1(dc)).sum())
        c_big = torch.logsumexp(t, dim=-1) - torch.logsumexp(s, dim=-1)
        use_small = delta.abs().max() < 1.0
        c = torch.where(use_small, c_small, c_big)

        x = delta - c  # log(p/q)

        # Series branch for small |x|: f(x) = sum_{k>=2} (k-1)/k! x^k
        thr = 0.2
        xs = torch.where(x.abs() < thr, x, torch.zeros_like(x))
        coeffs = [1.0 / 2, 2.0 / 6, 3.0 / 24, 4.0 / 120, 5.0 / 720,
                  6.0 / 5040, 7.0 / 40320, 8.0 / 362880, 9.0 / 3628800]
        poly = torch.full_like(xs, coeffs[-1])
        for cf in reversed(coeffs[:-1]):
            poly = poly * xs + cf
        f_series = xs * xs * poly

        # Mid-range branch
        xm = x.clamp(-20.0, 20.0)
        f_mid = xm * torch.exp(xm) - torch.expm1(xm)
        term_mid = torch.where(x.abs() < thr, q * f_series, q * f_mid)

        # Far-apart branch (avoids overflow)
        term_far = p * x - p + q
        term = torch.where(x.abs() <= 20.0, term_mid, term_far)
        kl = term.sum()

        # Gradient wrt student logits: q - p = -q*expm1(x)
        g_mid = -q * torch.expm1(xm)
        g_far = q - p
        grad = torch.where(x.abs() <= 20.0, g_mid, g_far)
        ctx.save_for_backward(grad)
        return kl

    @staticmethod
    def backward(ctx, grad_out):
        (grad,) = ctx.saved_tensors
        return grad_out * grad, None


def kl_from_logits(student_logits: torch.Tensor, teacher_logits: torch.Tensor) -> torch.Tensor:
    """KL(teacher || student) for logits of shape (vocab,). Returns a scalar tensor.

    Differentiable w.r.t. student_logits (teacher is treated as a constant).
    """
    return _KLFromLogits.apply(student_logits, teacher_logits.detach())
