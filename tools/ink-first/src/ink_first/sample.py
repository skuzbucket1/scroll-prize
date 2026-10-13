"""Cut 66-layer patches along the local sheet normal at points sampled on a surface prediction, with no mesh, and tile them
into one mosaic "surface volume" that any 66-layer ink model can ink unchanged.

  surface points  voxels of the prediction >= thr, one per stride^3 cell (the voxel nearest the cell's mean); cell by cell,
                  because a dense block can hold hundreds of millions of surface voxels
  normal          smallest-variance direction of the prediction's voxels within `radius`; points where the two smallest
                  variances are not clearly apart (ratio > `flat`) are not sheet-like (junctions, noise) and are dropped;
                  the sign points out of the papyrus (the CT is brighter 3 voxels behind the point than 3 voxels in front)
  patch           size x size pixels in the tangent plane (u close to the scroll axis z, so lines of text lie along v),
                  66 layers at (k - 32.5) voxels along the normal, the convention of Nieuwlaar's 66-layer renders
"""
from __future__ import annotations

import os
import time

import numpy as np
from scipy.ndimage import map_coordinates

LAYERS = 66


def surface_points(pr: np.ndarray, thr: int, stride: int, margin: int, min_voxels: int = 20, per_sheet: bool = False,
                   sheet_min: int = 200) -> np.ndarray:
    """Surface points of the block (block-local zyx): one per stride^3 cell, the prediction voxel nearest the cell's mean;
    or, with `per_sheet`, one per separate piece of surface in the cell (connected pieces of the prediction >= thr with at
    least `sheet_min` voxels), so that every sheet crossing the cell gets a point. Where sheets lie closer together than
    the cell, the plain mode gives most of them no point at all (on PHerc. 343: 37 of 766 patches on the letters' sheet)."""
    from scipy.ndimage import label
    centres = []
    for cz in range(margin, pr.shape[0] - margin, stride):
        for cy in range(margin, pr.shape[1] - margin, stride):
            for cx in range(margin, pr.shape[2] - margin, stride):
                cell = pr[cz:min(cz + stride, pr.shape[0] - margin), cy:min(cy + stride, pr.shape[1] - margin),
                          cx:min(cx + stride, pr.shape[2] - margin)]
                off = np.array([cz, cy, cx])
                if not per_sheet:
                    grp = np.argwhere(cell >= thr)
                    if len(grp) < min_voxels:
                        continue
                    mu = grp.mean(0)
                    centres.append(grp[np.argmin(((grp - mu) ** 2).sum(1))] + off)
                    continue
                lab, n = label(cell >= thr)
                if not n:
                    continue
                idx = np.argwhere(lab > 0); ids = lab[tuple(idx.T)]; order = np.argsort(ids, kind='stable')
                idx, ids = idx[order], ids[order]; cuts = np.flatnonzero(np.diff(ids)) + 1
                for grp in np.split(idx, cuts):
                    if len(grp) < max(sheet_min, min_voxels):
                        continue
                    mu = grp.mean(0)
                    centres.append(grp[np.argmin(((grp - mu) ** 2).sum(1))] + off)
    return np.array(centres).reshape(-1, 3)


def normals(pr: np.ndarray, ct: np.ndarray, centres: np.ndarray, thr: int, radius: int, flat: float) -> tuple[np.ndarray, np.ndarray]:
    """Unit normals at the sheet-like points; returns (kept centres, normals)."""
    keep, out = [], []
    for c in centres:
        sl = tuple(slice(max(0, q - radius), q + radius + 1) for q in c)
        loc = np.argwhere(pr[sl] >= thr)
        if len(loc) < 30:
            continue
        w, v = np.linalg.eigh(np.cov((loc - loc.mean(0)).T))
        if w[0] > flat * w[1]:
            continue
        n = v[:, 0]
        behind = map_coordinates(ct, (c - 3 * n)[:, None], order=1)[0]
        front = map_coordinates(ct, (c + 3 * n)[:, None], order=1)[0]
        keep.append(c); out.append(n if behind >= front else -n)
    return np.array(keep).reshape(-1, 3), np.array(out).reshape(-1, 3)


def tangent_bases(N: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """u: the scroll axis z projected into the tangent plane (fallback: y), v = n x u."""
    ez = np.array([1.0, 0, 0])
    U = ez - (N @ ez)[:, None] * N
    bad = np.linalg.norm(U, axis=1) < 0.3
    U[bad] = np.cross(N[bad], [0, 1.0, 0])
    U /= np.linalg.norm(U, axis=1, keepdims=True)
    return U, np.cross(N, U)


def cut_patch(ct: np.ndarray, c, n, u, v, size: int) -> np.ndarray:
    """(66, size, size) uint8 stack: layer k samples the CT at (k - 32.5) voxels along n around the plane c + i u + j v."""
    ii, jj = np.mgrid[0:size, 0:size].astype(np.float32) - (size - 1) / 2
    plane = c[:, None, None] + u[:, None, None] * ii + v[:, None, None] * jj
    stack = np.empty((LAYERS, size, size), np.uint8)
    for k in range(LAYERS):
        q = plane + n[:, None, None] * (k - (LAYERS - 1) / 2)
        stack[k] = np.clip(map_coordinates(ct, q.reshape(3, -1), order=1, mode='constant', cval=0), 0, 255).reshape(size, size)
    return stack


def sample_block(ct_path: str, pred_path: str, box, out: str, thr: int = 128, stride: int = 96, size: int = 256,
                 radius: int = 10, flat: float = 0.25, margin: int = 48, log=print, per_sheet: bool = False, sheet_min: int = 200) -> dict:
    """Read the block (z0 z1 y0 y1 x0 x1, level 0) of a CT zarr and a surface-prediction zarr, cut the patches, write
    <out>/mosaic.zarr (66, H, W) and <out>/patches.npz (centre in volume coords, normal, u, v, mosaic row/col, size, box)."""
    import zarr
    z0, z1, y0, y1, x0, x1 = map(int, box)
    os.makedirs(out, exist_ok=True); t0 = time.time()
    ct = np.asarray(zarr.open(ct_path, mode='r')['0'][z0:z1, y0:y1, x0:x1])
    pr = np.asarray(zarr.open(pred_path, mode='r')['0'][z0:z1, y0:y1, x0:x1])
    log(f'block {ct.shape}, CT nonzero {np.mean(ct > 0):.2f}, prediction >= {thr}: {np.mean(pr >= thr):.4f} ({time.time() - t0:.0f}s)')
    cen = surface_points(pr, thr, stride, margin, per_sheet=per_sheet, sheet_min=sheet_min)
    log(f'{len(cen)} surface points' + (' (one per sheet piece per cell)' if per_sheet else ''))
    cen, N = normals(pr, ct, cen, thr, radius, flat)
    log(f'{len(cen)} sheet-like points ({time.time() - t0:.0f}s)')
    if not len(cen):
        raise SystemExit('no sheet-like surface points in this block')
    U, V = tangent_bases(N)
    g = int(np.ceil(np.sqrt(len(cen)))); H = W = g * size
    mz = zarr.open_group(os.path.join(out, 'mosaic.zarr'), mode='w', zarr_format=2)
    arr = mz.create_array('0', shape=(LAYERS, H, W), chunks=(LAYERS, 256, 256), dtype='u1', fill_value=0)
    rowcol = []
    for p, (c, n, u, v) in enumerate(zip(cen, N, U, V)):
        r, k = divmod(p, g); rowcol.append((r, k))
        arr[:, r * size:(r + 1) * size, k * size:(k + 1) * size] = cut_patch(ct, c, n, u, v, size)
        if p % 500 == 0:
            log(f'  patch {p}/{len(cen)} ({time.time() - t0:.0f}s)')
    np.savez_compressed(os.path.join(out, 'patches.npz'), centre=cen + np.array([z0, y0, x0]), normal=N, u=U, v=V,
                        rowcol=np.array(rowcol), size=size, box=np.array([z0, z1, y0, y1, x0, x1]))
    info = dict(patches=len(cen), mosaic=[H, W], seconds=round(time.time() - t0))
    log(f'mosaic {H} x {W} ({g} x {g} patches of {size}) -> {out} in {info["seconds"]}s')
    return info
