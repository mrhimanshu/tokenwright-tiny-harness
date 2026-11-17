import torch
import torch.nn.functional as F


def kl_from_logits(student_logits: torch.Tensor, teacher_logits: torch.Tensor) -> torch.Tensor:
    """
    Computes KL(teacher || student) between the softmax distributions of two
    logit vectors of shape (vocab,). Returns a float32 scalar tensor that is
    differentiable with respect to student_logits.

    The computation is carried out in float64 so that the value and gradient
    remain accurate when the two distributions are nearly identical, where
    float32 log-differences would suffer catastrophic cancellation.
    """
    s = student_logits.to(torch.float64)
    t = teacher_logits.to(torch.float64)

    # Numerically stable log-probabilities (log_softmax never underflows to -inf
    # for finite logits, so 0 * log-term stays exactly 0).
    log_p_s = F.log_softmax(s, dim=-1)
    log_p_t = F.log_softmax(t, dim=-1)

    p_t = log_p_t.exp()
    kl = (p_t * (log_p_t - log_p_s)).sum(dim=-1)

    return kl.to(student_logits.dtype)
