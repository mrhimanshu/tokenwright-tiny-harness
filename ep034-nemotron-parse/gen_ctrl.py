#!/usr/bin/env python3
"""Control for the Hindi finding: separate type size from photo degradation.
ctrlsmall1-2 = small type (23 px) but clean; ctrlphoto1-2 = big type (31 px, same as clean pages) but photographed."""
import json
from PIL import Image, ImageDraw, ImageFont
import gen_pages as g
from gen_hard import photo_look
truth = json.loads((g.HERE / "truth.json").read_text())
for i, (title, body) in enumerate(g.HINDI[:2], 1):
    for kind, ts, bs, lh, photo in [("ctrlsmall", 34, 23, 40, False), ("ctrlphoto", 46, 31, 56, True)]:
        im = Image.new("RGB", (g.W, g.H), "white"); d = ImageDraw.Draw(im)
        ft, fb = ImageFont.truetype(g.DEVA, ts), ImageFont.truetype(g.DEVA, bs)
        y = 150; d.text((130, y), title, font=ft, fill="black"); y += int(ts * 2.4)
        for line in g.wrap(d, body, fb, g.W - 260):
            d.text((130, y), line, font=fb, fill="black"); y += lh
        if photo:
            im = photo_look(im, 600 + i, blur=1.0, scale=0.6, q=40)
        pid = f"{kind}{i}"; im.save(g.OUT / f"{pid}.png")
        truth[pid] = {"kind": "hindi", "tier": "control", "text": title + "\n" + body}
(g.HERE / "truth.json").write_text(json.dumps(truth, ensure_ascii=False, indent=1)); print("ok", len(truth))
