import torch
import torch.nn.functional as F


def kl_from_logits(student_logits: torch.Tensor, teacher_logits: torch.Tensor) -> torch.Tensor:
    """
    Returns KL(teacher || student) as a scalar tensor, where the distributions are
    softmax(teacher_logits) and softmax(student_logits) over the last dimension.

    Numerically stable when the two distributions are nearly equal:
      Let d = s - t (logit differences, computed without cancelling large logits),
      and let p_t = softmax(t). Since softmax is shift-invariant, we may center
      d by its p_t-mean, dc = d - E_t[d]. Then

          KL = log E_t[exp(dc)] - E_t[dc]
             = log1p(E_t[expm1(dc)]) - E_t[dc].

      expm1/log1p keep full relative precision when dc is small, so the value
      is accurate to roughly O(eps * |dc|) rather than O(eps * |logits|).
      Its gradient w.r.t. student logits is exactly softmax(s) - softmax(t).

    For large logit differences (where exp could overflow), it falls back to the
    standard log-softmax formulation, which is stable in that regime.
    """
    s = student_logits.float()
    t = teacher_logits.float()

    log_pt = F.log_softmax(t, dim=-1)
    p_t = log_pt.exp()

    # Logit differences; s - t is accurate when s and t are close.
    d = s - t
    mean_d = (p_t * d).sum(dim=-1, keepdim=True)
    dc = d - mean_d  # centered: E_t[dc] == 0 analytically

    if dc.abs().max().item() < 40.0:
        # Accurate regime: KL = log1p(E_t[expm1(dc)]) - E_t[dc]
        x = (p_t * torch.expm1(dc)).sum(dim=-1)
        mean_dc = (p_t * dc).sum(dim=-1)
        kl = torch.log1p(x) - mean_dc
    else:
        # Large-difference regime: standard formulation (stable here, no overflow)
        log_ps = F.log_softmax(s, dim=-1)
        kl = (p_t * (log_pt - log_ps)).sum(dim=-1)

    return kl.sum()
