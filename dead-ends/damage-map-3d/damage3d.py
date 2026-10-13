"""Damage in three dimensions (2026-10-13, idea 3; Ted: a crack on one winding that runs X layers into the scroll is
damage, so look at the whole scroll in 3D, not at one unrolled winding at a time). Per voxel of the CT (pyramid level 2,
37.4 µm), from the structure tensor of the smoothed CT (sigma 1 voxel, integration 3 voxels), eigenvalues l1 >= l2 >= l3
with first eigenvector e1 (the local normal of any layered structure):
  P  planarity (l1 - l2) / l1: 1 = a clean sheet, 0 = no layering (crushed, fibrous or uniform)
  A  |e1 . r|, r = the radial direction from the umbilicus: 1 = the layer's normal points at the axis, as a winding's does
  D  dark: smoothed CT below half the median of the material (air: gaps between windings, holes, open cracks)
  C  cross-sheet crack: dark AND planar AND not radial (A < 0.5): a gap whose plane cuts across the windings. The normal
     air between two windings is dark and planar with A near 1, so it is not counted.
  CT the smoothed CT itself (for pictures)
  EZ, EY, EX  the components of e1, stored as (e + 1) / 2 x 255, so that the projection step can test a gap's plane
     against the winding's OWN normal (from its mesh) instead of the radial direction: in a crushed scroll the sheets
     are often far from radial, and the first projection run showed that (A median well below 1).
All stored as uint8 (P, A x 255; D, C 0/255) in <out>/fields.zarr with the level-2 z range in attrs. A second script
(damage3d_project.py) samples these along the radial line through every mesh node of a winding, so that a flag on winding
w can be checked against the damage on the windings behind and in front of it. GPU (torch); about 24 slices at a time.
Usage: damage3d.py <volume.zarr> <umbilicus.json> <z0> <z1> <out dir>   (z0, z1 at level 0, e.g. 11998 13001)"""
import json, math, os, sys
import numpy as np, torch, zarr

vol_p, umb_p, Z0, Z1, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
os.makedirs(out, exist_ok=True); dev = torch.device('cuda')
L = 2; S = 2 ** L
V = zarr.open(vol_p, mode='r')[str(L)]; NZ, NY, NX = V.shape
z0, z1 = max(0, Z0 // S - 4), min(NZ, (Z1 + S - 1) // S + 4); nz = z1 - z0
print(f'level {L}: {V.shape}; z {z0}..{z1} ({nz} slices)', flush=True)
# umbilicus (level-0 coords) -> per-slice axis position at level 2
cp = sorted(json.load(open(umb_p))['control_points'], key=lambda c: c['z'])
uz = np.array([c['z'] for c in cp]); ux = np.array([c['x'] for c in cp]); uy = np.array([c['y'] for c in cp])
zs = (np.arange(z0, z1) + 0.5) * S
ax = np.interp(zs, uz, ux) / S; ay = np.interp(zs, uz, uy) / S
# material median from a few slices
samp = np.concatenate([np.asarray(V[z, ::4, ::4]).ravel() for z in range(z0, z1, max(1, nz // 6))]); samp = samp[samp > 0]
med = float(np.median(samp)); dark_thr = 0.5 * med
print(f'material median {med:.1f}; dark below {dark_thr:.1f}', flush=True)
g = zarr.open_group(os.path.join(out, 'fields.zarr'), mode='w', zarr_format=2)
arrs = {k: g.create_array(k, shape=(nz, NY, NX), chunks=(8, 256, 256), dtype='u1', fill_value=0) for k in ('P', 'A', 'D', 'C', 'CT', 'EZ', 'EY', 'EX')}
g.attrs.update(dict(level=L, z0=z0, z1=z1, Z0=Z0, Z1=Z1, median=med, dark_thr=dark_thr, volume=vol_p, umbilicus=umb_p,
                    sigma=1.0, rho=3.0, A_crack_max=0.5, P_crack_min=0.4))


def gauss1d(sig):
    r = int(3 * sig); x = torch.arange(-r, r + 1, dtype=torch.float32, device=dev); k = torch.exp(-x ** 2 / (2 * sig ** 2))
    return (k / k.sum()), r


def blur(x, sig):
    """Separable Gaussian on a (Z, Y, X) tensor, reflect padding."""
    k, r = gauss1d(sig); x = x[None, None]
    for dim in (2, 3, 4):
        shape = [1, 1, 1, 1, 1]; shape[dim] = -1
        pad = [0, 0] * 3; pad[2 * (4 - dim)] = r; pad[2 * (4 - dim) + 1] = r
        x = torch.nn.functional.conv3d(torch.nn.functional.pad(x, pad, mode='reflect'), k.view(*shape))
    return x[0, 0]


def eig_sym3(a, b, c, d, e, f):
    """Largest two eigenvalues and the first eigenvector of symmetric 3x3 matrices [[a,b,c],[b,d,e],[c,e,f]] given as
    (Y, X) tensors, in closed form (the trigonometric solution), with the eigenvector from the cross product of two rows
    of M - l1 I. Returns l1, l2 (Y, X) and e1 (Y, X, 3) in (z, y, x) order."""
    q = (a + d + f) / 3
    p1 = b * b + c * c + e * e
    p = torch.sqrt(((a - q) ** 2 + (d - q) ** 2 + (f - q) ** 2 + 2 * p1) / 6) + 1e-12
    b00, b11, b22, b01, b02, b12 = (a - q) / p, (d - q) / p, (f - q) / p, b / p, c / p, e / p
    detB = b00 * (b11 * b22 - b12 * b12) - b01 * (b01 * b22 - b12 * b02) + b02 * (b01 * b12 - b11 * b02)
    phi = torch.acos((detB / 2).clamp(-1, 1)) / 3
    l1 = q + 2 * p * torch.cos(phi); l3 = q + 2 * p * torch.cos(phi + 2 * math.pi / 3); l2 = 3 * q - l1 - l3
    r0 = torch.stack([a - l1, b, c], -1); r1 = torch.stack([b, d - l1, e], -1); r2 = torch.stack([c, e, f - l1], -1)
    v01, v02, v12 = torch.cross(r0, r1, dim=-1), torch.cross(r0, r2, dim=-1), torch.cross(r1, r2, dim=-1)
    n01, n02, n12 = v01.norm(dim=-1), v02.norm(dim=-1), v12.norm(dim=-1)
    v = torch.where(((n01 >= n02) & (n01 >= n12))[..., None], v01, torch.where((n02 >= n12)[..., None], v02, v12))
    return l1, l2, v / (v.norm(dim=-1, keepdim=True) + 1e-12)


M = 8; step = 24
yy, xx = torch.meshgrid(torch.arange(NY, device=dev, dtype=torch.float32), torch.arange(NX, device=dev, dtype=torch.float32), indexing='ij')
for a0 in range(0, nz, step):
    a1 = min(nz, a0 + step); b0, b1 = max(0, a0 - M), min(nz, a1 + M)
    ct = torch.from_numpy(np.asarray(V[z0 + b0:z0 + b1]).astype(np.float32)).to(dev)
    sm = blur(ct, 1.0)
    gz = torch.zeros_like(sm); gy = torch.zeros_like(sm); gx = torch.zeros_like(sm)
    gz[1:-1] = (sm[2:] - sm[:-2]) / 2; gy[:, 1:-1] = (sm[:, 2:] - sm[:, :-2]) / 2; gx[:, :, 1:-1] = (sm[:, :, 2:] - sm[:, :, :-2]) / 2
    T = [blur(u * v, 3.0) for u, v in ((gz, gz), (gz, gy), (gz, gx), (gy, gy), (gy, gx), (gx, gx))]
    del gz, gy, gx
    for i in range(a0 - b0, a1 - b0):
        l1, l2, e1 = eig_sym3(*(X[i] for X in T))                # closed form; torch.linalg.eigh wanted 998 GiB here
        P = ((l1 - l2) / (l1 + 1e-6)).clamp(0, 1)
        zi = b0 + i; rx = xx - float(ax[zi]); ry = yy - float(ay[zi]); rn = torch.sqrt(rx ** 2 + ry ** 2) + 1e-6
        A = (e1[..., 2] * rx / rn + e1[..., 1] * ry / rn).abs().clamp(0, 1)
        mat = ct[i] > 0; s = sm[i]
        D = (s < dark_thr) & mat
        C = D & (P > 0.4) & (A < 0.5)
        P = torch.where(mat, P, torch.zeros_like(P)); A = torch.where(mat, A, torch.zeros_like(A))
        arrs['P'][zi] = (P * 255).round().to(torch.uint8).cpu().numpy(); arrs['A'][zi] = (A * 255).round().to(torch.uint8).cpu().numpy()
        arrs['D'][zi] = (D.to(torch.uint8) * 255).cpu().numpy(); arrs['C'][zi] = (C.to(torch.uint8) * 255).cpu().numpy()
        arrs['CT'][zi] = s.clamp(0, 255).to(torch.uint8).cpu().numpy()
        for k, c in (('EZ', 0), ('EY', 1), ('EX', 2)):
            arrs[k][zi] = ((e1[..., c] + 1) / 2 * 255).round().clamp(0, 255).to(torch.uint8).cpu().numpy()
    del ct, sm, T; torch.cuda.empty_cache()
    print(f'slices {a0}..{a1} of {nz} done', flush=True)
# a quick summary over the material
zmid = nz // 2; Pm, Am, Dm, Cm, CTm = (np.asarray(arrs[k][zmid]) for k in ('P', 'A', 'D', 'C', 'CT'))
mat = CTm > 0
print(f'middle slice: material {mat.mean():.1%}; planarity median {np.median(Pm[mat]) / 255:.2f}; radial alignment median '
      f'{np.median(Am[mat]) / 255:.2f}; dark {(Dm[mat] > 0).mean():.1%}; cross-sheet crack {(Cm[mat] > 0).mean():.2%}', flush=True)
print('written', os.path.join(out, 'fields.zarr'))
