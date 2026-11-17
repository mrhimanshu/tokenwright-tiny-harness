import torch
import torch.nn.functional as F


def kl_from_logits(student_logits: torch.Tensor, teacher_logits: torch.Tensor) -> torch.Tensor:
    """
    Compute KL(teacher || student) between the softmax distributions defined by
    student_logits and teacher_logits, both of shape (vocab,).

    Returns a scalar tensor that is differentiable with respect to student_logits.
    """
    student_log_probs = F.log_softmax(student_logits, dim=-1)
    teacher_log_probs = F.log_softmax(teacher_logits, dim=-1)

    # F.kl_div(input, target, log_target=True) computes
    # sum(exp(target) * (target - input)), i.e. KL(target || exp(input)).
    kl = F.kl_div(
        student_log_probs,
        teacher_log_probs,
        reduction="sum",
        log_target=True,
    )
    return kl
