---
name: monthly-revenue-report
description: Compute a monthly revenue report (net revenue EUR, order count, unique customers, top product) from a raw order export plus a monthly FX rates file, applying Finance's counting and VAT rules.
---

# Monthly revenue report from an order export

Use this when asked for a monthly revenue report from an orders CSV and an fx_rates.json file, and an output such as report/answer.json.

## Finance rules (apply all six, every time)

1. Dedupe: the export sometimes writes the same order twice. Count each order_id once. Check for conflicting duplicates (same id, different content) and report them if any exist.
2. Status: only status 'paid' counts. Exclude 'refunded' and 'test' (QA) orders.
3. Currency: prices come in several currencies. Convert with that month's fx_rates.json, where the value is EUR per 1 unit of currency (EUR 1.0, USD 0.92, GBP 1.17 for 2026-01).
4. Decimal comma: some unit_price values use a comma decimal ("12,50"). Replace the comma with a dot before parsing. Use Decimal, not float.
5. Customers: count distinct customer_email, trimmed and lower-cased.
6. VAT: every price includes 20% VAT. Report revenue ex-VAT by dividing each line by 1.2.

Line amount = unit_price * qty * eur_per_unit[currency] / 1.2. Sum the lines, then round the total once to 2 decimals with ROUND_HALF_UP. The top product is the product with the highest summed EUR net revenue.

## Procedure

1. Inspect the files first: header, currencies, statuses, a sample of prices, and duplicate order_ids. Look for decimal commas, uppercase emails, and QA emails such as *.example domains.
2. Run scripts/compute_report.py (in this skill directory) with the orders CSV, the fx JSON, and the output path. It implements all six rules and writes the JSON. Verify the output by re-reading the file.
3. Output keys must be exactly: net_revenue_eur (number, 2 decimals), orders (int), unique_customers (int), top_product (string). Do not add extra keys unless asked.
4. Reply with the four values. Keep the reply short, and state the rules applied only briefly.

## Pitfalls

- Apply rule 6 (VAT) by default. The first pass of a past session omitted it and Finance rejected the numbers. If a request does not mention VAT, still check whether the export prices include tax. Ask if unclear.
- Do not compute net revenue on the unfiltered export. Filter by status after deduping.
- A first draft that skipped the explicit rules produced numbers that did not match Finance's. When Finance supplies a rule list, treat it as authoritative and reconcile to it before answering.
- See references/rules-and-checks.md for the checklist of data-quality checks and worked numbers from a past run.
