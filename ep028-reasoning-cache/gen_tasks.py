"""Generate 6 word-problem families: seed + 8 same-shape variants + 3 shape-shift variants each.
Ground truth comes from my own reference solvers (never from a model)."""
import json, random, datetime as dt, math

rng = random.Random(28)
OUT = []

def money(x): return round(x + 1e-9, 2)

# ---------- 1. loan ----------
def loan_pay(P, r, n):
    i = r / 100 / 12
    return money(P * i / (1 - (1 + i) ** -n))
LOAN_W = [
    "A business takes out a loan of ${P:,} at {r}% annual interest, compounded monthly, repaid in {n} equal monthly payments. What is the monthly payment, to the cent?",
    "You borrow ${P:,}. The bank charges {r}% a year (monthly compounding) and you pay it back over {n} months with equal payments. How much is each payment in dollars and cents?",
    "Equal monthly instalments: principal ${P:,}, nominal yearly rate {r}%, term {n} months. Find the instalment (round to cents).",
]
def loan(shift=False, w=0):
    P = rng.choice(range(8000, 90000, 500)); r = rng.choice([3.9, 4.75, 5.5, 6.25, 7.1, 8.4, 9.9]); n = rng.choice([24, 36, 37, 48, 60, 72])
    q = LOAN_W[w].format(P=P, r=r, n=n)
    if shift:
        f = rng.choice([450, 750, 1200])
        q += f" The bank also adds a ${f:,} arrangement fee to the amount borrowed."
        return q, loan_pay(P + f, r, n), {"P": P, "r": r, "n": n, "fee": f}
    return q, loan_pay(P, r, n), {"P": P, "r": r, "n": n}

# ---------- 2. savings ----------
def save_bal(S, D, r, n, stop=None):
    i = r / 100 / 12; b = S
    for m in range(1, n + 1):
        b *= (1 + i)
        if stop is None or m <= stop: b += D
    return money(b)
SAVE_W = [
    "A savings account starts with ${S:,}. It earns {r}% a year compounded monthly, and ${D} is deposited at the end of every month. What is the balance after {n} months, to the cent?",
    "Maya opens an account with ${S:,} and adds ${D} at the end of each month. Interest is {r}% per year, compounded monthly. How much is in the account after {n} months?",
    "Initial deposit ${S:,}; monthly end-of-month contribution ${D}; nominal annual rate {r}% compounded monthly; horizon {n} months. Final balance (cents)?",
]
def savings(shift=False, w=0):
    S = rng.choice(range(500, 20000, 250)); D = rng.choice([75, 120, 150, 230, 310, 400]); r = rng.choice([2.5, 3.2, 4.1, 4.8, 5.3]); n = rng.choice([18, 30, 41, 55, 66])
    q = SAVE_W[w].format(S=S, D=D, r=r, n=n)
    if shift:
        k = rng.choice([6, 10, 12])
        q += f" After month {k} the deposits stop, but the money keeps earning interest."
        return q, save_bal(S, D, r, n, k), {"S": S, "D": D, "r": r, "n": n, "stop": k}
    return q, save_bal(S, D, r, n), {"S": S, "D": D, "r": r, "n": n}

# ---------- 3. shipping ----------
def ship(w_kg, a, b, c, s, d, remote=0):
    first = min(w_kg, 5) * a; mid = max(0, min(w_kg, 20) - 5) * b; top = max(0, w_kg - 20) * c
    sub = first + mid + top
    sub *= (1 + s / 100)
    sub += remote
    return money(sub * (1 - d / 100))
SHIP_W = [
    "A courier charges ${a} per kg for the first 5 kg, ${b} per kg for each kg from 5 to 20 kg, and ${c} per kg above 20 kg. A {s}% fuel surcharge is added to that, then a {d}% discount code is applied to the total. What does a {w} kg parcel cost, to the cent?",
    "Shipping a {w} kg box: rates are ${a}/kg up to 5 kg, ${b}/kg for the part between 5 and 20 kg, ${c}/kg for anything over 20 kg. Add {s}% fuel surcharge, then take {d}% off with a promo code. Final price?",
    "Tiered freight: tier 1 (0-5 kg) ${a}/kg, tier 2 (5-20 kg) ${b}/kg, tier 3 (>20 kg) ${c}/kg. Surcharge {s}% on the freight; afterwards a {d}% discount. Parcel weight {w} kg. Total in dollars and cents?",
]
def shipping(shift=False, w=0):
    wk = rng.choice([3.5, 7.2, 12.8, 18.4, 23.6, 31.5, 44.0]); a = rng.choice([4.2, 5.1, 6.0]); b = rng.choice([2.8, 3.35, 3.9]); c = rng.choice([1.6, 2.15, 2.4]); s = rng.choice([7.5, 9, 12.5]); d = rng.choice([10, 15, 20])
    q = SHIP_W[w].format(w=wk, a=a, b=b, c=c, s=s, d=d).replace(">", "over ")
    if shift:
        F = rng.choice([8.5, 12, 15.75])
        q += f" The address is in a remote area, so a flat ${F} remote fee is added after the surcharge and before the discount."
        return q, ship(wk, a, b, c, s, d, F), {"w": wk, "a": a, "b": b, "c": c, "s": s, "d": d, "remote": F}
    return q, ship(wk, a, b, c, s, d), {"w": wk, "a": a, "b": b, "c": c, "s": s, "d": d}

# ---------- 4. trains ----------
def fmt_t(mins): mins = int(math.floor(mins + 0.5)); return f"{(mins // 60) % 24:02d}:{mins % 60:02d}"
def meet(D, t1, v1, t2, v2, stop=0):
    # times in minutes after midnight; train1 may stop `stop` minutes at the halfway point of the line
    t = max(t1, t2)
    # simulate in tiny steps exactly: piecewise linear
    def pos1(T):
        if T <= t1: return 0.0
        half_t = t1 + (D / 2) / v1 * 60
        if stop and T > half_t:
            if T <= half_t + stop: return D / 2
            return D / 2 + v1 * (T - half_t - stop) / 60
        return v1 * (T - t1) / 60
    def pos2(T):
        if T <= t2: return D
        return D - v2 * (T - t2) / 60
    lo, hi = 0.0, 24 * 60 * 3
    for _ in range(200):
        mid = (lo + hi) / 2
        if pos1(mid) >= pos2(mid): hi = mid
        else: lo = mid
    return fmt_t(hi)
TRAIN_W = [
    "Two towns are {D} km apart on a straight line. Train A leaves the first town at {T1} going {v1} km/h toward the second. Train B leaves the second town at {T2} going {v2} km/h toward the first. At what clock time (HH:MM, 24-hour, nearest minute) do they meet?",
    "A freight train sets off from Ashford at {T1} at {v1} km/h heading for Brookvale, {D} km away. A passenger train leaves Brookvale at {T2} toward Ashford at {v2} km/h on a parallel track. When do they pass each other? Give HH:MM.",
    "Line length {D} km. Train 1: departs end A at {T1}, speed {v1} km/h. Train 2: departs end B at {T2}, speed {v2} km/h, opposite direction. Meeting time to the nearest minute (24h HH:MM)?",
]
def trains(shift=False, w=0):
    D = rng.choice([180, 245, 312, 390, 455]); v1 = rng.choice([64, 72, 85, 90]); v2 = rng.choice([58, 77, 96, 110])
    t1 = rng.choice(range(6 * 60, 10 * 60, 7)); t2 = t1 + rng.choice([-35, -12, 18, 26, 44])
    q = TRAIN_W[w].format(D=D, T1=fmt_t(t1), T2=fmt_t(t2), v1=v1, v2=v2)
    if shift:
        st = rng.choice([15, 20, 25])
        q += f" Train A stops for {st} minutes at a station exactly halfway along the line."
        ans = meet(D, t1, v1, t2, v2, st)
        return q, ans, {"D": D, "t1": fmt_t(t1), "v1": v1, "t2": fmt_t(t2), "v2": v2, "stop": st}
    return q, meet(D, t1, v1, t2, v2), {"D": D, "t1": fmt_t(t1), "v1": v1, "t2": fmt_t(t2), "v2": v2}

# ---------- 5. work rate ----------
def work(a, b, t, c=None):
    done = t * (1 / a + 1 / b)
    rate = 1 / b + (1 / c if c else 0)
    return int(math.floor((t + (1 - done) / rate) * 60 + 0.5))
WORK_W = [
    "Ana can paint a fence alone in {a} hours; Ben can paint it alone in {b} hours. They paint together for {t} hours, then Ana leaves and Ben finishes alone. How many minutes after they started is the fence finished (nearest minute)?",
    "Pump A fills a tank in {a} hours, pump B in {b} hours. Both run for {t} hours, then pump A breaks and B finishes the job. Total time from the start, in minutes, rounded?",
    "Worker rates: A completes the job in {a} h, B in {b} h. Joint work for {t} h, then only B. Total elapsed minutes (nearest)?",
]
def workrate(shift=False, w=0):
    a = rng.choice([3, 4.5, 5, 6, 7.5]); b = rng.choice([8, 9, 10, 12, 14]); t = rng.choice([0.75, 1.25, 1.5, 2])
    q = WORK_W[w].format(a=a, b=b, t=t)
    if shift:
        c = rng.choice([6, 9, 15])
        q += f" As soon as A stops, a third worker C, who could do the whole job alone in {c} hours, joins B until it is done."
        return q, work(a, b, t, c), {"a": a, "b": b, "t": t, "c": c}
    return q, work(a, b, t), {"a": a, "b": b, "t": t}

# ---------- 6. business days ----------
def add_bd(d0, n, hol=()):
    d = d0; k = 0
    while k < n:
        d += dt.timedelta(days=1)
        if d.weekday() < 5 and d not in hol: k += 1
    return d.isoformat()
BD_W = [
    "An invoice is dated {d}. Payment is due {n} business days later (Saturdays and Sundays don't count; the invoice date itself doesn't count). What is the due date (YYYY-MM-DD)?",
    "We shipped on {d} and the client has {n} working days (Mon-Fri) to pay, counting from the day after shipping. On what date is payment due? Answer as YYYY-MM-DD.",
    "Start date {d}. Add {n} business days, skipping weekends. Result date (ISO)?",
]
def bdays(shift=False, w=0):
    d0 = dt.date(2026, 1, 1) + dt.timedelta(days=rng.randrange(0, 330)); n = rng.choice([9, 14, 17, 23, 30, 38])
    q = BD_W[w].format(d=d0.isoformat(), n=n)
    if shift:
        # pick a weekday inside the window as a public holiday
        cands = []; d = d0
        for _ in range(n + 5):
            d += dt.timedelta(days=1)
            if d.weekday() < 5: cands.append(d)
        h = rng.choice(cands[2:n - 1])
        q += f" {h.isoformat()} is a public holiday and does not count as a business day either."
        return q, add_bd(d0, n, (h,)), {"d": d0.isoformat(), "n": n, "holiday": h.isoformat()}
    return q, add_bd(d0, n), {"d": d0.isoformat(), "n": n}

FAMS = {"loan": loan, "savings": savings, "shipping": shipping, "trains": trains, "workrate": workrate, "bizdays": bdays}
KIND = {"loan": "money", "savings": "money", "shipping": "money", "trains": "clock", "workrate": "int", "bizdays": "date"}
for fam, f in FAMS.items():
    q, a, p = f(False, 0); OUT.append(dict(id=f"{fam}_seed", fam=fam, kind=KIND[fam], split="seed", q=q, answer=a, params=p))
    for i in range(8):
        q, a, p = f(False, i % 3); OUT.append(dict(id=f"{fam}_v{i}", fam=fam, kind=KIND[fam], split="same", q=q, answer=a, params=p))
    for i in range(3):
        q, a, p = f(True, i % 3); OUT.append(dict(id=f"{fam}_x{i}", fam=fam, kind=KIND[fam], split="shift", q=q, answer=a, params=p))
json.dump(OUT, open("tasks.json", "w"), indent=1)
print(len(OUT), "tasks")
for t in OUT[:2] + OUT[9:10]: print(t["q"], "->", t["answer"])
