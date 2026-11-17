import torch
import torch.nn.functional as F


def kl_from_logits(student_logits: torch.Tensor, teacher_logits: torch.Tensor) -> torch.Tensor:
    """
    Compute KL(teacher || student) = sum_i p_t[i] * (log p_t[i] - log p_s[i]),
    where p_t = softmax(teacher_logits) and p_s = softmax(student_logits).

    Args:
        student_logits: float tensor of shape (vocab,).
        teacher_logits: float tensor of shape (vocab,).

    Returns:
        Scalar tensor, differentiable with respect to student_logits.
    """
    if student_logits.shape != teacher_logits.shape:
        raise ValueError(
            f"Shape mismatch: student {tuple(student_logits.shape)} vs teacher {tuple(teacher_logits.shape)}"
        )

    # Numerically stable log-probabilities
    log_p_s = F.log_softmax(student_logits, dim=-1)
    log_p_t = F.log_softmax(teacher_logits, dim=-1)
    p_t = log_p_t.exp()

    # Entries where the teacher has zero probability contribute 0 (0 * log 0 = 0).
    # Replace them with finite values before the arithmetic so that neither the
    # forward pass nor the backward pass produces NaNs (e.g. from -inf logits).
    mask = p_t > 0
    zeros = torch.zeros_like(log_p_t)
    log_p_t_safe = torch.where(mask, log_p_t, zeros)
    log_p_s_safe = torch.where(mask, log_p_s, zeros)

    kl = (p_t * (log_p_t_safe - log_p_s_safe)).sum(dim=-1)
    return kl
