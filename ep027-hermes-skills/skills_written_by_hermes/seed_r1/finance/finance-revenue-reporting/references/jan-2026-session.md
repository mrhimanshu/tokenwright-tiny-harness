Session reference: January 2026 revenue report (kettle shop)

Inputs: data/orders_2026-01.csv (149 data rows, CRLF line endings, UTF-8), data/fx_rates.json (EUR per unit: EUR 1.0, USD 0.92, GBP 1.17).
Columns: order_id, date, customer_email, product, qty, unit_price, currency, status.
Profile: status paid 124, refunded 13, test 12. Currencies EUR 70, USD 41, GBP 38. 23 prices use decimal comma. 9 exact duplicate rows (same order_id, identical content).
Products: Tea Tin, Travel Flask, Gooseneck Kettle, Loose Leaf Sampler, Descaler 3-pack, Pour-over Set, Stovetop Kettle, Mug (pair).

Finance rules given for this report:
1. Count each order_id once.
2. Only status 'paid' counts. Refunded and QA test orders never count.
3. Convert to EUR with the month's fx file (EUR per 1 unit).
4. Decimal-comma prices, e.g. 12,50.
5. Customers counted by email, case-insensitive.
6. Revenue is ex-VAT. Prices include 20% VAT, so divide by 1.2.

Results (final, all six rules applied):
  net_revenue_eur 4238.98, orders 118, unique_customers 54, top_product Gooseneck Kettle (1062.19 ex-VAT).

Earlier result without the VAT step: 5086.77 (this was wrong for Finance; VAT step was missing).
Top product by ex-VAT revenue: Gooseneck Kettle 1062.19, then Pour-over Set, Mug (pair), Travel Flask.
