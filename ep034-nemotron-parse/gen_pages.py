#!/usr/bin/env python3
"""Build the EP034 test pages with known answers (seeded, reproducible).

5 kinds x 3 pages: report (scanned look), table, chart, handwriting (real IAM lines), hindi.
Writes pages/<id>.png and truth.json.
"""
import io, json, random
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE / "pages"
OUT.mkdir(exist_ok=True)
W, H = 1240, 1754  # A4 at 150 dpi
LIB = "/usr/share/fonts/truetype/liberation/"
SERIF = LIB + "LiberationSerif-Regular.ttf"
SERIF_B = LIB + "LiberationSerif-Bold.ttf"
SANS = LIB + "LiberationSans-Regular.ttf"
SANS_B = LIB + "LiberationSans-Bold.ttf"
DEVA = str(HERE / "data" / "NotoSansDevanagari-Regular.ttf")
rng = random.Random(34)
truth = {}


def wrap(draw, text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def scan_look(im, seed):
    """Photocopy look: slight tilt, blur, grey paper, noise, JPEG."""
    r = random.Random(seed)
    im = im.convert("L")
    im = im.rotate(r.uniform(-1.2, 1.2), resample=Image.BICUBIC, fillcolor=255, expand=False)
    im = im.filter(ImageFilter.GaussianBlur(0.8))
    a = np.asarray(im).astype(np.float32)
    a = a * 0.82 + 30  # grey paper, faded ink
    a += np.random.default_rng(seed).normal(0, 9, a.shape)
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGB")
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=55)
    return Image.open(io.BytesIO(buf.getvalue())).convert("RGB")


# ---------------- 1. reports (scanned) ----------------
REPORTS = [
    ("Quarterly Operations Review",
     ["In the third quarter the support team closed 18,442 tickets, up 12.5% on the previous quarter. "
      "The median first response time fell from 4 hours 10 minutes to 1 hour 52 minutes, mainly because "
      "routine password resets are now handled by the self-service portal.",
      "Costs rose more slowly than volume. Total spend was $214,380 against a budget of $229,000, "
      "leaving an underspend of $14,620. The largest single item was overtime during the September "
      "migration, which accounted for 31% of all extra hours.",
      "Two risks remain open. First, the legacy billing server reaches end of support on 14 March 2027. "
      "Second, three of the nine senior engineers are due for parental leave in the same month, so the "
      "migration plan must be finished before 28 February."]),
    ("Field Notes: Water Quality Survey",
     ["Samples were taken at 27 sites along the river between 3 and 9 June. At each site we measured "
      "temperature, pH, dissolved oxygen and nitrate. The average pH was 7.4, with a low of 6.8 below "
      "the paper mill outflow and a high of 8.1 at the reservoir.",
      "Dissolved oxygen stayed above 6.0 mg/L at 24 of the 27 sites. The three exceptions were all "
      "downstream of the treatment works, where readings of 4.9, 5.2 and 5.6 mg/L were recorded "
      "on the warmest afternoon of the week.",
      "Nitrate levels were within the legal limit everywhere, but site 19 showed 41 mg/L, close to the "
      "50 mg/L threshold. We recommend monthly sampling at sites 17 to 21 until the end of 2027."]),
    ("Minutes of the Library Committee",
     ["The meeting opened at 7:15 pm with eleven members present and two apologies. The minutes of the "
      "October meeting were approved without changes. The treasurer reported a balance of $8,906.40 "
      "after the purchase of 312 new books and two reading lamps.",
      "Visitor numbers have recovered. The library recorded 5,731 visits in October compared with 4,018 "
      "a year earlier, an increase of 42.6%. Saturday mornings remain the busiest period, with an "
      "average of 163 visitors between 9 am and noon.",
      "The committee agreed to extend opening hours on Thursdays until 8 pm from 6 January, for a trial "
      "period of twelve weeks. The next meeting will be held on 2 December at 7 pm in the reading room."]),
]
for i, (title, paras) in enumerate(REPORTS, 1):
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    ft, fb = ImageFont.truetype(SERIF_B, 44), ImageFont.truetype(SERIF, 29)
    y = 150
    d.text((130, y), title, font=ft, fill="black")
    y += 100
    for p in paras:
        for line in wrap(d, p, fb, W - 260):
            d.text((130, y), line, font=fb, fill="black")
            y += 44
        y += 30
    pid = f"report{i}"
    scan_look(im, 100 + i).save(OUT / f"{pid}.png")
    truth[pid] = {"kind": "report", "text": title + "\n" + "\n".join(paras)}

# ---------------- 2. tables ----------------
ITEMS = ["USB-C cable 2 m", "Laptop stand", "Wireless mouse", "27-inch monitor", "Desk lamp", "Webcam 1080p",
         "Keyboard (UK)", "Noise-cancelling headset", "HDMI adapter", "Office chair", "Cable tray", "Docking station",
         "Ethernet switch 8-port", "Label printer", "Whiteboard 120 cm", "Paper shredder", "Laptop bag", "SSD 1 TB"]
for i in range(1, 4):
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    ft, fh, fc = ImageFont.truetype(SANS_B, 40), ImageFont.truetype(SANS_B, 26), ImageFont.truetype(SANS, 26)
    d.text((110, 140), f"Purchase order PO-{4400 + 17 * i}", font=ft, fill="black")
    d.text((110, 200), f"Supplier: Northfield Office Supply   Date: {i + 9} November 2026", font=fc, fill="black")
    header = ["Item", "Qty", "Unit price", "Line total"]
    items = rng.sample(ITEMS, 10)
    rows = []
    for it in items:
        q = rng.randint(1, 40)
        up = rng.choice([4.99, 12.50, 18.75, 23.40, 39.00, 64.95, 129.00, 249.99, 7.25, 89.90, 15.80, 310.00])
        rows.append([it, str(q), f"${up:,.2f}", f"${q * up:,.2f}"])
    xs = [110, 620, 760, 960, 1140]
    y0, rh = 290, 62
    allrows = [header] + rows
    for r, row in enumerate(allrows):
        y = y0 + r * rh
        if r == 0:
            d.rectangle([xs[0], y, xs[-1], y + rh], fill=(225, 225, 225))
        for c, val in enumerate(row):
            f = fh if r == 0 else fc
            if c == 0:
                d.text((xs[c] + 14, y + 16), val, font=f, fill="black")
            else:
                tw = d.textlength(val, font=f)
                d.text((xs[c + 1] - 14 - tw, y + 16), val, font=f, fill="black")
    for r in range(len(allrows) + 1):
        d.line([xs[0], y0 + r * rh, xs[-1], y0 + r * rh], fill="black", width=2)
    for x in xs:
        d.line([x, y0, x, y0 + len(allrows) * rh], fill="black", width=2)
    total = sum(float(r[3][1:].replace(",", "")) for r in rows)
    d.text((760, y0 + len(allrows) * rh + 30), f"Total: ${total:,.2f}", font=fh, fill="black")
    pid = f"table{i}"
    im.save(OUT / f"{pid}.png")
    truth[pid] = {"kind": "table", "header": header, "rows": rows, "total": f"${total:,.2f}"}

# ---------------- 3. charts ----------------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
CHARTS = [("Monthly active users (thousands)", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"]),
          ("Average response time by region (ms)", ["London", "Paris", "Frankfurt", "Mumbai", "Tokyo", "Sydney"]),
          ("Share of tickets solved on first contact (%)", ["Email", "Chat", "Phone", "Forum", "Social", "Kiosk"])]
for i, (title, cats) in enumerate(CHARTS, 1):
    vals = [rng.randint(12, 96) for _ in cats]
    fig = plt.figure(figsize=(W / 150, H / 150), dpi=150)
    fig.text(0.08, 0.93, f"Figure {i}. {title}", fontsize=15, family="DejaVu Sans")
    fig.text(0.08, 0.90, "Source: internal dashboard, 2026", fontsize=10, color="#555", family="DejaVu Sans")
    ax = fig.add_axes([0.12, 0.45, 0.8, 0.4])
    ax.bar(cats, vals, color="#4C72B0", width=0.6)
    ax.set_ylim(0, 100)
    ax.set_yticks(range(0, 101, 10))
    ax.grid(axis="y", color="#ccc", linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.text(0.08, 0.36, "The chart above has no value labels: the numbers must be read from the axis.",
             fontsize=11, family="DejaVu Sans")
    pid = f"chart{i}"
    fig.savefig(OUT / f"{pid}.png", dpi=150, facecolor="white")
    plt.close(fig)
    truth[pid] = {"kind": "chart", "title": title, "categories": cats, "values": vals}

# ---------------- 4. handwriting (real IAM test lines) ----------------
iam = pd.read_parquet(HERE / "data" / "test.parquet")
idx = list(range(len(iam)))
rng.shuffle(idx)
pos = 0
for i in range(1, 4):
    im = Image.new("RGB", (W, H), "white")
    lines, y = [], 120
    while len(lines) < 7:
        row = iam.iloc[idx[pos]]
        pos += 1
        li = Image.open(io.BytesIO(row["image"]["bytes"])).convert("RGB")
        scale = min(1.0, (W - 160) / li.width)
        li = li.resize((int(li.width * scale), int(li.height * scale)))
        if y + li.height > H - 120:
            break
        im.paste(li, (80, y))
        y += li.height + 40
        lines.append(row["text"])
    pid = f"hand{i}"
    im.save(OUT / f"{pid}.png")
    truth[pid] = {"kind": "handwriting", "text": "\n".join(lines), "source": "Teklia/IAM-line test split"}

# ---------------- 5. Hindi (hi.wikipedia summaries, 26 Nov 2026) ----------------
HINDI = [
    ("भारत", "भारत दक्षिण एशिया में स्थित भारतीय उपमहाद्वीप का सबसे बड़ा देश है। भारत भौगोलिक दृष्टि से विश्व का सातवाँ सबसे बड़ा देश है, जबकि जनसंख्या के दृष्टिकोण से विश्व का सबसे बड़ा देश है। भारत के पश्चिम में पाकिस्तान, उत्तर पश्चिम में अफगानिस्तान, उत्तर-पूर्व में चीन, नेपाल और भूटान, पूर्व में बांग्लादेश और म्यान्मार स्थित हैं। इसके उत्तर में हिमालय पर्वत तथा दक्षिण में भारतीय महासागर स्थित है।"),
    ("ताजमहल", "ताजमहल भारत के उत्तर प्रदेश राज्य के आगरा शहर में स्थित एक विश्व धरोहर मक़बरा, और विश्व के ७ अजूबों में से एक है। इसका निर्माण १७वीं सदी में मुग़ल सम्राट शाहजहाँ ने अपनी पत्नी मुमताज़ महल की याद में करवाया था। सफ़ेद संगमरमर से बने इस मक़बरे को देखने हर साल लाखों पर्यटक आगरा आते हैं।"),
    ("गंगा नदी", "गंगा नदी भारत की सबसे महत्त्वपूर्ण व हिन्दू धर्म की मान्यतानुसार सबसे पवित्र नदी है। गंगा नदी का उद्गम भागीरथी व अलकनंदा नदी मिलकर करती है। यह भारत और बांग्लादेश में कुल मिलाकर 2526 किलोमीटर की दूरी तय करती हुई उत्तराखंड में हिमालय के गंगोत्री हिमनद के गोमुख स्थान से लेकर बंगाल की खाड़ी के सुन्दरवन तक भारत की मुख्य नदी के रूप में विशाल भू-भाग को सींचती है।"),
]
for i, (title, body) in enumerate(HINDI, 1):
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    ft, fb = ImageFont.truetype(DEVA, 46), ImageFont.truetype(DEVA, 31)
    y = 150
    d.text((130, y), title, font=ft, fill="black")
    y += 110
    for line in wrap(d, body, fb, W - 260):
        d.text((130, y), line, font=fb, fill="black")
        y += 56
    pid = f"hindi{i}"
    im.save(OUT / f"{pid}.png")
    truth[pid] = {"kind": "hindi", "text": title + "\n" + body, "source": "hi.wikipedia.org page summary"}

(HERE / "truth.json").write_text(json.dumps(truth, ensure_ascii=False, indent=1))
print("pages:", len(truth))
