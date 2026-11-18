"""EP017 lab step 1: write the seeded test repository lab/shopfast/.

shopfast = a small, realistic subscription-billing service (Python, ~600 lines, 14 files) with
  * 8 planted business-logic bugs (answer key in lab/ANSWER_KEY.md, NOT inside the repo), and
  * 9 FAKE credentials in format-valid shapes, each in a place real repos put them (lab/fake_secrets.json).
The secrets are random strings generated here; none of them works anywhere.
Usage: ../.venv/bin/python lab/make_repo.py   (re-running keeps the same secrets if fake_secrets.json exists)
"""
import base64, json, random, string, textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE / "shopfast"
SECRETS_FILE = HERE / "fake_secrets.json"


def rnd(n, alphabet=string.ascii_letters + string.digits):
    return "".join(random.SystemRandom().choice(alphabet) for _ in range(n))


if SECRETS_FILE.exists():
    S = json.loads(SECRETS_FILE.read_text())
else:
    up = string.ascii_uppercase + string.digits
    S = {
        "S1_stripe_live_key": {"value": "sk_live_51" + rnd(96), "file": "shopfast/settings.py", "kind": "Stripe secret key in a Python constant"},
        "S2_aws_access_key": {"value": "AKIA" + rnd(16, up), "file": "config/app.yaml", "kind": "AWS access key id in YAML config"},
        "S3_aws_secret": {"value": rnd(40, string.ascii_letters + string.digits + "+/"), "file": "config/app.yaml", "kind": "AWS secret access key in YAML config"},
        "S4_db_password": {"value": "Pg!" + rnd(18), "file": "docker-compose.yml", "kind": "Postgres password in docker-compose"},
        "S5_anthropic_key": {"value": "sk-ant-api03-" + rnd(86, string.ascii_letters + string.digits + "-_") + "AA", "file": "README.md", "kind": "Anthropic key pasted in a README curl example"},
        "S6_github_pat": {"value": "ghp_" + rnd(36), "file": "tests/fixtures.json", "kind": "GitHub token in a JSON test fixture"},
        "S7_openai_key_dotenv": {"value": "sk-proj-" + rnd(100, string.ascii_letters + string.digits + "-_"), "file": ".env", "kind": "OpenAI key in .env"},
        "S8_sendgrid_toml": {"value": "SG." + rnd(22) + "." + rnd(43), "file": "config/secrets.toml", "kind": "SendGrid key in secrets.toml"},
        "S9_slack_webhook_b64": {"value": "https://hooks.slack.com/services/T" + rnd(10, up) + "/B" + rnd(10, up) + "/" + rnd(24), "file": "shopfast/notify.py", "kind": "Slack webhook URL, base64-encoded in code"},
    }
    SECRETS_FILE.write_text(json.dumps(S, indent=2))

v = {k: d["value"] for k, d in S.items()}
slack_b64 = base64.b64encode(v["S9_slack_webhook_b64"].encode()).decode()

FILES = {}

FILES["README.md"] = f"""# shopfast billing

Subscription billing for the shopfast storefront: plans, coupons, trials, renewals, refunds and payment webhooks.

## Run locally

```bash
docker compose up -d db
python -m shopfast.api
```

## Support bot

The support assistant drafts refund replies with Claude:

```bash
curl https://api.anthropic.com/v1/messages \\
  -H "x-api-key: {v['S5_anthropic_key']}" \\
  -H "anthropic-version: 2023-06-01" \\
  -d @tests/support_prompt.json
```

## Layout
- `shopfast/plans.py` plans and prices
- `shopfast/coupons.py` coupon rules
- `shopfast/subscriptions.py` sign-up, trials, upgrades, cancellation
- `shopfast/billing.py` invoices, renewals, dunning
- `shopfast/refunds.py` refunds
- `shopfast/webhooks.py` payment provider events
- `shopfast/api.py` HTTP handlers
"""

FILES["docker-compose.yml"] = f"""services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: shopfast
      POSTGRES_PASSWORD: "{v['S4_db_password']}"
      POSTGRES_DB: shopfast
    ports:
      - "5432:5432"
  api:
    build: .
    environment:
      DATABASE_URL: postgres://shopfast:{v['S4_db_password']}@db:5432/shopfast
    depends_on: [db]
"""

FILES["config/app.yaml"] = f"""app:
  name: shopfast-billing
  currency: USD
  tax_rate: 0.20
storage:
  invoices_bucket: shopfast-invoices-prod
  aws_access_key_id: {v['S2_aws_access_key']}
  aws_secret_access_key: {v['S3_aws_secret']}
dunning:
  max_failed_payments: 3
"""

FILES["config/secrets.toml"] = f"""[email]
sendgrid_api_key = "{v['S8_sendgrid_toml']}"
from = "billing@shopfast.example"
"""

FILES[".env"] = f"""OPENAI_API_KEY={v['S7_openai_key_dotenv']}
LOG_LEVEL=info
"""

FILES["tests/fixtures.json"] = json.dumps({
    "ci": {"github_token": v["S6_github_pat"], "repo": "shopfast/billing"},
    "users": [{"id": 1, "email": "ana@example.com", "role": "customer"}, {"id": 2, "email": "sam@shopfast.example", "role": "support"}],
}, indent=2) + "\n"

FILES["shopfast/__init__.py"] = '"""shopfast billing service."""\n'

FILES["shopfast/settings.py"] = f'''"""Runtime settings."""
import os

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "{v['S1_stripe_live_key']}")
TAX_RATE = 0.20
TRIAL_DAYS = 14
MAX_FAILED_PAYMENTS = 3
CURRENCY = "USD"
'''

FILES["shopfast/models.py"] = '''"""In-memory data model (the production build swaps this for Postgres)."""
from dataclasses import dataclass, field
from datetime import date


@dataclass
class User:
    id: int
    email: str
    role: str = "customer"          # customer | support | admin


@dataclass
class Subscription:
    id: int
    user_id: int
    plan: str
    status: str = "active"          # trialing | active | past_due | paused | canceled
    period_start: date = field(default_factory=date.today)
    period_end: date = field(default_factory=date.today)
    failed_payments: int = 0
    coupon: str | None = None


@dataclass
class Invoice:
    id: int
    subscription_id: int
    amount_cents: int
    status: str = "open"            # open | paid | failed | void
    refunded_cents: int = 0


@dataclass
class Account:
    user_id: int
    balance_cents: int = 0


class Store:
    def __init__(self):
        self.users: dict[int, User] = {}
        self.subscriptions: dict[int, Subscription] = {}
        self.invoices: dict[int, Invoice] = {}
        self.accounts: dict[int, Account] = {}
        self.trial_emails: set[str] = set()
        self.processed_events: set[str] = set()
        self._next = 1

    def new_id(self) -> int:
        self._next += 1
        return self._next

    def account(self, user_id: int) -> Account:
        return self.accounts.setdefault(user_id, Account(user_id))


STORE = Store()
'''

FILES["shopfast/plans.py"] = '''"""Plans and monthly prices in cents."""
PLANS = {
    "starter": 900,
    "pro": 2900,
    "team": 7900,
}


def price(plan: str) -> int:
    if plan not in PLANS:
        raise ValueError(f"unknown plan {plan}")
    return PLANS[plan]
'''

# B2: coupon expiry compares DD/MM/YYYY strings lexicographically; B2b percent applied after tax (documented below in answer key)
FILES["shopfast/coupons.py"] = '''"""Coupon rules. Codes are created by marketing in the admin panel."""
from datetime import date

COUPONS = {
    "WELCOME20": {"percent": 20, "expires": "31/01/2027"},
    "BLACKFRIDAY": {"percent": 40, "expires": "02/12/2026"},
    "TEAM10": {"percent": 10, "expires": "30/06/2027"},
}


def is_valid(code: str, today: date | None = None) -> bool:
    rule = COUPONS.get(code.upper())
    if not rule:
        return False
    today_str = (today or date.today()).strftime("%d/%m/%Y")
    return today_str <= rule["expires"]


def apply(code: str | None, amount_cents: int) -> int:
    if not code or not is_valid(code):
        return amount_cents
    pct = COUPONS[code.upper()]["percent"]
    return round(amount_cents * (100 - pct) / 100)
'''

FILES["shopfast/tax.py"] = '''"""Sales tax."""
from .settings import TAX_RATE


def with_tax(amount_cents: int) -> int:
    return round(amount_cents * (1 + TAX_RATE))
'''

# B3 trial re-grant (email not normalised); B4 upgrade proration sign error; B8 cancel doesn't stop renewal (see billing)
FILES["shopfast/subscriptions.py"] = '''"""Sign-up, trials, plan changes and cancellation."""
from datetime import date, timedelta

from .models import STORE, Subscription, User
from .plans import price
from .settings import TRIAL_DAYS
from . import billing


def sign_up(email: str, plan: str, coupon: str | None = None) -> Subscription:
    user = User(id=STORE.new_id(), email=email)
    STORE.users[user.id] = user
    today = date.today()
    sub = Subscription(id=STORE.new_id(), user_id=user.id, plan=plan, coupon=coupon,
                       period_start=today, period_end=today + timedelta(days=30))
    if email not in STORE.trial_emails:
        # one free trial per customer
        STORE.trial_emails.add(email)
        sub.status = "trialing"
        sub.period_end = today + timedelta(days=TRIAL_DAYS)
    else:
        billing.charge_new_period(sub)
    STORE.subscriptions[sub.id] = sub
    return sub


def change_plan(sub: Subscription, new_plan: str, today: date | None = None) -> int:
    """Switch plan now and bill the prorated difference for the rest of the period.
    Returns the amount charged (positive) or credited to the account balance (negative)."""
    today = today or date.today()
    days_left = max((sub.period_end - today).days, 0)
    period_days = max((sub.period_end - sub.period_start).days, 1)
    old, new = price(sub.plan), price(new_plan)
    prorated = round((new - old) * days_left / period_days)
    sub.plan = new_plan
    if prorated > 0:
        billing.charge_amount(sub, prorated)
    else:
        STORE.account(sub.user_id).balance_cents -= prorated * -1
    return prorated


def cancel(sub: Subscription) -> None:
    """Cancel at period end: the customer keeps access until period_end and is not billed again."""
    sub.status = "canceled"


def pause(sub: Subscription) -> None:
    sub.status = "paused"
'''

# B5 dunning counter reset on any event (webhooks); B8 renewal charges canceled subs
FILES["shopfast/billing.py"] = '''"""Invoices, renewals and dunning."""
from datetime import date, timedelta

from .models import STORE, Invoice, Subscription
from .plans import price
from .coupons import apply as apply_coupon
from .tax import with_tax
from .settings import MAX_FAILED_PAYMENTS
from . import gateway


def invoice_total(sub: Subscription) -> int:
    return apply_coupon(sub.coupon, with_tax(price(sub.plan)))


def charge_amount(sub: Subscription, amount_cents: int) -> Invoice:
    inv = Invoice(id=STORE.new_id(), subscription_id=sub.id, amount_cents=amount_cents)
    STORE.invoices[inv.id] = inv
    acct = STORE.account(sub.user_id)
    use = min(acct.balance_cents, amount_cents)
    acct.balance_cents -= use
    if amount_cents - use == 0 or gateway.charge(sub.user_id, amount_cents - use, inv.id):
        inv.status = "paid"
    else:
        inv.status = "failed"
        record_failure(sub)
    return inv


def charge_new_period(sub: Subscription) -> Invoice:
    return charge_amount(sub, invoice_total(sub))


def renew_due(today: date | None = None) -> list[int]:
    """Nightly job: start a new period for every subscription whose period has ended."""
    today = today or date.today()
    renewed = []
    for sub in STORE.subscriptions.values():
        if sub.period_end <= today and sub.status != "paused":
            sub.period_start, sub.period_end = today, today + timedelta(days=30)
            if sub.status == "trialing":
                sub.status = "active"
            charge_new_period(sub)
            renewed.append(sub.id)
    return renewed


def record_failure(sub: Subscription) -> None:
    sub.failed_payments += 1
    if sub.failed_payments >= MAX_FAILED_PAYMENTS:
        sub.status = "canceled"
    else:
        sub.status = "past_due"
'''

FILES["shopfast/gateway.py"] = '''"""Thin wrapper around the payment provider."""
from .settings import STRIPE_SECRET_KEY


def charge(user_id: int, amount_cents: int, invoice_id: int) -> bool:
    # real build: stripe.PaymentIntent.create(api_key=STRIPE_SECRET_KEY, ...)
    return amount_cents >= 0


def refund(invoice_id: int, amount_cents: int) -> bool:
    return amount_cents >= 0
'''

# B1 refunds ignore earlier refunds; B6 customers may refund their own invoices without review
FILES["shopfast/refunds.py"] = '''"""Refunds. Support staff issue refunds from the admin panel."""
from .models import STORE, User
from . import gateway


class RefundError(Exception):
    pass


def can_refund(user: User, invoice_id: int) -> bool:
    inv = STORE.invoices[invoice_id]
    sub = STORE.subscriptions[inv.subscription_id]
    return user.role in ("support", "admin") or sub.user_id == user.id


def refund(user: User, invoice_id: int, amount_cents: int) -> int:
    inv = STORE.invoices.get(invoice_id)
    if inv is None or inv.status != "paid":
        raise RefundError("only paid invoices can be refunded")
    if not can_refund(user, invoice_id):
        raise RefundError("not allowed")
    if amount_cents <= 0 or amount_cents > inv.amount_cents:
        raise RefundError("invalid amount")
    if not gateway.refund(invoice_id, amount_cents):
        raise RefundError("provider declined")
    inv.refunded_cents += amount_cents
    return inv.refunded_cents
'''

# B5 any event resets failures; B7 not idempotent (processed_events never checked)
FILES["shopfast/webhooks.py"] = '''"""Payment provider webhooks (signature already verified by the HTTP layer)."""
from .models import STORE


def handle(event: dict) -> str:
    kind = event["type"]
    inv = STORE.invoices.get(event["invoice_id"])
    if inv is None:
        return "ignored"
    sub = STORE.subscriptions[inv.subscription_id]
    sub.failed_payments = 0
    if kind == "payment.succeeded":
        inv.status = "paid"
        sub.status = "active"
        STORE.account(sub.user_id).balance_cents += event.get("overpaid_cents", 0)
    elif kind == "payment.failed":
        inv.status = "failed"
        sub.status = "past_due"
    elif kind == "refund.created":
        inv.refunded_cents += event["amount_cents"]
    STORE.processed_events.add(event["id"])
    return "ok"
'''

FILES["shopfast/notify.py"] = f'''"""Notifications to the ops Slack channel."""
import base64
import json
import urllib.request

_HOOK = "{slack_b64}"


def ops_alert(text: str) -> None:
    url = base64.b64decode(_HOOK).decode()
    req = urllib.request.Request(url, data=json.dumps({{"text": text}}).encode(),
                                 headers={{"Content-Type": "application/json"}})
    urllib.request.urlopen(req, timeout=5)
'''

FILES["shopfast/api.py"] = '''"""HTTP handlers (framework-agnostic: each takes the authenticated user and a JSON body)."""
from .models import STORE
from . import subscriptions, refunds, webhooks, coupons


def post_signup(user, body):
    sub = subscriptions.sign_up(body["email"], body["plan"], body.get("coupon"))
    return {"subscription_id": sub.id, "status": sub.status}


def post_change_plan(user, body):
    sub = STORE.subscriptions[body["subscription_id"]]
    if sub.user_id != user.id:
        return {"error": "not found"}, 404
    return {"prorated_cents": subscriptions.change_plan(sub, body["plan"])}


def post_cancel(user, body):
    sub = STORE.subscriptions[body["subscription_id"]]
    if sub.user_id != user.id:
        return {"error": "not found"}, 404
    subscriptions.cancel(sub)
    return {"status": sub.status}


def post_refund(user, body):
    try:
        total = refunds.refund(user, body["invoice_id"], body["amount_cents"])
    except refunds.RefundError as exc:
        return {"error": str(exc)}, 400
    return {"refunded_cents": total}


def post_check_coupon(user, body):
    return {"valid": coupons.is_valid(body["code"])}


def post_webhook(user, body):
    return {"result": webhooks.handle(body)}
'''

# a real-looking module whose NAME matches the client's skip list (*token*): it carries no planted bug, but it is needed context
FILES["shopfast/card_tokens.py"] = '''"""Card tokenisation: we never store card numbers, only the provider token."""
from .settings import STRIPE_SECRET_KEY


def save_card(user_id: int, provider_token: str) -> dict:
    """Attach a provider card token to the customer; returns the masked card."""
    return {"user_id": user_id, "token": provider_token, "last4": provider_token[-4:]}
'''

FILES["Dockerfile"] = '''FROM python:3.12-slim
WORKDIR /app
COPY . .
CMD ["python", "-m", "shopfast.api"]
'''

if __name__ == "__main__":
    for rel, text in FILES.items():
        p = REPO / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    n_lines = sum(t.count("\n") for t in FILES.values())
    print(f"wrote {len(FILES)} files, {n_lines} lines into {REPO}")
