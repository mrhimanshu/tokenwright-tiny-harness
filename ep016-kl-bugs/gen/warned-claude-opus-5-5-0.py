import torch
import torch.nn.functional as F


def _h_small(x: torch.Tensor) -> torch.Tensor:
    # h(x) = exp(x) - 1 - x via Taylor series (accurate for |x| <= 0.5)
    c = [1.0 / 2, 1.0 / 6, 1.0 / 24, 1.0 / 120, 1.0 / 720,
         1.0 / 5040, 1.0 / 40320, 1.0 / 362880, 1.0 / 3628800]
    acc = torch.full_like(x, c[-1])
    for coef in reversed(c[:-1]):
        acc = acc * x + coef
    return x * x * acc


def kl_from_logits(student_logits: torch.Tensor, teacher_logits: torch.Tensor) -> torch.Tensor:
    """
    KL(teacher || student) where both distributions are softmax of the given logits.

    Uses the identity
        KL = log E_t[exp(d')] - E_t[d'],   d = s - t,  d' = d - E_t[d]
    and writes exp(d') = 1 + d' + h(d') with h(x) = exp(x) - 1 - x >= 0.
    Then with H = E_t[h(d')], r = E_t[d'] (~0 up to rounding), y = r + H:
        KL = log1p(y) - r = H + (log1p(y) - y)
    H is a sum of non-negative, second-order terms, so no catastrophic
    cancellation occurs when the distributions are nearly equal, and the
    autograd gradient p_t * (h'(d') - E_t[h'(d')]) is accurate as well.
    """
    s = student_logits.float()
    t = teacher_logits.float()

    log_pt = F.log_softmax(t, dim=-1)
    pt = log_pt.exp()

    d = s - t
    c = (pt * d).sum(dim=-1, keepdim=True)
    dp = d - c  # centered logit difference

    thresh = 0.5
    small = dp.abs() <= thresh

    # Small branch: series for h, input clamped so the unused branch stays finite.
    h_s = pt * _h_small(dp.clamp(-thresh, thresh))
    # Large branch: p_t * (exp(d') - 1 - d'), with p_t*exp(d') = exp(log p_t + d')
    # (= p_s * exp(KL), so it does not overflow).
    h_l = torch.exp(log_pt + dp) - pt * (1.0 + dp)

    terms = torch.where(small, h_s, h_l)
    H = terms.sum(dim=-1)
    r = (pt * dp).sum(dim=-1)
    y = r + H

    kl = H + (torch.log1p(y) - y)

    if kl.dim() > 0:
        kl = kl.mean()
    return kl
