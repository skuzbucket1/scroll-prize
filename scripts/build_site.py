#!/usr/bin/env python3
"""Render research/registry.json into a static, dependency-free research site under docs/.
Usage: python3 scripts/build_site.py   (copies referenced images from data/results/ into docs/img/)"""
import json, html, os, shutil, datetime, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
REG = ROOT / "research" / "registry.json"
OUT = ROOT / "docs"
IMG_SRC = ROOT / "data" / "results"
IMG_DST = OUT / "img"
d = json.load(open(REG))
OUT.mkdir(exist_ok=True); IMG_DST.mkdir(exist_ok=True)

VERDICT = {
    "pass": ("Pass", "#1b7f3b"), "improved": ("Improved", "#1b7f3b"), "partial": ("Partial", "#b7791f"),
    "null": ("Null result", "#8a8a8a"), "baseline": ("Baseline", "#355c9a"), "decision": ("Decision", "#355c9a"),
    "finding": ("Finding", "#6b3fa0"), "bug-found": ("Bug found", "#c0392b"), "done": ("Done", "#1b7f3b"),
    "running": ("Running", "#2a7fb8"), "pending": ("Pending", "#8a8a8a"), "active": ("Active", "#2a7fb8"),
}
def esc(s): return html.escape(str(s))
def badge(v):
    label, color = VERDICT.get(v, (v, "#555"))
    return f'<span class="badge" style="background:{color}">{esc(label)}</span>'
def copy_img(name):
    src = IMG_SRC / name
    if not src.exists():
        return None
    dst = IMG_DST / name
    if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
        shutil.copy2(src, dst)
    return f"img/{name}"

exps = sorted(d["experiments"], key=lambda e: (e["date"], e["id"]))
baseline = next((e for e in exps if e.get("verdict") == "baseline"), None)
b_metrics = baseline["metrics"] if baseline else {}

# --- timeline rows (metric progression) ---
rows = []
for e in exps:
    m = e.get("metrics", {})
    def cell(k):
        if k not in m: return "<td class='dim'>—</td>"
        v = m[k]; delta = ""
        if k in b_metrics and e is not baseline:
            dv = v - b_metrics[k]; cls = "up" if dv > 0 else "down" if dv < 0 else ""
            delta = f" <span class='{cls}'>({dv:+.3f})</span>"
        return f"<td>{v:.3f}{delta}</td>"
    rows.append(f"<tr><td>{esc(e['date'])}</td><td><a href='#{esc(e['id'])}'>{esc(e['title'])}</a></td>"
                f"{cell('satisfied_track_points')}{cell('satisfied_tracks')}<td>{badge(e.get('verdict','')) }</td></tr>")

# --- experiment cards ---
cards = []
for e in exps:
    imgs = [copy_img(n) for n in e.get("images", [])]
    imgs = [f"<a href='{p}' target='_blank'><img loading='lazy' src='{p}' alt='{esc(n)}'><figcaption>{esc(n)}</figcaption></a>"
            for p, n in zip(imgs, e.get("images", [])) if p]
    gallery = f"<div class='gallery'>{''.join(imgs)}</div>" if imgs else ""
    metrics = e.get("metrics", {})
    mt = ""
    if metrics:
        mt = "<table class='metrics'>" + "".join(f"<tr><th>{esc(k)}</th><td>{v}</td></tr>" for k, v in metrics.items()) + "</table>"
    cards.append(f"""
<section class="card" id="{esc(e['id'])}">
  <header><span class="phase">{esc(e.get('phase',''))}</span> <span class="date">{esc(e['date'])}</span> {badge(e.get('verdict',''))}<h3>{esc(e['title'])}</h3></header>
  <dl>
    <dt>Question</dt><dd>{esc(e.get('question',''))}</dd>
    <dt>Technique</dt><dd>{esc(e.get('technique',''))}</dd>
    <dt>Result</dt><dd>{esc(e.get('result',''))}</dd>
    <dt>What we learned</dt><dd class="learned">{esc(e.get('learned',''))}</dd>
  </dl>
  {mt}{gallery}
</section>""")

phases = "".join(f"<li><b>{esc(p['id'])} · {esc(p['title'])}</b> {badge(p['status'])}<br><span class='dim'>{esc(p['summary'])}</span></li>" for p in d["phases"])
findings_scroll = "".join(f"<li><b>{esc(f['title'])}</b><br>{esc(f['text'])}</li>" for f in d["findings"] if f["kind"] == "scroll")
findings_tool = "".join(f"<li><b>{esc(f['title'])}</b><br>{esc(f['text'])}</li>" for f in d["findings"] if f["kind"] == "tooling")
nexts = "".join(f"<li>{esc(n)}</li>" for n in d.get("next", []))
p = d["project"]
now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(p['title'])}</title>
<style>
:root{{--fg:#1d1d1f;--muted:#6e6e73;--line:#e3e3e8;--bg:#fff;--card:#fafafc}}
body{{font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:var(--fg);background:var(--bg);margin:0}}
main{{max-width:1080px;margin:0 auto;padding:24px}}
h1{{font-size:28px;margin:0 0 4px}} h2{{font-size:22px;margin:40px 0 12px;border-bottom:1px solid var(--line);padding-bottom:6px}} h3{{margin:6px 0 10px;font-size:19px}}
.sub{{color:var(--muted);margin:0 0 18px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}}
.box{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}}
.badge{{display:inline-block;color:#fff;border-radius:999px;padding:1px 10px;font-size:12px;font-weight:600;vertical-align:middle}}
table{{border-collapse:collapse;width:100%}} td,th{{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top;font-size:14px}}
.dim{{color:var(--muted)}} .up{{color:#1b7f3b}} .down{{color:#c0392b}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin:14px 0}}
.card header .phase{{font-weight:700;color:#355c9a}} .card header .date{{color:var(--muted);margin:0 8px}}
dl{{display:grid;grid-template-columns:140px 1fr;gap:4px 12px;margin:8px 0}} dt{{color:var(--muted)}} dd{{margin:0}} .learned{{font-weight:500}}
.metrics{{width:auto;margin:8px 0}} .metrics th{{font-weight:500;color:var(--muted)}}
.gallery{{display:flex;flex-wrap:wrap;gap:10px;margin-top:10px}} .gallery a{{display:block;width:260px;text-decoration:none;color:var(--muted);font-size:12px}}
.gallery img{{width:260px;height:180px;object-fit:cover;border-radius:6px;border:1px solid var(--line);display:block}}
ul.plain{{padding-left:18px}} ul.plain li{{margin:6px 0}}
footer{{color:var(--muted);font-size:13px;margin:40px 0 10px}}
</style></head><body><main>
<h1>{esc(p['title'])}</h1><p class="sub">{esc(p['subtitle'])}</p>
<div class="grid">
 <div class="box"><b>Goal</b><br>{esc(p['goal'])}</div>
 <div class="box"><b>Scroll</b><br>{esc(p['scroll'])}</div>
 <div class="box"><b>Hardware</b><br>{esc(p['hardware'])}</div>
</div>
<h2>Where we are</h2><ul class="plain">{phases}</ul>
<h2>Progression</h2>
<p class="dim">Spiral-fit quality is measured as the fraction of track points lying within 6 voxels and 0.45 winding of the fitted sheet (and the fraction of tracks fully satisfied). Deltas are against the pilot baseline.</p>
<table><thead><tr><th>Date</th><th>Run</th><th>On-sheet track points</th><th>Tracks fully satisfied</th><th>Verdict</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<h2>Findings so far</h2>
<div class="grid"><div class="box"><b>About the scroll and the geometry</b><ul class="plain">{findings_scroll}</ul></div>
<div class="box"><b>About the tools (Progress Prize material)</b><ul class="plain">{findings_tool}</ul></div></div>
<h2>Next</h2><ul class="plain">{nexts}</ul>
<h2>Every run, explained</h2>
{''.join(cards)}
<footer>Generated {now} from research/registry.json by scripts/build_site.py. Images are downsampled previews; full-resolution outputs live on the GPU box.</footer>
</main></body></html>"""
(OUT / "index.html").write_text(page)
(OUT / ".nojekyll").write_text("")
print(f"wrote {OUT/'index.html'} ({len(page)//1024} KB), {len(list(IMG_DST.iterdir()))} images in docs/img")
