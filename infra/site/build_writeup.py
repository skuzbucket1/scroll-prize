"""Render a write-up (research/writeups/<name>.md) into a page of the research site (docs/<name>.html), in the site's own
style (the CSS of docs/index.html). Handles the markdown the write-ups use: headings, paragraphs, lists, block quotes,
tables, code blocks, images with the italic caption paragraph that follows them, bold, italics, code and links. Image
paths ../../docs/img/X (so the markdown also renders on GitHub) become img/X.
Usage: python3 infra/site/build_writeup.py research/writeups/stroke-score-0.2.md"""
import html, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
src = Path(sys.argv[1]); out = ROOT / 'docs' / (src.stem + '.html')
css = re.search(r'<style>(.*?)</style>', (ROOT / 'docs' / 'index.html').read_text(), re.S).group(1)
EXTRA = """
.writeup{max-width:860px;margin:0 auto;padding:28px 22px 60px;line-height:1.6}
.writeup h1{font-size:1.9em;margin:.2em 0 .3em}.writeup h3{margin-top:1.8em}
.writeup figure{margin:1.4em 0}.writeup figure img{width:100%;height:auto;border-radius:6px}
.writeup figcaption{font-size:.92em;opacity:.85;margin-top:.4em}
.writeup table{border-collapse:collapse;width:100%;margin:1em 0;font-size:.95em}
.writeup td,.writeup th{border:1px solid rgba(128,128,128,.35);padding:6px 9px;vertical-align:top;text-align:left}
.writeup pre{overflow-x:auto;padding:12px;border-radius:6px;background:rgba(128,128,128,.12)}
.writeup blockquote{margin:1em 0;padding:.4em 1em;border-left:3px solid rgba(128,128,128,.5)}
.writeup .back{font-size:.95em}
"""


def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'(?<![*\w])\*([^*]+)\*(?![*\w])', r'<i>\1</i>', t)
    t = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', t)
    t = re.sub(r'(?<!["=>])(https?://[^\s<)]+)', r'<a href="\1">\1</a>', t)
    return t


lines = src.read_text().split('\n'); h, i, title = [], 0, src.stem
while i < len(lines):
    l = lines[i]
    if not l.strip():
        i += 1; continue
    if l.startswith('```'):
        j = i + 1
        while j < len(lines) and not lines[j].startswith('```'):
            j += 1
        h.append('<pre><code>' + html.escape('\n'.join(lines[i + 1:j])) + '</code></pre>'); i = j + 1; continue
    m = re.match(r'(#{1,4}) (.*)', l)
    if m:
        n = len(m.group(1)); title = m.group(2) if n == 1 else title
        h.append(f'<h{n}>{inline(m.group(2))}</h{n}>'); i += 1; continue
    m = re.match(r'!\[([^\]]*)\]\(([^)]+)\)\s*$', l)
    if m:
        s = re.sub(r'^(\.\./)+docs/', '', m.group(2)); cap = ''
        k = i + 1
        while k < len(lines) and not lines[k].strip():
            k += 1
        if k < len(lines) and lines[k].startswith('*') and not lines[k].startswith('**'):
            j = k
            while j < len(lines) and lines[j].strip():
                j += 1
            cap = inline(' '.join(lines[k:j]).strip().strip('*')); i = j
        else:
            i += 1
        h.append(f'<figure><img src="{s}" alt="{html.escape(m.group(1))}" loading="lazy">' + (f'<figcaption>{cap}</figcaption>' if cap else '') + '</figure>')
        continue
    if l.startswith('|'):
        rows = []
        while i < len(lines) and lines[i].startswith('|'):
            c = [x.strip() for x in lines[i].strip().strip('|').split('|')]
            if not all(re.fullmatch(r':?-{3,}:?', x) for x in c):
                rows.append(c)
            i += 1
        t = '<table><thead><tr>' + ''.join(f'<th>{inline(x)}</th>' for x in rows[0]) + '</tr></thead><tbody>'
        t += ''.join('<tr>' + ''.join(f'<td>{inline(x)}</td>' for x in r) + '</tr>' for r in rows[1:]) + '</tbody></table>'
        h.append(t); continue
    if l.startswith('- '):
        items = []
        while i < len(lines) and (lines[i].startswith('- ') or lines[i].startswith('  ')):
            if lines[i].startswith('- '):
                items.append(lines[i][2:])
            else:
                items[-1] += ' ' + lines[i].strip()
            i += 1
        h.append('<ul>' + ''.join(f'<li>{inline(x)}</li>' for x in items) + '</ul>'); continue
    if l.startswith('>'):
        q = []
        while i < len(lines) and lines[i].startswith('>'):
            q.append(lines[i].lstrip('>').strip()); i += 1
        h.append('<blockquote>' + '<br>'.join(inline(x) for x in q) + '</blockquote>'); continue
    p = []
    while i < len(lines) and lines[i].strip() and not re.match(r'(#{1,4} |!\[|\||- |>|```)', lines[i]):
        p.append(lines[i].strip()); i += 1
    h.append(f'<p>{inline(" ".join(p))}</p>')

page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="author" content="Ted Bienapfl"><title>{html.escape(title)}</title><style>{css}{EXTRA}</style></head><body>
<main class="writeup"><p class="back"><a href="index.html">← Research log</a></p>
{chr(10).join(h)}
</main>
<footer class="foot">© 2026 Ted Bienapfl. Text CC BY 4.0, code MIT; figures contain Vesuvius Challenge / EduceLab scan data, CC BY-NC 4.0.
Source: {html.escape(str(src))} in github.com/skuzbucket1/scroll-prize, rendered by infra/site/build_writeup.py.</footer>
</body></html>
"""
out.write_text(page); print('wrote', out, len(page) // 1024, 'KB')
