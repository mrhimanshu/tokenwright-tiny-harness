import torch
import torch.nn.functional as F


def kl_from_logits(student_logits: torch.Tensor, teacher_logits: torch.Tensor) -> torch.Tensor:
    """
    Computes KL(teacher || student) = sum_i p_t(i) * (log p_t(i) - log p_s(i)),
    where p_t = softmax(teacher_logits) and p_s = softmax(student_logits).

    Both inputs are float32 tensors of shape (vocab,). Returns a scalar tensor
    that is differentiable with respect to student_logits.
    """
    # Use log_softmax for numerical stability (no explicit softmax/log).
    log_p_s = F.log_softmax(student_logits, dim=-1)
    log_p_t = F.log_softmax(teacher_logits, dim=-1)
    p_t = log_p_t.exp()

    # Terms where p_t == 0 (e.g. log_p_t = -inf from masked logits) contribute 0.
    # Use torch.where to avoid 0 * inf = nan, in both forward and backward.
    diff = log_p_t - log_p_s
    terms = torch.where(p_t > 0, p_t * diff, torch.zeros_like(diff))
    return terms.sum()
