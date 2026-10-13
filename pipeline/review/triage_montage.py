#!/usr/bin/env python3
"""Stack triage CT previews (one row per winding, labelled, widths scaled to a common width) into one JPEG.
Usage: triage_montage.py <previews dir> <out.jpg> [width=2400] [w068 w069 ...]"""
import sys, os, glob
from PIL import Image, ImageDraw
d, out = sys.argv[1], sys.argv[2]; W = int(sys.argv[3]) if len(sys.argv) > 3 else 2400
names = sys.argv[4:] or sorted(os.path.basename(p)[:4] for p in glob.glob(os.path.join(d, "w*_ct_d0.png")))
rows = []
for n in names:
    p = os.path.join(d, f"{n}_ct_d0.png")
    if not os.path.exists(p): continue
    im = Image.open(p).convert("L"); s = W / im.width
    im = im.resize((W, max(1, int(im.height * s))), Image.LANCZOS)
    canvas = Image.new("L", (W, im.height + 28), 0); canvas.paste(im, (0, 28))
    ImageDraw.Draw(canvas).text((6, 6), f"{n}  (full width {Image.open(p).width * 2 * 9.362 / 10000:.1f} cm)", fill=255)
    rows.append(canvas)
H = sum(r.height for r in rows); M = Image.new("L", (W, H), 0); y = 0
for r in rows: M.paste(r, (0, y)); y += r.height
M.save(out, quality=85); print(out, M.size, len(rows), "rows")
