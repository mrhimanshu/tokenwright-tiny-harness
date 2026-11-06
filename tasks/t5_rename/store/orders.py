def calc_total(lines):
    """lines: list of (price, qty)."""
    return round(sum(p * q for p, q in lines), 2)
