import torch
import torch.nn.functional as F


def kl_from_logits(student_logits: torch.Tensor, teacher_logits: torch.Tensor) -> torch.Tensor:
    """
    Computes KL(teacher || student) = sum_i p_t(i) * (log p_t(i) - log p_s(i)),
    where p_t = softmax(teacher_logits) and p_s = softmax(student_logits).

    Both inputs are float32 tensors of shape (vocab,). Returns a scalar tensor
    that is differentiable with respect to student_logits.
    """
    student_logp = F.log_softmax(student_logits, dim=-1)
    teacher_logp = F.log_softmax(teacher_logits, dim=-1)
    teacher_p = teacher_logp.exp()

    # Use xlogy-style safety: terms where teacher_p == 0 contribute 0.
    diff = teacher_logp - student_logp
    terms = torch.where(teacher_p > 0, teacher_p * diff, torch.zeros_like(teacher_p))
    return terms.sum()
