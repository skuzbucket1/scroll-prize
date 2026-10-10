"""Unit tests of the arithmetic on small synthetic arrays. They check the maths (blur, tiles, size filter, reading vs
blind, the flag rule); whether the score finds text is tested on real scroll data, see ../README.md."""
import math
from types import SimpleNamespace

import numpy as np

from stroke_score.cli import flag
from stroke_score.core import Params, masked_blur, score, strokes, tile_scores, usable_area

P = Params(um=10.0)          # 10 um pixels: 1 mm = 100 px, 1 mm2 = 10,000 px


def blobs(shape, centres, r):
    yy, xx = np.mgrid[:shape[0], :shape[1]]
    m = np.zeros(shape, bool)
    for cy, cx in centres:
        m |= (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
    return m


def test_masked_blur_of_constant_is_constant():
    E = np.full((400, 600), 3.0, np.float32)
    valid = np.ones_like(E, bool)
    valid[:50] = False
    bg = masked_blur(E, valid, 150)
    assert np.allclose(bg[valid], 3.0, atol=1e-3)


def test_tile_scores_match_brute_force():
    rng = np.random.default_rng(0)
    S = rng.random((300, 500)) > 0.8
    valid = rng.random((300, 500)) > 0.1
    p = Params(um=10.0, step_mm=0.5)
    sc, ys, xs, t = tile_scores(S, valid, p, tile_mm=1.0, min_frac=0.6)
    for i in (0, 2):
        for j in (0, 3):
            y, x = ys[i], xs[j]
            nv = valid[y:y + t, x:x + t].sum()
            ns = (S & valid)[y:y + t, x:x + t].sum()
            want = ns / nv if nv >= 0.6 * t * t else math.nan
            assert (math.isnan(want) and math.isnan(sc[i, j])) or abs(sc[i, j] - want) < 1e-9


def test_size_filter_keeps_strokes_and_drops_specks_and_blooms():
    shape = (1000, 1000)
    E = np.zeros(shape, np.float32)
    E[blobs(shape, [(300, 300)], 15)] = 5.0      # ~0.07 mm2: stroke sized, kept
    E[blobs(shape, [(700, 700)], 2)] = 5.0       # ~0.001 mm2: speck, dropped
    E[blobs(shape, [(300, 750)], 120)] = 5.0     # ~4.5 mm2: bloom, dropped
    valid = np.ones(shape, bool)
    S, kept, total = strokes(E, valid, P)
    assert total == 3 and kept == 1
    assert S[300, 300] and not S[700, 700] and not S[300, 750]


def test_reading_side_with_strokes_beats_blind_side():
    shape = (1200, 1600)
    rng = np.random.default_rng(1)
    centres = [(400 + 60 * (k % 3), 300 + 90 * k) for k in range(12)]      # a row of stroke-sized marks
    reading = rng.normal(0, 0.3, shape).astype(np.float32)
    reading[blobs(shape, centres, 14)] += 5.0
    blind = rng.normal(0, 0.3, shape).astype(np.float32)
    valid = np.ones(shape, bool)
    use, _ = usable_area(valid, P)
    res, _ = score({'reading': reading, 'blind': blind}, valid, use, P)
    r, b = res['sides']['reading'], res['sides']['blind']
    # 12 marks of radius 14 px cover 12 * pi * 14^2 = 7,389 px of ~1.65 M usable px (after the 0.5 mm edge margin): ~0.4 %
    assert r['stroke_frac'] > 0.003 and b['stroke_frac'] < 0.0005
    top = res['top_reading_tiles'][0]
    assert 300 <= top['raw_y'] + top['size_px'] / 2 <= 600


def test_flag_rule():
    a = SimpleNamespace(area_thr=0.015, diff_thr=0.010, window_thr=0.030, window_thr4=0.035, window_ratio=2.0)
    assert not flag(1, 0.05, 0.0, 0.1, 0.0, a)                  # single models never flag
    assert flag(3, 0.016, 0.010, 0.0, 0.0, a)                   # area line
    assert flag(3, 0.012, 0.001, 0.0, 0.0, a)                   # reading minus blind line
    assert flag(3, 0.005, 0.004, 0.031, 0.010, a)               # window line, 3x the blind window
    assert not flag(3, 0.005, 0.004, 0.033, 0.029, a)           # window line but the blind side is as high
    assert not flag(4, 0.005, 0.004, 0.032, 0.010, a)           # four models need 0.035
