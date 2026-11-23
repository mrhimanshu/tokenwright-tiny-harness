---
name: monthly-revenue-report
description: Build a monthly revenue report (net revenue EUR, order count, unique customers, top product) from a raw order export CSV plus a monthly fx_rates.json. Use for any "monthly report", "revenue report", or finance-style aggregation over an order export.
version: 1.0.0
---

# Monthly revenue report from an order export

Use this for any monthly revenue/orders/customers aggregation over an order export and a month's FX file. The finance team's rules are authoritative; when a first-pass result differs from finance, apply the rules below rather than defending the first pass.

## Inputs
- Order export CSV, e.g. data/orders_YYYY-MM.csv. Columns: order_id, date, customer_email, product, qty, unit_price, currency, status.
- FX file, e.g. data/fx_rates.json, with "eur_per_unit" mapping currency to EUR per 1 unit (EUR 1.0, USD, GBP, ...).
- Output: report/answer.json (or whatever path the user names), with exactly the keys requested.

## Finance rules (apply all of them)
1. Duplicates: the export sometimes writes the same order twice. Count each order_id once. Check whether duplicate rows are identical; if they conflict, flag it to the user rather than silently picking one.
2. Status: only status == "paid" counts. Exclude "refunded" and "test". Test orders are QA traffic (for example, emails on a *.example domain), so exclude them as well.
3. Currency: convert each line to EUR with the month's fx file (amount * qty * eur_per_unit[currency]).
4. Decimal comma: some unit_price values use a decimal comma, such as "12,50". Replace "," with "." before parsing with Decimal. Watch for quoted CSV fields.
5. Customers: count unique customer_email values, case-insensitive and whitespace-stripped (lowercase before counting).
6. VAT: every price in the export INCLUDES 20% VAT. Report ex-VAT revenue, so divide the EUR total by 1.2. Revenue is ex-VAT unless finance says otherwise.
7. Rounding: compute in Decimal, sum at full precision, and round to 2 decimals only at the end (ROUND_HALF_UP). Divide by 1.2 on the total, not per line.
8. Top product: the product with the highest net revenue in EUR (same basis as the headline figure, i.e. ex-VAT, after the same filters). Ranking by gross or by units gives a different answer, so state which basis you used.
9. Orders: the count of distinct paid order_ids after dedupe, not row count.

## Procedure
1. Inspect the CSV: row count, distinct order_ids, status/currency/product counts, date month, unique and conflicting duplicates, and which unit_price values contain commas. Print these before aggregating.
2. Write one script that applies rules 1 to 9 in order. Use csv.DictReader with newline=''.
3. Print intermediate results: per-product EUR totals, gross total, ex-VAT total. Sanity-check that the ex-VAT total equals gross / 1.2.
4. Write the JSON with json.dump(indent=2) and read it back to verify the keys and types. net_revenue_eur must be a float with 2 decimals, orders and unique_customers must be ints.
5. Reply with the four values and a short note on the rules applied.

## Pitfalls seen in practice
- The first pass left out the ex-VAT step. The user had to ask for a redo, and the headline number was 20% too high. Always check the VAT basis against the rules before writing the file.
- When the user gives a rule list, implement all of it, including the ones that look minor (VAT, email case). Do not stop after the first plausible result.
- "Overwrite" means replace the existing file in place. Do not write a second file.

See references/order-export-quirks.md for the sample data quirks observed in the January 2026 export.
