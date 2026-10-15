#!/usr/bin/env python3
"""Build a local, offline viewer of every inked winding: data/viewer/index.html (open it by double-click).
Inputs: data/viewer/img/<set>/<group>/<w>/ with <w>__{ct,ens_reading,ens_blind}__d+NN.jpg and <w>__post.json
(stroke-score numbers per depth). The page embeds a small manifest; images stay in img/ and load by relative path.
Optional data/viewer/links.json (pipeline/review/viewer_links.py): for each winding, the same place on its neighbours in the list,
found through the 3D meshes, and the real size of a preview pixel; with it, the arrow keys keep the spot you are zoomed
on, and the scale bar and the Shift-drag ruler use the measured pixel size (else 2 x 9.362 um).
Private: data/ is not versioned. Python stdlib only. Usage: python3 infra/site/build_viewer.py [viewer dir]"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VIEW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'data', 'viewer')
if os.path.realpath(VIEW).startswith(os.path.realpath(os.path.join(ROOT, 'docs'))):   # privacy (2026-10-15): the viewer holds private reads
    sys.exit('refusing: the viewer is private and must not be written under docs/')
IMG = os.path.join(VIEW, 'img')
# known groups: folder -> (scroll, band, model set); any other <set>/<group> folder is picked up with its folder name
GROUPS = {
    'tier23/PHerc0813': ('PHerc0813', 'z 12,000–13,000', 'Reader v2 + d9v4C'),
    'tier23/PHerc0191': ('PHerc0191', 'z 11,200–12,200', 'Reader v2 + d9v4C'),
    'v02nulls/PHerc0191-three': ('PHerc0191', 'z 11,200–12,200', 'three models (ink_9um ×2 + dense_native)'),
}
# more labels in data/viewer/groups.json ({"<set>/<group>": [scroll, band, models]}; private, not versioned)
GJ = os.path.join(VIEW, 'groups.json')
if os.path.exists(GJ):
    GROUPS.update({k: tuple(v) for k, v in json.load(open(GJ)).items()})
KINDS = {'ct': 'ct', 'ens_reading': 'reading', 'ens_blind': 'blind'}
FILE = re.compile(r'^(w\d+)__(ct|ens_reading|ens_blind)__d([+-]\d+)\.jpg$')


def jpeg_size(path):
    """(width, height) from the first SOF marker of a JPEG, or None."""
    with open(path, 'rb') as f:
        if f.read(2) != b'\xff\xd8':
            return None
        while True:
            b = f.read(1)
            while b and b != b'\xff':
                b = f.read(1)
            while b == b'\xff':
                b = f.read(1)
            if not b:
                return None
            m = b[0]
            if m == 0x01 or 0xD0 <= m <= 0xD8:
                continue
            n = int.from_bytes(f.read(2), 'big')
            if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                f.read(1)
                h, w = int.from_bytes(f.read(2), 'big'), int.from_bytes(f.read(2), 'big')
                return w, h
            f.seek(n - 2, 1)


def num(x, nd):
    return None if x is None else round(float(x), nd)


groups, odd = [], []
for s in sorted(os.listdir(IMG)):
    if not os.path.isdir(os.path.join(IMG, s)):
        continue
    for g in sorted(os.listdir(os.path.join(IMG, s))):
        gdir = os.path.join(IMG, s, g)
        if not os.path.isdir(gdir):
            continue
        key = f'{s}/{g}'
        scroll, band, models = GROUPS.get(key, (g, '', s))
        items = []
        for w in sorted(os.listdir(gdir)):
            wdir = os.path.join(gdir, w)
            if not os.path.isdir(wdir):
                continue
            depths = {}
            for fn in sorted(os.listdir(wdir)):
                m = FILE.match(fn)
                if not m:
                    continue
                d = str(int(m.group(3)))
                depths.setdefault(d, {})[KINDS[m.group(2)]] = f'img/{key}/{w}/{fn}'
            post = {}
            pj = os.path.join(wdir, f'{w}__post.json')
            if os.path.exists(pj):
                try:
                    post = json.load(open(pj)).get('depths', {})
                except (ValueError, OSError) as e:
                    odd.append(f'{key}/{w}: unreadable post.json ({e})')
            for d, e in depths.items():
                size = None
                for k in ('ct', 'reading', 'blind'):
                    if k in e:
                        size = jpeg_size(os.path.join(VIEW, e[k]))
                        if size:
                            break
                e['w'], e['h'] = size if size else (0, 0)
                p = post.get(d, {})
                rr, ar, ab = p.get('row_R'), p.get('area_R'), p.get('area_B')
                e['rows'] = num(rr, 2)
                e['rb'] = num(ar - ab, 4) if ar is not None and ab is not None else None
                miss = [k for k in ('ct', 'reading', 'blind') if k not in e]
                if miss:
                    odd.append(f'{key}/{w} d{d}: missing {", ".join(miss)}')
            if not depths:
                odd.append(f'{key}/{w}: no images')
                continue
            items.append({'w': w, 'depths': depths})
        if items:
            groups.append({'id': key, 'scroll': scroll, 'band': band, 'models': models, 'items': items})
order = list(GROUPS)
groups.sort(key=lambda g: (order.index(g['id']) if g['id'] in order else len(order), g['id']))
LINKS = os.path.join(VIEW, 'links.json')
links = json.load(open(LINKS)) if os.path.exists(LINKS) else {}
for g in groups:
    for it in g['items']:
        e = links.get(g['id'], {}).get(it['w'])
        if e:
            it['um'] = e.get('um_px')
            it['links'] = {k: e[k] for k in ('prev', 'next') if k in e}

manifest = json.dumps({'groups': groups}, separators=(',', ':')).replace('</', '<\\/')
GALLERY = (('<a href="findings.html" style="color:var(--acc);margin-left:10px"><b>Findings</b> &rarr;</a>'
            if os.path.exists(os.path.join(VIEW, 'findings.html')) else '') +
           ('<a href="gallery.html" style="color:var(--acc);margin-left:10px">Gallery: 3D views and every other result image &rarr;</a>'
            if os.path.exists(os.path.join(VIEW, 'gallery.html')) else ''))
HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Inked windings</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{--bg:#141414;--panel:#1d1d1d;--line:#2c2c2c;--ink:#e8e6e1;--ink2:#a9a6a0;--ink3:#77746f;--sel:#3a3226;--acc:#e0a33c}
*{box-sizing:border-box}html,body{margin:0;height:100%;background:var(--bg);color:var(--ink);font:14px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
body{display:grid;grid-template-columns:300px 1fr;grid-template-rows:auto 1fr;height:100vh;overflow:hidden}
header{grid-column:1/3;padding:10px 16px;border-bottom:1px solid var(--line);color:var(--ink2)}
header b{color:var(--ink)}
aside{border-right:1px solid var(--line);display:flex;flex-direction:column;min-height:0}
.tools{padding:10px;display:flex;gap:6px;border-bottom:1px solid var(--line)}
.tools input,.tools select{background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:4px;padding:5px 7px;font:inherit}
.tools input{flex:1;min-width:0}
#list{overflow-y:auto;flex:1;padding-bottom:8px}
.gh{position:sticky;top:0;background:#191919;padding:8px 10px 6px;border-bottom:1px solid var(--line);font-size:12px;color:var(--ink2);z-index:1}
.gh b{color:var(--ink);font-size:13px}
.it{display:grid;grid-template-columns:52px 1fr 1fr;gap:4px;padding:3px 10px;cursor:pointer;font-variant-numeric:tabular-nums;font-size:13px}
.it:hover{background:#232323}.it.on{background:var(--sel)}
.it .n{color:var(--ink)}.it .v{color:var(--ink2);text-align:right}.it .v i{font-style:normal;color:var(--ink3);font-size:11px;margin-right:3px}
.legend{padding:8px 10px;border-top:1px solid var(--line);font-size:12px;color:var(--ink3)}
main{display:flex;flex-direction:column;min-width:0;min-height:0}
.bar{display:flex;flex-wrap:wrap;align-items:center;gap:14px;padding:8px 14px;border-bottom:1px solid var(--line)}
.bar .title{font-size:16px}.bar .title b{font-size:18px}.bar .meta{color:var(--ink2)}
.bar button{background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:4px;padding:4px 10px;font:inherit;cursor:pointer}
.bar button.on{border-color:var(--acc);color:var(--acc)}.bar button:disabled{opacity:.35;cursor:default}
.bar label{color:var(--ink2);cursor:pointer;user-select:none}
.spacer{flex:1}
#panels{flex:1;overflow:auto;padding:6px 14px 14px}
.lab{font-size:12px;color:var(--ink2);margin:8px 0 3px}
.pane{position:relative;overflow:hidden;background:#0c0c0c;border:1px solid var(--line);border-radius:3px;cursor:grab;touch-action:none}
.pane.drag{cursor:grabbing}
.stage{position:absolute;left:0;top:0;transform-origin:0 0;will-change:transform}
.stage img{display:block;width:100%;height:100%;user-select:none;-webkit-user-drag:none;pointer-events:none}
.stage img.rot{transform:rotate(180deg)}
.missing{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:var(--ink3)}
.keys{color:var(--ink3);font-size:12px}
.info{padding:4px 14px;min-height:22px;color:var(--acc);font-size:12px;border-bottom:1px solid var(--line)}
.ov{position:absolute;left:0;top:0;width:100%;height:100%;pointer-events:none}
.sbar{position:absolute;left:10px;bottom:8px;color:#fff;font-size:11px;text-shadow:0 0 3px #000,0 0 2px #000;pointer-events:none}
.sbar i{display:block;height:3px;background:#fff;box-shadow:0 0 2px #000;margin-bottom:3px}
</style></head><body>
<header><b>Ink previews, half resolution.</b> Bright = the models see ink. Real writing shows on the reading side only, in rows of thin strokes; cracks and damage often show on both sides. Letters are about 2–4 mm tall. GALLERY</header>
<aside>
  <div class="tools"><input id="q" placeholder="filter, e.g. w09 or 0813" autocomplete="off">
    <select id="sort" title="sort"><option value="w">winding</option><option value="rows">rows ↓</option><option value="rb">R−B ↓</option></select></div>
  <div id="list"></div>
  <div class="legend">rows = how much the reading-side ink lines up in rows like text (stroke-score 0.2 row score). R−B = inked share of the reading side minus the blind side. Both for the depth shown.</div>
</aside>
<main>
  <div class="bar">
    <span class="title"><b id="t-w">–</b> <span id="t-s"></span></span><span class="meta" id="t-m"></span>
    <span class="spacer"></span>
    <button id="d0">d0</button><button id="d1">d+1</button>
    <label><input type="checkbox" id="rot" checked> reading orientation</label>
    <button id="reset">reset</button>
    <span class="keys">← → winding (keeps your spot when zoomed in) · ↑ ↓ / D depth · Shift-drag measure · Esc clear · R reset · F flip</span>
  </div>
  <div class="info" id="info"></div>
  <div id="panels">
    <div class="lab">CT</div><div class="pane" data-k="ct"></div>
    <div class="lab">ink, reading side</div><div class="pane" data-k="reading"></div>
    <div class="lab">ink, blind side</div><div class="pane" data-k="blind"></div>
  </div>
</main>
<script id="manifest" type="application/json">__MANIFEST__</script>
<script>
const M = JSON.parse(document.getElementById('manifest').textContent);
const panes = [...document.querySelectorAll('.pane')];
const st = {g: null, it: null, depth: '0', rot: true, sort: 'w', q: ''};
const v = {s: 1, tx: 0, ty: 0, fit: 1};
let flat = [], ruler = null, flash = 0;
const umPx = () => (st.it && st.it.um) || 18.72;          // um per preview pixel (half-resolution previews)
const NICE = [0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50];
const $ = id => document.getElementById(id);
const fmt = (x, n) => x == null ? '–' : (Math.abs(x) < 0.5 * 10 ** -n ? 0 : x).toFixed(n);
const cur = () => st.it && (st.it.depths[st.depth] || st.it.depths[Object.keys(st.it.depths)[0]]);

function buildList() {
  const L = $('list'); L.innerHTML = ''; flat = [];
  const q = st.q.trim().toLowerCase();
  for (const g of M.groups) {
    let items = g.items.filter(it => !q || (it.w + ' ' + g.scroll + ' ' + g.models).toLowerCase().includes(q));
    if (!items.length) continue;
    const val = it => { const d = it.depths[st.depth]; return d ? (st.sort === 'rows' ? d.rows : d.rb) : null; };
    if (st.sort !== 'w') items = items.slice().sort((a, b) => (val(b) ?? -1e9) - (val(a) ?? -1e9));
    const h = document.createElement('div'); h.className = 'gh';
    h.innerHTML = `<b>${g.scroll}</b> · ${g.band}<br>${g.models} · ${items.length} windings`; L.appendChild(h);
    for (const it of items) {
      const d = it.depths[st.depth] || {};
      const r = document.createElement('div'); r.className = 'it' + (it === st.it ? ' on' : '');
      r.innerHTML = `<span class="n">${it.w}</span><span class="v"><i>rows</i>${fmt(d.rows, 1)}</span><span class="v"><i>R−B</i>${fmt(d.rb, 3)}</span>`;
      r.onclick = () => select(g, it); L.appendChild(r); it._row = r; flat.push([g, it]);
    }
  }
}

function layout() {
  const d = cur(); if (!d || !d.w) return;
  const W = panes[0].parentElement.clientWidth - 30;
  const avail = window.innerHeight - $('panels').getBoundingClientRect().top - 3 * 30 - 20;
  v.fit = W / d.w;
  const H = Math.max(110, Math.min(d.h * v.fit, avail / 3));
  for (const p of panes) { p.style.width = W + 'px'; p.style.height = H + 'px'; }
}
function reset() { const d = cur(); if (!d) return; layout(); v.s = v.fit; v.tx = 0; v.ty = (panes[0].clientHeight - d.h * v.s) / 2; apply(); }
function apply() { for (const p of panes) { const s = p.firstChild; if (s && s.classList.contains('stage')) s.style.transform = `translate(${v.tx}px,${v.ty}px) scale(${v.s})`; } overlays(); }
function overlays() {                                      // scale bar, ruler, crosshair after a linked step
  const ppm = v.s * 1000 / umPx(), L = NICE.find(l => l * ppm >= 70) || NICE[NICE.length - 1];
  const X = x => v.tx + x * v.s, Y = y => v.ty + y * v.s;
  for (const p of panes) {
    const b = p.querySelector('.sbar'); if (b) { b.firstChild.style.width = (L * ppm).toFixed(1) + 'px'; b.lastChild.textContent = L < 1 ? Math.round(L * 1000) + ' µm' : L + ' mm'; }
    const o = p.querySelector('.ov'); if (!o) continue;
    let h = '';
    if (ruler) {
      const len = Math.hypot(ruler.x2 - ruler.x1, ruler.y2 - ruler.y1) * umPx() / 1000;
      h += `<line x1="${X(ruler.x1)}" y1="${Y(ruler.y1)}" x2="${X(ruler.x2)}" y2="${Y(ruler.y2)}" stroke="#4fd1ff" stroke-width="2"/>` +
           `<circle cx="${X(ruler.x1)}" cy="${Y(ruler.y1)}" r="3" fill="#4fd1ff"/><circle cx="${X(ruler.x2)}" cy="${Y(ruler.y2)}" r="3" fill="#4fd1ff"/>` +
           `<text x="${X(ruler.x2) + 8}" y="${Y(ruler.y2) - 8}" fill="#4fd1ff" font-size="13" font-family="sans-serif" paint-order="stroke" stroke="#000" stroke-width="3">${len.toFixed(2)} mm</text>`;
    }
    if (Date.now() < flash) {
      const cx = p.clientWidth / 2, cy = p.clientHeight / 2;
      h += `<circle cx="${cx}" cy="${cy}" r="18" fill="none" stroke="#e0a33c" stroke-width="2"/><line x1="${cx - 28}" y1="${cy}" x2="${cx + 28}" y2="${cy}" stroke="#e0a33c"/><line x1="${cx}" y1="${cy - 28}" x2="${cx}" y2="${cy + 28}" stroke="#e0a33c"/>`;
    }
    o.innerHTML = h;
  }
}

function show(keepView) {
  const d = cur(); if (!d) return;
  for (const p of panes) {
    const src = d[p.dataset.k]; p.innerHTML = '';
    if (!src) { p.innerHTML = '<div class="missing">not available</div>'; continue; }
    const s = document.createElement('div'); s.className = 'stage'; s.style.width = d.w + 'px'; s.style.height = d.h + 'px';
    const im = new Image(); im.src = src; im.draggable = false; if (st.rot) im.className = 'rot';
    s.appendChild(im); p.appendChild(s);
    p.insertAdjacentHTML('beforeend', '<svg class="ov"></svg><div class="sbar"><i></i><span></span></div>');
  }
  $('d0').classList.toggle('on', st.depth === '0'); $('d1').classList.toggle('on', st.depth === '1');
  $('d0').disabled = !st.it.depths['0']; $('d1').disabled = !st.it.depths['1'];
  if (keepView) apply(); else reset();
}

function select(g, it, keep) {
  if (st.it && st.it._row) st.it._row.classList.remove('on');
  ruler = null; if (!keep) $('info').textContent = '';
  st.g = g; st.it = it; if (!it.depths[st.depth]) st.depth = Object.keys(it.depths)[0];
  if (it._row) { it._row.classList.add('on'); it._row.scrollIntoView({block: 'nearest'}); }
  $('t-w').textContent = it.w; $('t-s').textContent = g.scroll;
  $('t-m').textContent = `${g.band} · ${g.models} · depth ${st.depth === '0' ? 'd0' : 'd+' + st.depth}`;
  if (keep) {                                            // same spot, same zoom: keep.target = [row, col] in raw preview pixels
    layout(); v.s = keep.s; const d = cur(), p = panes[0];
    const sx = st.rot ? d.w - keep.target[1] : keep.target[1], sy = st.rot ? d.h - keep.target[0] : keep.target[0];
    v.tx = p.clientWidth / 2 - sx * v.s; v.ty = p.clientHeight / 2 - sy * v.s;
    flash = Date.now() + 1600; setTimeout(overlays, 1700);
  }
  show(!!keep); preload();
}
function centreRaw() {                                   // raw preview pixel (row, col) at the centre of the view
  const d = cur(), p = panes[0]; const sx = (p.clientWidth / 2 - v.tx) / v.s, sy = (p.clientHeight / 2 - v.ty) / v.s;
  return st.rot ? [d.h - sy, d.w - sx] : [sy, sx];
}
function preload() {
  const i = flat.findIndex(([, it]) => it === st.it);
  for (const j of [i + 1, i - 1]) { const e = flat[j]; if (!e) continue; const d = e[1].depths[st.depth]; if (d) for (const k of ['ct', 'reading', 'blind']) if (d[k]) new Image().src = d[k]; }
}
function step(n) {
  const i = flat.findIndex(([, it]) => it === st.it); const e = flat[Math.min(flat.length - 1, Math.max(0, i + n))];
  if (!e || e[1] === st.it) return;
  if (!(v.s > v.fit * 1.02) || e[0] !== st.g) { select(e[0], e[1]); return; }   // not zoomed in, or another scroll: fit the new strip
  const from = st.it, d0 = cur(), [ry, rx] = centreRaw(); let target, note;
  const L = from.links && Object.values(from.links).find(l => l.w === e[1].w);
  if (L && L.pts.length) {
    let best = L.pts[0], bd = Infinity;
    for (const q of L.pts) { const dd = (q[0] - ry) ** 2 + (q[1] - rx) ** 2; if (dd < bd) { bd = dd; best = q; } }
    target = [ry + best[2] - best[0], rx + best[3] - best[1]];
    note = `Same place as on ${from.w} (found through the 3D meshes). The two surfaces are ${(best[4] / 100).toFixed(2)} mm apart here` +
           (best[4] < 10 ? ': under 0.1 mm, so compare the CT; if it looks the same, it is the same sheet.' : '.');
  } else {
    const d1 = e[1].depths[st.depth] || Object.values(e[1].depths)[0];
    target = [ry / d0.h * d1.h, rx / d0.w * d1.w]; note = `About the same place as on ${from.w} (same fraction of the strip; no mesh link for this pair).`;
  }
  select(e[0], e[1], {s: v.s, target}); $('info').textContent = note;
}
function setDepth(d) { if (!st.it || !st.it.depths[d] || d === st.depth) return; st.depth = d; buildList(); if (st.it._row) st.it._row.classList.add('on'); select(st.g, st.it); }
function toggleDepth() { setDepth(st.depth === '0' ? '1' : '0'); }
function setRot(on) { st.rot = on; $('rot').checked = on; for (const im of document.querySelectorAll('.stage img')) im.classList.toggle('rot', on); }

function zoomAt(p, mx, my, k) {
  const s2 = Math.min(Math.max(v.s * k, v.fit * 0.5), 6);
  k = s2 / v.s; v.tx = mx - (mx - v.tx) * k; v.ty = my - (my - v.ty) * k; v.s = s2; apply();
}
for (const p of panes) {
  p.addEventListener('wheel', e => {
    e.preventDefault(); const r = p.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top;
    if (!e.ctrlKey && Math.abs(e.deltaX) > Math.abs(e.deltaY)) { v.tx -= e.deltaX; apply(); return; }
    const dy = e.deltaMode === 1 ? e.deltaY * 16 : e.deltaY;
    zoomAt(p, mx, my, Math.exp(-dy * (e.ctrlKey ? 0.01 : 0.002)));
  }, {passive: false});
  let g0 = 1;
  p.addEventListener('gesturestart', e => { e.preventDefault(); g0 = 1; });
  p.addEventListener('gesturechange', e => { e.preventDefault(); const r = p.getBoundingClientRect(); zoomAt(p, e.clientX - r.left, e.clientY - r.top, e.scale / g0); g0 = e.scale; });
  let drag = null, meas = false;
  const stagePt = e => { const r = p.getBoundingClientRect(); return [(e.clientX - r.left - v.tx) / v.s, (e.clientY - r.top - v.ty) / v.s]; };
  p.addEventListener('pointerdown', e => {
    p.setPointerCapture(e.pointerId);
    if (e.shiftKey) { const [x, y] = stagePt(e); ruler = {x1: x, y1: y, x2: x, y2: y}; meas = true; overlays(); return; }
    drag = {x: e.clientX, y: e.clientY, tx: v.tx, ty: v.ty}; p.classList.add('drag');
  });
  p.addEventListener('pointermove', e => {
    if (meas) { const [x, y] = stagePt(e); ruler.x2 = x; ruler.y2 = y; overlays();
      $('info').textContent = `Ruler: ${(Math.hypot(ruler.x2 - ruler.x1, ruler.y2 - ruler.y1) * umPx() / 1000).toFixed(2)} mm (1 preview pixel = ${umPx().toFixed(1)} µm)`; return; }
    if (!drag) return; v.tx = drag.tx + e.clientX - drag.x; v.ty = drag.ty + e.clientY - drag.y; apply();
  });
  const end = () => { drag = null; meas = false; p.classList.remove('drag'); };
  p.addEventListener('pointerup', end); p.addEventListener('pointercancel', end);
  p.addEventListener('dblclick', reset);
}
$('d0').onclick = () => setDepth('0'); $('d1').onclick = () => setDepth('1');
$('rot').onchange = e => setRot(e.target.checked); $('reset').onclick = reset;
$('q').oninput = e => { st.q = e.target.value; buildList(); if (st.it && st.it._row && flat.some(([, it]) => it === st.it)) st.it._row.classList.add('on'); };
$('sort').onchange = e => { st.sort = e.target.value; buildList(); if (st.it && st.it._row) { st.it._row.classList.add('on'); st.it._row.scrollIntoView({block: 'nearest'}); } };
document.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT' && e.target.type !== 'checkbox' || e.metaKey || e.ctrlKey || e.altKey) return;
  const k = e.key.toLowerCase();
  if (k === 'arrowright') step(1); else if (k === 'arrowleft') step(-1);
  else if (k === 'arrowup' || k === 'arrowdown' || k === 'd') toggleDepth();
  else if (k === 'r') reset(); else if (k === 'f') setRot(!st.rot);
  else if (k === 'escape') { ruler = null; $('info').textContent = ''; overlays(); } else return;
  e.preventDefault();
});
let rz; window.addEventListener('resize', () => { clearTimeout(rz); rz = setTimeout(reset, 120); });
buildList(); if (flat.length) select(flat[0][0], flat[0][1]);
if (location.hash === '#selftest') {
  const i = flat.findIndex(([, it]) => it.w === 'w079'); if (i >= 0) select(flat[i][0], flat[i][1]);
  const p = panes[0]; zoomAt(p, p.clientWidth * 0.3, p.clientHeight / 2, 6);
  const before = centreRaw(); step(1);
  const c = [(p.clientWidth / 2 - v.tx) / v.s, (p.clientHeight / 2 - v.ty) / v.s]; ruler = {x1: c[0] - 1000 / umPx(), y1: c[1] + 40, x2: c[0] + 1000 / umPx(), y2: c[1] + 40}; overlays();
  document.title = JSON.stringify({w: st.it.w, before: before.map(Math.round), after: centreRaw().map(Math.round), s: v.s, info: $('info').textContent,
    bar: panes[0].querySelector('.sbar span').textContent, um: umPx()});
}
</script></body></html>
'''
out = os.path.join(VIEW, 'index.html')
with open(out, 'w') as f:
    f.write(HTML.replace('__MANIFEST__', manifest).replace(' GALLERY</header>', ' ' + GALLERY + '</header>'))
for g in groups:
    n_img = sum(sum(1 for k in ('ct', 'reading', 'blind') if k in d) for it in g['items'] for d in it['depths'].values())
    print(f"{g['id']}: {len(g['items'])} windings, {n_img} images ({g['scroll']}, {g['models']})")
print(f'{out}: {os.path.getsize(out) / 1024:.0f} KiB')
for o in odd:
    print('  note:', o)
