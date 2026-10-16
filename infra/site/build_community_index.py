"""Build docs/community.html: a findable index of what the Vesuvius Challenge community has shared on its Discord (2026-10-16).

Discord search is hard to use, and people keep asking where the public models, datasets, code and write-ups are. This page
lists every public resource linked in the exported channels and forum threads (models, datasets, code, papers, pages, videos),
who shared it first and when, how often it came up, and the forum threads with who started them; each row links back to the
Discord message. It copies no message text: only links, names as shown on the server, dates and thread titles.
Input: Ted's DiscordChatExporter JSON export in data/ref/discord_json (not in the repo). Usage: python3 -I infra/site/build_community_index.py"""
import collections, datetime, glob, html, json, os, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'data', 'ref', 'discord_json'); OUT = os.path.join(ROOT, 'docs', 'community.html')
URL = re.compile(r'https?://[^\s<>()\[\]"\'`|]+')
KIND = [('model', r'^huggingface\.co/(?!datasets/|spaces/)[^/]+/[^/]+'), ('dataset', r'^huggingface\.co/datasets/'),
        ('app', r'^huggingface\.co/spaces/'), ('data', r'^(dl2?\.ash2txt\.org|vesuvius-challenge-open-data\.s3[.\w-]*amazonaws\.com|zenodo\.org)/'),
        ('code', r'^(github\.com|gitlab\.com|gist\.github\.com|[\w-]+\.gitlab\.io|pypi\.org|kaggle\.com/code)/'),
        ('competition', r'^kaggle\.com/(competitions|c)/'), ('paper', r'^(arxiv\.org|doi\.org|nature\.com|journals\.plos\.org|biorxiv\.org|science\.org)/'),
        ('notebook', r'^colab\.research\.google\.com/'), ('video', r'^(youtube\.com|youtu\.be)/'),
        ('official', r'^(scrollprize\.org|scrollprize\.substack\.com)'), ('viewer', r'^vesuvius\.virtual-void\.net')]
SECRET = re.compile(r'(signature|token|key|sig|auth|session|expires)=', re.I)   # never publish signed / private links
TERMS = os.path.join(ROOT, 'data', 'ref', 'private_terms.txt')   # unversioned: one regex per line for links / threads to leave out
if not os.path.isfile(TERMS):
    raise SystemExit(f'{TERMS} is missing: it lists what must stay off the public page')
SKIP = re.compile('|'.join(l.strip() for l in open(TERMS) if l.strip() and not l.startswith('#')), re.I)


def norm(u):
    """a resource's canonical form: no scheme, query or fragment; GitHub / Hugging Face to the repository, data paths to 4 levels"""
    if SECRET.search(u):
        return None
    u = re.sub(r'^https?://(www\.|m\.)?', '', u.split('#')[0].split('?')[0]).rstrip('.,;:!)*_~>').rstrip('/')
    p = u.split('/'); h = p[0].lower()
    if h in ('github.com', 'gitlab.com') and len(p) >= 3:
        return '/'.join([h] + p[1:3])
    if h == 'huggingface.co' and len(p) >= 3:
        return '/'.join([h] + p[1:4] if p[1] in ('datasets', 'spaces') else [h] + p[1:3])
    if h in ('youtube.com',) and 'watch' in u:
        return None                                              # the video id lives in the query; keep youtu.be links only
    if h.startswith('dl') and 'ash2txt' in h or 'amazonaws.com' in h:
        return '/'.join([h] + p[1:5])
    return '/'.join([h] + p[1:])


def kind(n):
    return next((k for k, rx in KIND if re.match(rx, n)), None)


def who(a):
    return (a.get('nickname') or a.get('name') or '?').strip()


files = sorted(glob.glob(os.path.join(SRC, '*.json')))
res = {}; threads = []; chans = []; seen_msgs = set(); total = 0; first_day = last_day = None
for f in files:
    d = json.load(open(f)); g, c = d['guild']['id'], d['channel']; ms = d.get('messages', [])
    link = lambda m: f'https://discord.com/channels/{g}/{c["id"]}/{m["id"]}'
    ms = [m for m in ms if m['id'] not in seen_msgs]; seen_msgs |= {m['id'] for m in ms}; total += len(ms)
    if not ms:
        continue
    days = [m['timestamp'][:10] for m in ms]; first_day = min(first_day or days[0], min(days)); last_day = max(last_day or days[0], max(days))
    is_thread = c.get('type', '').endswith('Thread') or (c.get('category') not in ('Text Channels',) and c.get('type') != 'GuildTextChat')
    if is_thread:
        first = next((m for m in ms if not m['author'].get('isBot')), ms[0])
        if not SKIP.search(c.get('name', '')):
            threads.append(dict(title=c.get('name', '?'), forum=c.get('category', ''), by=who(first['author']), day=first['timestamp'][:10],
                            last=days[-1], n=len(ms), link=link(first)))
    else:
        chans.append(dict(name=c.get('name', '?'), n=len(ms), a=min(days), b=max(days)))
    where = c.get('name', '?') if not is_thread else f'{c.get("category", "")} › {c.get("name", "")}'
    for m in ms:
        if m['author'].get('isBot'):
            continue
        for u in URL.findall(m.get('content') or ''):
            n = norm(u); k = kind(n) if n else None
            if not k or SKIP.search(n):
                continue
            r = res.setdefault(n, dict(kind=k, n=0, people=set(), first=None, places=set()))
            r['n'] += 1; r['people'].add(who(m['author'])); r['places'].add(where if not SKIP.search(where) else 'a forum thread')
            if r['first'] is None or m['timestamp'] < r['first'][0]:
                r['first'] = (m['timestamp'], who(m['author']), link(m), 'https://' + n)

esc = html.escape
rows = sorted(res.items(), key=lambda kv: (-kv[1]['n'], kv[0]))
r_html = ''.join(
    f'<tr data-k="{esc(r["kind"])}"><td><a href="{esc(r["first"][3])}" rel="nofollow noopener">{esc(n)}</a></td><td>{esc(r["kind"])}</td>'
    f'<td>{esc(r["first"][1])}</td><td><a href="{esc(r["first"][2])}" rel="nofollow noopener">{r["first"][0][:10]}</a></td>'
    f'<td class="num">{r["n"]}</td><td class="num">{len(r["people"])}</td><td class="muted">{esc(", ".join(sorted(r["places"]))[:120])}</td></tr>'
    for n, r in rows)
t_html = ''.join(
    f'<tr><td><a href="{esc(t["link"])}" rel="nofollow noopener">{esc(t["title"])}</a></td><td>{esc(t["forum"])}</td><td>{esc(t["by"])}</td>'
    f'<td>{t["day"]}</td><td>{t["last"]}</td><td class="num">{t["n"]}</td></tr>'
    for t in sorted(threads, key=lambda t: t['last'], reverse=True))
c_html = ', '.join(f'#{esc(c["name"])} ({c["n"]:,} messages, {c["a"]} to {c["b"]})' for c in sorted(chans, key=lambda c: -c['n']))
kinds = collections.Counter(r['kind'] for r in res.values())
chips = ''.join(f'<button data-kind="{k}">{k} ({n})</button>' for k, n in sorted(kinds.items(), key=lambda kv: -kv[1]))
built = datetime.date.today().isoformat()

page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="author" content="Ted Bienapfl"><title>Vesuvius Challenge community index: what people have shared on the Discord</title><style>
:root{{color-scheme:light;--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--border:rgba(11,11,11,.10);--accent:#2a78d6;--accent-wash:rgba(42,120,214,.10)}}
@media (prefers-color-scheme:dark){{:root{{color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--muted:#898781;--border:rgba(255,255,255,.10);--accent:#3987e5;--accent-wash:rgba(57,135,229,.16)}}}}
*{{box-sizing:border-box}} body{{margin:0;font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--ink);background:var(--page)}}
a{{color:var(--accent)}} main{{max-width:1180px;margin:0 auto;padding:28px 20px 60px}} h1{{font-size:26px;margin:0 0 6px}} h2{{margin:34px 0 8px;font-size:19px}}
.lede{{color:var(--ink2);max-width:860px}} .muted{{color:var(--muted)}} .bar{{position:sticky;top:0;background:var(--page);padding:10px 0;z-index:2;border-bottom:1px solid var(--border)}}
input{{width:100%;padding:9px 12px;border-radius:8px;border:1px solid var(--border);background:var(--surface);color:var(--ink);font:inherit}}
.chips{{margin-top:8px;display:flex;flex-wrap:wrap;gap:6px}} .chips button{{border:1px solid var(--border);background:var(--surface);color:var(--ink2);border-radius:999px;padding:3px 10px;font:inherit;font-size:12.5px;cursor:pointer}}
.chips button.on{{background:var(--accent-wash);border-color:var(--accent);color:var(--ink)}}
table{{width:100%;border-collapse:collapse;font-size:13.5px}} th,td{{text-align:left;padding:6px 8px;border-bottom:1px solid var(--border);vertical-align:top}}
th{{position:sticky;top:96px;background:var(--page);font-weight:600;white-space:nowrap;cursor:pointer;user-select:none}} th:hover{{color:var(--accent)}}
th[aria-sort=ascending]::after{{content:" ▲";font-size:10px}} th[aria-sort=descending]::after{{content:" ▼";font-size:10px}} td.num{{text-align:right;font-variant-numeric:tabular-nums}} td:first-child{{word-break:break-all}}
.count{{font-size:13px;color:var(--muted);margin:6px 0}}
</style></head><body><main>
<p class="muted"><a href="index.html">← Ted Bienapfl's Vesuvius Challenge research log</a></p>
<h1>What the community has shared on the Discord</h1>
<p class="lede">Discord search makes it hard to find the models, datasets, code and write-ups people post for the Vesuvius Challenge.
This is an index of them. Every public link shared in the channels and forum threads below is listed once, with the person who
shared it first, the date (linked to the message), how often it came up and by how many people. The forum threads are listed
with who started them. Nothing here is copied from the messages: only links, names as shown on the server, dates and thread titles.
Everything belongs to the people who made and shared it; follow the links to their work and credit them.</p>
<p class="muted">Click a column heading to sort by it; click again to reverse.</p>
<p class="muted">Built {built} from a Discord export ({total:,} messages, {first_day} to {last_day}): {c_html}; and {len(threads)} forum threads.
Signed or private-looking links are left out. Tell me on the Discord if you want something added, corrected or removed.</p>
<div class="bar"><input id="q" type="search" placeholder="Search links, people, threads (e.g. ink_9um, Paris 4, lasagna, fiber, 0841)" autofocus>
<div class="chips">{chips}</div></div>
<h2 id="resources">Shared resources <span class="muted">({len(res):,})</span></h2><div class="count" id="rc"></div>
<table id="rt"><thead><tr><th>resource</th><th>kind</th><th>first shared by</th><th>first shared</th><th>times</th><th>people</th><th>where</th></tr></thead><tbody>{r_html}</tbody></table>
<h2 id="threads">Forum threads <span class="muted">({len(threads)})</span></h2><div class="count" id="tc"></div>
<table id="tt"><thead><tr><th>thread</th><th>forum</th><th>started by</th><th>started</th><th>last message</th><th>messages</th></tr></thead><tbody>{t_html}</tbody></table>
<p class="muted">Index built with a script in <a href="https://github.com/skuzbucket1/scroll-prize">skuzbucket1/scroll-prize</a>
(infra/site/build_community_index.py); export made with DiscordChatExporter by Tyrrrz.</p>
</main><script>
const q=document.getElementById('q'), kinds=new Set();
function run(){{const t=q.value.toLowerCase().trim();
 for(const [id,cid] of [['rt','rc'],['tt','tc']]){{let n=0,all=0;
  for(const tr of document.querySelectorAll('#'+id+' tbody tr')){{all++;const k=tr.dataset.k;
   const ok=(!t||tr.textContent.toLowerCase().includes(t))&&(id!=='rt'||!kinds.size||kinds.has(k));tr.hidden=!ok;if(ok)n++;}}
  document.getElementById(cid).textContent=(t||kinds.size)?n+' of '+all+' shown':'';}}}}
q.addEventListener('input',run);
for(const th of document.querySelectorAll('th')){{th.addEventListener('click',()=>{{
 const tb=th.closest('table').tBodies[0], i=[...th.parentNode.children].indexOf(th), num=tb.rows[0]&&tb.rows[0].cells[i].classList.contains('num');
 const cur=th.getAttribute('aria-sort'), first=tb.rows[0]?tb.rows[0].cells[i].textContent.trim():'', newestFirst=num||/^\\d{{4}}-\\d\\d-\\d\\d$/.test(first);
 const dir=cur==='ascending'?-1:cur==='descending'?1:(newestFirst?-1:1);
 for(const h of th.parentNode.children)h.removeAttribute('aria-sort'); th.setAttribute('aria-sort',dir===1?'ascending':'descending');
 const key=r=>{{const t=r.cells[i].textContent.trim();return num?parseFloat(t)||0:t.toLowerCase();}};
 [...tb.rows].sort((a,b)=>{{const x=key(a),y=key(b);return (x<y?-1:x>y?1:0)*dir;}}).forEach(r=>tb.appendChild(r));}});}}
for(const b of document.querySelectorAll('.chips button'))b.addEventListener('click',()=>{{const k=b.dataset.kind;
 kinds.has(k)?kinds.delete(k):kinds.add(k);b.classList.toggle('on');run();}});
</script></body></html>
"""
open(OUT, 'w').write(page)
print(f'wrote {OUT}: {len(res)} resources ({dict(kinds)}), {len(threads)} threads, {len(chans)} channels, {total} messages; {len(page) / 1e6:.1f} MB')
