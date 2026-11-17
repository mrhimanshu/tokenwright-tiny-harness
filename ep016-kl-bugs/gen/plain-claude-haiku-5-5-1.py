import torch
import torch.nn.functional as F


def kl_from_logits(student_logits: torch.Tensor, teacher_logits: torch.Tensor) -> torch.Tensor:
    """
    Computes KL(teacher || student) where both distributions are softmax(logits).

    Args:
        student_logits: float32 tensor of shape (vocab,), requires grad for training.
        teacher_logits: float32 tensor of shape (vocab,), same vocabulary as student.

    Returns:
        Scalar tensor containing sum_i p_teacher(i) * (log p_teacher(i) - log p_student(i)).
    """
    # Work in log-space for numerical stability.
    log_p_teacher = F.log_softmax(teacher_logits, dim=-1)
    log_p_student = F.log_softmax(student_logits, dim=-1)

    # p_teacher * (log p_teacher - log p_student); terms with p_teacher == 0
    # contribute exactly 0 because log_softmax is finite for finite logits.
    p_teacher = log_p_teacher.exp()
    kl = (p_teacher * (log_p_teacher - log_p_student)).sum(dim=-1)
    return kl
