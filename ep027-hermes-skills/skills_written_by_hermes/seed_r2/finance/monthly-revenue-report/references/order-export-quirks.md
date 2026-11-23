# Order export quirks observed (January 2026 export, 149 rows)

- Columns: order_id, date, customer_email, product, qty, unit_price, currency, status.
- Status counts: paid 124 rows, refunded 13, test 12. Test rows all use the kettleandco.example QA domain.
- Duplicates: 9 order_ids appear twice as identical rows. Distinct order_ids = 140.
- Currencies: EUR, USD, GBP. The fx file (2026-01) gives EUR per unit: USD 0.92, GBP 1.17.
- Decimal comma: about two dozen unit_price values use a comma, e.g. "10,08", "41,03". They are quoted in the CSV.
- Email casing is mixed (e.g. "LENA.1@PROTON.ME" vs "lena.1@proton.me"). Lowercase before counting customers.
- Reference results for this export under the finance rules: paid distinct orders 118; unique customers 54; gross EUR 5086.77; ex-VAT net 4238.98; top product (ex-VAT EUR) Gooseneck Kettle at 1062.19. Use these only to check a re-run of the same file. Do not reuse them for a different month.
