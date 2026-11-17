import torch
import torch.nn.functional as F


def kl_from_logits(student_logits: torch.Tensor, teacher_logits: torch.Tensor) -> torch.Tensor:
    """
    Compute KL(teacher || student) between the softmax distributions of two logit vectors.

    Args:
        student_logits: float32 tensor of shape (vocab,), differentiable w.r.t. this argument.
        teacher_logits: float32 tensor of shape (vocab,), same vocabulary as the student.

    Returns:
        Scalar tensor equal to sum_i p_teacher[i] * (log p_teacher[i] - log p_student[i]).
    """
    # Numerically stable log-probabilities via log_softmax.
    log_p_student = F.log_softmax(student_logits, dim=-1)
    log_p_teacher = F.log_softmax(teacher_logits, dim=-1)

    # Teacher probabilities; finite logits guarantee finite log-probs,
    # so p_t * (log p_t - log p_s) is well-defined even when p_t underflows to 0.
    p_teacher = log_p_teacher.exp()

    kl = torch.sum(p_teacher * (log_p_teacher - log_p_student), dim=-1)
    return kl
