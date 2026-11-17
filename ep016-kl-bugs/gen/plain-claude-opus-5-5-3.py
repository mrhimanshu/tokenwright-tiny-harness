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

    # The teacher is a fixed target in distillation.
    teacher_logits = teacher_logits.detach()

    # log_softmax is numerically stable (uses log-sum-exp internally).
    log_p_s = F.log_softmax(student_logits, dim=-1)
    log_p_t = F.log_softmax(teacher_logits, dim=-1)
    p_t = log_p_t.exp()

    # Convention 0 * log(0 / q) = 0. Mask before multiplying so that entries
    # with p_t == 0 (e.g. -inf teacher logits) never produce 0 * inf = NaN,
    # in either the forward value or the gradient.
    diff = log_p_t - log_p_s
    safe_diff = torch.where(p_t > 0, diff, torch.zeros_like(diff))

    return (p_t * safe_diff).sum()
