import torch
import torch.nn.functional as F


def kl_from_logits(student_logits: torch.Tensor, teacher_logits: torch.Tensor) -> torch.Tensor:
    """
    Compute KL(teacher || student), where both distributions are softmax(logits).

    Args:
        student_logits: float32 tensor of shape (vocab,) or (..., vocab).
        teacher_logits: float32 tensor with the same shape as student_logits.

    Returns:
        A scalar tensor containing KL(p_teacher || p_student), differentiable
        with respect to student_logits.
    """
    # Log-probabilities computed in a numerically stable way.
    student_logp = F.log_softmax(student_logits, dim=-1)
    teacher_logp = F.log_softmax(teacher_logits, dim=-1)

    # p_teacher * (log p_teacher - log p_student); terms with p_teacher == 0
    # contribute 0 because teacher_logp is finite and exp(teacher_logp) == 0.
    teacher_p = teacher_logp.exp()
    kl = (teacher_p * (teacher_logp - student_logp)).sum(dim=-1)

    # Average over any leading batch dimensions so the result is a scalar.
    return kl.mean()
