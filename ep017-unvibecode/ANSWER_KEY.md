# EP017 answer key: 8 planted business-logic bugs in lab/shopfast (kept OUTSIDE the scanned repo)
| id | file | bug | business impact |
|---|---|---|---|
| B1 | shopfast/refunds.py `refund` | amount is checked against `inv.amount_cents` only, ignoring `inv.refunded_cents`: repeated partial refunds can exceed what was paid | money lost: refund more than the customer paid |
| B2 | shopfast/coupons.py `is_valid` | expiry compares DD/MM/YYYY strings lexicographically | expired coupons accepted / valid ones rejected (e.g. BLACKFRIDAY rejected on 15/11/2026, accepted on 01/03/2027) |
| B3 | shopfast/subscriptions.py `sign_up` | trial check uses the raw email (no lower-casing/trim) | unlimited free trials with Ana@ / ana@ / " ana@" |
| B4 | shopfast/subscriptions.py `change_plan` | downgrade credit has the wrong sign: `balance -= prorated * -1` debits the customer instead of crediting | customers charged extra when they downgrade |
| B5 | shopfast/webhooks.py `handle` | `sub.failed_payments = 0` runs on EVERY event, including payment.failed | dunning never reaches 3 failures, non-paying subs never cancel |
| B6 | shopfast/refunds.py `can_refund` | customers may refund their own invoices (`or sub.user_id == user.id`), though refunds are meant for support staff | self-service refunds of anything paid |
| B7 | shopfast/webhooks.py `handle` | not idempotent: `processed_events` is written but never checked | duplicate deliveries double-credit balances / double-count refunds |
| B8 | shopfast/billing.py `renew_due` | renews every sub with status != "paused", including "canceled" | canceled customers keep getting billed |

Not scored (debatable design, accepted as a valid extra finding, not a false positive): coupon applied after tax; `charge` stub always succeeds; hard-coded secrets (security, not business logic; counted separately).
A finding counts as a hit when it names the right function/file AND the mechanism (judge: lab/score.py, Claude Opus 5.5 with this key, checked by hand).
