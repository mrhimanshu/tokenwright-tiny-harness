import torch
import torch.nn.functional as F


def kl_from_logits(student_logits: torch.Tensor, teacher_logits: torch.Tensor) -> torch.Tensor:
    """
    Computes KL(teacher || student) between the softmax distributions of two
    logit tensors of shape (vocab,).

    KL(p_t || p_s) = sum_i p_t(i) * (log p_t(i) - log p_s(i))

    Returns a scalar tensor that is differentiable with respect to student_logits.
    """
    student_log_probs = F.log_softmax(student_logits, dim=-1)
    teacher_log_probs = F.log_softmax(teacher_logits, dim=-1)

    # F.kl_div(input, target) computes sum(target * (log target - input)) when
    # log_target=True, where input is the log-probability of the approximating
    # distribution (student) and target is the log-probability of the reference
    # distribution (teacher).
    return F.kl_div(
        student_log_probs,
        teacher_log_probs,
        reduction="sum",
        log_target=True,
    )
