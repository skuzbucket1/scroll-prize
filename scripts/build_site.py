#!/usr/bin/env python3
"""Render research/registry.json into a static research site under docs/ (no dependencies, no build step).

Layout: a left navigation listing every run in chronological order, grouped by phase, and a main panel that shows
one page at a time (Overview, Findings, Next, or a single run). Works without JavaScript (all pages stacked).
Usage: python3 scripts/build_site.py   (copies referenced images from data/results/ into docs/img/)
"""
import datetime
import html
import json
import math
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
    dst = IMG_DST / name
    if src.exists():
        if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
            shutil.copy2(src, dst)
        return f"img/{name}"
    return f"img/{name}" if dst.exists() else None      # images placed straight into docs/img/


def img_entry(im):
    """A run image is a file name, or {"file": ..., "caption": ...}; the caption doubles as alt text."""
    if isinstance(im, str):
        return im, im
    return im["file"], im.get("caption") or im["file"]


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

# ---------------------------------------------------------------- pipeline overview (concepts only; content in registry "pipeline")
ARROW = ('<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M3 12h16M13 6l6 6-6 6"/></svg>')


def _poly(pts):
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)


def _arrow(x1, y1, x2, y2, head=5.0):
    a = math.atan2(y2 - y1, x2 - x1)
    hx1, hy1 = x2 - head * math.cos(a - 0.5), y2 - head * math.sin(a - 0.5)
    hx2, hy2 = x2 - head * math.cos(a + 0.5), y2 - head * math.sin(a + 0.5)
    return (f'<path class="ic-acc" d="M{x1:.1f} {y1:.1f}L{x2:.1f} {y2:.1f}"/>'
            f'<path class="ic-head" d="M{hx1:.1f} {hy1:.1f}L{x2:.1f} {y2:.1f}L{hx2:.1f} {hy2:.1f}"/>')


def _icon_spiral():
    cx, cy, pts, t = 74, 45, [], 0.6
    while t <= 5.6 * math.pi:
        r = 2.55 * t
        pts.append((cx + r * math.cos(t), cy + 0.72 * r * math.sin(t)))
        t += 0.12
    dots = ""
    for t, off in ((2.6 * math.pi, 1.06), (3.3 * math.pi, 0.95), (4.1 * math.pi, 1.04), (4.6 * math.pi, 0.97),
                   (5.05 * math.pi, 1.03), (5.45 * math.pi, 0.98), (3.8 * math.pi, 1.0)):
        r = 2.55 * t * off
        dots += f'<circle class="ic-dot" cx="{cx + r * math.cos(t):.1f}" cy="{cy + 0.72 * r * math.sin(t):.1f}" r="2.2"/>'
    return ('<svg viewBox="0 0 200 90" aria-hidden="true" focusable="false">'
            f'<polyline class="ic-acc" points="{_poly(pts)}"/>{dots}'
            '<line class="ic-acc" x1="134" y1="34" x2="150" y2="34"/><text class="ic-txt" x="154" y="38">spiral</text>'
            '<circle class="ic-dot" cx="142" cy="56" r="2.6"/><text class="ic-txt" x="154" y="60">tracks</text></svg>')


def _icon_snap():
    xs = range(8, 194, 4)
    fit = [(x, 30 + 9 * math.sin(x / 17)) for x in xs]
    surf = [(x, 62 + 4 * math.sin(x / 29 + 1.2)) for x in xs]
    arrows = "".join(_arrow(x, 30 + 9 * math.sin(x / 17) + 5, x, 62 + 4 * math.sin(x / 29 + 1.2) - 6) for x in (40, 88, 136, 180))
    return ('<svg viewBox="0 0 200 90" aria-hidden="true" focusable="false">'
            f'<polyline class="ic-acc ic-dash" points="{_poly(fit)}"/><polyline class="ic-line" points="{_poly(surf)}"/>{arrows}'
            '<text class="ic-txt acc" x="8" y="13">fitted</text><text class="ic-txt" x="8" y="85">predicted surface</text></svg>')


def _icon_render():
    lines = "".join(f'<line class="ic-thin" x1="10" y1="{y}" x2="132" y2="{y}"/>' for y in (12, 20, 28, 36, 54, 62, 70, 78))
    return ('<svg viewBox="0 0 200 90" aria-hidden="true" focusable="false">'
            f'{lines}<line class="ic-acc" x1="10" y1="45" x2="132" y2="45" style="stroke-width:3.4"/>'
            '<text class="ic-txt" x="140" y="28">layers</text><text class="ic-txt acc" x="140" y="49">surface</text>'
            '<text class="ic-txt" x="140" y="70">layers</text></svg>')


def _icon_look():
    out = []
    for i, (lab, op) in enumerate((("writing side", 0.85), ("back", 0.3), ("CT", None))):
        x = 8 + i * 66
        out.append(f'<rect class="ic-panel" x="{x}" y="6" width="52" height="50" rx="4"/>')
        if op is None:
            out.append("".join(f'<line class="ic-thin" x1="{x + 5}" y1="{y}" x2="{x + 47}" y2="{y}"/>' for y in (16, 24, 32, 40, 48)))
            out.append(f'<path class="ic-line" d="M{x + 6} 36l8 -4 6 6 8 -5 7 4 9 -3"/>')
        else:
            for bx, by, br in ((14, 18, 4), (26, 30, 5), (38, 22, 3.5), (20, 44, 3.5), (40, 42, 4.5)):
                out.append(f'<circle class="ic-blob" cx="{x + bx}" cy="{by}" r="{br}" style="opacity:{op}"/>')
        out.append(f'<text class="ic-txt" x="{x + 26}" y="74" text-anchor="middle">{lab}</text>')
    return '<svg viewBox="0 0 200 90" aria-hidden="true" focusable="false">' + "".join(out) + "</svg>"


def _icon_gate():
    arrows = "".join(_arrow(66, 45, 112, y) for y in (16, 45, 74))
    return ('<svg viewBox="0 0 200 90" aria-hidden="true" focusable="false">'
            '<polygon class="ic-wash ic-acc" points="36,8 64,45 36,82 8,45"/><text class="ic-txt acc" x="36" y="50" text-anchor="middle" style="font-size:15px;font-weight:600">?</text>'
            f'{arrows}<text class="ic-txt" x="118" y="20">go deeper</text><text class="ic-txt" x="118" y="49">next band</text>'
            '<text class="ic-txt" x="118" y="78">next scroll</text></svg>')


ICONS = {"spiral": _icon_spiral(), "snap": _icon_snap(), "render": _icon_render(), "look": _icon_look(), "gate": _icon_gate()}
GROUP_CLS = {"Geometry": "geo", "Ink": "ink", "Decision": "dec"}


def snake(i, cols=3):
    """Grid cell of stage i in a 3-wide snake (row 2 runs right to left), so arrows always point to the next stage."""
    r, c = divmod(i, cols)
    return r + 1, (cols - c if r % 2 else c + 1)


def thumb_html(img, alt, icon=None, cls="thumb"):
    if img and (IMG_DST / img).exists():
        return (f'<button type="button" class="zoom {cls}" data-src="img/{esc(img)}" data-cap="{esc(alt)}" aria-label="Enlarge: {esc(alt)}">'
                f'<img loading="lazy" src="img/{esc(img)}" alt="{esc(alt)}"></button>')
    return f'<div class="{cls} icon" role="img" aria-label="{esc(alt)}">{ICONS.get(icon, "")}</div>'


pipeline_html = ""
pl = d.get("pipeline")
if pl:
    st = pl["stages"]
    lis = []
    for i, s in enumerate(st):
        r, c = snake(i)
        g = GROUP_CLS.get(s.get("group"), "geo")
        arrow = ""
        if i + 1 < len(st):
            r2, c2 = snake(i + 1)
            dirn = "d" if r2 != r else ("r" if c2 > c else "l")
            arrow = f'<span class="arrow {dirn}" aria-hidden="true">{ARROW}</span>'
        by = f'<p class="by">{esc(s["by"])}</p>' if s.get("by") else ""
        lis.append(
            f'<li class="stage {g}" style="--r:{r};--c:{c}"><div class="sthead"><span class="snum">{i + 1}</span><b>{esc(s["title"])}</b>'
            f'<span class="stag"><span class="dot {g}" aria-hidden="true"></span>{esc(s.get("group", ""))}</span></div>'
            f'<div class="stbody">{thumb_html(s.get("img"), s["alt"], s.get("icon"))}<div class="sttext"><p>{esc(s["text"])}</p>{by}</div></div>{arrow}</li>')
    side = []
    ctl = pl.get("control")
    if ctl:
        names = {i + 1: s["title"] for i, s in enumerate(st)}
        chips = '<span class="to" aria-hidden="true">' + ARROW + '</span>'
        links = [f'<span class="chip">{n} · {esc(names.get(n, ""))}</span>' for n in ctl.get("steps", [])]
        if ctl.get("outcome"):
            links.append(f'<span class="chip end">{esc(ctl["outcome"])}</span>')
        chain = links[0] + "".join(f'<span class="nw">{chips}{c}</span>' for c in links[1:])   # arrow stays with the chip it points to
        side.append(
            f'<div class="lane control"><div class="lanehead"><b>{esc(ctl["title"])}</b><span class="stag">runs alongside steps '
            f'{ctl["steps"][0]}–{ctl["steps"][-1]}</span></div><div class="lanebody">{thumb_html(ctl.get("img"), ctl["alt"], cls="thumb wide")}'
            f'<p>{esc(ctl["text"])}</p></div><p class="chips" aria-label="Steps the control goes through">{chain}</p></div>')
    wh = pl.get("where")
    if wh:
        items = "".join(f'<li><b>{esc(it["label"])}</b><p>{esc(it["text"])}</p></li>' for it in wh["items"])
        side.append(f'<div class="lane where"><div class="lanehead"><b>{esc(wh["title"])}</b></div><ul class="plain">{items}</ul></div>')
    pipeline_html = (f'<h2 id="h-pipeline">{esc(pl["title"])}</h2><p class="note">{esc(pl["lede"])}</p>'
                     f'<div class="pipe" aria-labelledby="h-pipeline"><ol class="pipe-flow">{"".join(lis)}</ol>'
                     f'<div class="pipe-side">{"".join(side)}</div></div>')


# ---------------------------------------------------------------- per-run extras: a data table and a depth chart
def table_html(t):
    if not t:
        return ""
    head = "".join(f"<th>{esc(h)}</th>" for h in t["head"])
    rows = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>" for r in t["rows"])
    cap = f'<p class="note tcap">{esc(t["caption"])}</p>' if t.get("caption") else ""
    return f'<div class="runtable">{cap}<div class="tscroll"><table class="data"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div></div>'


def depth_chart(ch):
    """One y axis: a value per (series, depth) as dots, the mean per depth as a line, reference values as horizontal lines."""
    if not ch:
        return ""
    xs_v, series, refs = ch["x"], ch["series"], ch.get("refs", [])
    W, H, ml, mr, mt, mb = 760, 330, 74, 176, 22, 58
    vals = [v for s in series.values() for v in s if v is not None]
    step = ch.get("y_step", 0.005)
    lo = math.floor(min(vals + [0.0]) / step - 1e-9) * step
    hi = math.ceil(max(vals + [r["value"] for r in refs]) / step + 1e-9) * step
    pw, phh = W - ml - mr, H - mt - mb
    X = lambda i: ml + pw * (i + 0.5) / len(xs_v)
    Y = lambda v: mt + phh * (1 - (v - lo) / (hi - lo))
    fmt = lambda v: "0" if abs(v) < 1e-12 else f"{v:+.3f}".replace("-", "−")
    parts = []
    k = 0
    while lo + k * step <= hi + 1e-12:
        t = lo + k * step
        cls = "axis" if abs(t) < 1e-12 else "grid"
        parts.append(f'<line class="{cls}" x1="{ml}" x2="{W - mr}" y1="{Y(t):.1f}" y2="{Y(t):.1f}"/>'
                     f'<text class="tick" x="{ml - 8}" y="{Y(t) + 4:.1f}" text-anchor="end">{fmt(t)}</text>')
        k += 1
    for i, xv in enumerate(xs_v):
        lab = "0" if xv == 0 else f"{xv:+d}".replace("-", "−")
        parts.append(f'<text class="tick" x="{X(i):.1f}" y="{H - mb + 18}" text-anchor="middle">{lab}</text>')
    parts.append(f'<text class="axt" x="{ml + pw / 2:.1f}" y="{H - 12}" text-anchor="middle">{esc(ch.get("x_label", ""))}</text>')
    parts.append(f'<text class="axt" transform="translate(16,{mt + phh / 2:.1f}) rotate(-90)" text-anchor="middle">{esc(ch.get("y_label", ""))}</text>')
    for r in refs:
        y = Y(r["value"])
        parts.append(f'<line class="ref {esc(r.get("style", "dashed"))}" x1="{ml}" x2="{W - mr}" y1="{y:.1f}" y2="{y:.1f}"/>'
                     f'<text class="reflbl" x="{W - mr + 8}" y="{y - 2:.1f}">{esc(r["label"])}</text>'
                     f'<text class="reflbl" x="{W - mr + 8}" y="{y + 11:.1f}">{fmt(r["value"])}</text>')
    n = len(series)
    for j, (name, sv) in enumerate(series.items()):
        dx = (j - (n - 1) / 2) * 5
        for i, v in enumerate(sv):
            if v is None:
                continue
            parts.append(f'<circle class="dotw" cx="{X(i) + dx:.1f}" cy="{Y(v):.1f}" r="3.6"><title>{esc(name)}, depth {xs_v[i]:+d}: {fmt(v)}</title></circle>')
    means = []
    for i in range(len(xs_v)):
        col = [s[i] for s in series.values() if s[i] is not None]
        means.append(sum(col) / len(col) if col else None)
    mpts = [(X(i), Y(m)) for i, m in enumerate(means) if m is not None]
    parts.append(f'<polyline class="meanline" points="{_poly(mpts)}"/>')
    for i, m in enumerate(means):
        if m is None:
            continue
        parts.append(f'<circle class="meanpt" cx="{X(i):.1f}" cy="{Y(m):.1f}" r="4.5"/>'
                     f'<text class="meanlbl" x="{X(i) + 8:.1f}" y="{Y(m) + 15:.1f}">{f"{m:+.4f}".replace("-", "−")}</text>')
    ly = mt + phh - 30
    parts.append(f'<circle class="dotw" cx="{W - mr + 14}" cy="{ly}" r="3.6"/><text class="reflbl" x="{W - mr + 24}" y="{ly + 4}">one winding</text>'
                 f'<line class="meanline" x1="{W - mr + 6}" x2="{W - mr + 22}" y1="{ly + 20}" y2="{ly + 20}"/>'
                 f'<circle class="meanpt" cx="{W - mr + 14}" cy="{ly + 20}" r="4"/><text class="reflbl" x="{W - mr + 24}" y="{ly + 24}">mean</text>')
    svg = (f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(ch["title"])}">{"".join(parts)}</svg>')
    note = f'<p class="note cnote">{esc(ch["note"])}</p>' if ch.get("note") else ""
    return f'<div class="runchart"><h3>{esc(ch["title"])}</h3><div class="chartwrap static">{svg}</div>{note}</div>'

overview = f"""
<section class="view" id="overview" aria-labelledby="h-overview">
  <h1 id="h-overview">{esc(p['title'])}</h1>
  <p class="lede">{esc(p['subtitle'])}</p>
  <div class="grid3">
    <div class="card"><h3>Goal</h3><p>{esc(p['goal'])}</p></div>
    <div class="card"><h3>Scroll</h3><p>{esc(p['scroll'])}</p></div>
    <div class="card"><h3>Hardware</h3><p>{esc(p['hardware'])}</p></div>
  </div>
  {pipeline_html}
  <h2>Latest</h2>
  <div class="grid3">{latest_cards}</div>
  <h2>Where we are</h2>
  <ul class="phases">{phase_list}</ul>
  <h2>Spiral-fit progression</h2>
  <p class="note">{METRIC_LABEL}: the share of track points lying within 6 voxels and 0.45 winding of the fitted sheet. Each dot is one fit run, in run order; hover for details, click to open the run. {esc(p.get('fit_chart_note', ''))}</p>
  <div class="chartwrap">{chart_svg}<div class="tip" role="tooltip" hidden></div></div>
  <div class="tscroll"><table class="data"><thead><tr><th>#</th><th>Run</th><th>{METRIC_LABEL}</th><th>vs baseline</th><th>Tracks fully satisfied</th><th>Verdict</th></tr></thead><tbody>{table_rows}</tbody></table></div>
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
  <p class="note">Scan data and everything derived from it (all images here) are the Vesuvius Challenge's and EduceLab's, under CC BY-NC 4.0. Copied third-party code keeps its licence notice in the repository (box/bin/ink343/).</p>
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
    for im in e.get("images", []):
        name, cap = img_entry(im)
        src = copy_img(name)
        wide = ' class="wide"' if isinstance(im, dict) and im.get("wide") else ""
        if src:
            imgs.append(f'<figure{wide}><button class="zoom" data-src="{src}" data-cap="{esc(cap)}" aria-label="Enlarge {esc(cap)}">'
                        f'<img loading="lazy" src="{src}" alt="{esc(cap)}"></button><figcaption>{esc(cap)}</figcaption></figure>')
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
  {table_html(e.get('table'))}
  {depth_chart(e.get('chart'))}
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
main{overflow-y:auto;min-height:0;min-width:0}aside{min-width:0}
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
.gallery figure.wide{grid-column:1/-1}.gallery figure.wide img{height:auto;object-fit:contain}
/* per-run table and depth chart */
.runtable{margin-top:16px}.tscroll{overflow-x:auto}.runtable table.data{margin-top:4px}.tcap{margin:0 0 4px}
.runchart{margin-top:18px}.runchart h3{margin-bottom:8px}.cnote{margin:8px 0 0}
.chart .axt{fill:var(--ink2);font-size:12px}.chart .ref.dotted{stroke-dasharray:2 4}
.chart .dotw{fill:var(--accent);fill-opacity:.55}.chart .meanline{fill:none;stroke:var(--ink);stroke-width:2}
.chart .meanpt{fill:var(--ink);stroke:var(--surface);stroke-width:1.5}.chart .meanlbl{fill:var(--ink);font-size:11px;font-variant-numeric:tabular-nums}
/* pipeline overview: one column by default, a 3-wide snake when there is room */
:root{--g-geo:#2a78d6;--g-ink:#b7791f;--g-dec:#0c8a0c}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme="light"])){--g-geo:#3987e5;--g-ink:#e0a93a;--g-dec:#2fb12f}}
:root[data-theme="dark"]{--g-geo:#3987e5;--g-ink:#e0a93a;--g-dec:#2fb12f}
.pipe{container-type:inline-size;margin:2px 0 6px}
.pipe-flow{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:minmax(0,1fr);row-gap:30px}
.stage{position:relative;min-width:0;background:var(--surface);border:1px solid var(--border);border-top:3px solid var(--g,var(--accent));border-radius:10px;padding:10px 12px 12px}
.stage.geo{--g:var(--g-geo)}.stage.ink{--g:var(--g-ink)}.stage.dec{--g:var(--g-dec)}
.sthead{display:flex;align-items:center;gap:8px;margin-bottom:8px}.sthead b{flex:1;font-size:14px;line-height:1.25}
.snum{flex:none;width:24px;height:24px;border-radius:50%;border:2px solid var(--g);display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;font-variant-numeric:tabular-nums}
.stag{display:inline-flex;align-items:center;gap:5px;font-size:11px;color:var(--muted);white-space:nowrap}
.dot.geo{background:var(--g-geo)}.dot.ink{background:var(--g-ink)}.dot.dec{background:var(--g-dec)}
.stbody{display:flex;gap:10px;align-items:flex-start}
.thumb{flex:none;display:block;width:120px;height:80px;padding:0;margin:0;border:1px solid var(--border);border-radius:6px;overflow:hidden;background:#000}
button.thumb{cursor:zoom-in}.thumb img{display:block;width:100%;height:100%;object-fit:cover}
.thumb.icon{background:var(--page);display:flex;align-items:center;justify-content:center;padding:4px}.thumb.icon svg{width:100%;height:100%;display:block}
.sttext{min-width:0}.sttext p{margin:0;font-size:13px;line-height:1.45;color:var(--ink2)}.sttext p.by{margin-top:6px;font-size:11.5px;color:var(--muted)}
.arrow{position:absolute;left:50%;bottom:-29px;width:26px;height:26px;transform:translateX(-50%) rotate(90deg);color:var(--accent);pointer-events:none}
.arrow svg,.chips .to svg{display:block;width:100%;height:100%;fill:none;stroke:currentColor;stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round}
.ic-line{fill:none;stroke:var(--ink2);stroke-width:2.2}.ic-thin{fill:none;stroke:var(--muted);stroke-width:1.2}
.ic-acc{fill:none;stroke:var(--accent);stroke-width:2.4;stroke-linecap:round}.ic-dash{stroke-dasharray:6 4}
.ic-head{fill:none;stroke:var(--accent);stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}
.ic-wash{fill:var(--accent-wash)}.ic-dot{fill:var(--ink2)}.ic-blob{fill:var(--accent)}.ic-panel{fill:var(--surface);stroke:var(--axis);stroke-width:1.2}
.ic-txt{fill:var(--ink2);font-size:11px;font-family:system-ui,-apple-system,"Segoe UI",sans-serif}.ic-txt.acc{fill:var(--accent)}
.pipe-side{display:grid;grid-template-columns:minmax(0,1fr);gap:12px;margin-top:22px}
.lane{background:var(--surface);border:1px dashed var(--axis);border-radius:10px;padding:12px 14px;min-width:0}
.lanehead{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap}.lanehead b{font-size:14px}
.lanebody{display:flex;gap:12px;align-items:flex-start}.lanebody p{margin:0;font-size:13px;color:var(--ink2);line-height:1.45}
.thumb.wide{width:170px;height:80px}
.chips{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:10px 0 0}
.chip{font-size:12px;line-height:1.3;border:1px solid var(--border);border-radius:999px;padding:3px 10px;background:var(--page);color:var(--ink2);white-space:nowrap}
.chip.end{border-color:var(--good);color:var(--ink)}.chips .nw{display:inline-flex;align-items:center;gap:6px;white-space:nowrap}.chips .to{display:inline-block;width:16px;height:16px;color:var(--accent)}
.lane.where ul{padding-left:0;list-style:none}.lane.where li{margin:0 0 10px}.lane.where li p{margin:2px 0 0;font-size:13px;color:var(--ink2)}
@container (min-width:640px){
 .pipe-flow{grid-template-columns:repeat(3,minmax(0,1fr));column-gap:44px;row-gap:42px}
 .stage{grid-row:var(--r);grid-column:var(--c)}
 .stbody{flex-direction:column;gap:8px}.thumb{width:100%;height:96px}
 .arrow.r{left:auto;right:-36px;top:50%;bottom:auto;transform:translateY(-50%)}
 .arrow.l{left:-36px;top:50%;bottom:auto;transform:translateY(-50%) rotate(180deg)}
 .arrow.d{bottom:-35px}
 .pipe-side{grid-template-columns:minmax(0,1.7fr) minmax(0,1fr)}.thumb.wide{width:200px;height:96px}
}
@container (max-width:519px){.stbody{flex-direction:column;gap:8px}.thumb{width:100%;height:100px}}
@container (max-width:420px){.lanebody{flex-direction:column}.thumb.wide{width:100%;height:90px}}
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
<footer class="foot">Scan data and derived images: Vesuvius Challenge / EduceLab, CC BY-NC 4.0. Tools, models and methods by others are credited on each run and on the <a href="#credits">Credits</a> page. Generated {now} from research/registry.json by scripts/build_site.py. Images are downsampled previews; full-resolution outputs live on the GPU box.</footer>
</main></div>
<div class="lightbox" id="lightbox" hidden><button type="button" aria-label="Close">✕</button><img alt=""><div class="cap"></div></div>
<script>{JS}</script></body></html>"""
(OUT / "index.html").write_text(page)
(OUT / ".nojekyll").write_text("")
print(f"wrote {OUT/'index.html'} ({len(page)//1024} KB), {len(exps)} runs, {len(fit_runs)} fit runs charted, {len(list(IMG_DST.iterdir()))} images")
