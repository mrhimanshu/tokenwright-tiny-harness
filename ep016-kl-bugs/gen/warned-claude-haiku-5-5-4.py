import torch
import torch.nn.functional as F


def kl_from_logits(student_logits: torch.Tensor, teacher_logits: torch.Tensor) -> torch.Tensor:
    """
    Returns KL(teacher || student) as a scalar tensor, where both distributions
    are softmax(logits) over the last dimension.

    Computed in float64 with log_softmax so that the value and the gradient
    w.r.t. student_logits remain accurate when teacher and student are nearly equal.
    The result is cast back to the input dtype (float32 in normal use).
    """
    out_dtype = student_logits.dtype

    s = student_logits.to(torch.float64)
    t = teacher_logits.to(torch.float64)

    # Stable log-probabilities; never form log(softmax(...)) manually.
    log_p_s = F.log_softmax(s, dim=-1)
    log_p_t = F.log_softmax(t, dim=-1)
    p_t = log_p_t.exp()

    # KL(p_t || p_s) = sum_i p_t,i * (log p_t,i - log p_s,i)
    kl = (p_t * (log_p_t - log_p_s)).sum()

    return kl.to(out_dtype)
