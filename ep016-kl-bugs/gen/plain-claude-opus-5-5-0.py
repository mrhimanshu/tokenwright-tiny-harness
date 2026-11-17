import torch
import torch.nn.functional as F


def kl_from_logits(student_logits: torch.Tensor, teacher_logits: torch.Tensor) -> torch.Tensor:
    """
    Compute KL(teacher || student) = sum_i p_t[i] * (log p_t[i] - log p_s[i]),
    where p_t = softmax(teacher_logits) and p_s = softmax(student_logits).

    Args:
        student_logits: float32 tensor of shape (vocab,). Gradients flow through this.
        teacher_logits: float32 tensor of shape (vocab,). Treated as a fixed target.

    Returns:
        Scalar tensor containing the KL divergence.
    """
    if student_logits.shape != teacher_logits.shape:
        raise ValueError(
            f"Shape mismatch: student {tuple(student_logits.shape)} vs "
            f"teacher {tuple(teacher_logits.shape)}"
        )

    # Numerically stable log-probabilities.
    student_log_probs = F.log_softmax(student_logits.float(), dim=-1)
    teacher_log_probs = F.log_softmax(teacher_logits.detach().float(), dim=-1)
    teacher_probs = teacher_log_probs.exp()

    # Terms with zero teacher probability contribute 0 (0 * log 0 := 0),
    # which also avoids NaNs from 0 * (-inf) when teacher logits are masked with -inf.
    terms = torch.where(
        teacher_probs > 0,
        teacher_probs * (teacher_log_probs - student_log_probs),
        torch.zeros_like(student_log_probs),
    )

    return terms.sum()
