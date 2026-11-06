from store.orders import calc_total


def checkout(lines):
    return {"total": calc_total(lines), "currency": "GBP"}
