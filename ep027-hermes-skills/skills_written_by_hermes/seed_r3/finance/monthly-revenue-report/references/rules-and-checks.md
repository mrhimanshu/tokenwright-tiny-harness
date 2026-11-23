Session reference: January 2026 export (data/orders_2026-01.csv, data/fx_rates.json)

Data facts seen:
- 149 data rows, 140 unique order_ids (9 ids appeared twice as exact copies; no conflicting duplicates).
- Statuses after dedupe: paid 118, refunded 12, test 10.
- Currencies: EUR, USD, GBP. FX: EUR 1.0, USD 0.92, GBP 1.17 (eur_per_unit).
- 24 prices use a decimal comma (e.g. "10,08"). Parse with replace(",", ".").
- Customer emails have mixed case (e.g. LENA.1@PROTON.ME vs lena.1@proton.me). Lower-case before counting.
- QA emails: qa+NN@kettleandco.example, on test orders only.
- Products: Tea Tin, Travel Flask, Gooseneck Kettle, Loose Leaf Sampler, Descaler 3-pack, Pour-over Set, Stovetop Kettle, Mug (pair).

Result with all six Finance rules:
- net_revenue_eur 4238.98 (ex-VAT). Before VAT division: 5086.77.
- orders 118, unique_customers 54.
- top_product Gooseneck Kettle (1062.19 EUR ex-VAT), then Pour-over Set (878.19).

Checklist before answering:
- Duplicate count matches the unique id count.
- Only paid rows remain.
- All currencies exist in fx_rates.json (a KeyError means a missing rate, so stop and ask).
- Totals rounded once at the end.
