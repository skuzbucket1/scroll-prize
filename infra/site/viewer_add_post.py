#!/usr/bin/env python3
"""Copy post_models.py previews into the winding viewer: every <root>/**/<name>__{ct,ens_reading,ens_blind}__d+NN.jpg and
<name>__post.json goes to data/viewer/img/<set>/<group>/<wNNN>/ renamed to wNNN__..., where wNNN is the winding number
found in <name> (e.g. exp30k-z7680_w040 -> w040). A --match text keeps only names that contain it. Existing files with the
same size are skipped, so it can be rerun as results come in; then rebuild with build_viewer.py.
Usage: viewer_add_post.py <root> <set>/<group> [--match text] [viewer dir]"""
import os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
args = sys.argv[1:]
match = None
if '--match' in args:
    i = args.index('--match'); match = args[i + 1]; del args[i:i + 2]
src, key = args[0], args[1]
VIEW = args[2] if len(args) > 2 else os.path.join(ROOT, 'data', 'viewer')
FILE = re.compile(r'^(.*?)__(ct|ens_reading|ens_blind)__d([+-]\d+)\.jpg$|^(.*?)__post\.json$')
n = 0
for d, _, files in os.walk(src):
    for f in files:
        m = FILE.match(f)
        if not m:
            continue
        name = m.group(1) or m.group(4)
        if match and match not in name:
            continue
        w = re.findall(r'(w\d+)', name)
        if not w:
            continue
        w = w[-1]; dst = os.path.join(VIEW, 'img', key, w); os.makedirs(dst, exist_ok=True)
        t = os.path.join(dst, w + f[len(name):]); s = os.path.join(d, f)
        if os.path.exists(t) and os.path.getsize(t) == os.path.getsize(s):
            continue
        shutil.copy2(s, t); n += 1
print(f'{key}: {n} files copied')
