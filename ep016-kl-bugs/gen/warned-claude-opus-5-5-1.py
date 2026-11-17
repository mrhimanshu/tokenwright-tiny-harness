import torch


def _phi_series(u):
    # (u - 1) * exp(u) + 1 = sum_{k>=2} (k-1)/k! * u^k, valid for small |u|.
    # Truncation after u^7 gives relative error below 1e-9 for |u| < 0.1.
    return u * u * (0.5 + u * (1.0 / 3.0 + u * (1.0 / 8.0 + u * (1.0 / 30.0
                    + u * (1.0 / 144.0 + u * (1.0 / 840.0))))))


class _KLFromLogits(torch.autograd.Function):
    """
    KL(p || q) with p = softmax(teacher), q = softmax(student).

    Written as an f-divergence: KL = sum_i q_i * phi(r_i), with r_i = p_i / q_i = exp(u_i)
    and phi(r) = r log r - r + 1 >= 0. Every term is nonnegative and O(u^2), so there is no
    catastrophic cancellation when p ~= q. The log-ratio u = (t - s) - (lse_t - lse_s) is
    computed via log1p/expm1 so it is accurate when the logits are nearly equal.
    The gradient q - p is computed analytically as -q * expm1(u), which also avoids cancellation.
    """

    @staticmethod
    def forward(ctx, student_logits, teacher_logits):
        s = student_logits
        t = teacher_logits

        log_q = torch.log_softmax(s, dim=-1)
        q = log_q.exp()
        d = t - s

        # L = lse(t) - lse(s) = log E_q[exp(d)], computed accurately for small d.
        z = (q * torch.expm1(d)).sum(dim=-1, keepdim=True)
        L_small = torch.log1p(z)
        L_big = (torch.logsumexp(t, dim=-1, keepdim=True)
                 - torch.logsumexp(s, dim=-1, keepdim=True))
        use_small = (d.abs().amax(dim=-1, keepdim=True) <= 1.0) & torch.isfinite(L_small)
        L = torch.where(use_small, L_small, L_big)

        u = d - L                       # log p - log q, accurate when p ~= q
        p = (log_q + u).exp()           # consistent p (no overflow)

        small = u.abs() < 0.1
        u_s = torch.where(small, u, torch.zeros_like(u))
        term_small = q * _phi_series(u_s)
        term_big = p * (u - 1.0) + q    # = q * ((u - 1) e^u + 1)
        term = torch.where(small, term_small, term_big)

        kl = term.sum(dim=-1).clamp_min(0.0)

        ctx.save_for_backward(q, p, u, kl)
        return kl

    @staticmethod
    def backward(ctx, grad_out):
        q, p, u, kl = ctx.saved_tensors
        g = grad_out.unsqueeze(-1)
        grad_s = grad_t = None
        if ctx.needs_input_grad[0]:
            # d KL / d s = q - p = -q * expm1(u)
            grad_s = g * (-q * torch.expm1(u))
        if ctx.needs_input_grad[1]:
            # d KL / d t = p * (log p - log q - KL)
            grad_t = g * (p * (u - kl.unsqueeze(-1)))
        return grad_s, grad_t


def kl_from_logits(student_logits: torch.Tensor, teacher_logits: torch.Tensor) -> torch.Tensor:
    """
    Returns KL(teacher || student) = sum softmax(t) * (log_softmax(t) - log_softmax(s))
    as a scalar tensor, differentiable w.r.t. student_logits (and teacher_logits),
    numerically accurate in float32 even when the two distributions are nearly equal.
    """
    if student_logits.shape != teacher_logits.shape:
        raise ValueError("student_logits and teacher_logits must have the same shape")
    return _KLFromLogits.apply(student_logits, teacher_logits)
