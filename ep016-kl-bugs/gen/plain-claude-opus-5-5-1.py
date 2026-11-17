import torch
import torch.nn.functional as F


def kl_from_logits(student_logits: torch.Tensor, teacher_logits: torch.Tensor) -> torch.Tensor:
    """
    Compute KL(teacher || student) = sum_i p_t[i] * (log p_t[i] - log p_s[i]),
    where p_t = softmax(teacher_logits) and p_s = softmax(student_logits).

    Both inputs are logit tensors of shape (vocab,). Returns a scalar tensor
    that is differentiable with respect to student_logits. The teacher is
    treated as a fixed target, so no gradient flows into teacher_logits.
    """
    if student_logits.shape != teacher_logits.shape:
        raise ValueError(
            f"shape mismatch: student {tuple(student_logits.shape)} "
            f"vs teacher {tuple(teacher_logits.shape)}"
        )

    student_logits = student_logits.float()
    teacher_logits = teacher_logits.detach().float()

    # log_softmax is numerically stable (uses the log-sum-exp trick internally).
    log_p_s = F.log_softmax(student_logits, dim=-1)
    log_p_t = F.log_softmax(teacher_logits, dim=-1)
    p_t = log_p_t.exp()

    # Use the convention 0 * log(0 / q) = 0. Masking also prevents NaNs when the
    # teacher assigns zero probability (e.g. -inf logits) to some tokens.
    terms = torch.where(
        p_t > 0,
        p_t * (log_p_t - log_p_s),
        torch.zeros_like(p_t),
    )

    return terms.sum()
