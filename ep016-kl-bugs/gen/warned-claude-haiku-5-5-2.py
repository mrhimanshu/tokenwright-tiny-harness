import torch
import torch.nn.functional as F


def kl_from_logits(student_logits: torch.Tensor, teacher_logits: torch.Tensor) -> torch.Tensor:
    """
    Computes KL(teacher || student) = sum_v p_t(v) * (log p_t(v) - log p_s(v)),
    where p_t = softmax(teacher_logits) and p_s = softmax(student_logits).

    Both inputs have shape (vocab,). Returns a scalar float32 tensor that is
    differentiable with respect to student_logits.

    The computation is carried out in float64 internally. When the two
    distributions are nearly identical, the KL value is a small difference of
    nearly equal log-probabilities, and float32 cancellation would otherwise
    destroy its accuracy (and the accuracy of its gradient p_s - p_t). Using
    float64 for the log-softmax and the reduction keeps both accurate, and the
    result is cast back to float32 at the end.
    """
    s = student_logits.to(torch.float64)
    t = teacher_logits.to(torch.float64)

    # Stable log-probabilities via log_softmax (never forms log(0)).
    log_p_s = F.log_softmax(s, dim=-1)
    log_p_t = F.log_softmax(t, dim=-1)

    # Teacher probabilities; log_p_t is always finite, so 0 * finite term is exact 0.
    p_t = log_p_t.exp()

    kl = (p_t * (log_p_t - log_p_s)).sum()

    return kl.to(torch.float32)
