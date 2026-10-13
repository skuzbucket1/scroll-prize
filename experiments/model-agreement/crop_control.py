"""A known-text control cut down to its labelled area (2026-10-13). The official ink labels in the open-data bucket
(announced 2026-09-22; <segment>/ink-labels/<volume>/<date>/{inklabels,supervision}.zarr) cover small parts of whole
windings that are 5-6 cm tall, so rendering the full winding for each would cost hours of CT download and CPU. This
downloads the segment's mesh on the 9 µm volume and its labels, finds the bounding box of the supervision mask (the area
someone actually checked), and writes a cropped mesh, cropped labels and a cropped supervision mask that line up with
each other: the labels span the mesh's whole UV grid (label_boxes.py and control_eval.py resize them to the render), so
the crop is taken in mesh-grid rows and columns and carried over to the label grid in proportion. Labels drawn on a
2.4 µm render of the same segment scale the same way.
Output <out>/: mesh.tifxyz/ (x, y, z .tif + meta.json), labels.zarr, supervision.zarr (zarr v2 groups with array '0'),
crop.json (the crop in mesh and label pixels).
Usage: crop_control.py <mesh prefix> <ink-labels prefix (…/<date>/)> <out dir> [--margin-mm 1.5] [--um 9.362]"""
import json, os, re, sys, urllib.request
import numpy as np, tifffile, zarr

S3 = 'https://vesuvius-challenge-open-data.s3.amazonaws.com'


def keys(prefix):
    out, token = [], None
    while True:
        url = f'{S3}/?list-type=2&prefix={prefix}' + (f'&continuation-token={urllib.request.quote(token)}' if token else '')
        x = urllib.request.urlopen(url, timeout=60).read().decode()
        out += re.findall(r'<Key>([^<]+)</Key>', x)
        m = re.search(r'<NextContinuationToken>([^<]+)</NextContinuationToken>', x)
        if not m:
            return out
        token = m.group(1)


def get_tree(prefix, dest):
    for k in keys(prefix):
        p = os.path.join(dest, os.path.relpath(k, prefix))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        if not os.path.exists(p):
            urllib.request.urlretrieve(f'{S3}/{k}', p + '.part'); os.replace(p + '.part', p)


args = sys.argv[1:]
def opt(k, d):
    if k in args:
        i = args.index(k); v = args[i + 1]; del args[i:i + 2]; return v
    return d
margin_mm, um = float(opt('--margin-mm', '1.5')), float(opt('--um', '9.362'))
mesh_p, lab_p, out = args[0].rstrip('/') + '/', args[1].rstrip('/') + '/', args[2]
raw = os.path.join(out, 'raw'); os.makedirs(raw, exist_ok=True)
get_tree(mesh_p, os.path.join(raw, 'mesh.tifxyz'))
get_tree(lab_p + 'inklabels.zarr/', os.path.join(raw, 'labels.zarr'))
get_tree(lab_p + 'supervision.zarr/', os.path.join(raw, 'supervision.zarr'))

X, Y, Z = (tifffile.imread(os.path.join(raw, 'mesh.tifxyz', f'{c}.tif')) for c in 'xyz')
meta = json.load(open(os.path.join(raw, 'mesh.tifxyz', 'meta.json')))
hm, wm = X.shape
L = np.asarray(zarr.open(os.path.join(raw, 'labels.zarr'), mode='r')['0'])
S = np.asarray(zarr.open(os.path.join(raw, 'supervision.zarr'), mode='r')['0'])
L, S = np.squeeze(L), np.squeeze(S)
hl, wl = S.shape
rr, cc = np.nonzero(S > 0)
if not len(rr):
    sys.exit('empty supervision mask')
# margin in mesh nodes: one node = 1 / scale render pixels of `um` µm
node_mm = um / 1000 / meta['scale'][0]
mg = int(np.ceil(margin_mm / node_mm))
r0 = max(0, int(np.floor(rr.min() / hl * hm)) - mg); r1 = min(hm, int(np.ceil((rr.max() + 1) / hl * hm)) + mg)
c0 = max(0, int(np.floor(cc.min() / wl * wm)) - mg); c1 = min(wm, int(np.ceil((cc.max() + 1) / wl * wm)) + mg)
lr0, lr1 = round(r0 / hm * hl), round(r1 / hm * hl); lc0, lc1 = round(c0 / wm * wl), round(c1 / wm * wl)

md = os.path.join(out, 'mesh.tifxyz'); os.makedirs(md, exist_ok=True)
for c, A in zip('xyz', (X, Y, Z)):
    tifffile.imwrite(os.path.join(md, f'{c}.tif'), A[r0:r1, c0:c1])
v = Z[r0:r1, c0:c1] > 0
pts = np.stack([A[r0:r1, c0:c1][v] for A in (X, Y, Z)], 1)
m2 = {k: meta[k] for k in meta if k not in ('bbox', 'area_vx2', 'area_cm2')}
m2['bbox'] = [pts.min(0).tolist(), pts.max(0).tolist()]
m2['uuid'] = os.path.basename(out.rstrip('/'))
json.dump(m2, open(os.path.join(md, 'meta.json'), 'w'))
for name, A in (('labels', L), ('supervision', S)):
    g = zarr.open_group(os.path.join(out, f'{name}.zarr'), mode='w', zarr_format=2)
    g.create_array(name='0', data=np.ascontiguousarray(A[lr0:lr1, lc0:lc1]), chunks=(1024, 1024))
crop = dict(mesh=dict(r0=r0, r1=r1, c0=c0, c1=c1, shape=[hm, wm]), labels=dict(r0=lr0, r1=lr1, c0=lc0, c1=lc1, shape=[hl, wl]),
            margin_mm=margin_mm, um=um, mesh_prefix=mesh_p, labels_prefix=lab_p,
            supervised_px=int((S[lr0:lr1, lc0:lc1] > 0).sum()), labelled_px=int((L[lr0:lr1, lc0:lc1] > 0).sum()))
json.dump(crop, open(os.path.join(out, 'crop.json'), 'w'), indent=1)
print(f'{out}: mesh {hm}x{wm} -> rows {r0}:{r1} cols {c0}:{c1} ({(r1 - r0) * (c1 - c0)} nodes, '
      f'{(r1 - r0) * node_mm:.1f} x {(c1 - c0) * node_mm:.1f} mm); labels {hl}x{wl} -> {lr0}:{lr1}, {lc0}:{lc1}; '
      f'supervised {crop["supervised_px"]} px, labelled {crop["labelled_px"]} px')
