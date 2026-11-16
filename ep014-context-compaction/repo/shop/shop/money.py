from decimal import Decimal, ROUND_HALF_UP


def to_money(x) -> Decimal:
    return Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def apply_discount(price, percent):
    """Return price after a percentage discount. 10 means 10% off."""
    return to_money(Decimal(str(price)) * (Decimal(100) - Decimal(str(percent))) / Decimal(100))
