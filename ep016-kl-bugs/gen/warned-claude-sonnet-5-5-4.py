import torch


def _h_series(r):
    # h(r) = r*e^r - expm1(r) = sum_{n>=2} (n-1)/n! * r^n   (accurate for small |r|)
    return r * r * (1.0 / 2 + r * (1.0 / 3 + r * (1.0 / 8 + r * (1.0 / 30 + r * (
        1.0 / 144 + r * (1.0 / 840 + r * (1.0 / 5760)))))))


class _KLFromLogits(torch.autograd.Function):
    @staticmethod
    def forward(ctx, student_logits, teacher_logits):
        s = student_logits.detach()
        t = teacher_logits.detach()
        delta = t - s

        if delta.abs().max().item() < 0.5:
            # Near-equal regime: avoid cancellation.
            # log(p/q) = delta - log(sum_i q_i exp(delta_i)), with the log-sum
            # computed as log1p(sum_i q_i expm1(delta_i)).
            q = torch.softmax(s, dim=-1)
            c = torch.log1p((q * torch.expm1(delta)).sum())
            r = delta - c
            er = torch.expm1(r)                     # p/q - 1
            small = r.abs() < 0.1
            r_safe = torch.where(small, torch.zeros_like(r), r)
            h = torch.where(small, _h_series(r),
                            r_safe * torch.exp(r_safe) - torch.expm1(r_safe))
            # KL = sum_i q_i * h(p_i/q_i), h(x) = x log x - x + 1 >= 0 termwise
            kl = (q * h).sum()
            p = q * (1.0 + er)
            grad_s = -q * er                        # = q - p, accurately
            grad_t = p * (r - kl)
        else:
            log_q = torch.log_softmax(s, dim=-1)
            log_p = torch.log_softmax(t, dim=-1)
            p = log_p.exp()
            q = log_q.exp()
            r = log_p - log_q
            kl = (p * r).sum()
            grad_s = q - p
            grad_t = p * (r - kl)

        ctx.save_for_backward(grad_s, grad_t)
        return kl

    @staticmethod
    def backward(ctx, grad_output):
        grad_s, grad_t = ctx.saved_tensors
        gs = grad_output * grad_s if ctx.needs_input_grad[0] else None
        gt = grad_output * grad_t if ctx.needs_input_grad[1] else None
        return gs, gt


def kl_from_logits(student_logits, teacher_logits):
    """KL(teacher || student) for softmax distributions given by 1-D float32 logits.

    Returns a scalar tensor, differentiable w.r.t. student_logits (and teacher_logits).
    Numerically accurate (value and gradient) when the distributions are nearly equal.
    """
    return _KLFromLogits.apply(student_logits, teacher_logits)
