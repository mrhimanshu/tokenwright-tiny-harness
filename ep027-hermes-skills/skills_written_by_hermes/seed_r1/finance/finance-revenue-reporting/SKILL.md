---
name: finance-revenue-reporting
description: Compute monthly revenue KPIs (net revenue, order count, unique customers, top product) from a raw order export plus an FX rates file, following Finance's reporting rules. Use for any monthly/periodic revenue report built from CSV order exports.
---

# Finance revenue reporting from order exports

## When to use
Any request like "do the monthly revenue report for <month>" where the inputs are an order export (CSV) and an FX rates file (JSON). Session-specific details for January 2026 are in references/jan-2026-session.md.

## Steps
1. Inspect inputs first: row count, status values, currency codes, product names, date range, price formats, duplicate order_ids. Run a quick profile before computing anything.
2. Confirm the revenue basis BEFORE computing. Ask Finance (or check the brief) whether prices include VAT and whether revenue should be ex-VAT. Do not assume. In the January 2026 session the first pass ignored VAT, and Finance's correct figure was 20% lower.
3. Apply the Finance rules in this order:
   a. De-duplicate by order_id. The export sometimes writes the same order twice. Keep one row per order_id.
   b. Keep only status == 'paid'. Exclude 'refunded' and 'test' (QA orders). Normalize case and whitespace on status first.
   c. Parse prices. Some use a decimal comma ("12,50" means 12.50). Replace the comma with a dot before Decimal conversion.
   d. Convert to EUR. The fx file gives EUR per 1 unit of currency (e.g. USD 0.92, GBP 1.17). Multiply, do not divide.
   e. VAT: if prices are VAT-inclusive, divide by 1.2 (20% VAT) for ex-VAT revenue.
   f. Customers: count distinct email, lowercased and stripped.
   g. Top product: sum ex-VAT EUR revenue per product, take the max.
4. Use Decimal, not float, for money. Compute per line, sum, and round to 2 decimals (ROUND_HALF_UP) once at the end.
5. Write the output JSON with exactly the keys requested and nothing extra. Check the file by reading it back.
6. Report the values plainly. If Finance's numbers differ, ask for their totals and compare line by line. Likely causes are rounding order, VAT basis, and fx direction.

## Pitfalls
- Do not dedupe by reading the first-seen row only. Check that duplicates are identical; in the January export they were.
- Emails appear in mixed case for the same customer. Count after lowercasing.
- Status and currency values may carry stray casing or spacing. Normalize them.
- Do not treat test orders as customers or revenue, even though they look like real orders. Test emails often look like qa+N@<domain>.example.
- If the user later changes a rule (e.g. adds VAT removal), recompute from the raw data. Do not patch the previous number.

## Verification
- Row counts after each filter step are logged, so the audit trail is clear.
- Sanity check: revenue per product sums to the total.
- Expect the orders count to equal the count of unique paid order_ids.
