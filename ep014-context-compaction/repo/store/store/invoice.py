from store import orders


def invoice_text(lines):
    return f"TOTAL: {orders.calc_total(lines):.2f} GBP"
