"""Which way does a render's +layer direction point: toward the scroll centre or away from it?
For a flattened tifxyz and its 66-layer render (layer k samples the CT at (k-32.5) voxels along the renderer's normal):
 1. at ~N interior grid nodes, compute n = normalize(dP/dcol x dP/drow) from the grid, sample the CT along +n and -n, and
    correlate each with the render column -> the sign s with render(+k) = P + s*(k-32.5)*n;
 2. scroll centre at the node's z from umbilicus.json, or from a circle fit to the mesh points;
 3. report the share of nodes where s*n points AWAY from the centre (render +k = outward).
Usage: side_check.py <name> <tifxyz dir> <render.zarr> <CT zarr path or URL> [umbilicus.json|-] [nodes=60]"""
import json, sys, numpy as np, tifffile, zarr
name, T, R, CT = sys.argv[1:5]; U = sys.argv[5] if len(sys.argv) > 5 else '-'; N = int(sys.argv[6]) if len(sys.argv) > 6 else 60
X, Y, Z = (tifffile.imread(f'{T}/{c}.tif').astype(np.float64) for c in 'xyz')
ok = (X > 0) & np.isfinite(X) & np.isfinite(Y) & np.isfinite(Z)
rend = zarr.open(R, mode='r')['0']
ct = zarr.open(CT, mode='r')['0'] if not CT.startswith('http') else zarr.open_group(CT, mode='r', storage_options={'anon': True} if CT.startswith('s3') else None)['0']
H, W = X.shape; rng = np.random.default_rng(0)
cand = [(i, j) for i in range(3, H - 3, 2) for j in range(3, W - 3, 2) if ok[i-2:i+3, j-2:j+3].all()]
sel = [cand[k] for k in rng.choice(len(cand), size=min(N, len(cand)), replace=False)]
def P(i, j): return np.array([X[i, j], Y[i, j], Z[i, j]])
# centre
if U != '-':
    cps = sorted(json.load(open(U))['control_points'], key=lambda c: c['z']); zs = [c['z'] for c in cps]
    cen = lambda z: (np.interp(z, zs, [c['x'] for c in cps]), np.interp(z, zs, [c['y'] for c in cps]))
    src = 'umbilicus'
else:
    mid = H // 2; pts = np.stack([X[mid-3:mid+4][ok[mid-3:mid+4]], Y[mid-3:mid+4][ok[mid-3:mid+4]]], 1)
    A = np.c_[2 * pts, np.ones(len(pts))]; b = (pts ** 2).sum(1); cx, cy, c0 = np.linalg.lstsq(A, b, rcond=None)[0]
    r = np.sqrt(c0 + cx ** 2 + cy ** 2); cen = lambda z: (cx, cy); src = f'circle fit (r {r:.0f} vx, from {len(pts)} pts)'
votes, outward, cors = 0, 0, []
k = np.arange(66) - 32.5
for (i, j) in sel:
    p = P(i, j); du = P(i, j + 1) - P(i, j - 1); dv = P(i + 1, j) - P(i - 1, j)
    n = np.cross(du, dv); n /= np.linalg.norm(n)
    col = np.asarray(rend[:, i * 20, j * 20]).astype(np.float64)
    if (col == 0).mean() > 0.2: continue
    def samp(sign):
        q = p[None, :] + sign * k[:, None] * n[None, :]; qi = np.rint(q).astype(int)
        lo = qi.min(0); hi = qi.max(0) + 1
        blk = np.asarray(ct[lo[2]:hi[2], lo[1]:hi[1], lo[0]:hi[0]]).astype(np.float64)
        return blk[qi[:, 2] - lo[2], qi[:, 1] - lo[1], qi[:, 0] - lo[0]]
    cp, cm = samp(+1), samp(-1)
    if cp.std() == 0 or cm.std() == 0: continue
    rp, rm = np.corrcoef(col, cp)[0, 1], np.corrcoef(col, cm)[0, 1]; s = 1 if rp > rm else -1
    votes += s; cors.append((rp, rm))
    c = cen(p[2]); radial = np.array([p[0] - c[0], p[1] - c[1], 0.0])
    outward += 1 if np.dot(s * n, radial) > 0 else 0
m = len(cors); cors = np.array(cors)
print(f'{name}: {m} nodes; sign votes (+1 = render +k along dP/dcol x dP/drow) sum {votes:+d}; mean r(+n) {cors[:,0].mean():.2f}, r(-n) {cors[:,1].mean():.2f}; '
      f'centre from {src}; render +k points AWAY from the centre at {outward}/{m} nodes ({outward/m:.0%})')
