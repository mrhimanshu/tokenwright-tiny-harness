import torch
import torch.nn.functional as F


def kl_from_logits(student_logits: torch.Tensor, teacher_logits: torch.Tensor) -> torch.Tensor:
    """
    Computes KL(teacher || student) = sum_i p_t(i) * (log p_t(i) - log p_s(i)),
    where p_t = softmax(teacher_logits) and p_s = softmax(student_logits).

    Both inputs are float32 tensors of shape (vocab,). Returns a scalar tensor
    that is differentiable with respect to student_logits.
    """
    # Teacher is the fixed target; no gradient flows through it.
    teacher_logits = teacher_logits.detach()

    log_p_t = F.log_softmax(teacher_logits, dim=-1)
    log_p_s = F.log_softmax(student_logits, dim=-1)
    p_t = log_p_t.exp()

    # Use xlogy-style safety: where p_t == 0 (underflow), the term contributes 0.
    # log_p_t is finite for finite logits, but handle -inf logits (masked tokens) safely.
    diff = torch.where(p_t > 0, log_p_t - log_p_s, torch.zeros_like(log_p_s))
    kl = (p_t * diff).sum()
    return kl
