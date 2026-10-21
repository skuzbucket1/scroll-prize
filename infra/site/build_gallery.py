#!/usr/bin/env python3
"""Build data/viewer/gallery.html: every result image we keep on the Mac, next to the winding viewer (index.html).
Sections: the 3D views in data/viewer/3d/*.html first (a <name>.jpg next to a page is its preview), then each folder under
data/results/ (newest first), then the loose images in data/results/ grouped by scroll (the PHercNNNN at the start of
the file name). JPEG and PNG only (TIFFs are left out); thumbnails load lazily; a click opens the full image.
Private: data/ is not versioned. Python stdlib only. Usage: python3 infra/site/build_gallery.py [viewer dir]"""
import html, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VIEW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'data', 'viewer')
if os.path.realpath(VIEW).startswith(os.path.realpath(os.path.join(ROOT, 'docs'))):   # privacy (2026-10-15): the viewer holds private reads
    sys.exit('refusing: the viewer is private and must not be written under docs/')
RES = os.path.join(ROOT, 'data', 'results')
IMG = re.compile(r'\.(jpe?g|png)$', re.I)


def rel(p):
    return os.path.relpath(p, VIEW).replace(os.sep, '/')


sections = []
D3 = os.path.join(VIEW, '3d')
if os.path.isdir(D3):
    cards = []
    for f in sorted(os.listdir(D3)):
        if f.endswith('.html'):
            prev = os.path.join(D3, f[:-5] + '.jpg')
            cards.append(dict(href=rel(os.path.join(D3, f)), img=rel(prev) if os.path.exists(prev) else None,
                              cap=f[:-5] + ' (opens the 3D view)'))
    if cards:
        sections.append(('3D views', 'drag to rotate, scroll to zoom; the sliders cut the stack and set the opacity', cards))
folders, loose = [], {}
if os.path.isdir(RES):
    for d, sub, files in os.walk(RES):
        sub.sort()
        if d == RES:
            for f in sorted(files):
                if IMG.search(f):
                    m = re.match(r'(PHerc\d+[A-Z]?)', f)
                    loose.setdefault(m.group(1) if m else 'other', []).append(os.path.join(d, f))
            continue
        pics = [os.path.join(d, f) for f in sorted(files) if IMG.search(f) or f.endswith('.html')]
        if pics:
            folders.append((max(os.path.getmtime(p) for p in pics), os.path.relpath(d, RES), pics))
for _, name, pics in sorted(folders, reverse=True):
    sections.append((name, f'data/results/{name}', [dict(href=rel(p), img=rel(p) if IMG.search(p) else None,
                                                         cap=os.path.basename(p)) for p in pics]))
for k in sorted(loose):
    sections.append((f'{k} (loose images)', 'data/results/', [dict(href=rel(p), img=rel(p), cap=os.path.basename(p)) for p in loose[k]]))

out = ['''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Gallery</title><link rel="stylesheet" href="hv-theme.css"><script src="hv-nav.js" defer></script>
<style>body{margin:0;background:#0d0d0d;color:#f2f2f0;font:14px/1.4 system-ui,-apple-system,sans-serif}
header{position:sticky;top:40px;background:#0d0d0d;padding:10px 16px;border-bottom:1px solid rgba(255,255,255,.12);display:flex;gap:14px;align-items:center;z-index:2}
header a{color:#7fb6ff}header input{background:#1d1d1c;color:#f2f2f0;border:1px solid rgba(255,255,255,.12);border-radius:4px;padding:5px 8px;width:260px}
section{padding:6px 16px 14px}h2{font-size:15px;margin:14px 0 2px}h2 small{color:#6d6c68;font-weight:normal;margin-left:8px}
.g{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px;margin-top:8px}
.c{background:#1d1d1c;border:1px solid rgba(255,255,255,.12);border-radius:4px;overflow:hidden}.c a{color:#f2f2f0;text-decoration:none;display:block}
.c img{width:100%;height:200px;object-fit:contain;background:#000;display:block}.c .x{height:200px;display:flex;align-items:center;justify-content:center;color:#e0a33c}
.c p{margin:0;padding:5px 7px;font-size:12px;color:#8a8984;word-break:break-all}</style></head><body>
<header><b>Gallery</b><input id="q" placeholder="filter by name" autocomplete="off"><span id="n"></span></header>''']
for title, sub, cards in sections:
    out.append(f'<section><h2>{html.escape(title)}<small>{html.escape(sub)} &middot; {len(cards)}</small></h2><div class="g">')
    for c in cards:
        inner = f'<img loading="lazy" src="{html.escape(c["img"])}">' if c['img'] else '<div class="x">open</div>'
        out.append(f'<div class="c" data-k="{html.escape((title + " " + c["cap"]).lower())}"><a href="{html.escape(c["href"])}">'
                   f'{inner}<p>{html.escape(c["cap"])}</p></a></div>')
    out.append('</div></section>')
out.append('''<script>const q=document.getElementById('q'),n=document.getElementById('n');
function f(){const v=q.value.toLowerCase();let k=0;for(const c of document.querySelectorAll('.c')){const s=!v||c.dataset.k.includes(v);c.style.display=s?'':'none';k+=s}
for(const s of document.querySelectorAll('section'))s.style.display=[...s.querySelectorAll('.c')].some(c=>c.style.display!=='none')?'':'none';n.textContent=k+' items'}
q.oninput=f;f();</script></body></html>''')
p = os.path.join(VIEW, 'gallery.html')
open(p, 'w').write('\n'.join(out))
print(f'{p}: {len(sections)} sections, {sum(len(c) for _, _, c in sections)} items')
