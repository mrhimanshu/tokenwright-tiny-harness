import torch
import torch.nn.functional as F


class _KLFromLogits(torch.autograd.Function):
    """
    KL(p_t || p_s) with p_t = softmax(teacher), p_s = softmax(student).

    Uses the identity (with r = log p_s - log p_t and sum p_t e^r = 1):
        KL = sum_i p_t,i * (expm1(r_i) - r_i)
    Every term is non-negative and second order in r, so the sum has no
    cancellation. The key is to compute r accurately. Because
        r = delta - d,   d = t - s,   delta = lse(t) - lse(s) = log E_s[e^d],
    delta is computed in a cancellation-free way when the logits are close.
    The gradient wrt the student is p_s - p_t, which equals p_t * expm1(r).
    """

    @staticmethod
    def forward(ctx, student_logits, teacher_logits):
        s = student_logits
        t = teacher_logits

        log_ps = F.log_softmax(s, dim=-1)
        log_pt = F.log_softmax(t, dim=-1)
        p_s = log_ps.exp()
        p_t = log_pt.exp()

        # Difference of logits: exact or nearly exact when s is close to t.
        d = t - s

        # delta = log E_s[exp(d)], computed stably.
        m = (p_s * d).sum(dim=-1, keepdim=True)
        v = d - m
        small_v = v.abs().amax(dim=-1, keepdim=True) < 1.0
        # Near-equal path: m + log1p(E_s[expm1(v)]).
        v_safe = torch.where(small_v, v, torch.zeros_like(v))
        delta_close = m + torch.log1p(
            (p_s * torch.expm1(v_safe)).sum(dim=-1, keepdim=True)
        )
        # General path, robust for distant distributions.
        delta_far = torch.logsumexp(log_ps + d, dim=-1, keepdim=True)
        delta = torch.where(small_v, delta_close, delta_far)

        # r = log p_s - log p_t, accurate even when tiny.
        r = delta - d

        small_r = r.abs() < 1.0
        r_safe = torch.where(small_r, r, torch.zeros_like(r))
        em1 = torch.expm1(r_safe)

        # p_t * (e^r - 1 - r), no cancellation for small r.
        terms = torch.where(small_r, p_t * (em1 - r_safe), p_s - p_t - p_t * r)
        kl = terms.sum().clamp_min(0.0)

        # dKL/ds = p_s - p_t = p_t * expm1(r), accurate for small r.
        grad_s = torch.where(small_r, p_t * em1, p_s - p_t)

        ctx.save_for_backward(grad_s, p_t, r, kl)
        return kl

    @staticmethod
    def backward(ctx, grad_output):
        grad_s, p_t, r, kl = ctx.saved_tensors
        grad_student = grad_teacher = None
        if ctx.needs_input_grad[0]:
            grad_student = grad_output * grad_s
        if ctx.needs_input_grad[1]:
            # dKL/dt = p_t * (log p_t - log p_s - KL) = p_t * (-r - KL)
            grad_teacher = grad_output * (p_t * (-r - kl))
        return grad_student, grad_teacher


def kl_from_logits(student_logits: torch.Tensor, teacher_logits: torch.Tensor) -> torch.Tensor:
    """
    Returns KL(teacher || student) as a scalar tensor, where the distributions
    are softmax(teacher_logits) and softmax(student_logits) over the last dim.
    Numerically accurate (value and gradient) in float32 even when the two
    distributions are nearly identical. Differentiable wrt student_logits
    (and teacher_logits, if it requires grad).
    """
    if student_logits.shape != teacher_logits.shape:
        raise ValueError("student_logits and teacher_logits must have the same shape")
    return _KLFromLogits.apply(student_logits, teacher_logits)
