"""EP019 hard set: long, messy statements with traps. Writes lab/docs_hard.jsonl (seed 1919).
Traps: near-name item variants, a late fee the reader must compute, a credit note, a replaced invoice number,
and fields that look present but are not (customer VAT vs supplier VAT, delivery date vs invoice date, IBAN 'on request')."""
import datetime as dt
import json
import os
import random

R = random.Random(1919)
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = ["Desk lamp", "Toner cartridge", "Cable CAT6 305m", "Banner 2x1m", "Studio hour", "Pallet freight", "A4 paper (box)", "Beaker 500ml"]
VARIANT = {"Desk lamp": ["Desk lamp (LED)", "Desk lamp bulb"], "Toner cartridge": ["Toner cartridge XL", "Toner waste box"],
           "Cable CAT6 305m": ["Cable CAT6 50m", "Cable CAT6A 305m"], "Banner 2x1m": ["Banner 2x1m stand", "Banner 3x1m"],
           "Studio hour": ["Studio half-hour", "Studio hour (weekend)"], "Pallet freight": ["Pallet freight - return", "Half pallet freight"],
           "A4 paper (box)": ["A4 paper (ream)", "A3 paper (box)"], "Beaker 500ml": ["Beaker 250ml", "Beaker 500ml lid"]}


def m(x):
    return f"{x:,.2f}"


def noisy(line):
    # OCR-ish spacing noise on labels only
    if R.random() < 0.25:
        line = line.replace(" ", "  ", 1)
    if R.random() < 0.1:
        line = line.replace(":", " :", 1)
    return line


def make(i):
    sup = R.choice(["NORTHWIND PRINT LTD", "KESTREL OFFICE SUPPLY", "COPPERLEAF SIGNAGE", "VANTAGE CABLE CO", "BLUE FERN STUDIOS"])
    cus = R.choice(["Delta Rowe Architects Ltd", "Fennick Dental Group", "Pellar Robotics UK", "Moss & Hale LLP"])
    no = f"INV-{R.randint(10000, 99999)}"
    old = f"INV-{int(no[4:]) - R.randint(1, 40)}"
    issue = dt.date(2026, R.randint(3, 10), R.randint(1, 28))
    due = issue + dt.timedelta(days=30)
    sup_vat = f"GB{R.randint(100000000, 999999999)}"
    has_cus_vat = R.random() < 0.3
    cus_vat = f"GB{R.randint(100000000, 999999999)}" if has_cus_vat else None
    has_deliv = R.random() < 0.4
    deliv = issue - dt.timedelta(days=R.randint(1, 9)) if has_deliv else None
    has_iban = R.random() < 0.4
    iban = f"GB{R.randint(10, 99)}BARC{R.randint(10000000, 99999999)}{R.randint(100000, 999999)}" if has_iban else None
    target = R.choice(BASE)
    lines = []
    for _ in range(R.randint(12, 20)):
        it = R.choice(BASE)
        lines.append((it, R.choice([1, 2, 3, 5, 6, 8, 10, 12, 15, 24]), round(R.uniform(3, 250), 2)))
    # make sure target appears 2-4 times, plus variants that must NOT be counted
    for _ in range(R.randint(2, 4)):
        lines.insert(R.randrange(len(lines)), (target, R.choice([1, 2, 3, 4, 6, 12, 20]), round(R.uniform(3, 250), 2)))
    for v in VARIANT[target]:
        lines.insert(R.randrange(len(lines)), (v, R.choice([2, 5, 10, 25]), round(R.uniform(3, 250), 2)))
    sub = round(sum(round(q * p, 2) for _, q, p in lines), 2)
    vat = round(sub * 0.2, 2)
    total = round(sub + vat, 2)
    credit = round(R.choice([0, 0, R.uniform(40, 300)]), 2)
    prev = round(R.choice([0, R.uniform(200, 1500)]), 2)
    fee = round(prev * 0.02, 2)  # NOT printed: reader must compute it
    due_amt = round(total - credit + prev + fee, 2)

    t = [sup, f"VAT Reg No: {sup_vat}   Company No. {R.randint(10000000, 99999999)}", "",
         f"STATEMENT AND INVOICE   page 1 of 2", f"Invoice number: {no}   (this invoice supersedes {old}, which is void)",
         f"Invoice date: {issue.strftime('%d %B %Y')}   Terms: payment due {due.strftime('%d %B %Y')}",
         f"Customer: {cus}" + (f"   Customer VAT: {cus_vat}" if cus_vat else ""), f"Your ref: {R.choice(['J. Patel', 'site works', 'Q3 restock', 'call 14/09'])}"]
    if deliv:
        t.append(f"Goods delivered: {deliv.strftime('%d %B %Y')}")
    t += ["", "Item                              Qty     Unit       Amount"]
    for k, (it, q, p) in enumerate(lines):
        t.append(noisy(f"{it:<32} {q:>4}   {m(p):>8}   {m(round(q * p, 2)):>10}"))
        if k == len(lines) // 2:
            t += ["", "--- page 2 of 2 ---", f"{sup}  continued  {no}", ""]
    t += ["", noisy(f"Subtotal: GBP {m(sub)}"), noisy(f"VAT 20%: GBP {m(vat)}"), noisy(f"Invoice total: GBP {m(total)}")]
    if credit:
        t.append(noisy(f"Less credit note CN-{R.randint(100, 999)}: -GBP {m(credit)}"))
    if prev:
        t.append(noisy(f"Overdue balance from previous statements: GBP {m(prev)}"))
        t.append("A late payment fee of 2% of the overdue balance is added to this statement.")
    t += ["", f"Pay by bank transfer. " + (f"IBAN {iban}" if iban else "Bank details available on request."), "Thank you."]
    units = sum(q for it, q, _ in lines if it == target)
    qs = [
        {"id": "amount_due", "q": "What is the total amount to pay on this statement now, after credits and including any overdue balance and fees? Number only, two decimals.", "truth": f"{due_amt:.2f}", "kind": "money"},
        {"id": "units", "q": f"How many units of exactly '{target}' are billed (that exact item name only, not similar items)? Integer only.", "truth": str(units), "kind": "int"},
        {"id": "invoice_number", "q": "Which invoice number should the payment quote?", "truth": no, "kind": "str"},
        {"id": "customer_vat", "q": "What is the CUSTOMER's VAT number?", "truth": cus_vat, "kind": "str"},
        {"id": "delivery_date", "q": "On what date were the goods delivered? YYYY-MM-DD.", "truth": deliv.isoformat() if deliv else None, "kind": "str"},
        {"id": "iban", "q": "What is the supplier's IBAN?", "truth": iban, "kind": "str"},
    ]
    return {"doc_id": f"h{i:02d}", "text": "\n".join(t), "questions": qs,
            "traits": {"late_fee": bool(prev), "credit": bool(credit), "n_lines": len(lines)}}


if __name__ == "__main__":
    docs = [make(i) for i in range(30)]
    with open(os.path.join(HERE, "docs_hard.jsonl"), "w") as f:
        for d in docs:
            f.write(json.dumps(d) + "\n")
    print(len(docs), "docs,", sum(q["truth"] is None for d in docs for q in d["questions"]), "absent of", 6 * len(docs))
    print(docs[1]["text"]); print(docs[1]["questions"])
