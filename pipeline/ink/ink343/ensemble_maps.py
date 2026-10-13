#!/usr/bin/env python3
"""ensemble_maps.py - grayscale images of the ink maps (four models and their ensemble, reading side and blind side)
and of the CT, for one 66-layer surface volume, exactly as used for viewing the PHerc0343 depth sweep.

  python ensemble_maps.py --surface <name>.zarr --maps <dir with run_ink.sh outputs> --out <dir> [--write-depths 0 -1]
                          [--stat-depths -15..15] [--orientation reading|raw]

What it computes (all statistics come from the READING side = the "reverse" maps; the BLIND side = "forward" maps is
shown with the reading side's statistics, never with its own):

  valid pixels   CT > 0 in all 66 layers of the surface volume.
  map values     villa models: uint8 v -> clip((v - 64) / 128, 0, 1), i.e. (p - 0.25) / 0.5 for the label-smoothed
                 models; Hecate: v / 255, bilinearly resized from its 9.6 um grid to the render grid (cv2.INTER_LINEAR).
  one stretch    per model: p1 and p99.5 of all valid pixels of all reverse depths in --stat-depths (exact, from a
                 histogram), mapped linearly to 0..255 and clipped. Never a per-depth stretch, so brightness differences
                 between depths remain visible.
  ensemble       per model a z-score with that model's pooled mean and SD (reverse, all --stat-depths, valid pixels);
                 ensemble = mean of the four z-scores; ONE ensemble stretch = p1..p99.5 of the ensemble over a fixed grid
                 (every 8th row and column, starting at 4) of valid pixels at all depths where all four models exist.
  CT             layer 33 + d; one stretch p1..p99.5 over the valid pixels of the 31 layers 18..48 (d -15..+15).
  orientation    'reading' = rotated by 180 degrees (rows and columns reversed): high z at the top, theta decreasing
                 to the right. This was measured for every official mesh from its tifxyz (sign of d(theta)/d(column)
                 and of dz/d(row) around my umbilicus estimate); 'raw' = render orientation.

Outputs: <name>__<stack>__d+NN.png with stack in {ensemble, dnative, hecate, ink9-42, ink9-43} (reading side),
the same with suffix _blind, and ct; plus <name>__stats.json with every number used. Invalid pixels are black.
No annotations of any kind are drawn.
"""
import argparse, glob, json, math, os, time
import numpy as np

MODELS = [('dnative', 'dnative'), ('hecate', 'hecate'),            # order matters for the float32 sums
          ('ink9-42', 'hybrid_3d2d-seed42'), ('ink9-43', 'hybrid_3d2d-seed43')]
N66, MID = 66, 33
P_LO, P_HI = 1.0, 99.5
FINE = 65536                 # histogram bins for Hecate values on [0, 1]
SUB = 8                      # fixed grid for the ensemble stretch


def pct_hist(hist, values, qs):
    """np.percentile (linear) computed exactly from a histogram over discrete values."""
    c = np.cumsum(hist)
    n = int(c[-1])
    out = []
    for q in qs:
        pos = q / 100.0 * (n - 1)
        lo = int(math.floor(pos)); fr = pos - lo
        i_lo = int(np.searchsorted(c, lo + 1))
        i_hi = int(np.searchsorted(c, min(lo + 2, n))) if fr > 0 else i_lo
        out.append(float(values[i_lo] + fr * (values[i_hi] - values[i_lo])))
    return out


def map_path(maps, name, mk, direction, d):
    rev = '_reverse' if direction == 'reverse' else ''
    if mk == 'hecate':
        p = os.path.join(maps, f'{name}__hecate__L66zc{32.5 + d:.2f}{rev}.png')
    else:
        p = os.path.join(maps, f'{name}__{mk}__L66s{d + 25}{rev}.tif')
    return p if os.path.isfile(p) else None


def read_map(path, shape):
    """ink map as float32 0..1 on the render grid."""
    import cv2, tifffile
    if path.lower().endswith('.png'):
        a = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if a.ndim == 3:
            a = a[..., 0]
        a = a.astype(np.float32) / (65535. if a.dtype == np.uint16 else 255.)
        if a.shape != tuple(shape):
            a = cv2.resize(a, (shape[1], shape[0]), interpolation=cv2.INTER_LINEAR)
    else:
        a = tifffile.imread(path)
        if a.dtype == np.uint8:
            a = np.clip((a.astype(np.float32) - 64.) / 128., 0, 1)
        elif a.dtype == np.uint16:
            a = a.astype(np.float32) / 65535.
        else:
            a = a.astype(np.float32)
        if a.shape != tuple(shape):
            raise ValueError(f'{path}: shape {a.shape} != surface {tuple(shape)}')
    return np.ascontiguousarray(a, dtype=np.float32)


def to8(M, lo, hi, valid, orient):
    b = (np.clip((M - lo) / max(hi - lo, 1e-9), 0, 1) * 255).astype(np.uint8)
    b[~valid] = 0
    return np.ascontiguousarray(b[::-1, ::-1]) if orient == 'reading' else b


def write_png(path, b):
    import cv2
    if not cv2.imwrite(path, b, [cv2.IMWRITE_PNG_COMPRESSION, 3]):
        raise IOError(path)


def parse_depths(s):
    out = []
    for part in s:
        if '..' in part:
            a, b = part.split('..')
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return sorted(set(out))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--surface', required=True, help='66-layer surface volume (zarr group, array "0")')
    ap.add_argument('--maps', required=True, help='directory with the run_ink.sh outputs for this surface')
    ap.add_argument('--out', required=True)
    ap.add_argument('--name', help='map name prefix (default: surface file name without .zarr)')
    ap.add_argument('--stat-depths', nargs='+', default=['-15..15'])
    ap.add_argument('--write-depths', nargs='+', default=['0'])
    ap.add_argument('--orientation', choices=('reading', 'raw'), default='reading')
    a = ap.parse_args()
    import zarr
    name = a.name or os.path.basename(a.surface.rstrip('/'))[:-5]
    stat_ds, write_ds = parse_depths(a.stat_depths), parse_depths(a.write_depths)
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()

    # valid pixels and CT statistics (layers 33-15 .. 33+15)
    st = zarr.open_group(a.surface, mode='r')['0']
    assert st.shape[0] == N66, st.shape
    H, W = int(st.shape[1]), int(st.shape[2])
    valid = np.zeros((H, W), bool)
    hist_ct = np.zeros(256, np.int64)
    ct_layers = {}
    for r0 in range(0, H, 128):
        blk = np.asarray(st[:, r0:r0 + 128, :])
        gg = (blk > 0).all(0)
        valid[r0:r0 + blk.shape[1]] = gg
        sel = blk[MID - 15:MID + 16]
        hist_ct += np.bincount(sel[:, gg].ravel(), minlength=256)
        for d in write_ds:
            ct_layers.setdefault(d, []).append(blk[MID + d])
    ct_lo, ct_hi = pct_hist(hist_ct, np.arange(256, dtype=float), [P_LO, P_HI])
    sub = np.zeros_like(valid)
    sub[SUB // 2::SUB, SUB // 2::SUB] = True
    sub &= valid
    stats = dict(surface=os.path.basename(a.surface.rstrip('/')), H=H, W=W, valid_px=int(valid.sum()),
                 ct=dict(p1=ct_lo, p99_5=ct_hi, layers=[MID - 15, MID + 15]), models={})

    # per-model statistics from the reading side
    subs = {}
    for sn, mk in MODELS:
        villa = mk != 'hecate'
        hist = np.zeros(129 if villa else FINE, np.int64)
        s1 = s2 = 0.0; n = 0; ds = []; sv = []
        for d in stat_ds:
            p = map_path(a.maps, name, mk, 'reverse', d)
            if not p:
                continue
            M = read_map(p, (H, W))
            v = M[valid]
            if villa:
                hist += np.bincount(np.rint(v * 128).astype(np.int64), minlength=129)[:129]
            else:
                hist += np.bincount(np.minimum((v * FINE).astype(np.int64), FINE - 1), minlength=FINE)
            s1 += float(v.sum(dtype=np.float64)); s2 += float(np.square(v, dtype=np.float64).sum()); n += v.size
            sv.append(M[sub].astype(np.float32)); ds.append(d)
        if not ds:
            stats['models'][sn] = dict(model=mk, depths=[])
            continue
        values = (np.arange(129) / 128.0) if villa else (np.arange(FINE) / FINE)
        lo, hi = pct_hist(hist, values, [P_LO, P_HI])
        mu = s1 / n
        sd = math.sqrt(max(s2 / n - mu * mu, 0.0)) + 1e-6
        stats['models'][sn] = dict(model=mk, depths=ds, p1=lo, p99_5=hi, mean=mu, sd=sd, n_px=n)
        subs[sn] = np.stack(sv)
        print(f'{sn}: {len(ds)} depths, stretch {lo:.4f}..{hi:.4f}, mean {mu:.4f}, sd {sd:.4f}', flush=True)

    # ensemble statistics on the fixed grid, at depths where every model with maps exists
    ens_models = [sn for sn, _ in MODELS if stats['models'][sn].get('depths')]
    common = sorted(set.intersection(*[set(stats['models'][sn]['depths']) for sn in ens_models])) if ens_models else []
    ens = dict(models=ens_models, depths=common)
    if len(ens_models) >= 2 and common:
        E = None
        for sn in ens_models:
            m = stats['models'][sn]
            idx = [m['depths'].index(d) for d in common]
            z = (subs[sn][idx] - m['mean']) / m['sd']
            E = z if E is None else E + z
        E /= len(ens_models)
        ens['p1'], ens['p99_5'] = (float(x) for x in np.percentile(E.ravel(), [P_LO, P_HI]))
        ens['n_grid'] = int(E.size)
    stats['ensemble'] = ens

    # images
    for d in write_ds:
        ct = np.concatenate(ct_layers[d], axis=0)
        write_png(os.path.join(a.out, f'{name}__ct__d{d:+03d}.png'), to8(ct.astype(np.float32), ct_lo, ct_hi, valid,
                                                                        a.orientation))
        for direction, suffix in (('reverse', ''), ('forward', '_blind')):
            acc = None; nmod = 0
            for sn, mk in MODELS:
                m = stats['models'][sn]
                if 'p1' not in m:
                    continue
                p = map_path(a.maps, name, mk, direction, d)
                if not p:
                    print(f'missing: {sn} {direction} d{d:+d}')
                    continue
                M = read_map(p, (H, W))
                write_png(os.path.join(a.out, f'{name}__{sn}{suffix}__d{d:+03d}.png'),
                          to8(M, m['p1'], m['p99_5'], valid, a.orientation))
                if ens.get('p1') is not None and sn in ens['models']:
                    zc = (M - m['mean']) / m['sd']
                    acc = zc if acc is None else acc + zc
                    nmod += 1
            if ens.get('p1') is not None and nmod == len(ens['models']):
                write_png(os.path.join(a.out, f'{name}__ensemble{suffix}__d{d:+03d}.png'),
                          to8(acc / nmod, ens['p1'], ens['p99_5'], valid, a.orientation))
            else:
                print(f'no ensemble for {direction} d{d:+d} ({nmod} of {len(ens["models"])} models)')
        print(f'd{d:+d} written', flush=True)
    stats['orientation'] = a.orientation
    stats['seconds'] = round(time.time() - t0, 1)
    json.dump(stats, open(os.path.join(a.out, f'{name}__stats.json'), 'w'), indent=1)
    print('done', a.out)


if __name__ == '__main__':
    main()
