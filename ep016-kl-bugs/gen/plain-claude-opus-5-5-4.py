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
            f"Shape mismatch: student {tuple(student_logits.shape)} vs teacher {tuple(teacher_logits.shape)}"
        )
    if student_logits.dim() != 1:
        raise ValueError(f"Expected 1-D logits of shape (vocab,), got {tuple(student_logits.shape)}")

    student_logits = student_logits.float()
    # The teacher is a fixed target in distillation; no gradient flows into it.
    teacher_logits = teacher_logits.detach().float()

    # log_softmax is numerically stable (uses the log-sum-exp trick internally).
    log_p_s = F.log_softmax(student_logits, dim=-1)
    log_p_t = F.log_softmax(teacher_logits, dim=-1)
    p_t = log_p_t.exp()

    # By convention 0 * log(0 / q) = 0. Mask out entries where the teacher has zero
    # probability (e.g. -inf teacher logits) so they contribute neither NaN values
    # nor NaN gradients.
    mask = p_t > 0
    zeros = torch.zeros_like(log_p_s)
    log_p_t_safe = torch.where(mask, log_p_t, zeros)
    log_p_s_safe = torch.where(mask, log_p_s, zeros)

    kl = (p_t * (log_p_t_safe - log_p_s_safe)).sum()
    return kl
