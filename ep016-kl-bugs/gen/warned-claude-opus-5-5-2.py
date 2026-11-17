import torch


def _series(x, coeffs):
    """Evaluate x^2 * (c0 + c1*x + c2*x^2 + ...) with Horner's method."""
    acc = torch.zeros_like(x)
    for c in reversed(coeffs):
        acc = acc * x + c
    return acc * x * x


# psi(x) = 1 + (x - 1) * e^x = sum_{n>=2} (n-1)/n! x^n   (>= 0, ~ x^2/2)
_PSI_COEFFS = [1.0 / 2, 1.0 / 3, 1.0 / 8, 1.0 / 30, 1.0 / 144,
               1.0 / 840, 1.0 / 5760, 1.0 / 45360]
# phi(x) = expm1(x) - x = sum_{n>=2} x^n / n!            (~ x^2/2)
_PHI_COEFFS = [1.0 / 2, 1.0 / 6, 1.0 / 24, 1.0 / 120, 1.0 / 720,
               1.0 / 5040, 1.0 / 40320, 1.0 / 362880]

_SERIES_THRESHOLD = 0.5
_FALLBACK_THRESHOLD = 30.0


def _psi(x):
    small = x.abs() < _SERIES_THRESHOLD
    xs = torch.where(small, x, torch.zeros_like(x))
    xl = torch.where(small, torch.ones_like(x), x)
    return torch.where(small, _series(xs, _PSI_COEFFS), 1.0 + (xl - 1.0) * torch.exp(xl))


def _phi(x):
    small = x.abs() < _SERIES_THRESHOLD
    xs = torch.where(small, x, torch.zeros_like(x))
    xl = torch.where(small, torch.ones_like(x), x)
    return torch.where(small, _series(xs, _PHI_COEFFS), torch.expm1(xl) - xl)


def _kl_standard(student_logits, teacher_logits):
    log_ps = torch.log_softmax(student_logits, dim=-1)
    log_pt = torch.log_softmax(teacher_logits, dim=-1)
    pt = log_pt.exp()
    return (pt * (log_pt - log_ps)).sum()


def kl_from_logits(student_logits: torch.Tensor, teacher_logits: torch.Tensor) -> torch.Tensor:
    """
    KL(teacher || student) for logits of shape (vocab,), returning a scalar.

    Uses an exact reformulation that avoids catastrophic cancellation when the
    two distributions are nearly identical. With d = t - s, shifted by an
    arbitrary constant c (delta = d - c), p_s = softmax(s):

        KL = (E_s[psi(delta)] - g(u)) / (1 + u),
        u  = E_s[delta] + E_s[phi(delta)]  (= E_s[e^delta] - 1),
        psi(x) = 1 + (x-1)e^x,  phi(x) = expm1(x) - x,
        g(u) = (1+u) log1p(u) - u.

    psi, phi >= 0 and are evaluated accurately (Taylor series near 0), so the
    value is O(delta^2) with full relative precision, and autograd yields
    accurate gradients w.r.t. student_logits.
    """
    s = student_logits.float()
    t = teacher_logits.float()

    d = t - s
    if not torch.isfinite(d).all():
        return _kl_standard(s, t)

    p_s = torch.softmax(s, dim=-1)
    # The result is mathematically independent of c, so detaching is exact.
    c = (p_s * d).sum().detach()
    delta = d - c

    if delta.abs().max().item() > _FALLBACK_THRESHOLD:
        # Distributions are far apart: no cancellation issue, avoid overflow.
        return _kl_standard(s, t)

    m = (p_s * delta).sum()
    b = (p_s * _phi(delta)).sum()
    a_minus_b = (p_s * _psi(delta)).sum()

    u = m + b
    g = (1.0 + u) * torch.log1p(u) - u

    return (a_minus_b - g) / (1.0 + u)
