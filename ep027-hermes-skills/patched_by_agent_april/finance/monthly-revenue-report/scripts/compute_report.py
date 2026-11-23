#!/usr/bin/env python3
"""Compute a monthly revenue report under Finance's rules.

Usage: compute_report.py ORDERS_CSV FX_JSON OUT_JSON

Rules: dedupe by order_id; only status 'paid'; EUR via fx eur_per_unit;
decimal comma parsed; customers by lower-cased trimmed email;
revenue ex-VAT (divide by 1.2).
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP

VAT_DIVISOR = Decimal("1.2")


def main(orders_path, fx_path, out_path):
    with open(fx_path, encoding="utf-8") as f:
        fx = {k: Decimal(str(v)) for k, v in json.load(f)["eur_per_unit"].items()}

    with open(orders_path, encoding="utf-8", newline="") as f:
        header = f.readline()
        delimiter = ";" if header.count(";") > header.count(",") else ","  # some exports use ';'
        f.seek(0)
        raw = list(csv.DictReader(f, delimiter=delimiter))

    # Rule 1: dedupe by order_id; report conflicting duplicates.
    first = {}
    conflicts = []
    for r in raw:
        oid = r["order_id"]
        if oid in first:
            if first[oid] != r:
                conflicts.append(oid)
            continue
        first[oid] = r
    if conflicts:
        print("WARNING conflicting duplicate order_ids:", sorted(set(conflicts)), file=sys.stderr)

    total = Decimal(0)
    orders = 0
    customers = set()
    by_product = defaultdict(Decimal)
    for r in first.values():
        if r["status"].strip().lower() != "paid":  # Rule 2
            continue
        price = Decimal(r["unit_price"].strip().replace(",", "."))  # Rule 4
        qty = int(r["qty"])
        rate = fx[r["currency"].strip().upper()]  # Rule 3
        amount = price * qty * rate / VAT_DIVISOR  # Rule 6
        total += amount
        orders += 1
        customers.add(r["customer_email"].strip().lower())  # Rule 5
        by_product[r["product"].strip()] += amount

    if not by_product:
        raise SystemExit("no paid orders found")
    top = max(by_product.items(), key=lambda kv: kv[1])[0]
    result = {
        "net_revenue_eur": float(total.quantize(Decimal("0.01"), ROUND_HALF_UP)),
        "orders": orders,
        "unique_customers": len(customers),
        "top_product": top,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
