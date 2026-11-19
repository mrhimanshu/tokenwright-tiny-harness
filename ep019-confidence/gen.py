"""EP019: generate messy plain-text invoices with exact ground truth.
Each document gets 6 questions. Some answers are absent on purpose (correct answer = not found).
Writes lab/docs.jsonl. Deterministic (seed 19)."""
import datetime as dt
import json
import os
import random

R = random.Random(19)
HERE = os.path.dirname(os.path.abspath(__file__))

SUPPLIERS = ["Northwind Print Ltd", "Brightline Fixtures GmbH", "Kestrel Office Supply", "Harbor & Pine Catering", "Vantage Cable Co.",
             "Oakridge Lab Glass", "Meridian Freight BV", "Copperleaf Signage", "Blue Fern Studios", "Arcadia Tool Hire"]
CUSTOMERS = ["Tokenwright Media", "Delta Rowe Architects", "Fennick Dental", "Quarry Lane School", "Moss & Hale LLP", "Pellar Robotics"]
ITEMS = ["A4 paper (box)", "Toner cartridge", "LED panel 60x60", "Cable CAT6 305m", "Desk lamp", "Catering - lunch per head",
         "Signage install (hour)", "Beaker 500ml", "Pallet freight", "Drill hire (day)", "Banner 2x1m", "Studio hour"]


def money(x, eu):
    s = f"{x:,.2f}"
    if eu:
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def make(i):
    eu = R.random() < 0.3
    cur = R.choice(["EUR", "GBP", "USD"]) if not eu else "EUR"
    sym = {"EUR": "EUR ", "GBP": "GBP ", "USD": "$"}[cur]
    doc_no = f"INV-{R.randint(1000, 9999)}"
    is_credit_ref = R.random() < 0.25
    other_no = f"INV-{R.randint(1000, 9999)}"
    issue = dt.date(2026, R.randint(1, 10), R.randint(1, 28))
    lines = []
    n = R.randint(3, 7)
    chosen = R.sample(ITEMS, k=min(n, len(ITEMS)))
    # repeat one product on a second line sometimes (unit-count trap)
    if R.random() < 0.5:
        chosen.append(chosen[0])
    for it in chosen:
        q = R.choice([1, 1, 2, 3, 4, 5, 10, 12])
        p = round(R.uniform(4, 400), 2)
        lines.append((it, q, p))
    sub = round(sum(q * p for _, q, p in lines), 2)
    disc = round(sub * R.choice([0, 0, 0.05, 0.1]), 2)
    ship = R.choice([0, 0, 12.5, 25.0, 40.0])
    rate = R.choice([0.2, 0.19, 0.21, 0.0825])
    tax = round((sub - disc + ship) * rate, 2)
    total = round(sub - disc + ship + tax, 2)
    paid = R.choice([0, 0, 0, round(total * R.choice([0.25, 0.5]), 2)])
    prev = R.choice([0, 0, 0, round(R.uniform(50, 900), 2)])
    due_amt = round(total - paid + prev, 2)
    show_balance = R.random() < 0.55          # if False the balance must be worked out
    due_mode = R.choice(["explicit", "explicit", "net", "absent"])
    net = R.choice([14, 30, 45])
    due_date = issue + dt.timedelta(days=net) if due_mode == "net" else (issue + dt.timedelta(days=R.choice([10, 21, 30])) if due_mode == "explicit" else None)
    has_po = R.random() < 0.55
    po = f"PO-{R.randint(10000, 99999)}" if has_po else None
    has_vat = R.random() < 0.6
    vat = (f"DE{R.randint(100000000, 999999999)}" if eu else f"GB{R.randint(100000000, 999999999)}") if has_vat else None
    company_no = f"{R.randint(10000000, 99999999)}"
    quote_no = f"Q-{R.randint(10000, 99999)}"
    sup, cus = R.choice(SUPPLIERS), R.choice(CUSTOMERS)

    t = []
    t.append(f"{sup.upper()}")
    t.append(f"Unit {R.randint(1, 40)}, {R.choice(['Mill Rd', 'Station St', 'Harbour Way', 'Kingsgate'])}")
    t.append(f"Company No. {company_no}" + (f"   VAT Reg: {vat}" if vat else ""))
    t.append("")
    t.append("TAX INVOICE" if rate else "INVOICE")
    t.append(f"Invoice no: {doc_no}      Date: {issue.strftime('%d/%m/%Y') if (eu or cur == 'GBP') else issue.strftime('%m/%d/%Y')}")
    if is_credit_ref:
        t.append(f"Note: this invoice replaces {other_no} (cancelled, do not pay)")
    t.append(f"Bill to: {cus}   Account: AC{R.randint(1000, 9999)}")
    t.append(f"Customer PO: {po}" if po else f"Quote ref: {quote_no}")
    t.append("")
    t.append("Description                 Qty   Unit      Line")
    for it, q, p in lines:
        t.append(f"{it:<27} {q:>3}   {money(p, eu):>8}  {money(q * p, eu):>10}")
    t.append("")
    t.append(f"Subtotal {sym}{money(sub, eu)}")
    if disc:
        t.append(f"Discount -{sym}{money(disc, eu)}")
    if ship:
        t.append(f"Delivery {sym}{money(ship, eu)}")
    t.append(f"Tax {rate * 100:g}% {sym}{money(tax, eu)}")
    t.append(f"TOTAL {sym}{money(total, eu)}")
    if paid:
        t.append(f"Deposit received {R.choice(['12 Oct', '3 Sep', '28 Aug'])}: -{sym}{money(paid, eu)}")
    if prev:
        t.append(f"Balance brought forward (unpaid prior invoices): {sym}{money(prev, eu)}")
    if show_balance and (paid or prev):
        t.append(f"BALANCE DUE {sym}{money(due_amt, eu)}")
    t.append("")
    if due_mode == "explicit":
        fmt = due_date.strftime('%d/%m/%Y') if (eu or cur == 'GBP') else due_date.strftime('%m/%d/%Y')
        t.append(f"Payment due by {fmt}")
    elif due_mode == "net":
        t.append(f"Terms: net {net} days from invoice date")
    else:
        t.append("Thank you for your business!")
    t.append(f"Bank: {R.choice(['Barclays', 'Deutsche Bank', 'Chase'])}  Sort/IBAN on request")

    prod = chosen[0]
    units = sum(q for it, q, _ in lines if it == prod)
    qs = [
        {"id": "amount_due", "q": "What is the total amount the customer must pay now, including any carried-forward balance and minus deposits already paid? Number only, two decimals, no currency.", "truth": f"{due_amt:.2f}", "kind": "money"},
        {"id": "due_date", "q": "What is the payment due date? Answer as YYYY-MM-DD.", "truth": due_date.isoformat() if due_date else None, "kind": "str"},
        {"id": "po_number", "q": "What is the customer's purchase order (PO) number?", "truth": po, "kind": "str"},
        {"id": "vat_number", "q": "What is the supplier's VAT registration number?", "truth": vat, "kind": "str"},
        {"id": "invoice_number", "q": "What is this invoice's own number (the one to quote when paying)?", "truth": doc_no, "kind": "str"},
        {"id": "units", "q": f"How many units of '{prod}' are billed in total on this invoice? Integer only.", "truth": str(units), "kind": "int"},
    ]
    return {"doc_id": f"d{i:02d}", "text": "\n".join(t), "questions": qs,
            "traits": {"eu_format": eu, "balance_printed": show_balance or not (paid or prev), "needs_math": bool(paid or prev) and not show_balance,
                       "due_mode": due_mode, "replaces_other": is_credit_ref, "repeat_line": len(chosen) != len(set(chosen))}}


if __name__ == "__main__":
    docs = [make(i) for i in range(40)]
    with open(os.path.join(HERE, "docs.jsonl"), "w") as f:
        for d in docs:
            f.write(json.dumps(d) + "\n")
    absent = sum(q["truth"] is None for d in docs for q in d["questions"])
    print(len(docs), "docs,", sum(len(d["questions"]) for d in docs), "questions,", absent, "absent")
    print(docs[0]["text"])
