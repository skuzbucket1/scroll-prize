"""Does stroke-score 0.2 triage better than plain ink measures? Known text cut into strips as tall as our search bands
and the null windings, every item scored with the same stroke-score functions (ensemble normalised within the item, as
for a search winding). Per item: the 0.2 features (row, shape, stroke-area contrast), the 0.2 flag, a 0.2 margin (the
rule's two lines as multiples of their thresholds; >= 1 means flagged) and plain-ink baselines: mean ink probability,
share of pixels >= 0.5, the reading - blind difference of that share, and the 0.1 stroke area.
Usage: triage_eval.py items <config.json> <out.jsonl> [--workers 3]
       triage_eval.py report <out.jsonl> [--top 20]
config: {"set": name, "models": [short names], "band_mm": 10.3, "step_mm": 2.0,
         "known": [{"label", "maps", "name", "depths", "um", "surface"(optional), "whole": false}],
         "nulls": [{"label", "maps", "renders", "windings", "depths", "um"}]}"""
import json, math, os, sys
from types import SimpleNamespace
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stroke-score-src'))
from stroke_score.cli import nieuwlaar_paths, v02_thresholds
from stroke_score.core import Params, map_footprint, read_map, score, usable_area, valid_mask

A = SimpleNamespace(row_ratio=1.8, row_thr=None, shape_thr=None, contrast_thr=None)


def features(R, B, valid, p, models):
    """R, B: model -> reading / blind map (0..1) on the item's grid. The ensemble is normalised as in core.ensemble."""
    E = {'reading': np.zeros(valid.shape, np.float32), 'blind': np.zeros(valid.shape, np.float32)}
    for m in R:
        v = R[m][valid].astype(np.float64); mu, sd = float(v.mean()), float(v.std()) + 1e-6
        E['reading'] += (R[m] - mu) / sd / len(R); E['blind'] += (B[m] - mu) / sd / len(R)
    use, _ = usable_area(valid, p)
    if use.sum() < 1000:
        return None
    res, _ = score(E, valid, use, p); sR, sB = res['sides']['reading'], res['sides']['blind']
    raw = {k: np.mean([X[m] for m in X], 0) for k, X in (('R', R), ('B', B))}
    x = dict(row_R=sR['row']['score'], row_B=sB['row']['score'], shape_R=sR['shape']['score'], area_R=sR['stroke_frac'], area_B=sB['stroke_frac'],
             mean_R=float(raw['R'][use].mean()), mean_B=float(raw['B'][use].mean()),
             frac_R=float((raw['R'][use] >= 0.5).mean()), frac_B=float((raw['B'][use] >= 0.5).mean()), px=int(use.sum()))
    t = v02_thresholds(models, A); rR, rB, sh = x['row_R'], x['row_B'], x['shape_R']
    rows = 0.0 if rR is None or rB is None or sh is None else min(rR / t['row'], rR / (A.row_ratio * rB) if rB > 0 else math.inf, sh / t['shape'])
    x['margin'] = max(rows, (x['area_R'] - x['area_B']) / t['contrast'])
    x['line_rows'], x['line_contrast'] = rows >= 1, (x['area_R'] - x['area_B']) >= t['contrast']
    x['flag'] = bool(x['line_rows'] or x['line_contrast'])
    return x


def load(maps_dir, name, models, d, shape=None):
    P = {m: nieuwlaar_paths(maps_dir, name, m, d) for m in models}
    if not all(P.values()):
        return None
    import tifffile
    shape = shape or tifffile.imread(P[models[0]][0]).shape
    R = {m: read_map(P[m][0], shape) for m in models}; B = {m: read_map(P[m][1], shape) for m in models}
    fp = None
    for pr, pb in P.values():
        v = map_footprint(pr, shape) | map_footprint(pb, shape); fp = v if fp is None else fp & v
    return R, B, fp


def job(args):
    kind, cfg, it, d, w = args
    models = cfg['models']; p = Params(um=it['um']); out = []
    if kind == 'null':
        z = os.path.join(it['renders'], f'{w}.zarr')
        L = load(it['maps'], w, models, d)
        if L is None:
            return out
        R, B, fp = L; render = os.path.isdir(os.path.join(z, '0'))
        valid = fp & valid_mask(z) if render else fp
        x = features(R, B, valid, p, models)
        if x:
            out.append(dict(kind='null', label=it['label'], name=w, depth=d, render_mask=render, **x))
        return out
    L = load(it['maps'], it['name'], models, d)
    if L is None:
        return out
    R, B, fp = L; valid = fp & valid_mask(it['surface']) if it.get('surface') else fp
    if it.get('whole'):
        x = features(R, B, valid, p, models)
        return [dict(kind='known', label=it['label'], name=it['name'], depth=d, strip=None, **x)] if x else []
    h, st = int(cfg['band_mm'] * 1000 / it['um']), int(cfg['step_mm'] * 1000 / it['um'])
    for i, y0 in enumerate(range(0, valid.shape[0] - h + 1, st)):
        sl = slice(y0, y0 + h)
        if valid[sl].mean() < 0.3:
            continue
        x = features({m: R[m][sl] for m in R}, {m: B[m][sl] for m in B}, valid[sl], p, models)
        if x:
            out.append(dict(kind='known', label=it['label'], name=it['name'], depth=d, strip=i, y0=y0, **x))
    return out


def items(cfg_path, out_path, workers):
    from multiprocessing import Pool
    cfg = json.load(open(cfg_path)); jobs = []
    for it in cfg['known']:
        jobs += [('known', cfg, it, d, None) for d in it['depths']]
    for it in cfg['nulls']:
        jobs += [('null', cfg, it, d, w) for w in it['windings'] for d in it['depths']]
    with Pool(workers) as pool, open(out_path, 'w') as f:
        for k, res in enumerate(pool.imap_unordered(job, jobs)):
            for x in res:
                x['set'] = cfg['set']; f.write(json.dumps(x, default=float) + '\n'); f.flush()
            if k % 25 == 0:
                print(f'{k + 1}/{len(jobs)} jobs', flush=True)
    print('TRIAGE-ITEMS-EXIT')


def auc(pos, neg):
    pos, neg = np.asarray(pos, float), np.asarray(neg, float); pos, neg = pos[np.isfinite(pos)], neg[np.isfinite(neg)]
    if not len(pos) or not len(neg):
        return float('nan')
    allv = np.concatenate([pos, neg]); r = np.argsort(np.argsort(allv, kind='stable'), kind='stable') + 1.0
    # mid-ranks for ties
    from collections import defaultdict
    g = defaultdict(list)
    for i, v in enumerate(allv):
        g[v].append(i)
    for idx in g.values():
        if len(idx) > 1:
            r[idx] = r[idx].mean()
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


SCORES = {'stroke-score 0.2 margin': lambda x: x['margin'],
          '0.2 contrast line alone (stroke area R-B)': lambda x: x['area_R'] - x['area_B'],
          '0.2 row score alone': lambda x: x['row_R'] if x['row_R'] is not None else np.nan,
          'baseline: mean ink probability (reading)': lambda x: x['mean_R'],
          'baseline: ink area, share >= 0.5 (reading)': lambda x: x['frac_R'],
          'baseline: ink area reading - blind': lambda x: x['frac_R'] - x['frac_B'],
          'baseline: mean ink reading - blind': lambda x: x['mean_R'] - x['mean_B'],
          '0.1 stroke area (reading)': lambda x: x['area_R']}


def report(path, top):
    X = [json.loads(l) for l in open(path)]
    for s in sorted({x['set'] for x in X}):
        K = [x for x in X if x['set'] == s and x['kind'] == 'known']; N = [x for x in X if x['set'] == s and x['kind'] == 'null']
        print(f'\n=== model set {s}: {len(N)} null winding-depths ({sum(x["render_mask"] for x in N)} with the render mask), '
              f'{len(K)} known-text items')
        nf = sum(x['flag'] for x in N)
        print(f'nulls flagged by 0.2: {nf} ({", ".join(f"{x["label"]} {x["name"]} d{x["depth"]:+d}" for x in N if x["flag"])})')
        for lab in sorted({x['label'] for x in K}):
            for d in sorted({x['depth'] for x in K if x['label'] == lab}):
                k = [x for x in K if x['label'] == lab and x['depth'] == d]
                print(f'  {lab} d{d:+d}: {len(k)} items, flagged {sum(x["flag"] for x in k)} ({100 * np.mean([x["flag"] for x in k]):.0f} %): '
                      f'rows line {sum(x["line_rows"] for x in k)}, contrast line {sum(x["line_contrast"] for x in k)}; '
                      f'margin median {np.median([x["margin"] for x in k]):.2f}')
        Ks = [x for x in K if x.get('strip') is not None]
        if not Ks:
            continue
        print(f'\n  separating known-text strips ({len(Ks)}) from nulls ({len(N)}): AUC, and the share of strips each score flags '
              f'when its threshold is set to flag as many nulls as the 0.2 rule does ({nf})')
        for nm, f in SCORES.items():
            pv, nv = np.array([f(x) for x in Ks], float), np.array([f(x) for x in N], float)
            nvs = np.sort(nv[np.isfinite(nv)])[::-1]; thr = nvs[nf] if nf < len(nvs) else -np.inf      # flags exactly nf nulls (ties aside)
            tpr = np.mean(np.nan_to_num(pv, nan=-np.inf) > thr)
            print(f'    {nm:46s} AUC {auc(pv, nv):.3f}   strips flagged at {nf} null flags: {100 * tpr:4.0f} %')
        # ranking: nulls + one set of non-overlapping strips (6 offsets of 2 mm strips, 12 mm apart), by the 0.2 margin and the best baseline
        print(f'\n  known text mixed into the null ranking (non-overlapping strips; averaged over 6 offsets): known strips in the top {top}, '
              f'median rank of a known strip')
        for nm in ('stroke-score 0.2 margin', 'baseline: ink area reading - blind', 'baseline: mean ink probability (reading)', '0.1 stroke area (reading)'):
            f = SCORES[nm]; tops, meds, nk = [], [], []
            for o in range(6):
                ks = [x for x in Ks if x['strip'] % 6 == o]
                pool = [(f(x), 1) for x in ks] + [(f(x), 0) for x in N]
                pool = sorted(pool, key=lambda t: -(t[0] if np.isfinite(t[0]) else -1e9))
                ranks = [i + 1 for i, (_, k) in enumerate(pool) if k]
                tops.append(sum(r <= top for r in ranks)); meds.append(np.median(ranks)); nk.append(len(ks))
            print(f'    {nm:46s} {np.mean(tops):4.1f} of {np.mean(nk):.1f} known strips in the top {top} of {len(N) + np.mean(nk):.0f}; '
                  f'median rank {np.mean(meds):.0f}')
        W = [x for x in K if x.get('strip') is None]
        for x in W:
            r = 1 + sum(SCORES['stroke-score 0.2 margin'](n) > x['margin'] for n in N)
            print(f'  whole segment {x["label"]} d{x["depth"]:+d}: margin {x["margin"]:.2f}, would rank {r} of {len(N) + 1} among the nulls')


if __name__ == '__main__':
    if sys.argv[1] == 'items':
        w = int(sys.argv[sys.argv.index('--workers') + 1]) if '--workers' in sys.argv else 3
        items(sys.argv[2], sys.argv[3], w)
    else:
        report(sys.argv[2], int(sys.argv[sys.argv.index('--top') + 1]) if '--top' in sys.argv else 20)
