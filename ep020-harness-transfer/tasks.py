"""Support-ticket routing tasks with HIDDEN house rules (ground truth computed by code, not by an LLM).
The seed harness only lists the label names; the optimizer has to discover the rules from failures.
usage: python tasks.py  -> writes tasks.json (fixed seed, evolve / held-out split)"""
import json, random, sys

LABELS = ["spam", "legal", "priority", "billing_dispute", "refund_auto", "refund_review",
          "bug_critical", "bug", "account", "shipping", "feedback"]

# hidden house rules, in precedence order (first match wins)
RULES = [
    "1 spam: unsolicited promotion / link to an unrelated offer",
    "2 legal: mentions lawyer, legal action, chargeback or reporting the company",
    "3 priority: Plan is Enterprise (anything not spam/legal), or a Team-plan data-loss bug",
    "4 billing_dispute: charged after cancelling, or a duplicate/double charge",
    "5 refund_auto: refund request with amount <= limit (Free 20, others 50) AND within window (digital 14 days, physical 30)",
    "6 refund_review: any other refund request",
    "7 bug_critical: bug that lost/deleted user data",
    "8 bug: other bug",
    "9 account: login/password/2FA problems, and digital orders whose key/download never arrived",
    "10 shipping: physical package late/lost/tracking",
    "11 feedback: feature request / suggestion",
]

OPEN = ["Hi,", "Hello team,", "Hey.", "Good morning,", "To whom it may concern,", "", "Urgent:", "Quick question -"]
CLOSE = ["Thanks.", "Regards, Sam", "Please help!!", "", "Cheers", "Waiting for your reply.", "- J"]


def make(rng):
    plan = rng.choices(["Free", "Pro", "Team", "Enterprise"], [3, 4, 3, 1.4])[0]
    order = rng.choice(["physical", "digital"])
    days = rng.choice([2, 5, 9, 13, 14, 15, 21, 28, 30, 31, 33, 45, 60])
    amt = rng.choice([9, 15, 19, 20, 21, 25, 39, 49, 50, 51, 59, 79, 120])
    kind = rng.choices(["spam", "legal_refund", "legal_bug", "cancel_charge", "double", "refund", "bug_loss", "bug",
                        "login", "digital_missing", "late", "feature"],
                       [0.7, 0.8, 0.5, 1, 1, 5, 1.5, 1, 1, 1, 1, 0.8])[0]
    # message bodies
    if kind == "spam":
        msg = rng.choice([f"Boost your store sales 300% with our SEO bundle, only ${amt}! Visit growfast-leads.biz",
                          "I can get you 10k followers this week. DM me or click promo-hub.net/offer",
                          "Congratulations, your account won a crypto airdrop, claim at airdrop-claims.io"])
    elif kind == "legal_refund":
        msg = f"I want my ${amt} back for the order from {days} days ago. If this isn't sorted I'm talking to my lawyer."
    elif kind == "legal_bug":
        msg = rng.choice(["Your app wiped my project folder. I'm filing a chargeback with my bank today.",
                          "The export button crashes every time. I will report you to the consumer protection office."])
    elif kind == "cancel_charge":
        msg = rng.choice([f"I cancelled my subscription last month but you charged me ${amt} again on the 3rd.",
                          f"Why was I billed ${amt}? I cancelled before renewal."])
    elif kind == "double":
        msg = rng.choice([f"I see two charges of ${amt} on my card for the same order.",
                          f"You billed me twice (${amt} each) this morning."])
    elif kind == "refund":
        msg = rng.choice([f"Can I get a refund? It cost ${amt} and I don't need it anymore.",
                          f"Please refund the ${amt} purchase, it's not what I expected.",
                          f"I'd like my money back (${amt}). The product doesn't fit my use case."])
    elif kind == "bug_loss":
        msg = rng.choice(["After the update all my saved notes disappeared.",
                          "Sync deleted three months of files from my workspace.",
                          "The app crashed and my draft is gone, nothing in history."])
    elif kind == "bug":
        msg = rng.choice(["The dark mode toggle doesn't stick after restart.",
                          "Charts render blank on Safari.",
                          "Search returns results in the wrong order."])
    elif kind == "login":
        msg = rng.choice(["I can't log in, the 2FA code never arrives.",
                          "Password reset link says expired every time.",
                          "Locked out of my account after changing phones."])
    elif kind == "digital_missing":
        msg = rng.choice(["I paid but never received my license key.",
                          "The download link in the email doesn't work and I have no key.",
                          "Order says delivered but there's no download anywhere."])
    elif kind == "late":
        msg = rng.choice(["My package is two weeks late and tracking hasn't moved.",
                          "Where is my parcel? Tracking says lost in transit.",
                          "Delivery was due Monday, still nothing."])
    else:
        msg = rng.choice(["Would love a keyboard shortcut for archiving.",
                          "Please add CSV export to the reports page.",
                          "Suggestion: let us pin favourite projects."])
    if kind in ("digital_missing",):
        order = "digital"
    if kind == "late":
        order = "physical"
    # gold label by the hidden rules
    if kind == "spam":
        gold = "spam"
    elif kind in ("legal_refund", "legal_bug"):
        gold = "legal"
    elif plan == "Enterprise" or (plan == "Team" and kind == "bug_loss"):
        gold = "priority"
    elif kind in ("cancel_charge", "double"):
        gold = "billing_dispute"
    elif kind == "refund":
        limit = 20 if plan == "Free" else 50
        window = 14 if order == "digital" else 30
        gold = "refund_auto" if (amt <= limit and days <= window) else "refund_review"
    elif kind == "bug_loss":
        gold = "bug_critical"
    elif kind == "bug":
        gold = "bug"
    elif kind in ("login", "digital_missing"):
        gold = "account"
    elif kind == "late":
        gold = "shipping"
    else:
        gold = "feedback"
    text = (f"Plan: {plan} | Order type: {order} | Purchased: {days} days ago\n"
            f"Message: {rng.choice(OPEN)} {msg} {rng.choice(CLOSE)}").replace("  ", " ")
    return dict(text=text, gold=gold, kind=kind)


if __name__ == "__main__":
    rng = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 20261119)
    items, seen = [], set()
    while len(items) < 100:
        t = make(rng)
        if t["text"] in seen:
            continue
        seen.add(t["text"]); items.append(t)
    for i, t in enumerate(items):
        t["id"] = i
    rng.shuffle(items)
    out = dict(labels=LABELS, rules=RULES, evolve=items[:40], heldout=items[40:])
    json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "tasks.json", "w"), indent=1)
    from collections import Counter
    print("evolve", Counter(t["gold"] for t in out["evolve"]))
    print("heldout", Counter(t["gold"] for t in out["heldout"]))
