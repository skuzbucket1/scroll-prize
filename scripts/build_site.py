#!/usr/bin/env python3
"""Render research/registry.json into a static research site under docs/ (no dependencies, no build step).

Layout: a left navigation listing every run in chronological order, grouped by phase, and a main panel that shows
one page at a time (Overview, Findings, Next, or a single run). Works without JavaScript (all pages stacked).
Usage: python3 scripts/build_site.py   (copies referenced images from data/results/ into docs/img/)
"""
import datetime
import html
import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
REG = ROOT / "research" / "registry.json"
OUT = ROOT / "docs"
IMG_SRC = ROOT / "data" / "results"
IMG_DST = OUT / "img"
d = json.load(open(REG))
OUT.mkdir(exist_ok=True)
IMG_DST.mkdir(exist_ok=True)

# Verdict -> (label, css class). Status colours are paired with a text label, never colour alone.
VERDICT = {
    "pass": ("Pass", "good"), "improved": ("Improved", "good"), "done": ("Done", "good"),
    "partial": ("Partial", "warn"), "bug-found": ("Bug found", "crit"),
    "null": ("Null result", "neutral"), "baseline": ("Baseline", "info"), "decision": ("Decision", "info"),
    "finding": ("Finding", "info"), "running": ("Running", "info"), "pending": ("Pending", "neutral"),
    "active": ("Active", "info"),
}
METRIC = "satisfied_track_points"
METRIC_LABEL = "On-sheet track points"


def esc(s):
    return html.escape(str(s), quote=True)


def badge(v):
    label, cls = VERDICT.get(v, (v or "—", "neutral"))
    return f'<span class="badge"><span class="dot {cls}" aria-hidden="true"></span>{esc(label)}</span>'


def copy_img(name):
    src = IMG_SRC / name
    if not src.exists():
        return None
    dst = IMG_DST / name
    if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
        shutil.copy2(src, dst)
    return f"img/{name}"


exps = d["experiments"]                      # registry order is chronological
for n, e in enumerate(exps, 1):
    e["_n"] = n
baseline = next((e for e in exps if e.get("verdict") == "baseline"), None)
b_val = (baseline or {}).get("metrics", {}).get(METRIC)
phases = {p["id"]: p for p in d["phases"]}
credits = {c["id"]: c for c in d.get("credits", [])}
p = d["project"]
now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def delta_html(v):
    if b_val is None or v is None:
        return ""
    dv = v - b_val
    if abs(dv) < 5e-4:
        return '<span class="delta">±0.000</span>'
    cls = "up" if dv > 0 else "down"
    return f'<span class="delta {cls}">{dv:+.3f}</span>'


# ---------------------------------------------------------------- navigation
nav_groups = []
for ph in d["phases"]:
    items = [e for e in exps if e.get("phase") == ph["id"]]
    if not items:
        continue
    lis = "".join(
        f'<li><a href="#run-{esc(e["id"])}" data-view="run-{esc(e["id"])}" data-search="{esc((e.get("short","") + " " + e["title"] + " " + e.get("track","")).lower())}">'
        f'<span class="num">{e["_n"]}</span><span class="lbl">{esc(e.get("short") or e["title"])}'
        f'<span class="meta">{esc(e.get("track",""))} · {esc(e["date"][5:])}</span></span>'
        f'<span class="dot {VERDICT.get(e.get("verdict"), ("", "neutral"))[1]}" title="{esc(VERDICT.get(e.get("verdict"), (e.get("verdict",""),))[0])}"></span></a></li>'
        for e in items)
    nav_groups.append(
        f'<div class="navgroup"><div class="navphase"><span>{esc(ph["id"])} · {esc(ph["title"])}</span>{badge(ph["status"])}</div><ul>{lis}</ul></div>')

# ---------------------------------------------------------------- progression chart (dot plot + baseline line)
fit_runs = [e for e in exps if METRIC in e.get("metrics", {})]
chart_svg = ""
if fit_runs:
    W, H, ml, mr, mt, mb = 760, 300, 52, 96, 24, 92
    vals = [e["metrics"][METRIC] for e in fit_runs]
    lo = min(vals + ([b_val] if b_val else [])) - 0.03
    hi = max(vals + ([b_val] if b_val else [])) + 0.03
    lo, hi = (int(lo * 20) / 20, (int(hi * 20) + 1) / 20)          # snap to 0.05
    pw, ph_ = W - ml - mr, H - mt - mb
    xs = [ml + pw * (i + 0.5) / len(fit_runs) for i in range(len(fit_runs))]
    y = lambda v: mt + ph_ * (1 - (v - lo) / (hi - lo))
    parts = []
    t = lo
    while t <= hi + 1e-9:
        parts.append(f'<line class="grid" x1="{ml}" x2="{W-mr}" y1="{y(t):.1f}" y2="{y(t):.1f}"/>'
                     f'<text class="tick" x="{ml-8}" y="{y(t)+4:.1f}" text-anchor="end">{t:.2f}</text>')
        t += 0.05
    if b_val is not None:
        parts.append(f'<line class="ref" x1="{ml}" x2="{W-mr}" y1="{y(b_val):.1f}" y2="{y(b_val):.1f}"/>'
                     f'<text class="reflbl" x="{W-mr+8}" y="{y(b_val)-2:.1f}">pilot</text><text class="reflbl" x="{W-mr+8}" y="{y(b_val)+11:.1f}">baseline {b_val:.3f}</text>')
    best = max(fit_runs, key=lambda e: e["metrics"][METRIC])
    for x, e in zip(xs, fit_runs):
        v = e["metrics"][METRIC]
        lbl = esc(e.get("short") or e["id"])
        tip = esc(f'#{e["_n"]} {e.get("short") or e["title"]}|{METRIC_LABEL} {v:.3f}' + (f' ({v-b_val:+.3f} vs baseline)' if b_val is not None and e is not baseline else ''))
        parts.append(
            f'<g class="pt" data-tip="{tip}" data-href="#run-{esc(e["id"])}" tabindex="0" role="link" aria-label="{tip.replace("|", ": ")}">'
            f'<circle class="hit" cx="{x:.1f}" cy="{y(v):.1f}" r="14"/>'
            f'<circle class="mark" cx="{x:.1f}" cy="{y(v):.1f}" r="5"/></g>'
            f'<text class="xl" transform="translate({x:.1f},{H-mb+14}) rotate(-38)" text-anchor="end">{lbl}</text>')
        if e is best:
            parts.append(f'<text class="direct" x="{x:.1f}" y="{y(v)-12:.1f}" text-anchor="middle">{v:.3f}</text>')
    chart_svg = (f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="{METRIC_LABEL} per spiral-fit run, in run order">'
                 f'<line class="axis" x1="{ml}" x2="{W-mr}" y1="{mt+ph_}" y2="{mt+ph_}"/>{"".join(parts)}</svg>')

table_rows = "".join(
    f'<tr><td class="n">{e["_n"]}</td><td><a href="#run-{esc(e["id"])}">{esc(e.get("short") or e["title"])}</a></td>'
    f'<td class="v">{e["metrics"][METRIC]:.3f}</td><td class="v">{delta_html(e["metrics"][METRIC]) if e is not baseline else "—"}</td>'
    f'<td class="v">{e["metrics"].get("satisfied_tracks", float("nan")):.3f}</td><td>{badge(e.get("verdict"))}</td></tr>'
    for e in fit_runs)

latest = exps[-3:][::-1]
latest_cards = "".join(
    f'<a class="card link" href="#run-{esc(e["id"])}"><div class="cardhead"><span class="num">#{e["_n"]}</span>{badge(e.get("verdict"))}</div>'
    f'<b>{esc(e["title"])}</b><p>{esc(e.get("learned",""))}</p></a>' for e in latest)

phase_list = "".join(
    f'<li><div class="phrow"><b>{esc(ph["id"])} · {esc(ph["title"])}</b>{badge(ph["status"])}</div><p>{esc(ph["summary"])}</p></li>'
    for ph in d["phases"])

overview = f"""
<section class="view" id="overview" aria-labelledby="h-overview">
  <h1 id="h-overview">{esc(p['title'])}</h1>
  <p class="lede">{esc(p['subtitle'])}</p>
  <div class="grid3">
    <div class="card"><h3>Goal</h3><p>{esc(p['goal'])}</p></div>
    <div class="card"><h3>Scroll</h3><p>{esc(p['scroll'])}</p></div>
    <div class="card"><h3>Hardware</h3><p>{esc(p['hardware'])}</p></div>
  </div>
  <h2>Latest</h2>
  <div class="grid3">{latest_cards}</div>
  <h2>Where we are</h2>
  <ul class="phases">{phase_list}</ul>
  <h2>Spiral-fit progression</h2>
  <p class="note">{METRIC_LABEL}: the share of track points lying within 6 voxels and 0.45 winding of the fitted sheet. Each dot is one fit run, in run order; hover for details, click to open the run.</p>
  <div class="chartwrap">{chart_svg}<div class="tip" role="tooltip" hidden></div></div>
  <table class="data"><thead><tr><th>#</th><th>Run</th><th>{METRIC_LABEL}</th><th>vs baseline</th><th>Tracks fully satisfied</th><th>Verdict</th></tr></thead><tbody>{table_rows}</tbody></table>
</section>"""

fs = "".join(f'<li><b>{esc(f["title"])}</b><p>{esc(f["text"])}</p></li>' for f in d["findings"] if f["kind"] == "scroll")
ft = "".join(f'<li><b>{esc(f["title"])}</b><p>{esc(f["text"])}</p></li>' for f in d["findings"] if f["kind"] == "tooling")
findings = f"""
<section class="view" id="findings" aria-labelledby="h-findings">
  <h1 id="h-findings">Findings</h1>
  <div class="grid2">
    <div class="card"><h3>About the scroll and the geometry</h3><ul class="plain">{fs}</ul></div>
    <div class="card"><h3>About the tools (Progress Prize material)</h3><ul class="plain">{ft}</ul></div>
  </div>
</section>"""


cl = "".join(
    f'<li><b>{(chr(60)+"a href=\""+esc(c["link"])+"\""+chr(62)+esc(c["who"])+chr(60)+"/a"+chr(62)) if c.get("link") else esc(c["who"])}</b><p>{esc(c["what"])}</p>'
    f'<p class="used">Used in {sum(1 for e in exps if c["id"] in e.get("credits", []))} of {len(exps)} runs</p></li>'
    for c in d.get("credits", []))
creditsview = f"""
<section class="view" id="credits" aria-labelledby="h-credits">
  <h1 id="h-credits">Credits</h1>
  <p class="lede">This campaign is built almost entirely on other people's work. Everything below is theirs; only the entry marked "This project" is ours. Each run page lists exactly what it used.</p>
  <ul class="plain creditlist">{cl}</ul>
  <p class="note">Scan data and everything derived from it (all images here) are the Vesuvius Challenge's, under CC BY-NC 4.0. Copied third-party code keeps its licence notice in the repository (box/bin/ink343/).</p>
</section>"""

nexts = "".join(f"<li>{esc(n)}</li>" for n in d.get("next", []))
nextview = f"""
<section class="view" id="next" aria-labelledby="h-next">
  <h1 id="h-next">Next</h1>
  <ol class="plain">{nexts}</ol>
</section>"""


def credit_card(e):
    ids = e.get("credits", [])
    if not ids:
        return ""
    items = []
    for cid in ids:
        c = credits.get(cid)
        if not c:
            continue
        who = f'<a href="{esc(c["link"])}">{esc(c["who"])}</a>' if c.get("link") else esc(c["who"])
        items.append(f'<li><b>{who}</b> — {esc(c["what"])}</li>')
    return f'<div class="card credits"><h3>Built on</h3><ul class="plain">{"".join(items)}</ul><p class="more"><a href="#credits">All credits</a></p></div>'

# ---------------------------------------------------------------- one page per run
run_views = []
for i, e in enumerate(exps):
    prev_e = exps[i - 1] if i > 0 else None
    next_e = exps[i + 1] if i + 1 < len(exps) else None
    imgs = []
    for name in e.get("images", []):
        src = copy_img(name)
        if src:
            imgs.append(f'<figure><button class="zoom" data-src="{src}" data-cap="{esc(name)}" aria-label="Enlarge {esc(name)}">'
                        f'<img loading="lazy" src="{src}" alt="{esc(name)}"></button><figcaption>{esc(name)}</figcaption></figure>')
    m = e.get("metrics", {})
    mt = ""
    if m:
        cells = []
        if METRIC in m:
            cells.append(f'<div class="stat"><span class="k">{METRIC_LABEL}</span><span class="val">{m[METRIC]:.3f}</span>{delta_html(m[METRIC]) if e is not baseline else ""}</div>')
        if "satisfied_tracks" in m:
            cells.append(f'<div class="stat"><span class="k">Tracks fully satisfied</span><span class="val">{m["satisfied_tracks"]:.3f}</span></div>')
        mt = f'<div class="stats">{"".join(cells)}</div>'
    pager = '<nav class="pager" aria-label="Run navigation">'
    pager += (f'<a href="#run-{esc(prev_e["id"])}" class="prev">← #{prev_e["_n"]} {esc(prev_e.get("short") or prev_e["title"])}</a>' if prev_e else '<span></span>')
    pager += (f'<a href="#run-{esc(next_e["id"])}" class="next">#{next_e["_n"]} {esc(next_e.get("short") or next_e["title"])} →</a>' if next_e else '<span></span>')
    pager += '</nav>'
    ph = phases.get(e.get("phase"), {})
    run_views.append(f"""
<section class="view run" id="run-{esc(e['id'])}" aria-labelledby="h-{esc(e['id'])}">
  <div class="crumb">{esc(e.get('phase',''))} · {esc(ph.get('title',''))} · Run {e['_n']} of {len(exps)} · {esc(e.get('track',''))}</div>
  <h1 id="h-{esc(e['id'])}">{esc(e['title'])}</h1>
  <div class="runmeta"><span>{esc(e['date'])}</span>{badge(e.get('verdict'))}</div>
  {mt}
  <div class="qa">
    <div class="card"><h3>Question</h3><p>{esc(e.get('question',''))}</p></div>
    <div class="card"><h3>Technique</h3><p>{esc(e.get('technique',''))}</p></div>
    <div class="card"><h3>Result</h3><p>{esc(e.get('result',''))}</p></div>
    <div class="card learned"><h3>What we learned</h3><p>{esc(e.get('learned',''))}</p></div>
    {credit_card(e)}
  </div>
  {f'<div class="gallery">{"".join(imgs)}</div>' if imgs else ''}
  {pager}
</section>""")

CSS = """
:root{color-scheme:light;--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;--axis:#c3c2b7;
--border:rgba(11,11,11,.10);--accent:#2a78d6;--accent-wash:rgba(42,120,214,.10);--good:#0ca30c;--warn:#fab219;--crit:#d03b3b;--up:#006300;--down:#b42323}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme="light"])){color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;
--grid:#2c2c2a;--axis:#383835;--border:rgba(255,255,255,.10);--accent:#3987e5;--accent-wash:rgba(57,135,229,.16);--up:#0ca30c;--down:#e66767}}
:root[data-theme="dark"]{color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--grid:#2c2c2a;--axis:#383835;
--border:rgba(255,255,255,.10);--accent:#3987e5;--accent-wash:rgba(57,135,229,.16);--up:#0ca30c;--down:#e66767}
*{box-sizing:border-box}
html,body{margin:0;height:100%}
body{font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--ink);background:var(--page)}
a{color:var(--accent)}
.layout{display:grid;grid-template-columns:320px 1fr;height:100vh}
aside{background:var(--surface);border-right:1px solid var(--border);display:flex;flex-direction:column;min-height:0}
.brand{padding:16px 16px 10px;border-bottom:1px solid var(--border)}
.brand b{display:block;font-size:15px;line-height:1.3}.brand span{color:var(--muted);font-size:12px}
.topnav{display:flex;gap:4px;padding:10px 12px 6px}
.topnav a{flex:1;text-align:center;text-decoration:none;color:var(--ink2);padding:6px 4px;border-radius:6px;font-size:13px;border:1px solid var(--border)}
.topnav a.active{background:var(--accent-wash);color:var(--ink);border-color:var(--accent)}
.filter{padding:6px 12px 8px}.filter input{width:100%;padding:7px 10px;border-radius:6px;border:1px solid var(--border);background:var(--page);color:var(--ink);font:inherit;font-size:13px}
.navscroll{overflow-y:auto;flex:1;padding:0 6px 12px}
.navgroup{margin-top:10px}
.navphase{display:flex;justify-content:space-between;align-items:center;gap:6px;padding:6px 8px;font-size:11px;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);position:sticky;top:0;background:var(--surface);z-index:1}
.navphase .badge{text-transform:none;letter-spacing:0}
.navgroup ul{list-style:none;margin:0;padding:0}
.navgroup a{display:grid;grid-template-columns:26px 1fr 12px;align-items:center;gap:6px;padding:6px 8px;border-radius:6px;text-decoration:none;color:var(--ink)}
.navgroup a:hover{background:var(--accent-wash)}
.navgroup a.active{background:var(--accent-wash);box-shadow:inset 3px 0 0 var(--accent)}
.navgroup .num{font-variant-numeric:tabular-nums;color:var(--muted);font-size:12px;text-align:right}
.navgroup .lbl{font-size:13px;line-height:1.3}.navgroup .meta{display:block;font-size:11px;color:var(--muted)}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;background:var(--muted)}
.dot.good{background:var(--good)}.dot.warn{background:var(--warn)}.dot.crit{background:var(--crit)}.dot.info{background:var(--accent)}.dot.neutral{background:var(--muted)}
.badge{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--ink2);white-space:nowrap}
.sidefoot{border-top:1px solid var(--border);padding:8px 12px;display:flex;justify-content:space-between;align-items:center;font-size:12px;color:var(--muted)}
.sidefoot button{font:inherit;font-size:12px;background:none;border:1px solid var(--border);color:var(--ink2);border-radius:6px;padding:4px 8px;cursor:pointer}
main{overflow-y:auto;min-height:0}
.view{max-width:980px;margin:0 auto;padding:28px 32px 48px}
.js .view{display:none}.js .view.shown{display:block}
h1{font-size:26px;line-height:1.25;margin:4px 0 8px}h2{font-size:19px;margin:32px 0 12px}h3{font-size:13px;margin:0 0 6px;color:var(--ink2);text-transform:uppercase;letter-spacing:.04em}
.lede{color:var(--ink2);margin:0 0 18px}.note{color:var(--ink2);font-size:13px;margin:-4px 0 10px}
.crumb{font-size:12px;color:var(--muted)}
.runmeta{display:flex;gap:14px;align-items:center;color:var(--ink2);font-size:13px;margin-bottom:16px}
.grid3{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px 16px}
.card p{margin:0}.card.link{text-decoration:none;color:var(--ink);display:block}.card.link:hover{border-color:var(--accent)}
.card.link p{color:var(--ink2);font-size:13px;margin-top:6px}
.cardhead{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}.cardhead .num{color:var(--muted);font-size:12px}
.qa{display:grid;gap:10px}.card.credits li{font-size:13px;margin:4px 0}.card.credits .more{margin-top:6px;font-size:12px}.creditlist li{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:10px 14px;list-style:none;margin:8px 0}.creditlist{padding:0}.creditlist .used{font-size:12px;color:var(--muted)}.qa .learned{border-left:3px solid var(--accent)}
.stats{display:flex;gap:12px;flex-wrap:wrap;margin:0 0 14px}
.stat{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:10px 14px;display:flex;flex-direction:column;min-width:180px}
.stat .k{font-size:12px;color:var(--ink2)}.stat .val{font-size:24px;font-weight:600}
.delta{font-size:13px;color:var(--ink2);font-variant-numeric:tabular-nums}.delta.up{color:var(--up)}.delta.down{color:var(--down)}
.phases{list-style:none;padding:0;margin:0;display:grid;gap:8px}
.phases li{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:10px 14px}.phases p{margin:4px 0 0;color:var(--ink2);font-size:13px}
.phrow{display:flex;justify-content:space-between;gap:10px}
.chartwrap{position:relative;background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:8px}
.chart{width:100%;height:auto;display:block}
.chart .grid{stroke:var(--grid);stroke-width:1}.chart .axis{stroke:var(--axis);stroke-width:1}
.chart .tick,.chart .xl{fill:var(--muted);font-size:11px;font-variant-numeric:tabular-nums}
.chart .ref{stroke:var(--ink2);stroke-width:1.5;stroke-dasharray:5 4}.chart .reflbl{fill:var(--ink2);font-size:11px}
.chart .mark{fill:var(--accent);stroke:var(--surface);stroke-width:2}
.chart .hit{fill:transparent;cursor:pointer}.chart .pt:hover .mark,.chart .pt:focus .mark{r:7}
.chart .pt:focus{outline:none}.chart .direct{fill:var(--ink);font-size:12px;font-weight:600}
.tip{position:absolute;pointer-events:none;background:var(--surface);color:var(--ink);border:1px solid var(--border);border-radius:8px;padding:8px 10px;font-size:12px;box-shadow:0 4px 14px rgba(0,0,0,.15);max-width:260px}
.tip b{display:block;margin-bottom:2px}
table.data{width:100%;border-collapse:collapse;margin-top:12px;background:var(--surface);border:1px solid var(--border);border-radius:10px;overflow:hidden}
.data th,.data td{padding:7px 10px;border-bottom:1px solid var(--grid);text-align:left;font-size:13px}
.data th{color:var(--ink2);font-weight:500}.data td.v,.data td.n{font-variant-numeric:tabular-nums}.data td.n{color:var(--muted)}
ul.plain,ol.plain{padding-left:18px;margin:0}ul.plain li,ol.plain li{margin:8px 0}ul.plain p{margin:2px 0 0;color:var(--ink2);font-size:13px}
.gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;margin-top:16px}
.gallery figure{margin:0}.gallery button.zoom{padding:0;border:1px solid var(--border);border-radius:8px;overflow:hidden;cursor:zoom-in;background:#000;display:block;width:100%}
.gallery img{display:block;width:100%;height:200px;object-fit:cover}.gallery figcaption{font-size:11px;color:var(--muted);margin-top:4px;word-break:break-all}
.pager{display:flex;justify-content:space-between;gap:12px;margin-top:28px;padding-top:14px;border-top:1px solid var(--border)}
.pager a{text-decoration:none;font-size:13px;max-width:48%}
.lightbox{position:fixed;inset:0;background:rgba(0,0,0,.88);display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:50;padding:24px}
.lightbox[hidden]{display:none}.lightbox img{max-width:96vw;max-height:86vh;object-fit:contain;background:#000}
.lightbox .cap{color:#ddd;font-size:12px;margin-top:8px}.lightbox button{position:absolute;top:14px;right:16px;font-size:22px;background:none;border:none;color:#fff;cursor:pointer}
.foot{max-width:980px;margin:0 auto;padding:0 32px 32px;color:var(--muted);font-size:12px}
@media (max-width:860px){.layout{grid-template-columns:1fr;height:auto}aside{position:static;max-height:none}.navscroll{max-height:45vh}main{overflow:visible}.view{padding:20px 16px 40px}}
"""

JS = """
(function(){
  document.documentElement.classList.add('js');
  var views=[].slice.call(document.querySelectorAll('.view'));
  var links=[].slice.call(document.querySelectorAll('[data-view]'));
  var main=document.querySelector('main');
  function show(id){
    if(!document.getElementById(id)) id='overview';
    views.forEach(function(v){v.classList.toggle('shown', v.id===id);});
    links.forEach(function(a){a.classList.toggle('active', a.getAttribute('data-view')===id);});
    var act=document.querySelector('.navgroup a.active'); if(act) act.scrollIntoView({block:'nearest'});
    main.scrollTop=0; var h=document.getElementById(id).querySelector('h1'); if(h) document.title=h.textContent+' — PHerc0191 research log';
  }
  window.addEventListener('hashchange', function(){show(location.hash.slice(1));});
  show(location.hash.slice(1)||'overview');
  // keyboard: left/right to step through runs
  document.addEventListener('keydown', function(ev){
    if(ev.target.tagName==='INPUT') return;
    var cur=document.querySelector('.view.shown'); if(!cur||!cur.classList.contains('run')) return;
    var a=cur.querySelector(ev.key==='ArrowLeft'?'.pager .prev':ev.key==='ArrowRight'?'.pager .next':null);
    if(a){location.hash=a.getAttribute('href');}
    if(ev.key==='Escape') closeLb();
  });
  // filter
  var f=document.getElementById('filter');
  f.addEventListener('input', function(){
    var q=f.value.trim().toLowerCase();
    document.querySelectorAll('.navgroup').forEach(function(g){
      var any=false;
      g.querySelectorAll('li').forEach(function(li){var a=li.querySelector('a');var ok=!q||a.getAttribute('data-search').indexOf(q)>=0;li.hidden=!ok;any=any||ok;});
      g.hidden=!any;
    });
  });
  // chart tooltip
  var wrap=document.querySelector('.chartwrap');
  if(wrap){
    var tip=wrap.querySelector('.tip');
    wrap.querySelectorAll('.pt').forEach(function(pt){
      function on(ev){
        var t=pt.getAttribute('data-tip').split('|'); tip.innerHTML='<b></b><span></span>';
        tip.firstChild.textContent=t[0]; tip.lastChild.textContent=t[1]||''; tip.hidden=false;
        var r=wrap.getBoundingClientRect(), c=pt.querySelector('.mark').getBoundingClientRect();
        var x=c.left-r.left+c.width/2, y=c.top-r.top;
        tip.style.left=Math.min(Math.max(8,x-130), r.width-270)+'px'; tip.style.top=Math.max(4,y-64)+'px';
      }
      pt.addEventListener('mouseenter',on); pt.addEventListener('focus',on);
      pt.addEventListener('mouseleave',function(){tip.hidden=true;}); pt.addEventListener('blur',function(){tip.hidden=true;});
      pt.addEventListener('click',function(){location.hash=pt.getAttribute('data-href');});
      pt.addEventListener('keydown',function(e){if(e.key==='Enter')location.hash=pt.getAttribute('data-href');});
    });
  }
  // lightbox
  var lb=document.getElementById('lightbox');
  function closeLb(){lb.hidden=true; lb.querySelector('img').src='';}
  document.querySelectorAll('button.zoom').forEach(function(b){b.addEventListener('click',function(){
    lb.querySelector('img').src=b.getAttribute('data-src'); lb.querySelector('.cap').textContent=b.getAttribute('data-cap'); lb.hidden=false;});});
  lb.addEventListener('click',function(e){if(e.target===lb||e.target.tagName==='BUTTON')closeLb();});
  // theme toggle
  var tb=document.getElementById('theme');
  var saved=localStorage.getItem('theme'); if(saved) document.documentElement.setAttribute('data-theme',saved);
  tb.addEventListener('click',function(){
    var cur=document.documentElement.getAttribute('data-theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');
    var nxt=cur==='dark'?'light':'dark'; document.documentElement.setAttribute('data-theme',nxt); localStorage.setItem('theme',nxt);
  });
})();
"""

page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(p['title'])}</title><style>{CSS}</style></head><body>
<div class="layout">
<aside aria-label="Research navigation">
  <div class="brand"><b>{esc(p['title'])}</b><span>{len(exps)} runs · updated {now}</span></div>
  <nav class="topnav"><a href="#overview" data-view="overview">Overview</a><a href="#findings" data-view="findings">Findings</a><a href="#next" data-view="next">Next</a><a href="#credits" data-view="credits">Credits</a></nav>
  <div class="filter"><input id="filter" type="search" placeholder="Filter runs (e.g. tracer, shell, ink)" aria-label="Filter runs"></div>
  <div class="navscroll">{''.join(nav_groups)}</div>
  <div class="sidefoot"><span>← → step through runs</span><button id="theme" type="button">Light / dark</button></div>
</aside>
<main>{overview}{findings}{nextview}{creditsview}{''.join(run_views)}
<footer class="foot">Scan data and derived images: Vesuvius Challenge, CC BY-NC 4.0. Tools, models and methods by others are credited on each run and on the <a href="#credits">Credits</a> page. Generated {now} from research/registry.json by scripts/build_site.py. Images are downsampled previews; full-resolution outputs live on the GPU box.</footer>
</main></div>
<div class="lightbox" id="lightbox" hidden><button type="button" aria-label="Close">✕</button><img alt=""><div class="cap"></div></div>
<script>{JS}</script></body></html>"""
(OUT / "index.html").write_text(page)
(OUT / ".nojekyll").write_text("")
print(f"wrote {OUT/'index.html'} ({len(page)//1024} KB), {len(exps)} runs, {len(fit_runs)} fit runs charted, {len(list(IMG_DST.iterdir()))} images")
