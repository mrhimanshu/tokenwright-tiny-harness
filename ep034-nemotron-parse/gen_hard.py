#!/usr/bin/env python3
"""Harder tier: phone-photo tables, charts read between gridlines, degraded small Hindi, dense 2-column scans.
Adds pages/hard*.png and merges into truth.json."""
import io, json, random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import gen_pages as g  # reuses fonts, wrap(), ITEMS (re-running it rebuilds the easy pages identically)

HERE = g.HERE
OUT = g.OUT
truth = json.loads((HERE / "truth.json").read_text())
rng = random.Random(3434)
W, H = g.W, g.H


def photo_look(im, seed, blur=1.5, tilt=3.0, scale=0.55, q=35, noise=12):
    r = random.Random(seed)
    im = im.convert("L")
    im = im.rotate(r.uniform(-tilt, tilt), resample=Image.BICUBIC, fillcolor=235, expand=False)
    sw, sh = int(im.width * scale), int(im.height * scale)
    im = im.resize((sw, sh), Image.BILINEAR).resize((W, H), Image.BILINEAR)
    im = im.filter(ImageFilter.GaussianBlur(blur))
    a = np.asarray(im).astype(np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    shade = 1 - 0.25 * ((xx / W - 0.3) ** 2 + (yy / H - 0.2) ** 2)  # uneven lighting
    a = a * 0.78 * shade + 25
    a += np.random.default_rng(seed).normal(0, noise, a.shape)
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGB")
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=q)
    return Image.open(io.BytesIO(buf.getvalue())).convert("RGB")


# hard tables: borderless, 14 rows, photographed
for i in range(1, 4):
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    fh, fc = ImageFont.truetype(g.SANS_B, 24), ImageFont.truetype(g.SANS, 24)
    d.text((110, 130), f"Stock count - warehouse {chr(64 + i)}", font=ImageFont.truetype(g.SANS_B, 36), fill="black")
    header = ["Item", "Qty", "Unit price", "Line total"]
    rows = []
    for it in rng.sample(g.ITEMS, 14):
        q = rng.randint(1, 60)
        up = round(rng.uniform(2, 400), 2)
        rows.append([it, str(q), f"${up:,.2f}", f"${q * up:,.2f}"])
    xs = [110, 620, 760, 960, 1140]
    y0, rh = 230, 50
    for r, row in enumerate([header] + rows):
        y = y0 + r * rh
        for c, val in enumerate(row):
            f = fh if r == 0 else fc
            if c == 0:
                d.text((xs[c] + 4, y), val, font=f, fill="black")
            else:
                d.text((xs[c + 1] - 4 - d.textlength(val, font=f), y), val, font=f, fill="black")
        if r == 0:
            d.line([xs[0], y + 38, xs[-1], y + 38], fill="black", width=2)
    total = sum(float(r[3][1:].replace(",", "")) for r in rows)
    d.text((760, y0 + 15 * rh + 20), f"Total: ${total:,.2f}", font=fh, fill="black")
    pid = f"hardtable{i}"
    photo_look(im, 300 + i).save(OUT / f"{pid}.png")
    truth[pid] = {"kind": "table", "tier": "hard", "header": header, "rows": rows, "total": f"${total:,.2f}"}

# hard charts: gridlines every 25, values not on gridlines
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
HC = [("Weekly deploys per team", ["Search", "Billing", "Mobile", "Infra", "Data", "Growth", "Docs"]),
      ("Cache hit rate by service (%)", ["auth", "cart", "feed", "img", "mail", "pay"]),
      ("GPU hours used per lab", ["Vision", "Speech", "NLP", "Robotics", "Bio", "RL"])]
for i, (title, cats) in enumerate(HC, 1):
    vals = []
    while len(vals) < len(cats):
        v = rng.randint(5, 98)
        if v % 25 not in (0, 1, 24):  # never sits on a gridline
            vals.append(v)
    fig = plt.figure(figsize=(W / 150, H / 150), dpi=150)
    fig.text(0.08, 0.93, title, fontsize=15, family="DejaVu Sans")
    ax = fig.add_axes([0.12, 0.5, 0.8, 0.36])
    ax.bar(cats, vals, color="#4C72B0", width=0.6)
    ax.set_ylim(0, 100)
    ax.set_yticks(range(0, 101, 25))
    ax.grid(axis="y", color="#ddd", linewidth=0.8)
    ax.set_axisbelow(True)
    pid = f"hardchart{i}"
    fig.savefig(OUT / f"{pid}.png", dpi=150, facecolor="white")
    plt.close(fig)
    truth[pid] = {"kind": "chart", "tier": "hard", "title": title, "categories": cats, "values": vals}

# hard Hindi: small type, photographed
for i, (title, body) in enumerate(g.HINDI, 1):
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    ft, fb = ImageFont.truetype(g.DEVA, 34), ImageFont.truetype(g.DEVA, 23)
    y = 150
    d.text((130, y), title, font=ft, fill="black")
    y += 80
    for line in g.wrap(d, body, fb, W - 260):
        d.text((130, y), line, font=fb, fill="black")
        y += 40
    pid = f"hardhindi{i}"
    photo_look(im, 400 + i, blur=1.0, scale=0.6, q=40).save(OUT / f"{pid}.png")
    truth[pid] = {"kind": "hindi", "tier": "hard", "text": title + "\n" + body}

# hard report: two columns, 21 px, photographed
for i, (title, paras) in enumerate(g.REPORTS, 1):
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    ft, fb = ImageFont.truetype(g.SERIF_B, 34), ImageFont.truetype(g.SERIF, 21)
    d.text((110, 120), title, font=ft, fill="black")
    colw = (W - 220 - 50) // 2
    lines = []
    for p in paras:
        lines += g.wrap(d, p, fb, colw) + [""]
    half = (len(lines) + 1) // 2
    for c, chunk in enumerate([lines[:half], lines[half:]]):
        y = 200
        for line in chunk:
            d.text((110 + c * (colw + 50), y), line, font=fb, fill="black")
            y += 31
    pid = f"hardreport{i}"
    photo_look(im, 500 + i, blur=1.1, scale=0.6, q=40).save(OUT / f"{pid}.png")
    truth[pid] = {"kind": "report", "tier": "hard", "text": title + "\n" + "\n".join(paras)}

for k, v in truth.items():
    v.setdefault("tier", "easy")
(HERE / "truth.json").write_text(json.dumps(truth, ensure_ascii=False, indent=1))
print("pages:", len(truth))
