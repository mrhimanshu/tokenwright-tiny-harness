"""Generate messy monthly order exports for the fictional shop "Kettle & Co".

Gotchas (the "team knowledge" a new teammate doesn't have):
  1. the export repeats some rows (retry bug)            -> drop exact duplicate order_id rows
  2. refunded and test orders don't count                -> status == paid only (test = status 'test')
  3. prices are in EUR/USD/GBP (+CHF from April)         -> convert with fx_rates.json (EUR per 1 unit)
  4. some prices use a decimal comma ("12,50")           -> parse both
  5. customer emails differ only in case                 -> unique customers case-insensitive
  6. HOUSE RULE (not guessable): finance reports revenue ex-VAT; every price includes 20% VAT -> divide by 1.2
Drift: the April export is semicolon-delimited and adds a CHF currency.
Ground truth goes to truth/<month>.json (never visible to the agent).
"""
import csv, json, random, sys
from pathlib import Path

ROOT = Path(__file__).parent
PRODUCTS = {"Stovetop Kettle": 39.0, "Gooseneck Kettle": 64.0, "Tea Tin": 12.5, "Pour-over Set": 48.0,
            "Mug (pair)": 22.0, "Descaler 3-pack": 9.9, "Travel Flask": 27.5, "Loose Leaf Sampler": 18.0}
FX = {"2026-01": {"EUR": 1.0, "USD": 0.92, "GBP": 1.17},
      "2026-02": {"EUR": 1.0, "USD": 0.93, "GBP": 1.16},
      "2026-03": {"EUR": 1.0, "USD": 0.91, "GBP": 1.18},
      "2026-04": {"EUR": 1.0, "USD": 0.90, "GBP": 1.19, "CHF": 1.05}}
FIRST = ["anna", "ben", "chloe", "dev", "elif", "farah", "gus", "hana", "ivan", "jo", "kai", "lena", "mo",
         "nia", "omar", "pia", "quinn", "rosa", "sam", "tara", "uma", "vic", "wen", "yusuf", "zoe"]
DOMAINS = ["mail.com", "post.de", "inbox.co.uk", "proton.me", "web.fr"]


def month_rows(month, n, rng):
    cur = list(FX[month].keys())
    customers = [f"{rng.choice(FIRST)}.{rng.randint(1, 60)}@{rng.choice(DOMAINS)}" for _ in range(70)]
    rows = []
    for i in range(n):
        prod = rng.choice(list(PRODUCTS))
        c = rng.choices(cur, weights=[5, 3, 2] + ([2] if len(cur) > 3 else []))[0]
        price = round(PRODUCTS[prod] / FX[month][c] * rng.uniform(0.97, 1.03), 2)
        status = rng.choices(["paid", "refunded", "test"], weights=[84, 11, 5])[0]
        email = rng.choice(customers)
        if status == "test":
            email = f"qa+{rng.randint(1, 99)}@kettleandco.example"
        if rng.random() < 0.3:  # case noise
            email = email.capitalize() if rng.random() < 0.5 else email.upper()
        price_s = f"{price:.2f}"
        if rng.random() < 0.25:
            price_s = price_s.replace(".", ",")
        day = rng.randint(1, 28)
        rows.append({"order_id": f"KC-{month.replace('-', '')}-{1000 + i}", "date": f"{month}-{day:02d}",
                     "customer_email": email, "product": prod, "qty": rng.choices([1, 2, 3, 4], [60, 25, 10, 5])[0],
                     "unit_price": price_s, "currency": c, "status": status})
    # duplicates from the export retry bug
    dups = rng.sample(rows, k=max(3, n // 15))
    out = rows + [dict(r) for r in dups]
    rng.shuffle(out)
    return out


def truth(month, rows):
    seen, net, orders, custs, byprod = set(), 0.0, 0, set(), {}
    for r in rows:
        if r["order_id"] in seen:
            continue
        seen.add(r["order_id"])
        if r["status"] != "paid":
            continue
        p = float(r["unit_price"].replace(",", "."))
        v = p * int(r["qty"]) * FX[month][r["currency"]]
        net += v
        orders += 1
        custs.add(r["customer_email"].lower())
        byprod[r["product"]] = byprod.get(r["product"], 0) + v
    top = max(byprod, key=byprod.get)
    net = net / 1.2  # house rule: ex-VAT
    # naive answer (no rules) for reference
    naive = sum(float(r["unit_price"].replace(",", ".")) * int(r["qty"]) for r in rows)
    return {"net_revenue_eur": round(net, 2), "orders": orders, "unique_customers": len(custs), "top_product": top,
            "_naive_sum_no_rules": round(naive, 2), "_rows_in_file": len(rows)}


def main():
    rng = random.Random(27)
    (ROOT / "truth").mkdir(exist_ok=True)
    (ROOT / "exports").mkdir(exist_ok=True)
    for month, n in [("2026-01", 140), ("2026-02", 150), ("2026-03", 160), ("2026-04", 155)]:
        rows = month_rows(month, n, rng)
        d = ROOT / "exports" / month
        d.mkdir(exist_ok=True)
        delim = ";" if month == "2026-04" else ","
        with open(d / f"orders_{month}.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter=delim)
            w.writeheader()
            w.writerows(rows)
        (d / "fx_rates.json").write_text(json.dumps({"month": month, "eur_per_unit": FX[month]}, indent=2))
        t = truth(month, rows)
        (ROOT / "truth" / f"{month}.json").write_text(json.dumps(t, indent=2))
        print(month, t)


if __name__ == "__main__":
    main()
