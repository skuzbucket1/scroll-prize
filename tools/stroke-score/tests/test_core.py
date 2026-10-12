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


def test_row_score_rows_beat_scattered_marks():
    from stroke_score.core import row_score
    rng = np.random.default_rng(2)
    shape = (2600, 2400)                                  # 26 x 24 mm at 10 um
    rows_img = rng.normal(0, 0.3, shape).astype(np.float32)
    scat_img = rng.normal(0, 0.3, shape).astype(np.float32)
    centres_rows = [(300 + 520 * i, 150 + 110 * k) for i in range(5) for k in range(20)]   # 5 lines, 5.2 mm apart
    centres_scat = [(int(rng.integers(100, 2500)), int(rng.integers(100, 2300))) for _ in range(len(centres_rows))]
    rows_img[blobs(shape, centres_rows, 25)] += 5.0
    scat_img[blobs(shape, centres_scat, 25)] += 5.0
    valid = np.ones(shape, bool)
    r_rows, _ = row_score(rows_img, valid, P)
    r_scat, _ = row_score(scat_img, valid, P)
    assert r_rows > 2.0 and r_rows > 3 * r_scat


def test_row_score_short_gappy_band_still_scored():
    from stroke_score.core import row_score
    rng = np.random.default_rng(4)
    shape = (2000, 2400)                                  # a 2 cm band: shorter than the 2.4 cm window
    img = rng.normal(0, 0.3, shape).astype(np.float32)
    img[blobs(shape, [(250 + 520 * i, 150 + 110 * k) for i in range(4) for k in range(20)], 25)] += 5.0
    valid = np.ones(shape, bool)
    valid[:, 1300:] = False                               # a mesh gap: best window coverage about 0.6
    valid[1900:] = False
    r, at = row_score(img, valid, P)
    assert r > 2.0 and at is not None
    valid[:, 300:] = False                                # too little left for a window: no score, no crash
    assert row_score(img, valid, P) == (0.0, None)


def test_row_score_ignores_lone_blobs():
    from dataclasses import replace
    from stroke_score.core import row_score
    rng = np.random.default_rng(5)
    shape = (2600, 2400)
    img = rng.normal(0, 0.3, shape).astype(np.float32)
    img[blobs(shape, [(800, 600), (1350, 650)], 120)] += 5.0   # two big bright blobs 5.5 mm apart, one strip
    valid = np.ones(shape, bool)
    one_strip, _ = row_score(img, valid, replace(P, row_strips=1))
    four, _ = row_score(img, valid, P)
    assert one_strip > 1.0 and four < 0.3 * one_strip


def test_row_score_leaves_out_the_mesh_border():
    from dataclasses import replace
    from stroke_score.core import row_score
    rng = np.random.default_rng(6)
    shape = (1400, 2400)
    img = rng.normal(0, 0.3, shape).astype(np.float32)
    valid = np.zeros(shape, bool)
    valid[200:1230] = True                                # a 1 cm band
    img[200:230] += 5.0                                   # bright line along the border (within 0.5 mm)
    img[720:750] += 5.0                                   # one line inside, 5.2 mm away
    no_margin, _ = row_score(img, valid, replace(P, row_edge_mm=0.0))
    margin, _ = row_score(img, valid, P)
    assert no_margin > 1.0 and margin < 0.5 * no_margin


def test_shape_score_strokes_beat_blobs():
    from stroke_score.core import shape_score
    rng = np.random.default_rng(7)
    shape = (2600, 2400)
    bars = rng.normal(0, 0.3, shape).astype(np.float32)
    dots = rng.normal(0, 0.3, shape).astype(np.float32)
    for i in range(4):
        for k in range(10):
            y, x = 300 + 550 * i, 100 + 220 * k
            if k % 2:
                bars[y:y + 200, x:x + 30] += 5.0               # 2 x 0.3 mm upright strokes
            else:
                bars[y + 80:y + 110, x:x + 180] += 5.0         # 1.8 x 0.3 mm bars
    dots[blobs(shape, [(300 + 550 * i, 150 + 220 * k) for i in range(4) for k in range(10)], 45)] += 5.0   # 0.9 mm round marks
    valid = np.ones(shape, bool)
    s_bars, s_dots = shape_score(bars, valid, P, [0, 0]), shape_score(dots, valid, P, [0, 0])
    assert s_bars['score'] > 0.8 and s_dots['score'] < 0.1 and s_dots['marks'] >= 8
    assert 0.3 < s_bars['horiz'] < 0.7                                    # half upright strokes, half bars
    assert shape_score(dots, valid, P, None)['score'] is None


def test_recurrence_and_v02_flag():
    from stroke_score.cli import flag_v02, recurrence
    base = list(np.sin(np.linspace(0, 6, 200)) + 1.5)
    other = list(np.random.default_rng(3).random(200))
    rows = [dict(name='fitA_w010', depth=0, models=2, _prof=base), dict(name='fitA_w011', depth=0, models=2, _prof=base),
            dict(name='fitB_w010', depth=0, models=2, _prof=base), dict(name='fitB_w011', depth=0, models=2, _prof=other)]
    recurrence(rows)
    assert rows[0]['recur'] > 0.99 and rows[1]['recur'] > 0.99    # the same pattern on neighbouring windings
    assert rows[2]['recur'] < 0.5                                   # nothing in common
    a = SimpleNamespace(row_thr=None, shape_thr=None, row_ratio=1.8)
    three, rd = ['dnative', 'hybrid_3d2d-seed42', 'hybrid_3d2d-seed43'], ['readerv2', 'd9v4c']
    assert flag_v02(three, 1.8, 0.4, 0.45, a) and flag_v02(rd, 2.2, 0.6, 0.5, a)    # rows of strokes
    assert not flag_v02(rd, 2.6, 0.5, 0.21, a)                                     # rows of blobs (PHerc0813 w094)
    assert not flag_v02(three, 1.1, 0.3, 0.5, a)                                   # weak rows
    assert not flag_v02(three, 2.0, 1.5, 0.5, a)                                   # rows on both sides
    assert not flag_v02(['readerv2'], 5.0, 0.1, 0.9, a)                            # single model
    assert flag_v02(three, 1.8, 0.4, 0.3, SimpleNamespace(row_thr=None, shape_thr=0.25, row_ratio=1.8))   # override
    four = ['dnative', 'hecate', 'hybrid_3d2d-seed42', 'hybrid_3d2d-seed43']
    assert flag_v02(four, 1.28, 0.0, 0.54, a, 0.0335, 0.0026)                    # PHerc. 0343 letters: contrast line
    assert flag_v02(three, 0.44, 0.0, 0.23, a, 0.0354, 0.0057)                   # same, three models
    assert not flag_v02(three, 0.9, 0.3, 0.2, a, 0.030, 0.0144)                  # best three-model null contrast (+0.016)
    assert not flag_v02(rd, 1.0, 0.5, 0.2, a, 0.0315, 0.0073)                    # best Reader v2 + d9v4C null contrast (+0.024)
