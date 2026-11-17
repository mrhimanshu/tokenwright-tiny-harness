import torch
import torch.nn.functional as F


def kl_from_logits(student_logits: torch.Tensor, teacher_logits: torch.Tensor) -> torch.Tensor:
    """
    Computes KL(teacher || student) = sum_i p_t(i) * (log p_t(i) - log p_s(i)),
    where p_t = softmax(teacher_logits) and p_s = softmax(student_logits).

    Both inputs are float32 tensors of shape (vocab,). Returns a scalar tensor,
    differentiable with respect to student_logits.
    """
    # Teacher is the fixed target; no gradient flows through it.
    teacher_logits = teacher_logits.detach()

    log_p_s = F.log_softmax(student_logits, dim=-1)
    log_p_t = F.log_softmax(teacher_logits, dim=-1)
    p_t = log_p_t.exp()

    # Use xlogy-style safety: terms where p_t == 0 contribute exactly 0
    # (avoids 0 * inf = nan when log_p_t is -inf, e.g. masked tokens).
    diff = torch.where(p_t > 0, log_p_t - log_p_s, torch.zeros_like(log_p_t))
    kl = (p_t * diff).sum()
    return kl
