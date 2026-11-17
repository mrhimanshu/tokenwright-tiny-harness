import torch
import torch.nn.functional as F


def kl_from_logits(student_logits: torch.Tensor, teacher_logits: torch.Tensor) -> torch.Tensor:
    """
    Returns KL(teacher || student) = sum_v p_t(v) * (log p_t(v) - log p_s(v)),
    where p_t = softmax(teacher_logits) and p_s = softmax(student_logits).

    The computation is carried out in float64 and the result is cast back to the
    input dtype. When the two distributions are nearly equal, the KL value is
    second-order small and the log-probability differences suffer catastrophic
    cancellation in float32; float64 keeps both the value and the gradient
    (p_s - p_t with respect to the student logits) accurate. The log-softmax
    formulation avoids underflow/overflow that a naive softmax-then-log would cause.
    """
    s = student_logits.to(torch.float64)
    t = teacher_logits.to(torch.float64)

    log_p_s = F.log_softmax(s, dim=-1)
    log_p_t = F.log_softmax(t, dim=-1)
    p_t = log_p_t.exp()

    kl = (p_t * (log_p_t - log_p_s)).sum()
    return kl.to(student_logits.dtype)
