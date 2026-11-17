import torch


# Coefficients of g(u) = u*e^u - expm1(u) = sum_{n>=2} (n-1)/n! * u^n.
# Stored highest order first for Horner evaluation of g(u) / u^2.
def _series_coeffs(n_max: int = 14):
    coeffs = []
    fact = 1.0
    facts = {}
    for n in range(1, n_max + 1):
        fact *= n
        facts[n] = fact
    for n in range(n_max, 1, -1):
        coeffs.append((n - 1) / facts[n])
    return coeffs


_COEFFS = _series_coeffs()
_SERIES_THRESHOLD = 0.5
_EXPM1_SAFE = 80.0


def _kl_forward_parts(s: torch.Tensor, t: torch.Tensor):
    """
    Returns (kl, q, p, u) where q = softmax(s), p = softmax(t),
    u = log(p/q), computed so that u is accurate even when p ~= q.
    """
    log_q = torch.log_softmax(s, dim=-1)
    q = torch.exp(log_q)

    # log(p_i/q_i) = d_i - log(sum_j q_j exp(d_j)),  d = t - s  (shift invariant)
    d = t - s
    # Center d with its q-weighted mean so the normaliser L is second order small.
    dc = d - (q * d).sum()

    # Accurate path: L = log1p(sum q * expm1(dc)); fallback to logsumexp if dc is huge.
    S = (q * torch.expm1(dc.clamp(max=_EXPM1_SAFE))).sum()
    L_acc = torch.log1p(S.clamp(min=-1.0 + 1e-30))
    L_safe = torch.logsumexp(log_q + dc, dim=-1)
    L = torch.where(dc.max() < _EXPM1_SAFE, L_acc, L_safe)

    u = dc - L                       # u_i = log(p_i / q_i)
    p = torch.exp(log_q + u)         # p_i = softmax(t)_i, no overflow

    # KL = sum_i q_i * g(u_i),  g(u) = u e^u - e^u + 1 >= 0  (no cancellation across terms)
    small = u.abs() < _SERIES_THRESHOLD
    us = torch.where(small, u, torch.zeros_like(u))
    poly = torch.full_like(us, _COEFFS[0])
    for c in _COEFFS[1:]:
        poly = poly * us + c
    g_series = q * (us * us) * poly
    g_direct = p * u - p + q         # = q * g(u), fine when |u| is not small
    terms = torch.where(small, g_series, g_direct)

    kl = terms.sum().clamp(min=0.0)
    return kl, q, p, u


class _KLFromLogits(torch.autograd.Function):
    @staticmethod
    def forward(ctx, student_logits, teacher_logits):
        kl, q, p, u = _kl_forward_parts(student_logits, teacher_logits)
        ctx.save_for_backward(q, p, u, kl)
        return kl

    @staticmethod
    def backward(ctx, grad_out):
        q, p, u, kl = ctx.saved_tensors
        grad_s = grad_t = None
        if ctx.needs_input_grad[0]:
            # dKL/ds = q - p = -q * expm1(log(p/q))  (accurate when p ~= q)
            grad_s = grad_out * (-q * torch.expm1(u))
        if ctx.needs_input_grad[1]:
            # dKL/dt = p * (log(p/q) - KL)
            grad_t = grad_out * (p * (u - kl))
        return grad_s, grad_t


def kl_from_logits(student_logits: torch.Tensor, teacher_logits: torch.Tensor) -> torch.Tensor:
    """
    KL(teacher || student) = sum_i p_i * (log p_i - log q_i),
    with p = softmax(teacher_logits), q = softmax(student_logits), both shape (vocab,).

    Returns a scalar tensor, differentiable w.r.t. student_logits (and teacher_logits),
    with value and gradient accurate in float32 even when the distributions nearly coincide.
    """
    if student_logits.shape != teacher_logits.shape:
        raise ValueError("student_logits and teacher_logits must have the same shape")
    if student_logits.dim() != 1:
        raise ValueError("expected 1-D logit tensors of shape (vocab,)")
    teacher_logits = teacher_logits.to(dtype=student_logits.dtype, device=student_logits.device)
    return _KLFromLogits.apply(student_logits, teacher_logits)
