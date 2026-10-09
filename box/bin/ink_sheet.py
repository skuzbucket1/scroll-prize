#!/usr/bin/env python3
"""Stack the fast-ink previews of one winding (all depths, one side) into a labelled sheet for viewing.
Usage: ink_sheet.py <previews dir> <winding> <side read|blind> <out.jpg> [width=2400]"""
import sys, glob, os, re
from PIL import Image, ImageDraw
d, w, side, out = sys.argv[1:5]; W = int(sys.argv[5]) if len(sys.argv) > 5 else 2400
fs = sorted(glob.glob(os.path.join(d, f"{w}_d*_{side}.png")), key=lambda f: int(re.search(r"_d([+-]\d+)_", f).group(1)))
rows = []
for f in fs:
    im = Image.open(f).convert("L"); s = W / im.width; im = im.resize((W, int(im.height * s)), Image.LANCZOS)
    c = Image.new("L", (W, im.height + 24), 0); c.paste(im, (0, 24))
    ImageDraw.Draw(c).text((6, 4), f"{w}  depth {re.search(r'_d([+-]\d+)_', f).group(1)}  {side} side  (ink_9um seed 42)", fill=255)
    rows.append(c)
M = Image.new("L", (W, sum(r.height for r in rows)), 0); y = 0
for r in rows: M.paste(r, (0, y)); y += r.height
M.save(out, quality=85); print(out, M.size)
