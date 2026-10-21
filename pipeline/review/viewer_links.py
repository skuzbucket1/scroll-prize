"""Links between neighbouring windings for the local viewer (infra/site/build_viewer.py). For points on each winding (every
`step` render pixels), the same place on the previous and the next winding of the list, found through the 3D flattened
meshes (the neighbour's nearest node), and the distance between the two surfaces there: a few hundredths of a mm means
the same sheet (the fit put both windings on it). Also each winding's real size of a preview pixel (median 3D spacing
of its mesh nodes, voxel size, render pixels per node and per preview pixel).
Usage: viewer_links.py <out.json> <group> <scroll dir> <fit> <um> <w,w,...> [<group> <scroll dir> <fit> <um> <w,...> ...] (all options: --help)
       [--step 400] [--preview 2]"""
import argparse, json, os
import numpy as np, tifffile
from scipy.spatial import cKDTree

ap = argparse.ArgumentParser()
ap.add_argument('out'); ap.add_argument('groups', nargs='+'); ap.add_argument('--step', type=int, default=400)
ap.add_argument('--preview', type=int, default=2)
a = ap.parse_args()
assert len(a.groups) % 5 == 0, 'groups come in fives: group scroll_dir fit um windings'
out = {}
for g in range(0, len(a.groups), 5):
    gid, sdir, fit, um, ws = a.groups[g:g + 5]; um = float(um)
    ws = sorted(w for w in ws.split(',') if w)
    mesh = {}
    for w in ws:
        d = f'{sdir}/geometry/{fit}/flattened/{w}/tifxyz/flatten.tifxyz'
        if not os.path.isdir(d):
            continue
        X, Y, Z = (tifffile.imread(f'{d}/{k}.tif').astype(np.float64) for k in 'xyz')
        sc = json.load(open(f'{d}/meta.json'))['scale'][0]; ok = (X >= 0) & (Y >= 0) & (Z >= 0)
        P = np.stack([Z, Y, X], -1)
        dc = np.linalg.norm(P[:, 1:] - P[:, :-1], axis=-1)[ok[:, 1:] & ok[:, :-1]]
        rr, cc = np.nonzero(ok)
        mesh[w] = dict(P=P, ok=ok, sc=sc, nodes=P[rr, cc], rc=np.stack([rr, cc], 1) / sc, tree=None,
                       um_px=float(np.median(dc)) * sc * um * a.preview)
    names = [w for w in ws if w in mesh]; G = out.setdefault(gid, {})
    nstep = max(1, int(round(a.step * mesh[names[0]]['sc']))) if names else 1
    for i, w in enumerate(names):
        m = mesh[w]; ent = {'um_px': round(m['um_px'], 3)}
        si, sj = np.meshgrid(np.arange(0, m['ok'].shape[0], nstep), np.arange(0, m['ok'].shape[1], nstep), indexing='ij')
        keep = m['ok'][si, sj]; si, sj = si[keep], sj[keep]; pts = m['P'][si, sj]
        for key, j in (('prev', i - 1), ('next', i + 1)):
            if not 0 <= j < len(names):
                continue
            n = mesh[names[j]]
            if n['tree'] is None:
                n['tree'] = cKDTree(n['nodes'])
            dist, k = n['tree'].query(pts)
            r2, c2 = n['rc'][k, 0], n['rc'][k, 1]
            p = a.preview
            ent[key] = {'w': names[j], 'pts': [[int(round(r / m['sc'] / p)), int(round(c / m['sc'] / p)), int(round(y / p)), int(round(x / p)),
                                                int(round(dd * um / 10))] for r, c, y, x, dd in zip(si, sj, r2, c2, dist)]}
        G[w] = ent
    print(f'{gid}: {len(names)} windings linked; preview pixel {np.median([mesh[w]["um_px"] for w in names]):.2f} um')
json.dump(out, open(a.out, 'w'), separators=(',', ':'))
print(a.out, f'{os.path.getsize(a.out) / 1024:.0f} KiB')
