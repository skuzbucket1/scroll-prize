#!/usr/bin/env python3
"""make_submission_image.py - the submission image: an ink prediction overlaid on a fibre-visible CT layer of the
submitted mesh, cut to one area (at most 4 cm^2), in reading orientation, with a 1 cm scale bar, thin row annotations
and a table of letter sizes.

Every pixel value in the image is computed from the 66-layer surface volume rendered from the submitted mesh (the CT)
and from the ink maps that the models produced from that same surface volume (run_ink.sh / run_depth_sweep.sh). The
only hand-made inputs are the area, the row lines and the letter boxes for the size table. None of them changes a CT or
ink value, and no character is drawn or annotated. Letter boxes are never drawn on the image; by default their numbers
go into a separate key image.

  python make_submission_image.py \\
      --mesh outputs/w047_R5B2_z9500-11000.tifxyz --umbilicus inputs/umbilicus_PHerc0343.json \\
      --ct w047_R5B2_z9500-11000.zarr --ct-layer d0 \\
      --ink maps/<name>__dnative__L66s25_reverse.tif maps/<name>__hecate__L66zc32.50_reverse.png \\
            maps/<name>__hybrid_3d2d-seed42__L66s25_reverse.tif maps/<name>__hybrid_3d2d-seed43__L66s25_reverse.tif \\
      --ensemble --ink-stats images/<name>__stats.json \\
      --area x0,y0,x1,y1 [--area-frame reading] --rows rows.json --letters letters.json --out-dir out/

INPUTS
  --mesh        the submitted tifxyz folder (x.tif, y.tif, z.tif, meta.json). The image is named after it:
                <folder name without .tifxyz>.png (unless --out is given). The mesh also gives the reading orientation
                (below), the theta/z extent and the 3D area of the chosen area. Of the mesh, only the geometry files
                (x.tif, y.tif, z.tif, and mask.tif if present) and the field "scale" of meta.json are used; the
                sidecar lists their sha256 separately (mesh.geometry) next to that of every file (mesh.files).
  --geometry-sums  a sha256 list (sha256sum format, e.g. outputs/SHA256SUMS). The script stops unless every geometry
                file of the mesh is in the list with the same sha256 (an entry "<mesh folder>/<file>" is preferred,
                otherwise the bare file name). Repeatable; the result goes into mesh.geometry_check.
  --forbid-words   publication check: a word list (one entry per line, case-insensitive; "re:<regex>" for a regular
                expression; "#" comment lines). The script stops before writing if the mesh folder name, a text file
                of the mesh (meta.json), an input or output file name, a caption, a label or the recorded command
                contains an entry, and does not write the sidecar if the sidecar does. Only the number of entries is
                recorded. The values of --geometry-sums and --forbid-words are not recorded in the command line.
  --umbilicus   scroll axis (JSON with control_points x, y, z), needed to MEASURE the reading orientation.
                Without it, give --flip-lr and --flip-ud explicitly. With both, a mismatch stops the script.
  --ct          the 66-layer surface volume rendered from the mesh (zarr; group with array "0", or the array itself).
                d = layer - 33; d = 0 is the layer just outside the mesh surface (+0.5 voxel), positive d points
                outward (the script measures the sign from the mesh and warns if the normal points inward).
  --ct-layer    background layer(s): a layer index (33), a depth (d0, d-1, d+2), or a range for a small mean over
                layers (d-1..d+1, 32..34).
  --ink         one or more ink maps of the same surface volume, raw render orientation:
                villa TIFF (uint8, value v -> clip((v - 64) / 128, 0, 1)) or Hecate PNG (v / 255, bilinearly resized
                to the render grid). The model is taken from the file name (__dnative__, __hecate__,
                __hybrid_3d2d-seed42__, __hybrid_3d2d-seed43__) or from --ink-names. Files ending in _reverse are the
                READING side; the other direction (the BLIND side) is refused unless --allow-blind is given.
                One map = that model alone. Several maps need --ensemble.
  --ink-stats   the <name>__stats.json written by ensemble_maps.py for this surface volume. With it, the z-scores,
                the stretches and the ensemble are exactly those of ensemble_maps.py (pooled over the reading side at
                all depths, see there). Without it they are computed from the given maps only (one depth); the
                sidecar JSON says which one was used. Blind-side maps always need --ink-stats (they are shown with
                the reading side's statistics, never with their own).
  --area        x0,y0,x1,y1 (x1, y1 exclusive) in pixels of the RAW render (x = column, y = row), or with
                --area-frame reading in pixels of the reading-oriented render. --area-json takes the region from a
                JSON with raw_render_px {row0, row1, col0, col1} (as written by the area-selection tool).
                The physical size is reported (1 px = --voxel-um); a warning is printed above --max-cm2.
  --rows        JSON, one entry per text row: {"frame": "area", "rows": [{"label": "1", "baseline": [[x, y], ...]},
                {"label": "2", "rect": [x0, y0, x1, y1]}]}. frame = "area" (default: reading orientation, origin
                at the top left of the area), "reading" (whole reading-oriented render) or "raw" (raw render).
                Baselines are drawn as thin polylines, rectangles as thin outlines; place them next to the letters,
                not on them (the script counts row pixels inside letter boxes and on strong ink; see "checks").
                A row may also be {"label": "1", "baseline_follows_letters": {}} (both modes): a line derived from the
                letter boxes of that row (letters with the same "row") and from the ink image, see ROW LINES.
  --letters     JSON {"frame": "area", "letters": [{"label": "A", "row": "1", "box": [x0, y0, x1, y1]}, ...]}
                -> letter_sizes.csv (width/height in px and mm). --letter-markers: "key" (default) writes a separate
                <stem>_letter_key.png with small numbers placed OUTSIDE the boxes; "on" puts them on the main image;
                "off" writes no markers. Optional per letter: "reading" (e.g. a Greek capital) and "class" (clear,
                probable or uncertain): the CSV then gets the columns "reading" (an uncertain reading with a dot below,
                Leiden convention) and "class", and the key image a legend with number, reading and class.
                Optional "id" (a positive integer, given for every letter or for none, all different): the number
                used in the CSV, the key image and the sidecar, e.g. to keep the numbers of a larger letter list in
                an image that shows only part of it; without it the letters are numbered 1, 2, ... in file order.

ROW LINES DERIVED FROM THE LETTERS ("baseline_follows_letters", optional keys with their defaults)
  gap 16 (px), clearance 3 (px), max_dip 0.35 and outlier 0.6 (x the median box height of the row), max_rise
  gap / 2, break_cost 40, level (8-bit ink value from which ink counts as visible; default: --threshold). The
  target runs <gap> px below the bottom of each box of the row (the lowest bottom where boxes overlap in x) and
  straight between boxes. A box whose bottom lies more than <outlier> below the median bottom of its neighbours (two
  on each side) gets no target of its own (a letter that reaches far below the row). The line is the cheapest path
  from the left end of the first box to the right end of the last: cost |y - target| per px plus 1 per px of height
  change, slope at most 1, never closer than <clearance> px (plus half the line width) to any letter box or to
  visible ink, at most max_dip below and max_rise above the target. Where no such path exists, or it would cost more
  (50 x break_cost to start an interruption, break_cost per px), the line is interrupted; pieces shorter than 40 px
  are dropped. The path is smoothed (moving mean over 22 px, kept only where it stays clear) and simplified to within
  0.75 px. So it follows the text just below the letters, never crosses ink or a box, and is never far below the
  letters. The sidecar records the segments, the interruptions and the letters without a target.

OVERLAY
  CT: (CT - lo) / (hi - lo), clipped, in grey. --ct-stretch auto (default) = the CT stretch of --ink-stats
  (p1..p99.5 of the valid pixels of layers 18..48, as ensemble_maps.py) or, without --ink-stats, the same computed
  here; "area" = p1..p99.5 of the shown CT within the area; or explicit "lo,hi".
  Ink: the stretched map u = clip((x - lo) / (hi - lo), 0, 1), quantised to 8 bit exactly like the grey images of
  ensemble_maps.py (x = the model value, or the ensemble = mean of the per-model z-scores). Colour = --cmap(u)
  (default one orange colour, so the strength is shown by the opacity);
  opacity = --alpha * clip((u - --threshold) / (--full - --threshold), 0, 1). Below the threshold the CT is
  untouched. With --blend tint (default) the colour is multiplied by (--tint-floor + (1 - --tint-floor) * CT grey),
  so the fibre texture stays visible inside the ink; --blend alpha mixes the plain colour. Invalid pixels (any of the
  66 layers = 0) are black.
  --overlay-style sets the defaults of these options as one named style (each option can still be given):
    default     --cmap mono:255,140,0 --alpha 0.75 --threshold 0.5 --full 0.9 --blend tint --ct-dim 1 (as above)
    dimmed-ct   --cmap mono:255,235,120 --alpha 0.9 --threshold 0.35 --full 0.75 --blend alpha --ct-dim 0.45: the CT
                grey is multiplied by --ct-dim (fibres visible, darker), the ink is one light-yellow colour with
                opacity 0.9 * clip((u - 0.35) / 0.40, 0, 1), pixel = CT grey * 0.45 * (1 - opacity) + colour * opacity.
                The legend shows the ink values (ensemble z-score) at u = --threshold and u = --full.
  --caption compact writes a shorter caption (ink, depth and style in one line, the area in one line; in two-panel
  mode one line on the panels and the seam). All numbers stay in the sidecar. Default: full.
  --panel-line TEXT (two-panel mode) replaces the caption line on the panels and the seam with TEXT (an empty TEXT
  drops that line); the seam numbers stay in the sidecar. Without it the caption is unchanged.

OUTPUTS (next to the image)
  <stem>.png               the image: the area at 1 render pixel = 1 image pixel, in reading orientation, with a
                           frame, row lines, row labels in the left margin, a 1 cm scale bar (round(10000 / voxel_um)
                           px, 1157 px at 8.64 um) and a colour legend in the bottom margin, captions at the top.
  <stem>.json              sidecar: sha256 of every input (files; a zarr as a sorted tree hash plus the sha256 of the
                           decoded layers used), the measured orientation, all normalisation numbers, the area in raw
                           and reading pixels, mm and cm^2, theta/z extent, checks, software versions, and the sha256
                           of every output. Only file names are recorded, no local paths.
  letter_sizes.csv         with --letters (--sizes-csv to rename).
  <stem>_letter_key.png    with --letters and --letter-markers key.
  <stem>_ct.png, <stem>_ink.png   with --write-components: the plain grey area images, no annotations.
The script is deterministic: the same inputs give byte-identical outputs. Existing outputs are not overwritten
without --force.

TWO-PANEL MODE (letters on two consecutive meshes)
  Give --mesh twice, and --ct, --area (and --ink, --ink-stats, --render-offset when used) once per mesh, in the same
  order: the first mesh is the LEFT panel, the second the RIGHT panel (reading order). Example:
      --mesh A.tifxyz --ct A.zarr --ink <4 maps of A> --ink-stats A__stats.json --area <area of A>
      --mesh B.tifxyz --ct B.zarr --ink <4 maps of B> --ink-stats B__stats.json --area <area of B>
  Each panel is cut from the render of its own mesh, exactly as a one-mesh image of that area (same CT layer, stretch,
  ink normalisation from its own --ink-stats, overlay); nothing is resampled or stitched across meshes. The panels are
  put side by side, separated by a thin neutral vertical line (--panel-gap px) labelled with both mesh names. The
  seam is the right edge of the left area and the left edge of the right area: per render row, the outermost valid
  pixel on that side (within 256 px of the area edge), its mesh z and theta. The right panel is shifted vertically by
  D rows (right row = left row + D, reading orientation) so that the mesh z is equal at equal image rows along the
  seam; D minimises the RMS z difference over the rows of the left area, with the right mesh's seam profile taken
  over all rows of its render (--panel-dy auto, default; an integer fixes D and the residual is still reported). For
  one continuous text band give the right area the rows of the left area + D (the script warns otherwise). The image
  is named <left mesh>__<right mesh>.png; the area is reported per panel and as the SUM of both (checked against
  --max-cm2), with the 3D mesh surface of the valid pixels. The 3D distance between the two seam-edge pixels of each
  image row (papyrus that is in neither render) is reported too.
  --geometry-sums lists are matched per mesh by their "<mesh folder>/<file>" entries; every mesh must be in a list.
  Rows and letters: "frame": "composite" (default in this mode) = pixels of the panel band (origin at its top left;
  the left panel starts at x 0, the right panel at x = left width + gap), or "area" / "reading" / "raw" with
  "panel": 1 | 2 or "mesh": "<mesh name>" in each entry. A row may be given as {"label": "1",
  "baseline_below_letters": {"gap": 15, "max_slope": 0.3}} (or just a number = gap): a polyline derived from the
  letter boxes of that row (letters with the same "row"). It lies at least <gap> px below every one of those boxes and
  never enters a box; without max_slope it is horizontal under each box, with max_slope it is the highest line below
  the boxes whose slope nowhere exceeds max_slope (it follows the row, not the single boxes). letter_sizes.csv gets a
  column "mesh"; its boxes are in composite pixels. The sidecar has one entry per panel (mesh, orientation, CT, ink,
  area, placement), the seam measurement and the total area.
  --seam-edge render measures the seam at the render edge of each mesh (the outermost valid pixel of the whole render
  row on the seam side) instead of at the area edge, so D and the gap do not depend on how far the areas reach
  towards the seam. --unequal-panels: the two areas cover different rows on purpose (for example a second text row
  on one mesh only); the placement is recorded in the sidecar instead of a warning. Rows given as
  "baseline_follows_letters" (see ROW LINES) may run across the seam.

Dependencies: numpy, opencv-python(-headless), tifffile, zarr.
"""
import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys

import numpy as np

N_LAYERS, MID = 66, 33
P_LO, P_HI = 1.0, 99.5
FINE = 65536                    # histogram bins for Hecate values on [0, 1] (as ensemble_maps.py)
SUB = 8                         # fixed grid for the ensemble stretch (every 8th row and column, from 4)
CT_STAT_LAYERS = (MID - 15, MID + 15)
MODELS = [('dnative', '__dnative__'), ('hecate', '__hecate__'),        # order matters for the float32 sums
          ('ink9-42', '__hybrid_3d2d-seed42__'), ('ink9-43', '__hybrid_3d2d-seed43__')]
MODEL_ORDER = [m for m, _ in MODELS]
CMAPS = ('inferno', 'magma', 'hot', 'plasma', 'viridis', 'turbo', 'autumn', 'cividis')
FONT = 0                        # cv2.FONT_HERSHEY_SIMPLEX
WARNINGS = []
# named overlay styles: the defaults of the overlay options (an option given on the command line wins)
STYLES = {'default': dict(cmap='mono:255,140,0', alpha=0.75, threshold=0.5, full=0.9, blend='tint', ct_dim=1.0),
          'dimmed-ct': dict(cmap='mono:255,235,120', alpha=0.9, threshold=0.35, full=0.75, blend='alpha', ct_dim=0.45)}
LETTER_CLASSES = ('clear', 'probable', 'uncertain')


def resolve_style(a):
    """fill the overlay options that were not given with the defaults of --overlay-style."""
    for k, v in STYLES[a.overlay_style].items():
        if getattr(a, k) is None:
            setattr(a, k, v)
    if not 0 < a.ct_dim <= 1:
        raise SystemExit('--ct-dim must be in (0, 1]')
    return a


def overlay_record(a, legend, panels=False):
    """the sidecar entry "overlay"; for the default style (CT not dimmed) exactly as before the styles existed."""
    per_panel = '; u per panel with that panel\'s statistics' if panels else ''
    if a.overlay_style == 'default' and a.ct_dim == 1.0:
        return dict(cmap=a.cmap, alpha=a.alpha, threshold=a.threshold, full=a.full, blend=a.blend,
                    tint_floor=a.tint_floor if a.blend == 'tint' else None, legend=legend,
                    rule='opacity = alpha * clip((u - threshold) / (full - threshold), 0, 1); '
                         'pixel = CT grey * (1 - opacity) + colour * opacity, colour = cmap(u) '
                         '(blend alpha) or cmap(u) * (tint_floor + (1 - tint_floor) * CT grey / 255) '
                         '(blend tint); invalid pixels black' + per_panel)
    return dict(style=a.overlay_style, cmap=a.cmap, alpha=a.alpha, threshold=a.threshold, full=a.full, blend=a.blend,
                ct_dim=a.ct_dim, tint_floor=a.tint_floor if a.blend == 'tint' else None, legend=legend,
                rule='u = the 8-bit ink image / 255; opacity = alpha * clip((u - threshold) / (full - threshold), 0, 1); '
                     'pixel = CT grey * ct_dim * (1 - opacity) + colour * opacity, colour = cmap(u) (blend alpha) or '
                     'cmap(u) * (tint_floor + (1 - tint_floor) * CT grey / 255) (blend tint); per pixel in float32, '
                     'rounded to 8 bit; invalid pixels black' + per_panel)


def depth_txt(v):
    if isinstance(v, bool) or v is None:
        return 'depth not in the file name'
    return f'd = {v:+d}' if isinstance(v, int) else f'd = {v:+g}'


def compact_ink_line(a, maps, blind, layers, panels=False):
    """--caption compact: ink, depth, style and background in one line."""
    colour = {'mono:255,235,120': 'light-yellow ink', 'mono:255,140,0': 'orange ink'}.get(a.cmap, f'ink ({a.cmap})')
    if len(layers) == 1:
        bg = f'CT layer {layers[0]} ({depth_txt(layers[0] - MID)})'
    else:
        bg = f'the mean of CT layers {layers[0]}..{layers[-1]} ({depth_txt(layers[0] - MID)}..{layers[-1] - MID:+d})'
    dim = f' dimmed to {100 * a.ct_dim:g} %' if a.ct_dim != 1.0 else ''
    tail = f'{bg}{dim} (overlay style {a.overlay_style}) | volume {a.volume_id}, {a.voxel_um:g} um voxels'
    if not maps:
        return f'CT only: {tail}'
    side = 'reading side' if not blind else 'BLIND side (shown with the reading side statistics)'
    ds = ', '.join(sorted({depth_txt(m['depth']) for m in maps}))
    if len(maps) > 1:
        ink = (f"Ink: ensemble of {len(maps)} models ({', '.join(m['model'] for m in maps)}), mean of the per-model "
               f"z-scores, {side}, {ds}" + ('; each panel normalised with its own statistics' if panels else ''))
    else:
        ink = f"Ink: model {maps[0]['model']}, {side}, {ds}"
    return f'{ink}. Shown as {colour} over {tail}'


def key_legend_strip(letters, width, fs, th1, lh, bgc, marker_col):
    """legend of the key image: number, reading (an uncertain reading with a dot below, Leiden convention) and class
    of every letter, as a grid of cells. None if the letters carry no reading."""
    import cv2
    if not any('reading' in L for L in letters):
        return None
    rad = int(round(18 * fs / 1.3))
    cw = int(round(330 * fs / 1.3))
    per = max(1, (width - 60) // cw)
    nrow = (len(letters) + per - 1) // per
    head = ('Letters: number, reading, confidence class (clear, probable, uncertain; an uncertain reading has a dot '
            'below, Leiden convention).')
    hl = wrap(head, fs, th1, width - 60)
    rh = int(round(2.0 * lh))
    strip = np.empty((20 + len(hl) * lh + nrow * rh + 20, width, 3), np.uint8)
    strip[:] = bgc
    for i, s in enumerate(hl):
        put(strip, s, 30, 20 + (i + 1) * lh - int(0.25 * lh), fs, (235, 235, 235), th1)
    y_top = 20 + len(hl) * lh
    for i, L in enumerate(letters):
        cx = 30 + (i % per) * cw + rad
        cy = y_top + (i // per) * rh + rh // 2
        cv2.circle(strip, (cx, cy), rad, (0, 0, 0), -1, cv2.LINE_AA)
        cv2.circle(strip, (cx, cy), rad, marker_col, 2, cv2.LINE_AA)
        s = str(L.get('id', i + 1))
        tw, tht, _ = text_size(s, fs * 0.75, th1)
        put(strip, s, cx - tw // 2, cy + tht // 2, fs * 0.75, marker_col, th1)
        rd = L.get('reading', '?').replace('Ϲ', 'C')      # lunate sigma: the font has no glyph, the shape is C
        gs = fs * 1.35
        tw, tht, _ = text_size(rd, gs, th1 + 1)
        gx = cx + rad + 16
        put(strip, rd, gx, cy + tht // 2, gs, (235, 235, 235), th1 + 1)
        if L.get('class') == 'uncertain':
            cv2.circle(strip, (gx + tw // 2, cy + tht // 2 + int(round(12 * fs / 1.3))), max(3, int(round(4 * fs / 1.3))),
                       (235, 235, 235), -1, cv2.LINE_AA)
        put(strip, L.get('class', ''), gx + max(tw, int(round(40 * fs / 1.3))) + 14, cy + tht // 2, fs * 0.85,
            (150, 150, 150), max(1, th1 - 1))
    return strip


def legend_ramp(a, lut, lw):
    """legend colour ramp (lw x 3, float32): the ink colour as it appears over mid-grey CT (dimmed as in the image)."""
    u = np.linspace(0, 1, lw, dtype=np.float32)
    u8 = (u * 255).astype(np.uint8)
    al = a.alpha * np.clip((u - a.threshold) / max(a.full - a.threshold, 1e-6), 0, 1)
    tint = (a.tint_floor + (1 - a.tint_floor) * 128 / 255.0) if a.blend == 'tint' else 1.0
    return lut[u8].astype(np.float32) * tint * al[:, None] + 128 * a.ct_dim * (1 - al[:, None])


def warn(msg):
    WARNINGS.append(msg)
    print('WARNING: ' + msg, file=sys.stderr, flush=True)


# ------------------------------------------------------------------ hashing
def sha256_file(path, bs=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        while True:
            b = fh.read(bs)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def sha256_tree(root):
    """sha256 over the sorted lines '<relative path>\\t<sha256 of the file>\\n' of every file below root."""
    lines, n, nbytes = [], 0, 0
    for dp, dns, fns in os.walk(root):
        dns.sort()
        for fn in sorted(fns):
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, root).replace(os.sep, '/')
            lines.append(f'{rel}\t{sha256_file(p)}\n')
            n += 1
            nbytes += os.path.getsize(p)
    lines.sort()
    h = hashlib.sha256(''.join(lines).encode())
    return dict(tree_sha256=h.hexdigest(), files=n, bytes=nbytes,
                tree_rule='sha256 of the sorted lines "<relative path>\\t<sha256>\\n" of every file in the folder')


def sha256_array(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def base(p):
    return os.path.basename(os.path.normpath(p))


# ------------------------------------------------------------------ mesh identity and publication check
GEOMETRY_FILES = ('x.tif', 'y.tif', 'z.tif', 'mask.tif')      # the only mesh files that change a pixel (+ "scale")
REDACT = {'--geometry-sums': '<sha256-list>', '--forbid-words': '<word-list>'}


def read_sums(path):
    """sha256sum-format list -> [(sha256, path)]."""
    out = []
    for ln in open(path, encoding='utf-8', errors='replace'):
        m = re.fullmatch(r'\s*([0-9a-fA-F]{64})\s+\*?(.+?)\s*', ln.rstrip('\r\n'))
        if m:
            out.append((m.group(1).lower(), re.sub(r'^\./', '', m.group(2).replace('\\', '/'))))
    return out


def check_geometry(sums_path, mesh_name, geo):
    """every geometry file of the mesh must be in the list with the same sha256."""
    entries = read_sums(sums_path)
    if not entries:
        raise SystemExit(f'--geometry-sums {base(sums_path)}: no sha256 lines')
    matched = []
    for f, h in geo:
        exact = {s for s, p in entries if p == f'{mesh_name}/{f}'}           # "<mesh folder>/<file>" first,
        deep = {s for s, p in entries if p.endswith(f'/{mesh_name}/{f}')}    # then deeper, then the bare name
        cand = exact or deep or {s for s, p in entries if p == f}
        if not cand:
            raise SystemExit(f'--geometry-sums {base(sums_path)}: {f} of {mesh_name} is not in the list')
        if len(cand) > 1:
            raise SystemExit(f'--geometry-sums {base(sums_path)}: {f} is listed with different sha256 values')
        if h not in cand:
            raise SystemExit(f'--geometry-sums {base(sums_path)}: {f} of {mesh_name} does NOT match the list (here '
                             f'{h[:16]}..., listed {next(iter(cand))[:16]}...): the mesh geometry differs')
        matched.append(f)
    return dict(list_sha256=sha256_file(sums_path), list_lines=len(entries), files_matched=matched,
                result='every geometry file matches')


def load_word_list(path):
    pats = []
    for ln in open(path, encoding='utf-8'):
        s = ln.strip()
        if s and not s.startswith('#'):
            pats.append(re.compile(s[3:] if s.startswith('re:') else re.escape(s), re.I))
    if not pats:
        raise SystemExit('--forbid-words: the list has no entries')
    return pats


def word_hits(pats, items):
    """items [(where, text)] -> ['<where>: entry <n>'] (the entry itself is not repeated)."""
    return [f'{where}: entry {i}' for where, text in items if text for i, p in enumerate(pats, 1) if p.search(text)]


def mesh_text_files(mesh_dir):
    out = []
    for f in sorted(os.listdir(mesh_dir)):
        p = os.path.join(mesh_dir, f)
        if os.path.isfile(p) and os.path.getsize(p) <= (1 << 20):
            b = open(p, 'rb').read()
            if b'\0' not in b[:8192]:
                out.append((f'mesh file {f}', b.decode('utf-8', 'replace')))
    return out


def reduced_command(tokens, a, out_png):
    """the command line with every path reduced to its file name; the values of REDACT options are replaced."""
    red, hide = [], None
    for t in tokens:
        if hide:
            red.append(hide)
            hide = None
            continue
        opt = t.split('=', 1)[0]
        key = [k for k in REDACT if opt.startswith('--') and len(opt) > 3 and k.startswith(opt)]
        if key:
            if '=' in t:
                red.append(f'{key[0]}={REDACT[key[0]]}')
            else:
                red.append(key[0])
                hide = REDACT[key[0]]
            continue
        if not t.startswith('-') and (os.path.exists(t) or t in (a.out, a.out_dir, out_png)
                                      or re.match(r'(/|~|\.\.?/)', t)):
            t = base(t)
        red.append(t if re.fullmatch(r'[\w.,:+\-=/]+', t) else "'" + t.replace("'", "'\\''") + "'")
    return 'make_submission_image.py ' + ' '.join(red)


# ------------------------------------------------------------------ mesh geometry
def load_mesh(folder):
    import tifffile
    X = tifffile.imread(os.path.join(folder, 'x.tif')).astype(np.float64)
    Y = tifffile.imread(os.path.join(folder, 'y.tif')).astype(np.float64)
    Z = tifffile.imread(os.path.join(folder, 'z.tif')).astype(np.float64)
    # tifxyz validity as in VC3D: (-1, -1, -1) marks a hole, z <= 0 is invalid too; a mask.tif (if any) is honoured
    ok = (X > -0.5) & (Y > -0.5) & (Z > 0.5) & np.isfinite(X) & np.isfinite(Y) & np.isfinite(Z)
    mp = os.path.join(folder, 'mask.tif')
    if os.path.isfile(mp):
        m = tifffile.imread(mp)
        if m.ndim == 3:
            m = m[..., 0]
        if m.shape == ok.shape:
            ok &= m > 0
    meta = json.load(open(os.path.join(folder, 'meta.json')))
    sc = float(meta['scale'][0])
    return X, Y, Z, ok, sc


def load_umbilicus(path):
    cp = json.load(open(path))['control_points']
    uz = np.array([p['z'] for p in cp], float)
    ux = np.array([p['x'] for p in cp], float)
    uy = np.array([p['y'] for p in cp], float)
    o = np.argsort(uz)
    return uz[o], ux[o], uy[o]


def theta_unwrapped(X, Y, Z, ok, umb):
    """theta (degrees) around the umbilicus per node, unwrapped along each node row; every row is put on the turn of
    the first usable row at that row's middle column."""
    uz, ux, uy = umb
    TH = np.full(X.shape, np.nan)
    ref = None
    for ri in range(X.shape[0]):
        m = ok[ri]
        if m.sum() < 8:
            continue
        idx = np.nonzero(m)[0]
        zz = np.median(Z[ri, idx])
        cx = np.interp(zz, uz, ux)
        cy = np.interp(zz, uz, uy)
        t = np.degrees(np.unwrap(np.arctan2(Y[ri, idx] - cy, X[ri, idx] - cx)))
        if ref is None:
            ref = (idx[len(idx) // 2], t[len(t) // 2])
        else:
            j = np.searchsorted(idx, ref[0])
            j = min(max(j, 0), len(idx) - 1)
            t = t - 360.0 * round((t[j] - ref[1]) / 360.0)
        TH[ri, idx] = t
    return TH


def theta_by_column(X, Y, Z, ok, umb):
    """theta (degrees) per node, unwrapped along the node columns: circular mean per column, np.unwrap over the
    columns, every node put on the turn of its column (robust for the theta extent of an area)."""
    import warnings
    cx = np.interp(Z, umb[0], umb[1])
    cy = np.interp(Z, umb[0], umb[2])
    phi = np.where(ok, np.degrees(np.arctan2(Y - cy, X - cx)), np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        c = np.nanmean(np.cos(np.radians(phi)), 0)
        s = np.nanmean(np.sin(np.radians(phi)), 0)
    psi = np.degrees(np.arctan2(s, c))
    v = np.isfinite(psi)
    j = np.arange(psi.size)
    Psi = np.interp(j, j[v], np.degrees(np.unwrap(np.radians(psi[v]))))
    return phi + 360.0 * np.round((Psi[None, :] - phi) / 360.0)


def measure_orientation(X, Y, Z, ok, umb):
    """reading orientation from the mesh: a = sign(d theta / d column), b = sign(dz / d row) (medians over the node
    grid). Reading orientation = high z at the top and theta decreasing to the right, i.e. flip_lr = a > 0,
    flip_ud = b > 0. Also the render normal n = dP/dcolumn x dP/drow against the outward radial direction."""
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        TH = theta_unwrapped(X, Y, Z, ok, umb)
        dth = float(np.nanmedian(np.diff(TH, axis=1)))
        zr = np.nanmedian(np.where(ok, Z, np.nan), axis=1)
        dz = float(np.nanmedian(np.diff(zr)))
        P = np.stack([X, Y, Z], -1)
        P[~ok] = np.nan
        dc = P[1:-1, 2:] - P[1:-1, :-2]
        dr = P[2:, 1:-1] - P[:-2, 1:-1]
        n = np.cross(dc, dr)
        n /= np.linalg.norm(n, axis=-1, keepdims=True)
        Pm = P[1:-1, 1:-1]
        cx = np.interp(Pm[..., 2], umb[0], umb[1])
        cy = np.interp(Pm[..., 2], umb[0], umb[2])
        rh = np.stack([Pm[..., 0] - cx, Pm[..., 1] - cy, np.zeros_like(cx)], -1)
        rh /= np.linalg.norm(rh, axis=-1, keepdims=True)
        nr = np.sum(n * rh, -1)
        nr = nr[np.isfinite(nr)]
    a, b = int(np.sign(dth)), int(np.sign(dz))
    return TH, dict(source='measured from the mesh and the umbilicus', sign_dtheta_per_column=a, sign_dz_per_row=b,
                    dtheta_deg_per_node_column=round(dth, 5), dz_voxels_per_node_row=round(dz, 4),
                    flip_lr=bool(a > 0), flip_ud=bool(b > 0),
                    normal_dot_outward_median=round(float(np.median(nr)), 4) if nr.size else None,
                    normal_outward_fraction=round(float((nr > 0).mean()), 4) if nr.size else None,
                    rule='flip_lr = sign(dtheta/dcolumn) > 0, flip_ud = sign(dz/drow) > 0; the render normal is '
                         'n = dP/dcolumn x dP/drow')


def bilinear_nodes(a, rows, cols, sc, off):
    """node grid -> render pixels (rows x cols, raw orientation); pixel (r, c) sits at node ((r + off_r) * scale,
    (c + off_c) * scale), as in the renderer. NaN stays NaN."""
    h, w = a.shape
    fr = np.clip((off[0] + rows.astype(np.float64)) * sc, 0, h - 1.001)
    fc = np.clip((off[1] + cols.astype(np.float64)) * sc, 0, w - 1.001)
    i0 = fr.astype(int)
    j0 = fc.astype(int)
    dr = (fr - i0)[:, None]
    dc = (fc - j0)[None, :]
    return (a[np.ix_(i0, j0)] * (1 - dr) * (1 - dc) + a[np.ix_(i0, j0 + 1)] * (1 - dr) * dc
            + a[np.ix_(i0 + 1, j0)] * dr * (1 - dc) + a[np.ix_(i0 + 1, j0 + 1)] * dr * dc)


def quad_area_px(X, Y, Z, ok, sc):
    """3D area (voxel^2) of one render pixel for every mesh quad; NaN where a corner is invalid."""
    P = np.stack([X, Y, Z], -1)
    P[~ok] = np.nan
    dc = 0.5 * ((P[:-1, 1:] - P[:-1, :-1]) + (P[1:, 1:] - P[1:, :-1]))
    dr = 0.5 * ((P[1:, :-1] - P[:-1, :-1]) + (P[1:, 1:] - P[:-1, 1:]))
    return np.linalg.norm(np.cross(dc, dr), axis=-1) * sc * sc


# ------------------------------------------------------------------ orientation frame
class Frame:
    """raw render (H x W) <-> reading orientation; the area in both."""

    def __init__(self, H, W, flip_lr, flip_ud):
        self.H, self.W, self.flip_lr, self.flip_ud = H, W, bool(flip_lr), bool(flip_ud)

    def to_reading(self, A):
        if self.flip_ud:
            A = A[::-1]
        if self.flip_lr:
            A = A[:, ::-1]
        return np.ascontiguousarray(A)

    def rect_raw_to_reading(self, x0, y0, x1, y1):
        X0, X1 = (self.W - x1, self.W - x0) if self.flip_lr else (x0, x1)
        Y0, Y1 = (self.H - y1, self.H - y0) if self.flip_ud else (y0, y1)
        return X0, Y0, X1, Y1

    rect_reading_to_raw = rect_raw_to_reading          # the same involution

    def point_raw_to_reading(self, x, y):
        return ((self.W - 1 - x) if self.flip_lr else x), ((self.H - 1 - y) if self.flip_ud else y)


# ------------------------------------------------------------------ CT
def open_surface(path):
    import zarr
    z = zarr.open(path, mode='r')
    if isinstance(z, zarr.Group):
        z = z['0']
    if len(z.shape) != 3 or z.shape[0] != N_LAYERS:
        raise SystemExit(f'{base(path)}: expected a ({N_LAYERS}, H, W) surface volume, got shape {z.shape}')
    return z


def parse_layers(spec):
    """'33' | 'd0' | 'd-1' | 'd-1..d+1' | '32..34' -> sorted list of layer indices."""
    s = spec.strip().replace(' ', '')

    def one(t):
        if t.lower().startswith('d'):
            return MID + int(t[1:])
        return int(t)
    if '..' in s:
        a, b = s.split('..')
        lo, hi = one(a), one(b)
        layers = list(range(min(lo, hi), max(lo, hi) + 1))
    else:
        layers = [one(s)]
    for k in layers:
        if not 0 <= k < N_LAYERS:
            raise SystemExit(f'--ct-layer {spec}: layer {k} outside 0..{N_LAYERS - 1}')
    if len(layers) > 7:
        warn(f'--ct-layer {spec}: mean over {len(layers)} layers blurs the fibres; a small mean (<= 3) is intended')
    return layers


def pct_hist(hist, values, qs):
    """np.percentile (linear) computed exactly from a histogram over discrete values (as ensemble_maps.py)."""
    c = np.cumsum(hist)
    n = int(c[-1])
    out = []
    for q in qs:
        pos = q / 100.0 * (n - 1)
        lo = int(math.floor(pos))
        fr = pos - lo
        i_lo = int(np.searchsorted(c, lo + 1))
        i_hi = int(np.searchsorted(c, min(lo + 2, n))) if fr > 0 else i_lo
        out.append(float(values[i_lo] + fr * (values[i_hi] - values[i_lo])))
    return out


def full_pass(st, block=128):
    """valid mask of the whole render (all 66 layers > 0) and the CT histogram of layers 18..48 on valid pixels."""
    H, W = int(st.shape[1]), int(st.shape[2])
    valid = np.zeros((H, W), bool)
    hist = np.zeros(256, np.int64)
    for r0 in range(0, H, block):
        blk = np.asarray(st[:, r0:r0 + block, :])
        gg = (blk > 0).all(0)
        valid[r0:r0 + blk.shape[1]] = gg
        hist += np.bincount(blk[CT_STAT_LAYERS[0]:CT_STAT_LAYERS[1] + 1][:, gg].ravel(), minlength=256)
    return valid, hist


def read_area(st, r0, r1, c0, c1, layers, block=256):
    """valid mask, mean of the chosen layers (float32) and the chosen uint8 layers, raw orientation."""
    h, w = r1 - r0, c1 - c0
    valid = np.zeros((h, w), bool)
    ct = np.zeros((h, w), np.float32)
    lay = {k: np.zeros((h, w), np.uint8) for k in layers}
    for i in range(0, h, block):
        blk = np.asarray(st[:, r0 + i:min(r0 + i + block, r1), c0:c1])
        valid[i:i + blk.shape[1]] = (blk > 0).all(0)
        acc = np.zeros(blk.shape[1:], np.float32)
        for k in layers:
            lay[k][i:i + blk.shape[1]] = blk[k]
            acc += blk[k].astype(np.float32)
        ct[i:i + blk.shape[1]] = acc / len(layers)
    return valid, ct, lay


# ------------------------------------------------------------------ ink maps
def read_map(path, shape):
    """ink map as float32 0..1 on the render grid (identical to ensemble_maps.py read_map)."""
    import cv2
    import tifffile
    if path.lower().endswith('.png'):
        a = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if a is None:
            raise SystemExit(f'cannot read {base(path)}')
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
            raise SystemExit(f'{base(path)}: shape {a.shape} != surface volume {tuple(shape)}')
    return np.ascontiguousarray(a, dtype=np.float32)


def identify_map(path, name=None):
    b = base(path)
    stem = re.sub(r'\.(tif|tiff|png)$', '', b, flags=re.I)
    model = name
    if model is None:
        hits = [m for m, tag in MODELS if tag in b]
        model = hits[0] if len(hits) == 1 else stem
    direction = 'reverse' if stem.endswith('_reverse') else 'forward'
    depth = None
    m = re.search(r'__L66s(\d+)', b)
    if m:
        depth = int(m.group(1)) - 25              # villa: 17-layer window s..s+16, d = s - 25
    m = re.search(r'__L66zc(\d+(?:\.\d+)?)', b)
    if m:
        dd = round(float(m.group(1)) - 32.5, 2)   # Hecate: window centre zc = 32.5 + d
        depth = int(dd) if dd == int(dd) else dd
    return dict(file=b, model=model, direction=direction, side='reading' if direction == 'reverse' else 'blind',
                depth=depth, villa=not b.lower().endswith('.png'))


def stats_from_map(M, valid, villa):
    v = M[valid]
    if villa:
        hist = np.bincount(np.rint(v * 128).astype(np.int64), minlength=129)[:129]
        values = np.arange(129) / 128.0
    else:
        hist = np.bincount(np.minimum((v * FINE).astype(np.int64), FINE - 1), minlength=FINE)
        values = np.arange(FINE) / FINE
    lo, hi = pct_hist(hist, values, [P_LO, P_HI])
    n = v.size
    s1 = float(v.sum(dtype=np.float64))
    s2 = float(np.square(v, dtype=np.float64).sum())
    mu = s1 / n
    sd = math.sqrt(max(s2 / n - mu * mu, 0.0)) + 1e-6
    return dict(p1=lo, p99_5=hi, mean=mu, sd=sd, n_px=int(n))


# ------------------------------------------------------------------ annotations
def load_annotations(path, key, frame, area_reading):
    """rows or letters JSON -> (list in area coordinates, input frame, raw JSON)."""
    j = json.load(open(path))
    fr = j.get('frame', 'area')
    if fr not in ('area', 'reading', 'raw'):
        raise SystemExit(f'{base(path)}: frame must be area, reading or raw (got {fr!r})')
    ax0, ay0 = area_reading[0], area_reading[1]

    def pt(x, y):
        x, y = float(x), float(y)
        if fr == 'raw':
            x, y = frame.point_raw_to_reading(x, y)
        if fr in ('raw', 'reading'):
            x, y = x - ax0, y - ay0
        return [x, y]

    def rect(r):
        x0, y0, x1, y1 = (float(v) for v in r)
        if x1 < x0 or y1 < y0:
            raise SystemExit(f'{base(path)}: box {r} has x1 < x0 or y1 < y0')
        if fr == 'raw':
            x0, y0, x1, y1 = frame.rect_raw_to_reading(x0, y0, x1, y1)
        if fr in ('raw', 'reading'):
            x0, x1, y0, y1 = x0 - ax0, x1 - ax0, y0 - ay0, y1 - ay0
        return [x0, y0, x1, y1]

    out = []
    for i, e in enumerate(j.get(key, [])):
        e2 = dict(label=str(e.get('label', i + 1)))
        if key == 'rows':
            if 'baseline' in e:
                pts = [pt(*p) for p in e['baseline']]
                if len(pts) < 2:
                    raise SystemExit(f'{base(path)}: row {e2["label"]}: a baseline needs at least 2 points')
                e2['baseline'] = pts
            elif 'rect' in e:
                e2['rect'] = rect(e['rect'])
            elif 'baseline_follows_letters' in e:
                e2['follows_letters'] = follow_params(e['baseline_follows_letters'], path, e2['label'])
            else:
                raise SystemExit(f'{base(path)}: row {e2["label"]} has neither "baseline" nor "rect"')
        else:
            e2['row'] = str(e.get('row', ''))
            e2['box'] = rect(e['box'])
            letter_extras(e, e2, path)
        out.append(e2)
    if key == 'letters':
        check_letter_ids(out, path)
    return out, fr, j


def letter_extras(e, e2, path):
    """optional letter fields "id", "reading" and "class" (only copied when given)."""
    if 'id' in e:
        v = e['id']
        if isinstance(v, bool) or not isinstance(v, int) or v < 1:
            raise SystemExit(f'{base(path)}: letter {e2["label"]}: id must be a positive integer (got {v!r})')
        e2['id'] = v
    if 'reading' in e:
        e2['reading'] = str(e['reading'])
    if 'class' in e:
        if e['class'] not in LETTER_CLASSES:
            raise SystemExit(f'{base(path)}: letter {e2["label"]}: class must be one of {", ".join(LETTER_CLASSES)}')
        e2['class'] = e['class']


def check_letter_ids(letters, path):
    """the optional letter "id": given for every letter or for none, all different."""
    n = sum('id' in L for L in letters)
    if n and n != len(letters):
        raise SystemExit(f'{base(path)}: "id" is given for {n} of {len(letters)} letters; give it for every letter or '
                         f'for none')
    if len({L['id'] for L in letters if 'id' in L}) != n:
        raise SystemExit(f'{base(path)}: the letter ids must all be different')


def letter_number(L, i):
    """the number of a letter in the CSV, the key image and the sidecar: its "id", else its position (1, 2, ...)."""
    return L.get('id', i)


def sidecar_letter(L, i):
    """a letter as recorded in the sidecar: its number first, then its fields."""
    return dict(id=letter_number(L, i), **{k: v for k, v in L.items() if k != 'id'})


def leiden(L):
    """the reading as written in the CSV: an uncertain reading gets a combining dot below (Leiden convention)."""
    s = L.get('reading', '')
    return s + '̣' if s and L.get('class') == 'uncertain' else s


def derive_follow_rows(rows, letters, ink, shape, thick, level_default):
    """rows given as baseline_follows_letters -> segments (in place). Returns the letter extents (for the checks)."""
    for r in rows:
        if 'follows_letters' in r:
            ls = [L for L in letters if L['row'] == r['label']]
            if not ls:
                raise SystemExit(f"row {r['label']}: baseline_follows_letters needs letters with row {r['label']!r} "
                                 f"(--letters)")
            r['segments'], r['derived'] = baseline_follows_letters(ls, letters, ink, shape, r['follows_letters'], thick,
                                                                   level_default)
            if not r['segments']:
                raise SystemExit(f"row {r['label']}: no row line could be derived")
    return letter_extents(letters, ink, level_default, shape)


def extent_checks(checks, rows, extents, shape, thick, dash):
    """row lines derived from the letters may run through the empty lower part of a letter box (below its visible
    ink); they must not enter a letter extent. Rows given otherwise are still checked against the whole boxes."""
    H, W = shape
    em = np.zeros((H, W), bool)
    for x0, y0, x1, y1 in extents:
        x0, y0, x1, y1 = (int(round(v)) for v in (x0, y0, x1, y1))
        em[max(y0, 0):max(y1, 0), max(x0, 0):max(x1, 0)] = True
    rm = np.zeros((H, W), np.uint8)
    draw_rows(rm, [r for r in rows if 'segments' in r], 0, 0, 255, thick, dash, aa=False)
    n_ext = int(((rm > 0) & em).sum())
    checks['row_pixels_inside_letter_extents'] = n_ext
    checks['letter_extent_rule'] = ('letter box with its bottom raised to the lowest box row with visible ink (see '
                                    'letter_extents in the rows); the derived row lines are checked against these')
    if n_ext:
        warn(f'{n_ext} derived row-line pixels lie inside letter extents (rows should not cover letters)')
    return [r for r in rows if 'segments' not in r]


def row_points(r):
    return r.get('baseline') or ([p for s in r['segments'] for p in s] if 'segments' in r else
                                 [r['rect'][:2], r['rect'][2:]])


def dashed_segments(pts, dash):
    """split a polyline into drawn pieces [(p, q), ...] for a dash pattern (on, off) in px; dash None = solid."""
    segs = []
    if not dash:
        return [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    on, off = dash
    period = on + off
    t = 0.0
    for i in range(len(pts) - 1):
        p = np.array(pts[i], float)
        q = np.array(pts[i + 1], float)
        L = float(np.linalg.norm(q - p))
        s = 0.0
        while s < L:
            ph = (t + s) % period
            if ph < on:
                e = min(L, s + (on - ph))
                segs.append((p + (q - p) * s / L, p + (q - p) * e / L))
            else:
                e = min(L, s + (period - ph))
            s = e
        t += L
    return segs


def draw_rows(img, rows, ox, oy, color, thick, dash, aa=True):
    import cv2
    lt = cv2.LINE_AA if aa else cv2.LINE_8
    for r in rows:
        if 'baseline' in r:
            pts = [(x + ox, y + oy) for x, y in r['baseline']]
            for p, q in dashed_segments(pts, dash):
                cv2.line(img, (int(round(p[0])), int(round(p[1]))), (int(round(q[0])), int(round(q[1]))), color,
                         thick, lt)
        elif 'segments' in r:
            for sg in r['segments']:
                pts = [(x + ox, y + oy) for x, y in sg]
                for p, q in dashed_segments(pts, dash):
                    cv2.line(img, (int(round(p[0])), int(round(p[1]))), (int(round(q[0])), int(round(q[1]))), color,
                             thick, lt)
        else:
            x0, y0, x1, y1 = r['rect']
            pts = [(x0 + ox, y0 + oy), (x1 - 1 + ox, y0 + oy), (x1 - 1 + ox, y1 - 1 + oy), (x0 + ox, y1 - 1 + oy),
                   (x0 + ox, y0 + oy)]
            for p, q in dashed_segments(pts, dash):
                cv2.line(img, (int(round(p[0])), int(round(p[1]))), (int(round(q[0])), int(round(q[1]))), color,
                         thick, lt)


def row_anchor_y(r):
    if 'baseline' in r:
        return r['baseline'][0][1]
    if 'segments' in r:
        return r['segments'][0][0][1]
    return 0.5 * (r['rect'][1] + r['rect'][3])


# ------------------------------------------------------------------ text helpers
def text_size(s, scale, thick):
    import cv2
    (w, h), bl = cv2.getTextSize(s, FONT, scale, thick)
    return w, h, bl


def put(img, s, x, y, scale, color, thick):
    """text with its baseline at y."""
    import cv2
    cv2.putText(img, s, (int(x), int(y)), FONT, scale, color, thick, cv2.LINE_AA)


def wrap(s, scale, thick, width):
    words, lines, cur = s.split(' '), [], ''
    for wd in words:
        t = (cur + ' ' + wd).strip()
        if cur and text_size(t, scale, thick)[0] > width:
            lines.append(cur)
            cur = wd
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def colormap_lut(name):
    """256 x 3 BGR lookup table."""
    import cv2
    if name.startswith('mono:'):
        r, g, b = (int(v) for v in name[5:].split(','))
        return np.tile(np.array([[b, g, r]], np.uint8), (256, 1))
    cm = getattr(cv2, 'COLORMAP_' + name.upper(), None)
    if cm is None:
        raise SystemExit(f'--cmap {name}: choose one of {", ".join(CMAPS)} or mono:R,G,B')
    return cv2.applyColorMap(np.arange(256, dtype=np.uint8)[:, None], cm)[:, 0, :]


def parse_color(s):
    r, g, b = (int(v) for v in s.split(','))
    return (b, g, r)


def fmt(x, n=3):
    return float(round(float(x), n))


# ------------------------------------------------------------------ two-panel mode: helpers
PANEL_OPTS = (('mesh', None), ('ct', None), ('ink', []), ('ink_stats', None), ('area', None),
              ('render_offset', '0,0'))


def collapse_single(a):
    """one mesh: every per-panel option takes its last value, exactly as the plain (store) option did."""
    for k, dflt in PANEL_OPTS:
        v = getattr(a, k)
        setattr(a, k, v[-1] if v else dflt)
    return a


def check_geometry_panels(sums_path, meshes):
    """two-panel mode: meshes [(mesh folder name, [(file, sha256)])]. A list applies to a mesh when it has
    "<mesh folder>/<file>" entries for it (exact, or deeper in the list); every mesh it lists must match completely.
    Bare file names are not used here (they cannot say which mesh they belong to)."""
    entries = read_sums(sums_path)
    if not entries:
        raise SystemExit(f'--geometry-sums {base(sums_path)}: no sha256 lines')
    out = {}
    for mesh_name, geo in meshes:
        cands = []
        for f, h in geo:
            exact = {s for s, p in entries if p == f'{mesh_name}/{f}'}
            deep = {s for s, p in entries if p.endswith(f'/{mesh_name}/{f}')}
            cands.append((f, h, exact or deep))
        if not any(c for _, _, c in cands):
            continue
        matched = []
        for f, h, cand in cands:
            if not cand:
                raise SystemExit(f'--geometry-sums {base(sums_path)}: {f} of {mesh_name} is not in the list')
            if len(cand) > 1:
                raise SystemExit(f'--geometry-sums {base(sums_path)}: {f} of {mesh_name} is listed with different '
                                 f'sha256 values')
            if h not in cand:
                raise SystemExit(f'--geometry-sums {base(sums_path)}: {f} of {mesh_name} does NOT match the list '
                                 f'(here {h[:16]}..., listed {next(iter(cand))[:16]}...): the mesh geometry differs')
            matched.append(f)
        out[mesh_name] = dict(list_sha256=sha256_file(sums_path), list_lines=len(entries), files_matched=matched,
                              result='every geometry file matches')
    if not out:
        raise SystemExit(f'--geometry-sums {base(sums_path)}: lists none of the panel meshes as "<mesh folder>/<file>"')
    return out


def bilinear_points(a, rows, cols, sc, off):
    """as bilinear_nodes, but point by point: render pixels (rows[k], cols[k]) -> value; NaN stays NaN."""
    h, w = a.shape
    fr = np.clip((off[0] + np.asarray(rows, np.float64)) * sc, 0, h - 1.001)
    fc = np.clip((off[1] + np.asarray(cols, np.float64)) * sc, 0, w - 1.001)
    i0 = fr.astype(int)
    j0 = fc.astype(int)
    dr = fr - i0
    dc = fc - j0
    return (a[i0, j0] * (1 - dr) * (1 - dc) + a[i0, j0 + 1] * (1 - dr) * dc
            + a[i0 + 1, j0] * dr * (1 - dc) + a[i0 + 1, j0 + 1] * dr * dc)


def seam_edge(Q, side, strip=256, max_step=16, block=128, to_render=False):
    """per row of the whole render (reading orientation): the outermost valid pixel on `side` ('right' or 'left') of
    the area's columns (searched within `strip` px of that side of the area; valid = all 66 layers > 0), and the mesh
    x, y, z and theta there (bilinear from the nodes; if the nodes are invalid there, up to max_step px further
    inward). to_render: search from `strip` px inside that side of the area outward to the end of the render, i.e.
    the render edge of the mesh even where the area stops short of it. Returns dict of arrays over the H render rows
    (NaN where the row has no value)."""
    fr, off, sc, st = Q['frame'], Q['off'], Q['sc'], Q['st']
    rx0, ry0, rx1, ry1 = Q['reading_px']
    H = Q['H']
    xs0, xs1 = (max(rx0, rx1 - strip), rx1) if side == 'right' else (rx0, min(rx1, rx0 + strip))
    if to_render:
        xs0, xs1 = (xs0, Q['W']) if side == 'right' else (0, xs1)
    c0, _, c1, _ = fr.rect_reading_to_raw(xs0, 0, xs1, H)
    vraw = np.zeros((H, c1 - c0), bool)
    for r0 in range(0, H, block):
        vraw[r0:r0 + block] = (np.asarray(st[:, r0:r0 + block, c0:c1]) > 0).all(0)
    valid = vraw[::-1] if fr.flip_ud else vraw                # the strip in reading orientation
    valid = valid[:, ::-1] if fr.flip_lr else valid
    w = valid.shape[1]
    xs = np.full(H, -1, np.int64)
    for i in range(H):
        idx = np.flatnonzero(valid[i])
        if idx.size:
            xs[i] = idx[-1] if side == 'right' else idx[0]
    fields = {k: np.where(Q['ok'], Q[k], np.nan) for k in ('X', 'Y', 'Z')}
    fields['T'] = Q['theta']
    out = {k: np.full(H, np.nan) for k in ('X', 'Y', 'Z', 'T', 'x_reading')}
    step = -1 if side == 'right' else 1
    todo = np.flatnonzero(xs >= 0)
    for k in range(max_step + 1):
        if not todo.size:
            break
        xr = xs[todo] + step * k
        inside = (xr >= 0) & (xr < w)
        todo, xr = todo[inside], xr[inside]
        rawx, rawy = fr.point_raw_to_reading(xs0 + xr, todo)       # the same involution
        z = bilinear_points(fields['Z'], rawy, rawx, sc, off)
        good = np.isfinite(z)
        for key in ('X', 'Y', 'Z', 'T'):
            out[key][todo[good]] = bilinear_points(fields[key], rawy[good], rawx[good], sc, off)
        out['x_reading'][todo[good]] = xs0 + xr[good]
        todo = todo[~good]
    return out


def fit_panel_dy(zl, yl0, zr, yr0, fixed=None):
    """z profiles along the seam (left profile from reading row yl0, right profile from reading row yr0) -> D (right
    row = left row + D) with the smallest RMS z difference over the common rows (at least half of the shorter
    profile), or the fixed D."""
    hl, hr = zl.size, zr.size
    min_n = max(20, min(hl, hr) // 2)

    def diff(D):
        i0 = max(0, yr0 - D - yl0)
        i1 = min(hl, yr0 + hr - D - yl0)
        if i1 <= i0:
            return None, 0, 0
        a_ = zl[i0:i1]
        b_ = zr[yl0 + i0 + D - yr0:yl0 + i1 + D - yr0]
        m = np.isfinite(a_) & np.isfinite(b_)
        return a_[m] - b_[m], i1 - i0, (i0, i1)
    best = None
    for D in range(yr0 - (yl0 + hl - 1), yr0 + hr - 1 - yl0 + 1):
        d, nov, _ = diff(D)
        if d is None or nov < min_n or d.size < min_n // 2:
            continue
        rms = float(np.sqrt(np.mean(d * d)))
        if best is None or rms < best[1]:
            best = (D, rms)
    if best is None and fixed is None:
        raise SystemExit('two-panel mode: the seam z profiles of the two areas have too few common rows to align them')
    D = best[0] if fixed is None else int(fixed)
    d, nov, span = diff(D)
    if d is None or not d.size:
        raise SystemExit(f'two-panel mode: --panel-dy {D} leaves no common seam rows')
    res = dict(D=D, rows_compared=int(d.size), rows_overlapping=int(nov), left_area_rows=[int(yl0 + span[0]),
               int(yl0 + span[1])], z_diff_mean_vox=fmt(d.mean()), z_diff_rms_vox=fmt(np.sqrt(np.mean(d * d))),
               z_diff_max_abs_vox=fmt(np.abs(d).max()))
    if best is not None:
        res['best_fit'] = dict(D=best[0], z_diff_rms_vox=fmt(best[1]))
    return res, span


def baseline_below(boxes, gap, max_slope=None):
    """a polyline that runs at least `gap` px below every box [x0, y0, x1, y1] (y down), from the left end of the first
    box to the right end of the last, and never enters a box. Under each box (widened by `gap` on both sides, and by
    1 px more for rounding) it lies at (box bottom + gap) or lower. Without max_slope it is the plain envelope:
    horizontal under each box, vertical steps where boxes of different depth meet, straight between boxes. With
    max_slope (dy/dx, e.g. 0.5) it is the highest line on or below that envelope (the envelope bridged straight
    between boxes) whose slope nowhere exceeds max_slope: no vertical steps, it descends and rises at most at that
    slope."""
    segs = sorted((b[0] - gap, b[2] + gap, b[3] + gap) for b in boxes)
    if max_slope is None:
        xs = sorted({s[0] for s in segs} | {s[1] for s in segs})
        pts = []
        for x0, x1 in zip(xs[:-1], xs[1:]):
            cov = [s[2] for s in segs if s[0] <= x0 and s[1] >= x1]
            if cov:
                lv = max(cov)
                for p in ([x0, lv], [x1, lv]):
                    if not pts or pts[-1] != p:
                        pts.append(p)
    else:
        s_ = float(max_slope)
        if s_ <= 0:
            raise SystemExit('baseline_below_letters: max_slope must be > 0')
        xa = int(math.floor(segs[0][0]))
        xb = int(math.ceil(max(s[1] for s in segs)))
        e = np.full(xb - xa + 1, -np.inf)
        for x0, x1, lv in segs:
            i0_ = max(int(math.floor(x0)) - 1 - xa, 0)
            i1_ = min(int(math.ceil(x1)) + 1 - xa, e.size - 1)
            e[i0_:i1_ + 1] = np.maximum(e[i0_:i1_ + 1], lv)
        cov = np.isfinite(e)                            # between boxes: straight from box end to box start
        idx = np.flatnonzero(cov)
        e = np.interp(np.arange(e.size), idx, e[idx])
        f = e.copy()                                    # smallest slope-limited function >= e (y down)
        for i in range(1, f.size):
            f[i] = max(f[i], f[i - 1] - s_)
        for i in range(f.size - 2, -1, -1):
            f[i] = max(f[i], f[i + 1] - s_)
        d = np.round(np.diff(f), 9)
        keep = [0] + [i for i in range(1, f.size - 1) if d[i] != d[i - 1]] + [f.size - 1]
        pts = [[float(xa + i), float(f[i])] for i in keep]
    out = []
    for p in pts:                                   # drop the middle point of straight horizontal runs
        if len(out) >= 2 and out[-1][1] == p[1] == out[-2][1]:
            out[-1] = p
        else:
            out.append(p)
    return [[fmt(x, 2), fmt(y, 2)] for x, y in out]


FOLLOW_KEYS = ('gap', 'clearance', 'max_dip', 'max_rise', 'outlier', 'break_cost', 'level')


def simplify_polyline(P, eps):
    """Douglas-Peucker: the points of the polyline P (n x 2) that keep every point within eps px."""
    keep = np.zeros(len(P), bool)
    keep[0] = keep[-1] = True
    stack = [(0, len(P) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = P[i], P[j]
        d = b - a
        L = math.hypot(d[0], d[1])
        seg = P[i + 1:j]
        if L == 0:
            dist = np.hypot(seg[:, 0] - a[0], seg[:, 1] - a[1])
        else:
            dist = np.abs(d[0] * (seg[:, 1] - a[1]) - d[1] * (seg[:, 0] - a[0])) / L
        m = int(np.argmax(dist))
        if dist[m] > eps:
            keep[i + 1 + m] = True
            stack += [(i, i + 1 + m), (i + 1 + m, j)]
    return P[keep]


def follow_params(v, path, label):
    v = {} if v in (None, True) else v
    if not isinstance(v, dict) or set(v) - set(FOLLOW_KEYS):
        raise SystemExit(f'{base(path)}: row {label}: baseline_follows_letters takes an object with the keys '
                         f'{", ".join(FOLLOW_KEYS)}')
    return {k: float(x) for k, x in v.items()}


def letter_extents(letters, ink, level, shape, min_row_frac=0.03, min_frac=0.02):
    """the extent of each letter for the row lines: its box with the bottom raised to the lowest box row that holds
    visible ink (>= level) in at least max(3 px, 3 % of the box width); unchanged if the box holds less than 2 %
    visible ink (a faint letter keeps its whole box) or if there is no ink image."""
    H, W = shape
    out = []
    for L in letters:
        x0, y0, x1, y1 = L['box']
        e = [x0, y0, x1, y1]
        if ink is not None:
            X0, Y0 = max(int(math.floor(x0)), 0), max(int(math.floor(y0)), 0)
            X1, Y1 = min(int(math.ceil(x1)), W), min(int(math.ceil(y1)), H)
            sub = ink[Y0:Y1, X0:X1] >= level
            if sub.size and sub.mean() >= min_frac:
                rows_ok = np.flatnonzero(sub.sum(1) >= max(3.0, min_row_frac * (X1 - X0)))
                if rows_ok.size:
                    e[3] = min(y1, float(Y0 + rows_ok.max() + 1))
        out.append(e)
    return out


def baseline_follows_letters(row_letters, all_letters, ink, shape, p, thick, level_default):
    """row line that follows the letters of one row just below them (y down; see ROW LINES in the header).
    row_letters: the letters of the row (dicts with "box" [x0, y0, x1, y1] and "label"); all_letters: every letter
    (none may be touched); ink: the 8-bit ink image in the same frame (None: boxes only); shape: (H, W) of the frame.
    Returns (segments [[[x, y], ...], ...], record for the sidecar)."""
    import cv2
    H, W = shape
    level = int(p.get('level', level_default))
    ext_all = letter_extents(all_letters, ink, level, shape)
    ext_of = {id(L): e for L, e in zip(all_letters, ext_all)}
    Ls = sorted(row_letters, key=lambda L: 0.5 * (L['box'][0] + L['box'][2]))
    B = np.array([ext_of[id(L)] for L in Ls], np.float64)
    all_boxes = ext_all
    n = len(B)
    mh = float(np.median([L['box'][3] - L['box'][1] for L in Ls]))
    gap = p.get('gap', 16.0)
    clr = p.get('clearance', 3.0)
    max_dip = p.get('max_dip', 0.35) * mh
    max_rise = p.get('max_rise', 0.5 * gap)
    outl = p.get('outlier', 0.6) * mh
    bcost = p.get('break_cost', 40.0)
    step, bstart, min_seg, w_step, dmax, ksm = 2, 50.0 * bcost, 40.0, 1.0, 2, 5
    bot = B[:, 3]
    keep = np.ones(n, bool)
    for i in range(n):
        nb = [bot[j] for j in range(max(0, i - 2), min(n, i + 3)) if j != i]
        if nb and bot[i] - float(np.median(nb)) > outl:
            keep[i] = False
    xa = max(int(math.floor(B[:, 0].min())), 0)
    xb = min(int(math.ceil(B[:, 2].max())), W - 1)
    xs = np.arange(xa, xb + 1, step)
    if xs[-1] != xb:
        xs = np.append(xs, xb)
    T = np.full(xs.size, -np.inf)
    for b in B[keep]:
        m = (xs >= b[0]) & (xs <= b[2])
        T[m] = np.maximum(T[m], b[3] + gap)
    cov = np.isfinite(T)
    T = np.interp(xs, xs[cov], T[cov])
    r = int(math.ceil(clr + thick / 2.0))
    y0 = max(int(math.floor(T.min() - max_rise)) - 1, 0)
    y1 = min(int(math.ceil(T.max() + max_dip)) + 1, H - 1)
    S = y1 - y0 + 1
    blk = np.zeros((S, xb - xa + 1), bool)          # rows y0..y1, columns xa..xb
    if ink is not None:
        ya, yb_, ca, cb = max(y0 - r, 0), min(y1 + r, H - 1), max(xa - r, 0), min(xb + r, W - 1)
        vis = (ink[ya:yb_ + 1, ca:cb + 1] >= level).astype(np.uint8)
        vis = cv2.dilate(vis, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))) > 0
        blk |= vis[y0 - ya:y0 - ya + S, xa - ca:xa - ca + blk.shape[1]]
    for b in all_boxes:
        bx0, by0 = int(math.floor(b[0] - r)), int(math.floor(b[1] - r))
        bx1, by1 = int(math.ceil(b[2] + r)), int(math.ceil(b[3] + r))
        blk[max(by0 - y0, 0):max(by1 - y0, 0), max(bx0 - xa, 0):max(bx1 - xa, 0)] = True
    ys = np.arange(y0, y1 + 1, dtype=np.float64)
    cost = np.abs(ys[None, :] - T[:, None])                                   # (columns, states)
    cost[(ys[None, :] < T[:, None] - max_rise) | (ys[None, :] > T[:, None] + max_dip)] = np.inf
    cost[blk[:, xs - xa].T] = np.inf
    nc = xs.size
    moves = list(range(-dmax, dmax + 1))              # dy per column step (slope <= dmax / step)
    back = np.zeros((nc, S), np.int8)                 # index into moves, or len(moves): from the break
    backb = np.full(nc, -1, np.int64)                 # break state: -1 from the break, else from that state
    prev = cost[0].copy()
    prevb = bstart + bcost * step
    for k in range(1, nc):
        cand = np.full((len(moves) + 1, S), np.inf)
        for i, d in enumerate(moves):                 # state s from state s - d
            if d >= 0:
                cand[i, d:] = prev[:S - d] + w_step * d
            else:
                cand[i, :S + d] = prev[-d:] - w_step * d
        cand[-1] = prevb
        ch = np.argmin(cand, 0)
        back[k] = ch
        j = int(np.argmin(prev))
        if prevb <= prev[j] + bstart:
            curb = prevb + bcost * (xs[k] - xs[k - 1])
        else:
            curb = prev[j] + bstart + bcost * (xs[k] - xs[k - 1])
            backb[k] = j
        prev = cand[ch, np.arange(S)] + cost[k]
        prevb = curb
    path = np.full(nc, -1, np.int64)
    s = int(np.argmin(prev)) if prev.min() <= prevb else -1
    for k in range(nc - 1, -1, -1):
        path[k] = s
        if k == 0:
            break
        if s < 0:
            s = int(backb[k])
        else:
            c = int(back[k, s])
            s = -1 if c == len(moves) else s - moves[c]
    free = np.isfinite(cost)
    out, runs, k = [], [], 0
    while k < nc:                                     # runs of drawn columns
        if path[k] < 0:
            k += 1
            continue
        k1 = k
        while k1 + 1 < nc and path[k1 + 1] >= 0:
            k1 += 1
        runs.append((k, k1))
        k = k1 + 1
    for k0, k1 in runs:
        if xs[k1] - xs[k0] < min_seg:
            continue
        idx = np.arange(k0, k1 + 1)
        yr = ys[path[idx]]
        pad = np.concatenate([np.full(ksm, yr[0]), yr, np.full(ksm, yr[-1])])
        ysm = np.convolve(pad, np.ones(2 * ksm + 1) / (2 * ksm + 1), mode='valid')   # moving mean over 22 px
        st_ = np.clip(np.rint(ysm).astype(np.int64) - y0, 0, S - 1)
        ok_ = free[idx, st_] & (np.abs(ysm - yr) <= 2 * dmax * ksm)
        yf = np.where(ok_, ysm, yr)                  # smoothed where that stays clear, else the path itself
        pts = simplify_polyline(np.stack([xs[idx].astype(np.float64), yf], 1), 0.75)
        out.append([[fmt(x, 1), fmt(y, 1)] for x, y in pts])
    breaks = [[a_[-1][0], b_[0][0]] for a_, b_ in zip(out[:-1], out[1:])]
    if out and out[0][0][0] > xa + step:
        breaks.insert(0, [float(xa), out[0][0][0]])
    if out and out[-1][-1][0] < xb - step:
        breaks.append([out[-1][-1][0], float(xb)])
    on = np.array([path[k] >= 0 for k in range(nc)])
    dev = np.array([ys[path[k]] - T[k] for k in range(nc) if path[k] >= 0])
    rec = dict(rule='baseline_follows_letters: target <gap> px below the letter boxes of the row; cheapest path (cost '
                    '|y - target| per px, + 1 per px of height change, slope <= 1) that keeps <clearance> px plus half '
                    'the line width from every letter box and from visible ink, at most max_dip below / max_rise above '
                    'the target; interrupted where no such path exists or it would cost more (break_start + break_cost '
                    'per px); then a moving mean over 22 px where that stays clear, simplified to within 0.75 px',
               gap_px=gap, clearance_px=clr, line_px=thick, max_dip_px=fmt(max_dip, 1), max_rise_px=fmt(max_rise, 1),
               max_slope=dmax / step, break_start=bstart,
               outlier_px=fmt(outl, 1), break_cost=bcost, ink_level_8bit=level if ink is not None else None,
               median_box_height_px=fmt(mh, 1), letters=[L['label'] for L in Ls],
               letters_without_target=[L['label'] for L, k_ in zip(Ls, keep) if not k_],
               letter_bottoms=[dict(label=L['label'], box_bottom=fmt(L['box'][3], 1), extent_bottom=fmt(b[3], 1))
                               for L, b in zip(Ls, B)],
               drawn_fraction=fmt(on.mean(), 4), interruptions_x=breaks,
               below_target_px=dict(median=fmt(np.median(dev), 1), max=fmt(dev.max(), 1)) if dev.size else None)
    if not out:
        warn(f'row line from the letters: no path found for the letters {", ".join(L["label"] for L in Ls)}')
    return out, rec


# ------------------------------------------------------------------ main
def build_parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_argument_group('mesh and orientation')
    g.add_argument('--mesh', required=True, action='append',
                   help='submitted .tifxyz folder; the image is named after it (twice: two-panel mode, see there)')
    g.add_argument('--umbilicus', help='scroll axis JSON (control_points); measures the reading orientation')
    g.add_argument('--flip-lr', type=int, choices=(0, 1), help='explicit: mirror columns for reading orientation')
    g.add_argument('--flip-ud', type=int, choices=(0, 1), help='explicit: mirror rows for reading orientation')
    g.add_argument('--render-offset', action='append',
                   help='row,col of render pixel (0, 0) in the full render of the mesh (for a cropped render; '
                        'default 0,0)')
    g.add_argument('--geometry-sums', action='append', default=[],
                   help='sha256 list (e.g. outputs/SHA256SUMS): stop unless x/y/z(/mask).tif match it (repeatable)')
    g.add_argument('--forbid-words', help='publication check: word list, see INPUTS')
    g = ap.add_argument_group('CT background')
    g.add_argument('--ct', required=True, action='append', help='66-layer surface volume (zarr) rendered from --mesh')
    g.add_argument('--ct-layer', default='d0', help="layer index, depth 'd0'/'d-1', or a range 'd-1..d+1' (mean)")
    g.add_argument('--ct-stretch', default='auto', help="auto | area | lo,hi (see OVERLAY)")
    g.add_argument('--skip-tree-hash', action='store_true',
                   help='do not hash every file of the zarr (the decoded layers used are always hashed)')
    g = ap.add_argument_group('ink')
    g.add_argument('--ink', nargs='+', action='append', help='ink map files (reading side); none = CT only')
    g.add_argument('--ink-names', nargs='+', help='model names for --ink, same order (default: from the file names)')
    g.add_argument('--ensemble', action='store_true', help='mean of the per-model z-scores of all --ink maps')
    g.add_argument('--ink-stats', action='append', help='<name>__stats.json of ensemble_maps.py for this surface volume')
    g.add_argument('--allow-blind', action='store_true', help='accept blind-side (forward) maps, e.g. for a control')
    g = ap.add_argument_group('area')
    g.add_argument('--area', action='append',
                   help='x0,y0,x1,y1 (exclusive), raw render pixels unless --area-frame reading')
    g.add_argument('--area-frame', choices=('raw', 'reading'), default='raw')
    g.add_argument('--area-json', help='JSON with raw_render_px {row0,row1,col0,col1} (top level or under "region")')
    g.add_argument('--max-cm2', type=float, default=4.0)
    g.add_argument('--voxel-um', type=float, default=8.64, help='render pixel size (default 8.64 um)')
    g.add_argument('--panel-dy', default='auto',
                   help='two-panel mode: auto (default) = measured from the mesh z at the seam, or an integer D '
                        '(right panel row = left panel row + D)')
    g.add_argument('--panel-gap', type=int, default=6, help='two-panel mode: width of the separator line in px')
    g.add_argument('--unequal-panels', action='store_true',
                   help='two-panel mode: the two areas cover different rows on purpose (e.g. a second text row on one '
                        'mesh only); recorded in the sidecar instead of a warning')
    g.add_argument('--seam-edge', choices=('area', 'render'), default='area',
                   help='two-panel mode: measure the seam at the outermost valid pixel of each area (default), or of '
                        'the whole render row (the render edge of each mesh, also where the area stops short of it)')
    g = ap.add_argument_group('annotations')
    g.add_argument('--rows', help='rows JSON (baselines or rectangles)')
    g.add_argument('--letters', help='letters JSON (boxes for the size table)')
    g.add_argument('--letter-markers', choices=('key', 'on', 'off'), default='key')
    g.add_argument('--sizes-csv', help='default: letter_sizes.csv next to the image')
    g.add_argument('--row-color', default='0,255,255', help='R,G,B (default cyan)')
    g.add_argument('--row-thickness', type=int, default=2)
    g.add_argument('--row-dash', default='', help="on,off in px for a dashed line (default solid)")
    g = ap.add_argument_group('overlay style')
    g.add_argument('--overlay-style', choices=tuple(STYLES), default='default',
                   help='named style = the defaults of the options below (see OVERLAY): default (orange tint over the '
                        'CT) or dimmed-ct (light-yellow ink over the CT grey x 0.45)')
    g.add_argument('--cmap', default=None, help=f'mono:R,G,B or {", ".join(CMAPS)} (default: from --overlay-style; '
                                                f'default orange mono:255,140,0, dimmed-ct light yellow mono:255,235,120)')
    g.add_argument('--alpha', type=float, default=None, help='maximum ink opacity (default 0.75; dimmed-ct 0.9)')
    g.add_argument('--threshold', type=float, default=None,
                   help='stretched ink value below which nothing is drawn (default 0.5; dimmed-ct 0.35)')
    g.add_argument('--full', type=float, default=None,
                   help='stretched ink value at which the opacity is --alpha (default 0.9; dimmed-ct 0.75)')
    g.add_argument('--blend', choices=('tint', 'alpha'), default=None,
                   help='tint (default style): ink colour scaled by the CT brightness, so the fibres stay visible inside '
                        'the ink; alpha (dimmed-ct): plain alpha blending')
    g.add_argument('--tint-floor', type=float, default=0.3,
                   help='tint: colour factor over black CT (1.0 over white CT)')
    g.add_argument('--ct-dim', type=float, default=None,
                   help='factor on the CT grey of the image (default 1; dimmed-ct 0.45); the _ct.png component is '
                        'never dimmed')
    g = ap.add_argument_group('labels and output')
    g.add_argument('--caption', choices=('full', 'compact'), default='full',
                   help='compact: a shorter caption (all numbers stay in the sidecar)')
    g.add_argument('--scroll', default='PHerc. 343', help='scroll name for the caption')
    g.add_argument('--volume-id', default='20250521140437', help='volume id for the caption')
    g.add_argument('--title', help='replace the first caption line')
    g.add_argument('--note', action='append', default=[], help='extra caption line (repeatable)')
    g.add_argument('--panel-line', default=None,
                   help='two panels: replace the caption line on the panels and the seam with this text (empty: no '
                        'such line); the seam numbers stay in the sidecar')
    g.add_argument('--font-scale', type=float, default=1.3)
    g.add_argument('--out', help='output PNG (default <out-dir>/<mesh name>.png)')
    g.add_argument('--out-dir', default='.')
    g.add_argument('--write-components', action='store_true', help='also write <stem>_ct.png and <stem>_ink.png')
    g.add_argument('--force', action='store_true', help='overwrite existing outputs')
    return ap


def main(argv=None):
    import cv2
    cv2.setNumThreads(1)
    a = resolve_style(build_parser().parse_args(argv))
    if len(a.mesh) > 1:
        return main_panels(a, argv)
    if a.panel_line is not None:
        raise SystemExit('--panel-line is for two-panel mode (two --mesh)')
    collapse_single(a)
    mesh_dir = os.path.normpath(a.mesh)
    mesh_name = base(mesh_dir)
    stem = mesh_name[:-7] if mesh_name.endswith('.tifxyz') else mesh_name
    out_png = a.out or os.path.join(a.out_dir, stem + '.png')
    out_dir = os.path.dirname(os.path.abspath(out_png))
    ostem = os.path.splitext(base(out_png))[0]
    side_json = os.path.join(out_dir, ostem + '.json')
    key_png = os.path.join(out_dir, ostem + '_letter_key.png')
    sizes_csv = a.sizes_csv or os.path.join(out_dir, 'letter_sizes.csv')
    comp_ct = os.path.join(out_dir, ostem + '_ct.png')
    comp_ink = os.path.join(out_dir, ostem + '_ink.png')
    planned = [out_png, side_json]
    if a.letters:
        planned.append(sizes_csv)
        if a.letter_markers == 'key':
            planned.append(key_png)
    if a.write_components:
        planned += [comp_ct] + ([comp_ink] if a.ink else [])
    exist = [p for p in planned if os.path.exists(p)]
    if exist and not a.force:
        raise SystemExit('outputs exist (use --force): ' + ', '.join(base(p) for p in exist))
    command = reduced_command(sys.argv[1:] if argv is None else argv, a, out_png)
    pats = None
    if a.forbid_words:                          # publication check, before anything is written
        pats = load_word_list(a.forbid_words)
        items = [('mesh folder name', mesh_name)] + mesh_text_files(mesh_dir)
        items += [('input file name', base(p)) for p in [a.ct, a.umbilicus, a.ink_stats, a.rows, a.letters,
                                                         a.area_json] + list(a.ink) if p]
        items += [('output file name', base(p)) for p in planned]
        items += [('caption', t) for t in [a.title, a.scroll, a.volume_id] + list(a.note) + list(a.ink_names or [])]
        for p, key in ((a.rows, 'rows'), (a.letters, 'letters')):
            if p:
                for e in json.load(open(p)).get(key, []):
                    items.append((f'{key} label', f"{e.get('label', '')} {e.get('row', '')}"))
        if a.ink_stats:
            items.append(('ink-stats field "surface"', str(json.load(open(a.ink_stats)).get('surface', ''))))
        items.append(('recorded command', command))
        hits = word_hits(pats, items)
        if hits:
            raise SystemExit('publication check failed, nothing written: ' + '; '.join(hits))
    os.makedirs(out_dir, exist_ok=True)
    side = dict(schema='make_submission_image/1', scroll=a.scroll, volume_id=a.volume_id, voxel_size_um=a.voxel_um)

    # ---------------------------------------------------------- mesh, orientation
    X, Y, Z, ok, sc = load_mesh(mesh_dir)
    mesh_files = sorted(f for f in os.listdir(mesh_dir) if os.path.isfile(os.path.join(mesh_dir, f)))
    mesh_sha = {f: sha256_file(os.path.join(mesh_dir, f)) for f in mesh_files}
    geo = [(f, mesh_sha[f]) for f in GEOMETRY_FILES if f in mesh_sha]
    side['mesh'] = dict(name=mesh_name, scale=sc, nodes_hw=list(X.shape), valid_nodes=int(ok.sum()),
                        geometry=[dict(file=f, sha256=h) for f, h in geo],
                        geometry_note='the image depends only on these files and on the field "scale" of meta.json; '
                                      'the rest of meta.json and any other file in the mesh folder change no pixel',
                        files=[dict(file=f, sha256=mesh_sha[f]) for f in mesh_files])
    if a.geometry_sums:
        side['mesh']['geometry_check'] = [check_geometry(p, mesh_name, geo) for p in a.geometry_sums]

    orient = None
    if a.umbilicus:
        umb = load_umbilicus(a.umbilicus)
        _, orient = measure_orientation(X, Y, Z, ok, umb)
        orient['umbilicus'] = dict(file=base(a.umbilicus), sha256=sha256_file(a.umbilicus))
        for k, v in (('flip_lr', a.flip_lr), ('flip_ud', a.flip_ud)):
            if v is not None and bool(v) != orient[k]:
                raise SystemExit(f'--{k.replace("_", "-")} {v} contradicts the measured orientation ({k} = '
                                 f'{orient[k]}); remove the flag or check the mesh/umbilicus')
        if orient['normal_dot_outward_median'] is not None and orient['normal_dot_outward_median'] < 0:
            warn('the render normal points INWARD on this mesh (median n.r < 0): positive d is inward here')
    else:
        if a.flip_lr is None or a.flip_ud is None:
            raise SystemExit('give --umbilicus (measured orientation) or both --flip-lr and --flip-ud')
        orient = dict(source='given on the command line', flip_lr=bool(a.flip_lr), flip_ud=bool(a.flip_ud))
    side['orientation'] = orient
    off = tuple(int(v) for v in a.render_offset.split(','))

    # ---------------------------------------------------------- CT surface volume, area
    st = open_surface(a.ct)
    H, W = int(st.shape[1]), int(st.shape[2])
    exp_hw = (int(round(X.shape[0] / sc)), int(round(X.shape[1] / sc)))
    if off == (0, 0) and (H, W) != exp_hw:
        warn(f'surface volume is {H} x {W} px but the mesh renders to {exp_hw[0]} x {exp_hw[1]} px; if the volume is a '
             f'crop, give --render-offset')
    fr = Frame(H, W, orient['flip_lr'], orient['flip_ud'])
    if a.area_json:
        j = json.load(open(a.area_json))
        rr = j.get('raw_render_px') or j.get('region', {}).get('raw_render_px')
        if not rr:
            raise SystemExit(f'{base(a.area_json)}: no raw_render_px')
        c0, r0, c1, r1 = int(rr['col0']), int(rr['row0']), int(rr['col1']), int(rr['row1'])
        area_src = dict(source='area JSON', file=base(a.area_json), sha256=sha256_file(a.area_json))
    elif a.area:
        v = [int(round(float(t))) for t in a.area.split(',')]
        if len(v) != 4:
            raise SystemExit('--area needs x0,y0,x1,y1')
        if a.area_frame == 'reading':
            c0, r0, c1, r1 = fr.rect_reading_to_raw(*v)
        else:
            c0, r0, c1, r1 = v
        area_src = dict(source='command line', frame=a.area_frame, values=v)
    else:
        raise SystemExit('give --area or --area-json')
    if not (0 <= c0 < c1 <= W and 0 <= r0 < r1 <= H):
        raise SystemExit(f'area raw cols {c0}..{c1}, rows {r0}..{r1} is empty or outside the render ({W} x {H})')
    rx0, ry0, rx1, ry1 = fr.rect_raw_to_reading(c0, r0, c1, r1)
    w, h = c1 - c0, r1 - r0
    mm = a.voxel_um / 1000.0
    cm2 = w * h * (a.voxel_um * 1e-4) ** 2
    if cm2 > a.max_cm2 + 1e-9:
        warn(f'area {w * mm:.2f} x {h * mm:.2f} mm = {cm2:.4f} cm2 is larger than {a.max_cm2} cm2')
    layers = parse_layers(a.ct_layer)
    print(f'area: raw cols {c0}..{c1}, rows {r0}..{r1}; reading x {rx0}..{rx1}, y {ry0}..{ry1}; '
          f'{w * mm:.2f} x {h * mm:.2f} mm = {cm2:.4f} cm2', flush=True)
    valid_raw, ct_raw, lay = read_area(st, r0, r1, c0, c1, layers)

    # ---------------------------------------------------------- ink maps and statistics
    stats = json.load(open(a.ink_stats)) if a.ink_stats else None
    maps = []
    if a.ink_names and len(a.ink_names) != len(a.ink):
        raise SystemExit('--ink-names needs one name per --ink file')
    for i, p in enumerate(a.ink):
        info = identify_map(p, a.ink_names[i] if a.ink_names else None)
        info['sha256'] = sha256_file(p)
        info['path'] = p
        maps.append(info)
    if len(maps) > 1 and not a.ensemble:
        raise SystemExit('several --ink maps: add --ensemble (or give one map)')
    if len({m['model'] for m in maps}) != len(maps):
        raise SystemExit('two --ink maps have the same model: ' + ', '.join(m['model'] for m in maps))
    blind = [m for m in maps if m['direction'] == 'forward']
    if blind and not a.allow_blind:
        raise SystemExit('blind-side (forward) map(s) given: ' + ', '.join(m['file'] for m in blind) +
                         '; the image uses the reading side (_reverse). Use --allow-blind for a control image.')
    if blind and not stats:
        raise SystemExit('blind-side maps need --ink-stats: they are shown with the reading side\'s statistics')
    if len({m['direction'] for m in maps}) > 1:
        raise SystemExit('mixed reading-side and blind-side maps')
    depths = sorted({str(m['depth']) for m in maps})
    if len(depths) > 1:
        warn('ink maps at different depths: ' + ', '.join(f"{m['model']} d={m['depth']}" for m in maps))
    # canonical model order (float32 sums as in ensemble_maps.py), unknown names after
    maps.sort(key=lambda m: (MODEL_ORDER.index(m['model']) if m['model'] in MODEL_ORDER else 99, m['model']))

    need_full = (maps and not stats) or (a.ct_stretch == 'auto' and not (stats and 'ct' in stats))
    valid_full = ct_hist = None
    if need_full:
        print('reading the whole surface volume (valid mask / statistics) ...', flush=True)
        valid_full, ct_hist = full_pass(st)
        if not np.array_equal(valid_full[r0:r1, c0:c1], valid_raw):
            raise SystemExit('internal error: valid mask of the area differs between the two reads')
    if stats is not None:
        if stats.get('H') not in (None, H) or stats.get('W') not in (None, W):
            raise SystemExit(f'--ink-stats is for a {stats.get("H")} x {stats.get("W")} surface, not {H} x {W}')
        if stats.get('surface') and stats['surface'] != base(a.ct):
            warn(f'--ink-stats was computed for {stats["surface"]}, the CT is {base(a.ct)}')

    ink_u8 = None
    ink_desc = None
    norm = None
    if maps:
        sub = None
        if not stats:
            sub = np.zeros((H, W), bool)
            sub[SUB // 2::SUB, SUB // 2::SUB] = True
            sub &= valid_full
        acc = None
        subacc = None
        per_model = {}
        for m in maps:
            M = read_map(m['path'], (H, W))
            if stats:
                sm = stats.get('models', {}).get(m['model'])
                if not sm or 'mean' not in sm:
                    raise SystemExit(f"--ink-stats has no statistics for model {m['model']}")
                s = dict(p1=sm['p1'], p99_5=sm['p99_5'], mean=sm['mean'], sd=sm['sd'],
                         source='ink-stats (reading side, pooled over depths ' +
                                f"{min(sm.get('depths', [0]))}..{max(sm.get('depths', [0]))})")
            else:
                s = stats_from_map(M, valid_full, m['villa'])
                s['source'] = 'this map only (valid pixels of the whole render)'
            per_model[m['model']] = s
            A = M[r0:r1, c0:c1]
            if a.ensemble:
                z = (A - s['mean']) / s['sd']
                acc = z if acc is None else acc + z
                if sub is not None:
                    zs = (M[sub] - s['mean']) / s['sd']
                    subacc = zs if subacc is None else subacc + zs
            else:
                acc = A
            del M
        if a.ensemble:
            E = acc / len(maps)
            if stats:
                ens = stats.get('ensemble', {})
                if sorted(ens.get('models', [])) != sorted(m['model'] for m in maps) or ens.get('p1') is None:
                    raise SystemExit(f"--ink-stats ensemble is over {ens.get('models')}, the maps are "
                                     f"{[m['model'] for m in maps]}: the stretch would not apply")
                lo, hi = ens['p1'], ens['p99_5']
                esrc = 'ink-stats (fixed grid, every 8th row and column, all depths of the reading side)'
            else:
                lo, hi = (float(x) for x in np.percentile(subacc / len(maps), [P_LO, P_HI]))
                esrc = 'these maps (fixed grid, every 8th row and column, valid pixels)'
            norm = dict(mode='ensemble', models=[m['model'] for m in maps], per_model=per_model,
                        ensemble_stretch=dict(p1=lo, p99_5=hi, source=esrc),
                        rule='z = (map - mean) / sd per model; ensemble = mean of the z-scores; '
                             'u = clip((ensemble - p1) / (p99_5 - p1), 0, 1), 8 bit')
            X8 = E
        else:
            s = per_model[maps[0]['model']]
            lo, hi = s['p1'], s['p99_5']
            norm = dict(mode='single model', models=[maps[0]['model']], per_model=per_model,
                        rule='u = clip((map - p1) / (p99_5 - p1), 0, 1), 8 bit')
            X8 = acc
        ink_u8 = (np.clip((X8 - lo) / max(hi - lo, 1e-9), 0, 1) * 255).astype(np.uint8)
        ink_u8[~valid_raw] = 0
        norm['display_range'] = dict(lo=lo, hi=hi)
        sidetxt = 'reading side' if not blind else 'BLIND side (shown with the reading side statistics)'
        dtxt = ', '.join(sorted({f"d = {m['depth']}" if m['depth'] is not None else 'depth not in the file name'
                                 for m in maps}))
        if a.ensemble:
            ink_desc = (f"Ink: ensemble of {len(maps)} models ({', '.join(m['model'] for m in maps)}), mean of the "
                        f"per-model z-scores, {sidetxt}, {dtxt}")
        else:
            ink_desc = f"Ink: model {maps[0]['model']}, {sidetxt}, {dtxt}"

    # CT stretch
    cs = a.ct_stretch
    if cs == 'auto':
        if stats and 'ct' in stats:
            ct_lo, ct_hi = stats['ct']['p1'], stats['ct']['p99_5']
            ct_src = 'ink-stats: p1..p99.5 of the valid pixels of layers 18..48'
        else:
            ct_lo, ct_hi = pct_hist(ct_hist, np.arange(256, dtype=float), [P_LO, P_HI])
            ct_src = 'p1..p99.5 of the valid pixels of layers 18..48 (whole render)'
    elif cs == 'area':
        v = ct_raw[valid_raw]
        ct_lo, ct_hi = (float(x) for x in np.percentile(v, [P_LO, P_HI])) if v.size else (0.0, 255.0)
        ct_src = 'p1..p99.5 of the shown CT within the area (valid pixels)'
    else:
        ct_lo, ct_hi = (float(t) for t in cs.split(','))
        ct_src = 'given on the command line'
    ct_u8 = (np.clip((ct_raw - ct_lo) / max(ct_hi - ct_lo, 1e-9), 0, 1) * 255).astype(np.uint8)
    ct_u8[~valid_raw] = 0

    # ---------------------------------------------------------- compose (reading orientation)
    valid = fr.to_reading(valid_raw)
    ct_r = fr.to_reading(ct_u8)
    img = np.repeat(ct_r[..., None], 3, -1).astype(np.float32)
    if a.ct_dim != 1.0:                # dimmed CT (e.g. --overlay-style dimmed-ct): the grey times --ct-dim
        img *= np.float32(a.ct_dim)
    lut = colormap_lut(a.cmap)
    if ink_u8 is not None:
        ink_r = fr.to_reading(ink_u8)
        u = ink_r.astype(np.float32) / 255.0
        alpha = a.alpha * np.clip((u - a.threshold) / max(a.full - a.threshold, 1e-6), 0, 1)
        col = lut[ink_r].astype(np.float32)
        if a.blend == 'tint':          # keep the CT texture inside the ink: colour scaled by the CT brightness
            col *= (a.tint_floor + (1 - a.tint_floor) * ct_r.astype(np.float32) / 255.0)[..., None]
        img = img * (1 - alpha[..., None]) + col * alpha[..., None]
    img[~valid] = 0
    panel = np.clip(np.rint(img), 0, 255).astype(np.uint8)

    # ---------------------------------------------------------- annotations (area coordinates, reading orientation)
    rows, rows_frame, letters, letters_frame = [], None, [], None
    if a.rows:
        rows, rows_frame, _ = load_annotations(a.rows, 'rows', fr, (rx0, ry0))
    if a.letters:
        letters, letters_frame, _ = load_annotations(a.letters, 'letters', fr, (rx0, ry0))
    extents = None
    if any('follows_letters' in r for r in rows):
        extents = derive_follow_rows(rows, letters, fr.to_reading(ink_u8) if ink_u8 is not None else None, (h, w),
                                     a.row_thickness, int(math.ceil(a.threshold * 255)))
    dash = tuple(float(t) for t in a.row_dash.split(',')) if a.row_dash else None
    row_col = parse_color(a.row_color)
    checks = {}
    if rows:
        rm = np.zeros((h, w), np.uint8)
        draw_rows(rm, rows, 0, 0, 255, a.row_thickness, dash, aa=False)
        rmask = rm > 0
        checks['row_pixels'] = int(rmask.sum())
        for r in rows:
            pts = row_points(r)
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            if min(xs) < 0 or min(ys) < 0 or max(xs) > w or max(ys) > h:
                warn(f"row {r['label']} extends outside the area")
        if letters:
            lm = np.zeros((h, w), bool)
            for L in letters:
                x0, y0, x1, y1 = (int(round(v)) for v in L['box'])
                lm[max(y0, 0):max(y1, 0), max(x0, 0):max(x1, 0)] = True
            n_in = int((rmask & lm).sum())
            checks['row_pixels_inside_letter_boxes'] = n_in
            if extents is not None:           # derived rows: checked against the letter extents; others as before
                plain = extent_checks(checks, rows, extents, (h, w), a.row_thickness, dash)
                rp = np.zeros((h, w), np.uint8)
                draw_rows(rp, plain, 0, 0, 255, a.row_thickness, dash, aa=False)
                n_in = int(((rp > 0) & lm).sum())
            if n_in:
                warn(f'{n_in} row-line pixels lie inside letter boxes (rows should not cover letters)')
        if ink_u8 is not None:
            strong = fr.to_reading(ink_u8) >= int(math.ceil(a.threshold * 255))
            fr_on = (rmask & strong).sum() / max(rmask.sum(), 1)
            checks['row_pixels_on_ink_above_threshold_fraction'] = fmt(fr_on, 4)
            if fr_on > 0.02:
                warn(f'{100 * fr_on:.1f} % of the row-line pixels lie on ink above the threshold: check that the rows '
                     f'do not run over letters')
            checks['area_ink_above_threshold_fraction'] = fmt((strong & valid).sum() / max(valid.sum(), 1), 4)
    for L in letters:
        x0, y0, x1, y1 = L['box']
        if x0 < 0 or y0 < 0 or x1 > w or y1 > h:
            warn(f"letter {L['label']} box extends outside the area")

    # ---------------------------------------------------------- canvas
    fs = a.font_scale
    th1 = max(1, int(round(2 * fs / 1.3)))
    lh = int(round(34 * fs))                               # line height
    px_cm = 10000.0 / a.voxel_um
    bar = int(round(px_cm))
    label_w = max([text_size(f"row {r['label']}", fs, th1)[0] for r in rows] + [0]) + (40 if rows else 0)
    left = max(40, label_w + 30)
    right = 40
    legend_w = 520 if ink_u8 is not None else 0
    min_w = bar + 80 + legend_w + (60 if legend_w else 0)
    Wc = max(left + w + right, left + min_w + right)
    text_w = Wc - 2 * 30
    title = a.title or f'{a.scroll} | mesh {stem} | reading orientation'
    bg = f"Background: CT layer {layers[0]} (d = {layers[0] - MID})" if len(layers) == 1 else \
        f"Background: CT, mean of layers {layers[0]}..{layers[-1]} (d = {layers[0] - MID}..{layers[-1] - MID})"
    bg += f" of the 66-layer surface volume | volume {a.volume_id}, {a.voxel_um:g} um voxels"
    cap = [ink_desc or 'Ink: none (CT only)', bg,
           f"Area: {w} x {h} px = {w * mm:.2f} x {h * mm:.2f} mm = {cm2:.2f} cm2 "
           f"(reading-orientation px x {rx0}-{rx1}, y {ry0}-{ry1})"]
    if a.caption == 'compact':
        cap = [compact_ink_line(a, maps, blind, layers),
               f"Area: {w} x {h} px = {w * mm:.2f} x {h * mm:.2f} mm = {cm2:.2f} cm2"]
    top_lines = [(ln, fs * 1.15, th1 + 1) for ln in wrap(title, fs * 1.15, th1 + 1, text_w)]
    for c in cap:
        top_lines += [(ln, fs, th1) for ln in wrap(c, fs, th1, text_w)]
    rows_note = []
    if rows:
        kinds = sorted({'baselines' if ('baseline' in r or 'segments' in r) else 'rectangles' for r in rows})
        rows_note = [f"Text rows: {len(rows)}, marked by thin {' and '.join(kinds)} in the image and labels in the "
                     f"left margin. No character is drawn or annotated."]
        if any('segments' in r for r in rows):
            rows_note = [f"Text rows: {len(rows)}, each marked by a thin line just below its letters (derived from "
                         f"the letter boxes and the ink; never over ink or a letter, interrupted where a letter reaches "
                         f"below the line) and a label in the left margin. No character is drawn or annotated."]
    bot_lines = []
    for c in rows_note + a.note:
        bot_lines += [(ln, fs, th1) for ln in wrap(c, fs, th1, text_w)]
    top = 30 + len(top_lines) * lh + 20
    bar_block = int(round(150 * fs / 1.3))
    bottom = 30 + bar_block + len(bot_lines) * lh + 20
    Hc = top + h + bottom
    bgc = (24, 24, 24)
    fg = (235, 235, 235)
    grey = (150, 150, 150)
    canvas = np.empty((Hc, Wc, 3), np.uint8)
    canvas[:] = bgc
    canvas[top:top + h, left:left + w] = panel
    # frame just outside the area
    import cv2
    cv2.rectangle(canvas, (left - 2, top - 2), (left + w + 1, top + h + 1), grey, 1, cv2.LINE_8)
    y = 30
    for s, sc_, t in top_lines:
        y += lh
        put(canvas, s, 30, y - int(0.25 * lh), sc_, fg, t)
    # rows: lines in the area, labels + ticks in the left margin
    if rows:
        draw_rows(canvas, rows, left, top, row_col, a.row_thickness, dash)
        for r in rows:
            yy = int(round(row_anchor_y(r))) + top
            s = f"row {r['label']}"
            tw, tht, _ = text_size(s, fs, th1)
            cv2.line(canvas, (left - 28, yy), (left - 6, yy), row_col, a.row_thickness, cv2.LINE_AA)
            put(canvas, s, left - 34 - tw, yy + tht // 2, fs, row_col, th1)
    # scale bar
    yb = top + h + 30 + int(round(60 * fs / 1.3))
    xb = left
    lbl = '1 cm'
    tw, tht, _ = text_size(lbl, fs, th1)
    put(canvas, lbl, xb + (bar - tw) // 2, yb - 18, fs, fg, th1)
    # bar and end ticks all within columns xb .. xb + bar - 1: exactly `bar` pixels wide
    cv2.rectangle(canvas, (xb, yb), (xb + bar - 1, yb + 11), fg, -1)
    cv2.rectangle(canvas, (xb, yb - 8), (xb + 2, yb + 19), fg, -1)
    cv2.rectangle(canvas, (xb + bar - 3, yb - 8), (xb + bar - 1, yb + 19), fg, -1)
    small = fs * 0.7
    st_ = f'{bar} px = 10 mm at {a.voxel_um:g} um/px'
    put(canvas, st_, xb, yb + 19 + int(34 * small), small, grey, max(1, th1 - 1))
    # colour legend: the ink colour as it appears over mid-grey CT
    legend = None
    if ink_u8 is not None:
        lx = xb + bar + 60
        lw, lhh = legend_w, 24
        u = np.linspace(0, 1, lw, dtype=np.float32)
        u8 = (u * 255).astype(np.uint8)
        al = a.alpha * np.clip((u - a.threshold) / max(a.full - a.threshold, 1e-6), 0, 1)
        tint = (a.tint_floor + (1 - a.tint_floor) * 128 / 255.0) if a.blend == 'tint' else 1.0
        colr = lut[u8].astype(np.float32) * tint * al[:, None] + 128 * (1 - al[:, None])
        styled = a.overlay_style != 'default' or a.ct_dim != 1.0
        if styled:
            colr = legend_ramp(a, lut, lw)
        canvas[yb - 6:yb - 6 + lhh, lx:lx + lw] = np.clip(np.rint(colr), 0, 255).astype(np.uint8)[None]
        cv2.rectangle(canvas, (lx - 1, yb - 7), (lx + lw, yb - 6 + lhh), grey, 1)
        lo_, hi_ = norm['display_range']['lo'], norm['display_range']['hi']
        val = (lambda q: lo_ + q * (hi_ - lo_))
        name = 'ensemble z-score' if a.ensemble else f"{maps[0]['model']} value"
        put(canvas, (f'ink ({name}) over dimmed CT' if a.ct_dim != 1.0 else f'ink ({name}) over grey') if styled else
            f'ink ({name}), over grey', lx, yb - 18, small, fg, max(1, th1 - 1))
        for q in ((a.threshold, a.full) if styled else (a.threshold, 1.0)):
            xx = lx + int(round(q * (lw - 1)))
            cv2.line(canvas, (xx, yb - 6 + lhh), (xx, yb - 6 + lhh + 8), fg, 1)
            s = f'{val(q):.2f}'
            tw2 = text_size(s, small, max(1, th1 - 1))[0]
            put(canvas, s, min(xx - tw2 // 2, lx + lw - tw2), yb + lhh + 10 + int(22 * small), small, grey,
                max(1, th1 - 1))
        legend = dict(threshold_value=fmt(val(a.threshold), 4), full_value=fmt(val(a.full), 4),
                      top_value=fmt(val(1.0), 4))
    y = top + h + 30 + bar_block
    for s, sc_, t in bot_lines:
        y += lh
        put(canvas, s, 30, y - int(0.25 * lh), sc_, fg, t)

    # ---------------------------------------------------------- letter sizes and markers
    marker_pos = []
    if letters:
        occupied = [tuple(L['box']) for L in letters]
        rad = int(round(18 * fs / 1.3))
        gap = 8
        for i, L in enumerate(letters, 1):
            x0, y0, x1, y1 = L['box']
            cx, cy = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
            d = rad + gap
            cands = [(cx, y0 - d), (cx, y1 + d), (x0 - d, cy), (x1 + d, cy), (x0 - d, y0 - d), (x1 + d, y0 - d),
                     (x0 - d, y1 + d), (x1 + d, y1 + d), (cx, y0 - 2 * d), (cx, y1 + 2 * d)]
            chosen = None
            # first choice inside the area, second choice in the margin next to it (never on a letter box)
            for lim in ((0, 0, w, h), (-left + 4, -top + 4, w + right - 4, h + 20)):
                for px, py in cands:
                    bb = (px - rad - 2, py - rad - 2, px + rad + 2, py + rad + 2)
                    if any(bb[0] < o[2] and o[0] < bb[2] and bb[1] < o[3] and o[1] < bb[3] for o in occupied):
                        continue
                    if bb[0] < lim[0] or bb[1] < lim[1] or bb[2] > lim[2] or bb[3] > lim[3]:
                        continue
                    chosen = (px, py)
                    break
                if chosen is not None:
                    break
            if chosen is None:
                warn(f"no free place for marker {letter_number(L, i)} ({L['label']}) outside all letter boxes; "
                     f"marker omitted")
                marker_pos.append(None)
                continue
            occupied.append((chosen[0] - rad, chosen[1] - rad, chosen[0] + rad, chosen[1] + rad))
            marker_pos.append(chosen)

    def draw_markers(img):
        for i, mp in zip([letter_number(L_, k) for k, L_ in enumerate(letters, 1)], marker_pos):
            if mp is None:
                continue
            cx, cy = int(round(mp[0] + left)), int(round(mp[1] + top))
            rad = int(round(18 * fs / 1.3))
            cv2.circle(img, (cx, cy), rad, (0, 0, 0), -1, cv2.LINE_AA)
            cv2.circle(img, (cx, cy), rad, (0, 215, 255), 2, cv2.LINE_AA)
            s = str(i)
            ss = fs * 0.75
            tw, tht, _ = text_size(s, ss, th1)
            put(img, s, cx - tw // 2, cy + tht // 2, ss, (0, 215, 255), th1)

    main_img = canvas.copy()
    if letters and a.letter_markers == 'on':
        draw_markers(main_img)

    # ---------------------------------------------------------- write
    def write_png(path, arr):
        if not cv2.imwrite(path, arr, [cv2.IMWRITE_PNG_COMPRESSION, 6]):
            raise SystemExit(f'cannot write {path}')
        return dict(file=base(path), sha256=sha256_file(path), width_px=int(arr.shape[1]),
                    height_px=int(arr.shape[0]))

    if pats:
        hits = word_hits(pats, [('caption', s) for s, _, _ in top_lines + bot_lines] +
                         [('row label', r['label']) for r in rows] + [('warning', t) for t in WARNINGS])
        if hits:
            raise SystemExit('publication check failed, nothing written: ' + '; '.join(hits))
    outputs = dict(image=write_png(out_png, main_img))
    outputs['image']['data_panel'] = dict(x=left, y=top, width=w, height=h,
                                          note='image pixels of the area; 1 image pixel = 1 render pixel')
    if letters:
        with open(sizes_csv, 'w', newline='') as fh:
            wr = csv.writer(fh, lineterminator='\n')
            ext = any('reading' in L or 'class' in L for L in letters)
            wr.writerow(['id', 'label'] + (['reading', 'class'] if ext else []) + ['row', 'width_px', 'height_px',
                                                                                  'width_mm', 'height_mm',
                                                                                  'x0', 'y0', 'x1', 'y1'])
            for i, L in enumerate(letters, 1):
                x0, y0, x1, y1 = L['box']
                wr.writerow([letter_number(L, i), L['label']] + ([leiden(L), L.get('class', '')] if ext else []) +
                            [L['row'], f'{x1 - x0:g}', f'{y1 - y0:g}', f'{(x1 - x0) * mm:.2f}',
                             f'{(y1 - y0) * mm:.2f}', f'{x0:g}', f'{y0:g}', f'{x1:g}', f'{y1:g}'])
        outputs['letter_sizes_csv'] = dict(file=base(sizes_csv), sha256=sha256_file(sizes_csv),
                                           note='box coordinates in area pixels (reading orientation, origin at the '
                                                'top left of the area; x1, y1 exclusive)')
        if a.letter_markers == 'key':
            kimg = canvas.copy()
            draw_markers(kimg)
            knote = wrap(f'Key image: the numbers are the ids in {base(sizes_csv)} (letter width and height in px and '
                         f'mm). They are placed outside the measured letters; the image itself carries no markers.',
                         fs, th1, text_w)
            strip = np.empty((len(knote) * lh + 20, Wc, 3), np.uint8)
            strip[:] = bgc
            for i, s in enumerate(knote):
                put(strip, s, 30, (i + 1) * lh - int(0.25 * lh), fs, (0, 215, 255), th1)
            kleg = key_legend_strip(letters, Wc, fs, th1, lh, bgc, (0, 215, 255))
            outputs['letter_key_image'] = write_png(key_png, np.vstack([kimg, strip] + ([kleg] if kleg is not None
                                                                                        else [])))
    if a.write_components:
        outputs['component_ct'] = write_png(comp_ct, ct_r)
        if ink_u8 is not None:
            outputs['component_ink'] = write_png(comp_ink, fr.to_reading(ink_u8))

    # ---------------------------------------------------------- area geometry from the mesh
    area = dict(raw_render_px=dict(col0=c0, row0=r0, col1=c1, row1=r1),
                reading_px=dict(x0=rx0, y0=ry0, x1=rx1, y1=ry1),
                note='x1/col1 and y1/row1 exclusive; reading = raw render mirrored as in "orientation"',
                given=area_src, width_px=w, height_px=h, width_mm=fmt(w * mm), height_mm=fmt(h * mm),
                area_cm2=fmt(cm2, 4), limit_cm2=a.max_cm2, within_limit=bool(cm2 <= a.max_cm2 + 1e-9),
                valid_fraction=fmt(valid_raw.mean(), 4),
                papyrus_cm2_nominal=fmt(valid_raw.sum() * (a.voxel_um * 1e-4) ** 2, 4))
    rows_i = np.arange(r0, r1)
    cols_i = np.arange(c0, c1)
    Zp = bilinear_nodes(np.where(ok, Z, np.nan), rows_i[::4], cols_i[::4], sc, off)
    vs = valid_raw[::4, ::4] & np.isfinite(Zp)
    if vs.any():
        area['z_voxels'] = dict(min=fmt(Zp[vs].min(), 1), max=fmt(Zp[vs].max(), 1),
                                note='mesh z of the valid pixels (every 4th pixel)')
    if a.umbilicus:
        Tp = bilinear_nodes(theta_by_column(X, Y, Z, ok, load_umbilicus(a.umbilicus)), rows_i[::4], cols_i[::4], sc, off)
        vt = vs & np.isfinite(Tp)
        if vt.any():
            area['theta_deg'] = dict(min=fmt(Tp[vt].min(), 2), max=fmt(Tp[vt].max(), 2),
                                     min_mod360=fmt(Tp[vt].min() % 360, 2), max_mod360=fmt(Tp[vt].max() % 360, 2),
                                     note='angle around the umbilicus per node, unwrapped along the mesh '
                                          'columns (circular mean per column), bilinear per pixel (every 4th px)')
    A = quad_area_px(X, Y, Z, ok, sc)
    qi = np.clip(((off[0] + rows_i) * sc).astype(int), 0, A.shape[0] - 1)
    qj = np.clip(((off[1] + cols_i) * sc).astype(int), 0, A.shape[1] - 1)
    Aq = A[np.ix_(qi, qj)]
    mA = valid_raw & np.isfinite(Aq)
    if mA.any():
        tot = float(Aq[mA].sum()) + float(np.median(Aq[mA])) * int((valid_raw & ~np.isfinite(Aq)).sum())
        area['papyrus_cm2_mesh3d'] = fmt(tot * (a.voxel_um * 1e-4) ** 2, 4)
        area['mesh_area_ratio_3d_to_flat'] = fmt(tot / max(int(valid_raw.sum()), 1), 4)
    side['area'] = area

    # ---------------------------------------------------------- sidecar
    ct_info = dict(file=base(a.ct), shape=[N_LAYERS, H, W], layers=layers, depths=[k - MID for k in layers],
                   depth_rule='d = layer - 33; d = 0 is the layer just outside the mesh surface; positive d along the '
                              'render normal (outward when orientation.normal_dot_outward_median > 0)',
                   stretch=dict(lo=ct_lo, hi=ct_hi, source=ct_src), valid_rule='all 66 layers > 0',
                   area_layers_sha256={str(k): sha256_array(lay[k]) for k in layers},
                   area_valid_mask_sha256=sha256_array(np.packbits(valid_raw)),
                   area_data_note='sha256 of the decoded uint8 layers (raw orientation, area only, C order) and of '
                                  'np.packbits(valid mask)')
    if not a.skip_tree_hash:
        print('hashing the surface volume files ...', flush=True)
        ct_info.update(sha256_tree(a.ct))
    side['ct'] = ct_info
    side['ink'] = None if not maps else dict(
        maps=[{k: v for k, v in m.items() if k != 'path'} for m in maps], normalisation=norm,
        stats_file=dict(file=base(a.ink_stats), sha256=sha256_file(a.ink_stats)) if a.ink_stats else None)
    side['overlay'] = overlay_record(a, legend)
    side['scale_bar'] = dict(length_px=bar, px_per_cm=fmt(px_cm, 3), label='1 cm')
    side['rows'] = None if not a.rows else dict(file=base(a.rows), sha256=sha256_file(a.rows), frame=rows_frame,
                                                rows_area_px=rows, color_rgb=a.row_color,
                                                thickness_px=a.row_thickness, dash=a.row_dash or 'solid')
    side['letters'] = None if not a.letters else dict(
        file=base(a.letters), sha256=sha256_file(a.letters), frame=letters_frame, markers=a.letter_markers,
        letters_area_px=[sidecar_letter(L, i) for i, L in enumerate(letters, 1)],
        marker_centres_area_px=[None if p is None else [fmt(p[0], 1), fmt(p[1], 1)] for p in marker_pos])
    side['checks'] = checks
    side['warnings'] = WARNINGS
    side['outputs'] = outputs
    import zarr
    import tifffile
    side['software'] = dict(python=sys.version.split()[0], numpy=np.__version__, opencv=cv2.__version__,
                            zarr=zarr.__version__, tifffile=tifffile.__version__)
    side['command'] = command
    side['command_note'] = 'paths reduced to file names' + (
        '; the values of --geometry-sums and --forbid-words are not recorded'
        if (a.geometry_sums or a.forbid_words) else '')
    if pats:
        side['publication_check'] = dict(word_list_entries=len(pats), hits=0,
                                         checked='mesh folder name, text files of the mesh, input and output file '
                                                 'names, captions, labels, warnings, the command and this sidecar')
    txt = json.dumps(side, indent=1, ensure_ascii=False) + '\n'
    if pats:
        hits = word_hits(pats, [('sidecar', txt)])
        if hits:
            raise SystemExit(f'publication check failed on the sidecar: {"; ".join(hits)}. The image files were '
                             f'written, the sidecar {base(side_json)} was NOT; rename the inputs and rerun with --force')
    with open(side_json, 'w') as fh:
        fh.write(txt)
    print(f'wrote {base(out_png)} ({main_img.shape[1]} x {main_img.shape[0]} px), {base(side_json)}'
          + (f', {base(sizes_csv)}' if letters else '') + (f', {base(key_png)}' if 'letter_key_image' in outputs
                                                          else ''), flush=True)
    if WARNINGS:
        print(f'{len(WARNINGS)} warning(s), listed in {base(side_json)}', flush=True)
    return side


# ------------------------------------------------------------------ two-panel mode
def panel_mesh(a, mesh_dir, umb):
    """one panel: mesh, identity and measured orientation (as in the one-mesh mode)."""
    X, Y, Z, ok, sc = load_mesh(mesh_dir)
    name = base(mesh_dir)
    files = sorted(f for f in os.listdir(mesh_dir) if os.path.isfile(os.path.join(mesh_dir, f)))
    sha = {f: sha256_file(os.path.join(mesh_dir, f)) for f in files}
    geo = [(f, sha[f]) for f in GEOMETRY_FILES if f in sha]
    mesh = dict(name=name, scale=sc, nodes_hw=list(X.shape), valid_nodes=int(ok.sum()),
                geometry=[dict(file=f, sha256=h) for f, h in geo],
                geometry_note='the image depends only on these files and on the field "scale" of meta.json; '
                              'the rest of meta.json and any other file in the mesh folder change no pixel',
                files=[dict(file=f, sha256=sha[f]) for f in files])
    _, orient = measure_orientation(X, Y, Z, ok, umb)
    orient['umbilicus'] = dict(file=base(a.umbilicus), sha256=sha256_file(a.umbilicus))
    for k, v in (('flip_lr', a.flip_lr), ('flip_ud', a.flip_ud)):
        if v is not None and bool(v) != orient[k]:
            raise SystemExit(f'--{k.replace("_", "-")} {v} contradicts the measured orientation of {name} ({k} = '
                             f'{orient[k]}); remove the flag or check the mesh/umbilicus')
    if orient['normal_dot_outward_median'] is not None and orient['normal_dot_outward_median'] < 0:
        warn(f'{name}: the render normal points INWARD on this mesh (median n.r < 0): positive d is inward here')
    return dict(dir=mesh_dir, name=name, stem=name[:-7] if name.endswith('.tifxyz') else name, X=X, Y=Y, Z=Z, ok=ok,
                sc=sc, mesh=mesh, geo=geo, orient=orient, theta=theta_by_column(X, Y, Z, ok, umb))


def panel_render(a, Q, ct_path, ink_paths, stats_path, area_str, off_str, layers, lut):
    """one panel: area, CT, ink and the overlay, computed exactly as in the one-mesh mode."""
    import cv2
    nm = Q['stem']
    off = tuple(int(v) for v in off_str.split(','))
    st = open_surface(ct_path)
    H, W = int(st.shape[1]), int(st.shape[2])
    X, sc = Q['X'], Q['sc']
    exp_hw = (int(round(X.shape[0] / sc)), int(round(X.shape[1] / sc)))
    if off == (0, 0) and (H, W) != exp_hw:
        warn(f'{nm}: surface volume is {H} x {W} px but the mesh renders to {exp_hw[0]} x {exp_hw[1]} px; if the '
             f'volume is a crop, give --render-offset')
    fr = Frame(H, W, Q['orient']['flip_lr'], Q['orient']['flip_ud'])
    v = [int(round(float(t))) for t in area_str.split(',')]
    if len(v) != 4:
        raise SystemExit('--area needs x0,y0,x1,y1')
    if a.area_frame == 'reading':
        c0, r0, c1, r1 = fr.rect_reading_to_raw(*v)
    else:
        c0, r0, c1, r1 = v
    area_src = dict(source='command line', frame=a.area_frame, values=v)
    if not (0 <= c0 < c1 <= W and 0 <= r0 < r1 <= H):
        raise SystemExit(f'{nm}: area raw cols {c0}..{c1}, rows {r0}..{r1} is empty or outside the render ({W} x {H})')
    rx0, ry0, rx1, ry1 = fr.rect_raw_to_reading(c0, r0, c1, r1)
    w, h = c1 - c0, r1 - r0
    mm = a.voxel_um / 1000.0
    cm2 = w * h * (a.voxel_um * 1e-4) ** 2
    print(f'{nm}: area raw cols {c0}..{c1}, rows {r0}..{r1}; reading x {rx0}..{rx1}, y {ry0}..{ry1}; '
          f'{w * mm:.2f} x {h * mm:.2f} mm = {cm2:.4f} cm2', flush=True)
    valid_raw, ct_raw, lay = read_area(st, r0, r1, c0, c1, layers)

    # ink maps and statistics (as in the one-mesh mode)
    stats = json.load(open(stats_path)) if stats_path else None
    maps = []
    if a.ink_names and len(a.ink_names) != len(ink_paths):
        raise SystemExit('--ink-names needs one name per --ink file (of each panel)')
    for i, p in enumerate(ink_paths):
        info = identify_map(p, a.ink_names[i] if a.ink_names else None)
        info['sha256'] = sha256_file(p)
        info['path'] = p
        maps.append(info)
    if len(maps) > 1 and not a.ensemble:
        raise SystemExit('several --ink maps: add --ensemble (or give one map)')
    if len({m['model'] for m in maps}) != len(maps):
        raise SystemExit(f'{nm}: two --ink maps have the same model: ' + ', '.join(m['model'] for m in maps))
    blind = [m for m in maps if m['direction'] == 'forward']
    if blind and not a.allow_blind:
        raise SystemExit('blind-side (forward) map(s) given: ' + ', '.join(m['file'] for m in blind) +
                         '; the image uses the reading side (_reverse). Use --allow-blind for a control image.')
    if blind and not stats:
        raise SystemExit('blind-side maps need --ink-stats: they are shown with the reading side\'s statistics')
    if len({m['direction'] for m in maps}) > 1:
        raise SystemExit(f'{nm}: mixed reading-side and blind-side maps')
    depths = sorted({str(m['depth']) for m in maps})
    if len(depths) > 1:
        warn(f'{nm}: ink maps at different depths: ' + ', '.join(f"{m['model']} d={m['depth']}" for m in maps))
    maps.sort(key=lambda m: (MODEL_ORDER.index(m['model']) if m['model'] in MODEL_ORDER else 99, m['model']))
    need_full = (maps and not stats) or (a.ct_stretch == 'auto' and not (stats and 'ct' in stats))
    valid_full = ct_hist = None
    if need_full:
        print(f'{nm}: reading the whole surface volume (valid mask / statistics) ...', flush=True)
        valid_full, ct_hist = full_pass(st)
        if not np.array_equal(valid_full[r0:r1, c0:c1], valid_raw):
            raise SystemExit('internal error: valid mask of the area differs between the two reads')
    if stats is not None:
        if stats.get('H') not in (None, H) or stats.get('W') not in (None, W):
            raise SystemExit(f'--ink-stats {base(stats_path)} is for a {stats.get("H")} x {stats.get("W")} surface, '
                             f'not {H} x {W}')
        if stats.get('surface') and stats['surface'] != base(ct_path):
            warn(f'--ink-stats was computed for {stats["surface"]}, the CT is {base(ct_path)}')
    ink_u8 = norm = None
    if maps:
        sub = None
        if not stats:
            sub = np.zeros((H, W), bool)
            sub[SUB // 2::SUB, SUB // 2::SUB] = True
            sub &= valid_full
        acc = subacc = None
        per_model = {}
        for m in maps:
            M = read_map(m['path'], (H, W))
            if stats:
                sm = stats.get('models', {}).get(m['model'])
                if not sm or 'mean' not in sm:
                    raise SystemExit(f"--ink-stats {base(stats_path)} has no statistics for model {m['model']}")
                s = dict(p1=sm['p1'], p99_5=sm['p99_5'], mean=sm['mean'], sd=sm['sd'],
                         source='ink-stats (reading side, pooled over depths ' +
                                f"{min(sm.get('depths', [0]))}..{max(sm.get('depths', [0]))})")
            else:
                s = stats_from_map(M, valid_full, m['villa'])
                s['source'] = 'this map only (valid pixels of the whole render)'
            per_model[m['model']] = s
            A = M[r0:r1, c0:c1]
            if a.ensemble:
                z = (A - s['mean']) / s['sd']
                acc = z if acc is None else acc + z
                if sub is not None:
                    zs = (M[sub] - s['mean']) / s['sd']
                    subacc = zs if subacc is None else subacc + zs
            else:
                acc = A
            del M
        if a.ensemble:
            E = acc / len(maps)
            if stats:
                ens = stats.get('ensemble', {})
                if sorted(ens.get('models', [])) != sorted(m['model'] for m in maps) or ens.get('p1') is None:
                    raise SystemExit(f"--ink-stats ensemble is over {ens.get('models')}, the maps are "
                                     f"{[m['model'] for m in maps]}: the stretch would not apply")
                lo, hi = ens['p1'], ens['p99_5']
                esrc = 'ink-stats (fixed grid, every 8th row and column, all depths of the reading side)'
            else:
                lo, hi = (float(x) for x in np.percentile(subacc / len(maps), [P_LO, P_HI]))
                esrc = 'these maps (fixed grid, every 8th row and column, valid pixels)'
            norm = dict(mode='ensemble', models=[m['model'] for m in maps], per_model=per_model,
                        ensemble_stretch=dict(p1=lo, p99_5=hi, source=esrc),
                        rule='z = (map - mean) / sd per model; ensemble = mean of the z-scores; '
                             'u = clip((ensemble - p1) / (p99_5 - p1), 0, 1), 8 bit')
            X8 = E
        else:
            s = per_model[maps[0]['model']]
            lo, hi = s['p1'], s['p99_5']
            norm = dict(mode='single model', models=[maps[0]['model']], per_model=per_model,
                        rule='u = clip((map - p1) / (p99_5 - p1), 0, 1), 8 bit')
            X8 = acc
        ink_u8 = (np.clip((X8 - lo) / max(hi - lo, 1e-9), 0, 1) * 255).astype(np.uint8)
        ink_u8[~valid_raw] = 0
        norm['display_range'] = dict(lo=lo, hi=hi)

    # CT stretch (as in the one-mesh mode)
    cs = a.ct_stretch
    if cs == 'auto':
        if stats and 'ct' in stats:
            ct_lo, ct_hi = stats['ct']['p1'], stats['ct']['p99_5']
            ct_src = 'ink-stats: p1..p99.5 of the valid pixels of layers 18..48'
        else:
            ct_lo, ct_hi = pct_hist(ct_hist, np.arange(256, dtype=float), [P_LO, P_HI])
            ct_src = 'p1..p99.5 of the valid pixels of layers 18..48 (whole render)'
    elif cs == 'area':
        vv = ct_raw[valid_raw]
        ct_lo, ct_hi = (float(x) for x in np.percentile(vv, [P_LO, P_HI])) if vv.size else (0.0, 255.0)
        ct_src = 'p1..p99.5 of the shown CT within the area (valid pixels)'
    else:
        ct_lo, ct_hi = (float(t) for t in cs.split(','))
        ct_src = 'given on the command line'
    ct_u8 = (np.clip((ct_raw - ct_lo) / max(ct_hi - ct_lo, 1e-9), 0, 1) * 255).astype(np.uint8)
    ct_u8[~valid_raw] = 0

    # compose (reading orientation, as in the one-mesh mode)
    valid = fr.to_reading(valid_raw)
    ct_r = fr.to_reading(ct_u8)
    img = np.repeat(ct_r[..., None], 3, -1).astype(np.float32)
    if a.ct_dim != 1.0:                # dimmed CT (e.g. --overlay-style dimmed-ct): the grey times --ct-dim
        img *= np.float32(a.ct_dim)
    ink_r = None
    if ink_u8 is not None:
        ink_r = fr.to_reading(ink_u8)
        u = ink_r.astype(np.float32) / 255.0
        alpha = a.alpha * np.clip((u - a.threshold) / max(a.full - a.threshold, 1e-6), 0, 1)
        col = lut[ink_r].astype(np.float32)
        if a.blend == 'tint':
            col *= (a.tint_floor + (1 - a.tint_floor) * ct_r.astype(np.float32) / 255.0)[..., None]
        img = img * (1 - alpha[..., None]) + col * alpha[..., None]
    img[~valid] = 0
    panel = np.clip(np.rint(img), 0, 255).astype(np.uint8)

    # area geometry from the mesh (as in the one-mesh mode)
    Y_, Z, ok = Q['Y'], Q['Z'], Q['ok']
    area = dict(raw_render_px=dict(col0=c0, row0=r0, col1=c1, row1=r1),
                reading_px=dict(x0=rx0, y0=ry0, x1=rx1, y1=ry1),
                note='x1/col1 and y1/row1 exclusive; reading = raw render mirrored as in "orientation"',
                given=area_src, width_px=w, height_px=h, width_mm=fmt(w * mm), height_mm=fmt(h * mm),
                area_cm2=fmt(cm2, 4), valid_fraction=fmt(valid_raw.mean(), 4),
                papyrus_cm2_nominal=fmt(valid_raw.sum() * (a.voxel_um * 1e-4) ** 2, 4))
    rows_i = np.arange(r0, r1)
    cols_i = np.arange(c0, c1)
    Zp = bilinear_nodes(np.where(ok, Z, np.nan), rows_i[::4], cols_i[::4], sc, off)
    vs = valid_raw[::4, ::4] & np.isfinite(Zp)
    if vs.any():
        area['z_voxels'] = dict(min=fmt(Zp[vs].min(), 1), max=fmt(Zp[vs].max(), 1),
                                note='mesh z of the valid pixels (every 4th pixel)')
    Tp = bilinear_nodes(Q['theta'], rows_i[::4], cols_i[::4], sc, off)
    vt = vs & np.isfinite(Tp)
    if vt.any():
        area['theta_deg'] = dict(min=fmt(Tp[vt].min(), 2), max=fmt(Tp[vt].max(), 2),
                                 min_mod360=fmt(Tp[vt].min() % 360, 2), max_mod360=fmt(Tp[vt].max() % 360, 2),
                                 note='angle around the umbilicus per node, unwrapped along the mesh '
                                      'columns (circular mean per column), bilinear per pixel (every 4th px)')
    Aq_all = quad_area_px(X, Y_, Z, ok, sc)
    qi = np.clip(((off[0] + rows_i) * sc).astype(int), 0, Aq_all.shape[0] - 1)
    qj = np.clip(((off[1] + cols_i) * sc).astype(int), 0, Aq_all.shape[1] - 1)
    Aq = Aq_all[np.ix_(qi, qj)]
    mA = valid_raw & np.isfinite(Aq)
    if mA.any():
        tot = float(Aq[mA].sum()) + float(np.median(Aq[mA])) * int((valid_raw & ~np.isfinite(Aq)).sum())
        area['papyrus_cm2_mesh3d'] = fmt(tot * (a.voxel_um * 1e-4) ** 2, 4)
        area['mesh_area_ratio_3d_to_flat'] = fmt(tot / max(int(valid_raw.sum()), 1), 4)

    ct_info = dict(file=base(ct_path), shape=[N_LAYERS, H, W], layers=layers, depths=[k - MID for k in layers],
                   depth_rule='d = layer - 33; d = 0 is the layer just outside the mesh surface; positive d along the '
                              'render normal (outward when orientation.normal_dot_outward_median > 0)',
                   stretch=dict(lo=ct_lo, hi=ct_hi, source=ct_src), valid_rule='all 66 layers > 0',
                   render_offset=list(off),
                   area_layers_sha256={str(k): sha256_array(lay[k]) for k in layers},
                   area_valid_mask_sha256=sha256_array(np.packbits(valid_raw)),
                   area_data_note='sha256 of the decoded uint8 layers (raw orientation, area only, C order) and of '
                                  'np.packbits(valid mask)')
    if not a.skip_tree_hash:
        print(f'{nm}: hashing the surface volume files ...', flush=True)
        ct_info.update(sha256_tree(ct_path))
    ink_info = None if not maps else dict(
        maps=[{k: v for k, v in m.items() if k != 'path'} for m in maps], normalisation=norm,
        stats_file=dict(file=base(stats_path), sha256=sha256_file(stats_path)) if stats_path else None)
    Q.update(frame=fr, off=off, H=H, W=W, raw_px=(c0, r0, c1, r1), reading_px=(rx0, ry0, rx1, ry1), w=w, h=h,
             cm2=cm2, valid=valid, ct_r=ct_r, ink_r=ink_r, panel=panel, area=area, ct_info=ct_info,
             ink_info=ink_info, maps=maps, blind=blind, norm=norm, st=st)
    return Q


def panel_annotations(path, key, P, place):
    """rows or letters JSON in two-panel mode -> list in composite coordinates, frame, and the entries' panels."""
    j = json.load(open(path))
    frm = j.get('frame', 'composite')
    if frm not in ('composite', 'area', 'reading', 'raw'):
        raise SystemExit(f'{base(path)}: frame must be composite, area, reading or raw (got {frm!r})')

    def which(e):
        if frm == 'composite' and 'panel' not in e and 'mesh' not in e:
            return None
        if 'panel' in e:
            k = int(e['panel']) - 1
            if not 0 <= k < len(P):
                raise SystemExit(f'{base(path)}: panel {e["panel"]} does not exist (1..{len(P)})')
            return k
        if 'mesh' in e:
            nm = str(e['mesh'])
            for k, Q in enumerate(P):
                if nm in (Q['name'], Q['stem']):
                    return k
            raise SystemExit(f'{base(path)}: mesh {nm!r} is not one of the panels')
        raise SystemExit(f'{base(path)}: frame {frm} needs "panel" (1 or 2) or "mesh" in every entry')

    def pt(k, x, y):
        x, y = float(x), float(y)
        if frm == 'composite':
            return [x, y]
        Q = P[k]
        if frm == 'raw':
            x, y = Q['frame'].point_raw_to_reading(x, y)
        if frm in ('raw', 'reading'):
            x, y = x - Q['reading_px'][0], y - Q['reading_px'][1]
        return [x + place[k][0], y + place[k][1]]

    def rect(k, r):
        x0, y0, x1, y1 = (float(v) for v in r)
        if x1 < x0 or y1 < y0:
            raise SystemExit(f'{base(path)}: box {r} has x1 < x0 or y1 < y0')
        if frm == 'composite':
            return [x0, y0, x1, y1]
        Q = P[k]
        if frm == 'raw':
            x0, y0, x1, y1 = Q['frame'].rect_raw_to_reading(x0, y0, x1, y1)
        if frm in ('raw', 'reading'):
            x0, x1, y0, y1 = x0 - Q['reading_px'][0], x1 - Q['reading_px'][0], y0 - Q['reading_px'][1], \
                y1 - Q['reading_px'][1]
        ox, oy = place[k]
        return [x0 + ox, y0 + oy, x1 + ox, y1 + oy]

    out = []
    for i, e in enumerate(j.get(key, [])):
        k = which(e)
        e2 = dict(label=str(e.get('label', i + 1)))
        if key == 'rows':
            if 'baseline' in e:
                pts = [pt(k, *p) for p in e['baseline']]
                if len(pts) < 2:
                    raise SystemExit(f'{base(path)}: row {e2["label"]}: a baseline needs at least 2 points')
                e2['baseline'] = pts
            elif 'rect' in e:
                e2['rect'] = rect(k, e['rect'])
            elif 'baseline_below_letters' in e:
                v = e['baseline_below_letters']
                v = v if isinstance(v, dict) else dict(gap=v)
                e2['below_letters'] = dict(gap=float(v.get('gap', 15)), max_slope=v.get('max_slope'))
            elif 'baseline_follows_letters' in e:
                e2['follows_letters'] = follow_params(e['baseline_follows_letters'], path, e2['label'])
            else:
                raise SystemExit(f'{base(path)}: row {e2["label"]} has neither "baseline", "rect" nor '
                                 f'"baseline_below_letters"')
        else:
            e2['row'] = str(e.get('row', ''))
            e2['box'] = rect(k, e['box'])
            if k is not None:
                e2['mesh'] = P[k]['stem']
            else:                                   # composite box: the panel that contains its centre
                cx = 0.5 * (e2['box'][0] + e2['box'][2])
                e2['mesh'] = next((P[q]['stem'] for q in range(len(P))
                                   if place[q][0] <= cx < place[q][0] + P[q]['w']), '')
            letter_extras(e, e2, path)
        out.append(e2)
    if key == 'letters':
        check_letter_ids(out, path)
    return out, frm


def main_panels(a, argv):
    """two-panel mode: see TWO-PANEL MODE in the header."""
    import cv2
    n = len(a.mesh)
    if n != 2:
        raise SystemExit(f'two-panel mode takes exactly two --mesh (left panel first), got {n}')

    def per(opt, vals, need, dflt):
        vals = list(vals or [])
        if len(vals) == n:
            return vals
        if not vals and not need:
            return [dflt] * n
        raise SystemExit(f'two-panel mode: give {opt} once per --mesh, in the same order ({n} times; got '
                         f'{len(vals)})')
    cts = per('--ct', a.ct, True, None)
    areas = per('--area', a.area, True, None)
    offs = per('--render-offset', a.render_offset, False, '0,0')
    inks = per('--ink', a.ink, False, [])
    statps = per('--ink-stats', a.ink_stats, False, None)
    if a.area_json:
        raise SystemExit('two-panel mode: give --area once per panel (--area-json is for one mesh)')
    if not a.umbilicus:
        raise SystemExit('two-panel mode needs --umbilicus: the orientation and the seam are measured from the meshes')
    if bool(inks[0]) != bool(inks[1]):
        raise SystemExit('two-panel mode: give ink maps for both panels or for neither')
    if (statps[0] is None) != (statps[1] is None):
        raise SystemExit('two-panel mode: give --ink-stats for both panels or for neither')
    if a.panel_gap < 2:
        raise SystemExit('--panel-gap must be at least 2 px')
    if a.panel_dy != 'auto' and not re.fullmatch(r'[+-]?\d+', a.panel_dy):
        raise SystemExit('--panel-dy: auto or an integer')
    mesh_dirs = [os.path.normpath(m) for m in a.mesh]
    names = [base(m) for m in mesh_dirs]
    if len(set(names)) != n:
        raise SystemExit('two-panel mode: the two --mesh folders must be different meshes')
    stems = [nm[:-7] if nm.endswith('.tifxyz') else nm for nm in names]
    stem = '__'.join(stems)
    out_png = a.out or os.path.join(a.out_dir, stem + '.png')
    out_dir = os.path.dirname(os.path.abspath(out_png))
    ostem = os.path.splitext(base(out_png))[0]
    side_json = os.path.join(out_dir, ostem + '.json')
    key_png = os.path.join(out_dir, ostem + '_letter_key.png')
    sizes_csv = a.sizes_csv or os.path.join(out_dir, 'letter_sizes.csv')
    comp_ct = os.path.join(out_dir, ostem + '_ct.png')
    comp_ink = os.path.join(out_dir, ostem + '_ink.png')
    planned = [out_png, side_json]
    if a.letters:
        planned.append(sizes_csv)
        if a.letter_markers == 'key':
            planned.append(key_png)
    if a.write_components:
        planned += [comp_ct] + ([comp_ink] if inks[0] else [])
    exist = [p for p in planned if os.path.exists(p)]
    if exist and not a.force:
        raise SystemExit('outputs exist (use --force): ' + ', '.join(base(p) for p in exist))
    command = reduced_command(sys.argv[1:] if argv is None else argv, a, out_png)
    pats = None
    if a.forbid_words:                          # publication check, before anything is written
        pats = load_word_list(a.forbid_words)
        items = [('mesh folder name', nm) for nm in names]
        for md in mesh_dirs:
            items += mesh_text_files(md)
        items += [('input file name', base(p)) for p in cts + [a.umbilicus, a.rows, a.letters] + statps +
                  [q for g in inks for q in g] if p]
        items += [('output file name', base(p)) for p in planned]
        items += [('caption', t) for t in [a.title, a.scroll, a.volume_id, a.panel_line] + list(a.note) +
                  list(a.ink_names or [])]
        for p, key in ((a.rows, 'rows'), (a.letters, 'letters')):
            if p:
                for e in json.load(open(p)).get(key, []):
                    items.append((f'{key} label', f"{e.get('label', '')} {e.get('row', '')} {e.get('mesh', '')}"))
        for p in statps:
            if p:
                items.append(('ink-stats field "surface"', str(json.load(open(p)).get('surface', ''))))
        items.append(('recorded command', command))
        hits = word_hits(pats, items)
        if hits:
            raise SystemExit('publication check failed, nothing written: ' + '; '.join(hits))
    os.makedirs(out_dir, exist_ok=True)
    side = dict(schema='make_submission_image/1', mode='two panels', scroll=a.scroll, volume_id=a.volume_id,
                voxel_size_um=a.voxel_um)

    # ---------------------------------------------------------- meshes, identity, orientation
    umb = load_umbilicus(a.umbilicus)
    P = [panel_mesh(a, md, umb) for md in mesh_dirs]
    if a.geometry_sums:
        chk = {Q['name']: [] for Q in P}
        for p in a.geometry_sums:
            for nm, r in check_geometry_panels(p, [(Q['name'], Q['geo']) for Q in P]).items():
                chk[nm].append(r)
        for Q in P:
            if not chk[Q['name']]:
                raise SystemExit(f"--geometry-sums: {Q['name']} is not in any of the lists (as "
                                 f"'<mesh folder>/<file>')")
            Q['mesh']['geometry_check'] = chk[Q['name']]

    # ---------------------------------------------------------- each panel as in the one-mesh mode
    layers = parse_layers(a.ct_layer)
    lut = colormap_lut(a.cmap)
    for i, Q in enumerate(P):
        panel_render(a, Q, cts[i], inks[i], statps[i], areas[i], offs[i], layers, lut)
    mm = a.voxel_um / 1000.0
    L, R = P
    if (L['ink_r'] is None) != (R['ink_r'] is None):
        raise SystemExit('internal error: ink in one panel only')

    # ---------------------------------------------------------- seam: equal mesh z at equal image rows
    eL = seam_edge(L, 'right', to_render=a.seam_edge == 'render')
    eR = seam_edge(R, 'left', to_render=a.seam_edge == 'render')
    yl0, yl1 = L['reading_px'][1], L['reading_px'][3]
    eL = {k: v[yl0:yl1] for k, v in eL.items()}             # left: the rows of its area; right: all render rows
    fit, span = fit_panel_dy(eL['Z'], yl0, eR['Z'], 0, None if a.panel_dy == 'auto' else int(a.panel_dy))
    D = fit['D']
    iL = np.arange(span[0], span[1])
    iR = yl0 + iL + D
    both = np.isfinite(eL['Z'][iL]) & np.isfinite(eR['Z'][iR])
    pL = np.stack([eL[k][iL][both] for k in ('X', 'Y', 'Z')], 1)
    pR = np.stack([eR[k][iR][both] for k in ('X', 'Y', 'Z')], 1)
    gap3d = np.linalg.norm(pL - pR, axis=1)
    dzL = np.diff(eL['Z'][iL])
    dzR = np.diff(eR['Z'][iR])
    slope = float(np.nanmedian(np.abs(np.concatenate([dzL, dzR]))))
    tL = float(np.nanmedian(eL['T'][iL] % 360))
    tR = float(np.nanmedian(eR['T'][iR] % 360))
    seam = dict(rule='per render row, the outermost valid pixel on the seam side of each area (right edge of the '
                     'left area, left edge of the right area; searched within 256 px of that edge); mesh x, y, z, '
                     'theta there (bilinear from the nodes). D = the vertical offset with the smallest RMS z '
                     'difference over the rows of the left area (right panel reading row = left panel reading row + '
                     'D; the right profile is taken over all rows of its render, so D does not depend on the right '
                     'area rows); the panels are placed with that offset',
                given=a.panel_dy, **fit,
                **({} if a.seam_edge == 'area' else dict(
                    seam_edge='render: the outermost valid pixel of the whole render row on the seam side (the render '
                              'edge of each mesh), also where the area stops short of it')),
                z_per_render_row_vox=fmt(slope, 4),
                z_diff_rms_rows=fmt(float(fit['z_diff_rms_vox']) / max(slope, 1e-6), 2),
                theta_left_edge_deg_mod360=fmt(tL, 2), theta_right_edge_deg_mod360=fmt(tR, 2),
                edge_x_reading=dict(left_panel=[fmt(np.nanmin(eL['x_reading']), 1), fmt(np.nanmax(eL['x_reading']), 1)],
                                    right_panel=[fmt(np.nanmin(eR['x_reading']), 1),
                                                 fmt(np.nanmax(eR['x_reading']), 1)]),
                gap_3d_vox=dict(median=fmt(np.median(gap3d), 2), p10=fmt(np.percentile(gap3d, 10), 2),
                                p90=fmt(np.percentile(gap3d, 90), 2), n=int(gap3d.size),
                                note='3D distance between the two seam-edge pixels on the same image row: the papyrus '
                                     'between the two render edges, which is in neither panel'),
                gap_3d_mm_median=fmt(np.median(gap3d) * mm, 3),
                note='two separate meshes side by side, not a stitched mesh: each panel is cut from the render of its '
                     'own mesh (its own isometric flattening); nothing is resampled across the meshes')
    print(f"seam: D = {D} (right row = left row + D), z residual RMS {fit['z_diff_rms_vox']} vox over "
          f"{fit['rows_compared']} rows; theta at the seam {tL:.1f} | {tR:.1f} deg; 3D gap median "
          f"{np.median(gap3d):.1f} vox", flush=True)

    # ---------------------------------------------------------- placement (composite = the panel band)
    gap = int(a.panel_gap)
    s = R['reading_px'][1] - D - L['reading_px'][1]            # right area top relative to the left area top
    oyL, oyR = (max(0, -s), max(0, s))
    place = [(0, oyL), (L['w'] + gap, oyR)]
    HC = max(oyL + L['h'], oyR + R['h'])
    WC = L['w'] + gap + R['w']
    unequal_note = None
    if (s != 0 or L['h'] != R['h']) and a.unequal_panels:
        unequal_note = (f"the two areas differ in their top/bottom rows by design (--unequal-panels): right area top "
                        f"{s:+d} rows, bottom {s + R['h'] - L['h']:+d} rows against the left area, after the z "
                        f"alignment (D = {D})")
    elif s != 0 or L['h'] != R['h']:
        warn(f"after the z alignment (D = {D}) the two areas do not share their top/bottom rows (right area top "
             f"{s:+d} rows, bottom {s + R['h'] - L['h']:+d} rows against the left area); for one continuous band give "
             f"the right area the reading rows of the left area + D")
    comp_valid = np.zeros((HC, WC), bool)
    comp_ct_a = np.zeros((HC, WC), np.uint8)
    comp_ink_a = np.zeros((HC, WC), np.uint8) if L['ink_r'] is not None else None
    for Q, (ox, oy) in zip(P, place):
        comp_valid[oy:oy + Q['h'], ox:ox + Q['w']] = Q['valid']
        comp_ct_a[oy:oy + Q['h'], ox:ox + Q['w']] = Q['ct_r']
        if comp_ink_a is not None:
            comp_ink_a[oy:oy + Q['h'], ox:ox + Q['w']] = Q['ink_r']

    # ---------------------------------------------------------- annotations (composite coordinates)
    rows, rows_frame, letters, letters_frame = [], None, [], None
    if a.letters:
        letters, letters_frame = panel_annotations(a.letters, 'letters', P, place)
    if a.rows:
        rows, rows_frame = panel_annotations(a.rows, 'rows', P, place)
        for r in rows:
            if 'below_letters' in r:
                bx = [L_['box'] for L_ in letters if L_['row'] == r['label']]
                if not bx:
                    raise SystemExit(f"row {r['label']}: baseline_below_letters needs letters with row "
                                     f"{r['label']!r} (--letters)")
                bl = r['below_letters']
                r['baseline'] = baseline_below(bx, bl['gap'], bl['max_slope'])
                r['derived'] = (f"from the {len(bx)} letter boxes of row {r['label']}: at least {bl['gap']:g} px below "
                                f"each box, never inside a box" + (
                                    f"; slope limited to {bl['max_slope']:g} (the highest such line)"
                                    if bl['max_slope'] is not None else '; horizontal under each box'))
    extents = None
    if rows and any('follows_letters' in r for r in rows):
        extents = derive_follow_rows(rows, letters, comp_ink_a, (HC, WC), a.row_thickness,
                                     int(math.ceil(a.threshold * 255)))
    dash = tuple(float(t) for t in a.row_dash.split(',')) if a.row_dash else None
    row_col = parse_color(a.row_color)
    checks = {}
    if rows:
        rm = np.zeros((HC, WC), np.uint8)
        draw_rows(rm, rows, 0, 0, 255, a.row_thickness, dash, aa=False)
        rmask = rm > 0
        checks['row_pixels'] = int(rmask.sum())
        for r in rows:
            pts = row_points(r)
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            if min(xs) < 0 or min(ys) < 0 or max(xs) > WC or max(ys) > HC:
                warn(f"row {r['label']} extends outside the panels")
        if letters:
            lm = np.zeros((HC, WC), bool)
            for L_ in letters:
                x0, y0, x1, y1 = (int(round(v)) for v in L_['box'])
                lm[max(y0, 0):max(y1, 0), max(x0, 0):max(x1, 0)] = True
            n_in = int((rmask & lm).sum())
            checks['row_pixels_inside_letter_boxes'] = n_in
            if extents is not None:           # derived rows: checked against the letter extents; others as before
                plain = extent_checks(checks, rows, extents, (HC, WC), a.row_thickness, dash)
                rp = np.zeros((HC, WC), np.uint8)
                draw_rows(rp, plain, 0, 0, 255, a.row_thickness, dash, aa=False)
                n_in = int(((rp > 0) & lm).sum())
            if n_in:
                warn(f'{n_in} row-line pixels lie inside letter boxes (rows should not cover letters)')
        if comp_ink_a is not None:
            strong = comp_ink_a >= int(math.ceil(a.threshold * 255))
            fr_on = (rmask & strong).sum() / max(rmask.sum(), 1)
            checks['row_pixels_on_ink_above_threshold_fraction'] = fmt(fr_on, 4)
            if fr_on > 0.02:
                warn(f'{100 * fr_on:.1f} % of the row-line pixels lie on ink above the threshold: check that the rows '
                     f'do not run over letters')
            checks['area_ink_above_threshold_fraction'] = fmt((strong & comp_valid).sum() / max(comp_valid.sum(), 1),
                                                              4)
    for L_ in letters:
        x0, y0, x1, y1 = L_['box']
        k = next((q for q in range(n) if P[q]['stem'] == L_['mesh']), None)
        if k is None:
            warn(f"letter {L_['label']} box is not on a panel")
            continue
        ox, oy = place[k]
        if x0 < ox or y0 < oy or x1 > ox + P[k]['w'] or y1 > oy + P[k]['h']:
            warn(f"letter {L_['label']} box extends outside the area of its panel")

    # ---------------------------------------------------------- canvas
    fs = a.font_scale
    th1 = max(1, int(round(2 * fs / 1.3)))
    lh = int(round(34 * fs))
    px_cm = 10000.0 / a.voxel_um
    bar = int(round(px_cm))
    label_w = max([text_size(f"row {r['label']}", fs, th1)[0] for r in rows] + [0]) + (40 if rows else 0)
    left = max(40, label_w + 30)
    right = 40
    legend_w = 520 if comp_ink_a is not None else 0
    min_w = bar + 80 + legend_w + (60 if legend_w else 0)
    Wc = max(left + WC + right, left + min_w + right)
    text_w = Wc - 2 * 30
    title = a.title or f'{a.scroll} | meshes {stems[0]} (left) and {stems[1]} (right) | reading orientation'
    if L['maps']:
        ms = [', '.join(m['model'] for m in Q['maps']) for Q in P]
        ds = [', '.join(sorted({f"d = {m['depth']}" if m['depth'] is not None else 'depth not in the file name'
                                for m in Q['maps']})) for Q in P]
        sidetxt = 'reading side' if not L['blind'] else 'BLIND side (shown with the reading side statistics)'
        same = ms[0] == ms[1] and ds[0] == ds[1]
        if not same:
            warn(f'the two panels use different models or depths: {ms[0]} {ds[0]} | {ms[1]} {ds[1]}')
        if a.ensemble:
            ink_desc = (f"Ink: ensemble of {len(L['maps'])} models ({ms[0]}), mean of the per-model z-scores, "
                        f"{sidetxt}, {ds[0]}" + ('' if same else f' | right panel: {ms[1]}, {ds[1]}') +
                        "; each panel normalised with the statistics of its own surface volume")
        else:
            ink_desc = f"Ink: model {ms[0]}, {sidetxt}, {ds[0]}" + ('' if same else f' | right panel: {ms[1]}, {ds[1]}')
    else:
        ink_desc = 'Ink: none (CT only)'
    bg = f"Background: CT layer {layers[0]} (d = {layers[0] - MID})" if len(layers) == 1 else \
        f"Background: CT, mean of layers {layers[0]}..{layers[-1]} (d = {layers[0] - MID}..{layers[-1] - MID})"
    bg += f" of each mesh's 66-layer surface volume | volume {a.volume_id}, {a.voxel_um:g} um voxels"
    tot_cm2 = sum(Q['cm2'] for Q in P)
    arealine = 'Area: ' + '; '.join(
        f"{('left', 'right')[k]} {Q['w']} x {Q['h']} px = {Q['w'] * mm:.2f} x {Q['h'] * mm:.2f} mm = {Q['cm2']:.2f} cm2 "
        f"(reading px x {Q['reading_px'][0]}-{Q['reading_px'][2]}, y {Q['reading_px'][1]}-{Q['reading_px'][3]})"
        for k, Q in enumerate(P)) + f"; total {tot_cm2:.2f} cm2"
    t3d = [Q['area'].get('papyrus_cm2_mesh3d') for Q in P]
    if all(v is not None for v in t3d):
        arealine += f" (3D mesh surface of the papyrus pixels {sum(t3d):.2f} cm2)"
    panelline = (f"Two panels = two separate meshes side by side, not a stitched mesh: each panel is cut from the "
                 f"render of its own mesh (its own isometric flattening, no resampling). Seam: left panel edge at theta "
                 f"{tL:.1f} deg, right panel edge at theta {tR:.1f} deg; the panels are placed so that the mesh z is "
                 f"equal on each image row at the seam (right-panel row = left-panel row {D:+d}, reading orientation; "
                 f"residual RMS {fit['z_diff_rms_vox']:.1f} voxels over {fit['rows_compared']} rows); about "
                 f"{np.median(gap3d) * mm:.2f} mm of papyrus between the two render edges is in neither panel.")
    cap = [ink_desc, bg, panelline, arealine]
    if a.caption == 'compact':
        cap = [compact_ink_line(a, L['maps'], L['blind'], layers, panels=True),
               f"Two separate meshes side by side, not a stitched mesh: each panel is cut from the render of its own "
               f"mesh, and the panels are placed so that the mesh z is equal along the seam (theta {tL:.1f} | "
               f"{tR:.1f} deg at the {'render edges of the two meshes' if a.seam_edge == 'render' else 'panel edges'}"
               f"; about {np.median(gap3d) * mm:.2f} mm of papyrus between the two "
               f"{'render' if a.seam_edge == 'render' else 'panel'} edges is in neither panel).",
               'Area: ' + ' + '.join(f"{Q['cm2']:.2f} cm2 ({('left', 'right')[k]}, {Q['w'] * mm:.2f} x "
                                     f"{Q['h'] * mm:.2f} mm)" for k, Q in enumerate(P)) + f" = {tot_cm2:.2f} cm2"]
    if a.panel_line is not None:                            # --panel-line: own text for the panels/seam line
        cap[1 if a.caption == 'compact' else 2] = a.panel_line
        cap = [c for c in cap if c]
    if tot_cm2 > a.max_cm2 + 1e-9:
        warn(f'total area {tot_cm2:.4f} cm2 (sum of both panels) is larger than {a.max_cm2} cm2')
    if all(v is not None for v in t3d) and sum(t3d) > a.max_cm2 + 1e-9:
        warn(f'3D mesh surface of the papyrus pixels {sum(t3d):.4f} cm2 (both panels) is larger than {a.max_cm2} cm2')
    top_lines = [(ln, fs * 1.15, th1 + 1) for ln in wrap(title, fs * 1.15, th1 + 1, text_w)]
    for c in cap:
        top_lines += [(ln, fs, th1) for ln in wrap(c, fs, th1, text_w)]
    rows_note = []
    if rows:
        kinds = sorted({'baselines' if ('baseline' in r or 'segments' in r) else 'rectangles' for r in rows})
        rows_note = [f"Text rows: {len(rows)}, marked by thin {' and '.join(kinds)} in the image and labels in the "
                     f"left margin. No character is drawn or annotated."]
        if any('segments' in r for r in rows):
            rows_note = [f"Text rows: {len(rows)}, each marked by a thin line just below its letters (derived from "
                         f"the letter boxes and the ink; never over ink or a letter, interrupted where a letter reaches "
                         f"below the line) and a label in the left margin. No character is drawn or annotated."]
    bot_lines = []
    for c in rows_note + a.note:
        bot_lines += [(ln, fs, th1) for ln in wrap(c, fs, th1, text_w)]
    small = fs * 0.7
    strip_h = 2 * lh + 16                                   # mesh names and seam theta above the separator
    top = 30 + len(top_lines) * lh + 20 + strip_h
    bar_block = int(round(150 * fs / 1.3))
    bottom = 30 + bar_block + len(bot_lines) * lh + 20
    Hc = top + HC + bottom
    bgc = (24, 24, 24)
    fg = (235, 235, 235)
    grey = (150, 150, 150)
    sepc = (128, 128, 128)
    canvas = np.empty((Hc, Wc, 3), np.uint8)
    canvas[:] = bgc
    for Q, (ox, oy) in zip(P, place):
        canvas[top + oy:top + oy + Q['h'], left + ox:left + ox + Q['w']] = Q['panel']
        cv2.rectangle(canvas, (left + ox - 2, top + oy - 2), (left + ox + Q['w'] + 1, top + oy + Q['h'] + 1), grey, 1,
                      cv2.LINE_8)
    sx0, sx1 = left + L['w'], left + L['w'] + gap - 1           # the separator: the gap between the panels
    canvas[top - strip_h + 8:top + HC + 8, sx0:sx1 + 1] = sepc
    y = 30
    for s_, sc_, t in top_lines:
        y += lh
        put(canvas, s_, 30, y - int(0.25 * lh), sc_, fg, t)
    for k, (s1, s2) in enumerate(((stems[0], f'theta {tL:.1f} deg at the seam'),
                                  (stems[1], f'theta {tR:.1f} deg at the seam'))):
        for j, (s_, scl, tt, col_) in enumerate(((s1, fs, th1, fg), (s2, small, max(1, th1 - 1), grey))):
            tw = text_size(s_, scl, tt)[0]
            xx = sx0 - 14 - tw if k == 0 else sx1 + 15
            put(canvas, s_, xx, top - strip_h + 8 + (j + 1) * lh - int(0.3 * lh), scl, col_, tt)
    if rows:
        draw_rows(canvas, rows, left, top, row_col, a.row_thickness, dash)
        for r in rows:
            yy = int(round(row_anchor_y(r))) + top
            s_ = f"row {r['label']}"
            tw, tht, _ = text_size(s_, fs, th1)
            cv2.line(canvas, (left - 28, yy), (left - 6, yy), row_col, a.row_thickness, cv2.LINE_AA)
            put(canvas, s_, left - 34 - tw, yy + tht // 2, fs, row_col, th1)
            if 'segments' in r:                 # dotted leader from the label to the line, over empty canvas only
                yc = row_anchor_y(r)
                x_end = r['segments'][0][0][0]
                blocked = [(ox - 3, ox + Q['w'] + 3) for Q, (ox, oy) in zip(P, place) if oy - 3 <= yc < oy + Q['h'] + 3]
                blocked.append((L['w'] - 3, L['w'] + gap + 3))
                x, iv = 0.0, []
                for b0, b1 in sorted(blocked):
                    if b0 > x:
                        iv.append((x, min(b0, x_end)))
                    x = max(x, b1)
                iv = [(u, v) for u, v in iv if v - u >= 40]
                for u, v in iv:
                    for p_, q_ in dashed_segments([(u + left, yc + top), (v + left, yc + top)], (4, 10)):
                        cv2.line(canvas, (int(round(p_[0])), int(round(p_[1]))), (int(round(q_[0])), int(round(q_[1]))),
                                 row_col, 1, cv2.LINE_AA)
                r['label_leader_x'] = [[fmt(u, 1), fmt(v, 1)] for u, v in iv]
    # scale bar (as in the one-mesh mode)
    yb = top + HC + 30 + int(round(60 * fs / 1.3))
    xb = left
    lbl = '1 cm'
    tw, tht, _ = text_size(lbl, fs, th1)
    put(canvas, lbl, xb + (bar - tw) // 2, yb - 18, fs, fg, th1)
    cv2.rectangle(canvas, (xb, yb), (xb + bar - 1, yb + 11), fg, -1)
    cv2.rectangle(canvas, (xb, yb - 8), (xb + 2, yb + 19), fg, -1)
    cv2.rectangle(canvas, (xb + bar - 3, yb - 8), (xb + bar - 1, yb + 19), fg, -1)
    put(canvas, f'{bar} px = 10 mm at {a.voxel_um:g} um/px', xb, yb + 19 + int(34 * small), small, grey,
        max(1, th1 - 1))
    # colour legend: one colour ramp; the values at the threshold and at full scale for each panel
    legend = None
    if comp_ink_a is not None:
        lx = xb + bar + 60
        lw, lhh = legend_w, 24
        u = np.linspace(0, 1, lw, dtype=np.float32)
        u8 = (u * 255).astype(np.uint8)
        al = a.alpha * np.clip((u - a.threshold) / max(a.full - a.threshold, 1e-6), 0, 1)
        tint = (a.tint_floor + (1 - a.tint_floor) * 128 / 255.0) if a.blend == 'tint' else 1.0
        colr = lut[u8].astype(np.float32) * tint * al[:, None] + 128 * (1 - al[:, None])
        styled = a.overlay_style != 'default' or a.ct_dim != 1.0
        if styled:
            colr = legend_ramp(a, lut, lw)
        canvas[yb - 6:yb - 6 + lhh, lx:lx + lw] = np.clip(np.rint(colr), 0, 255).astype(np.uint8)[None]
        cv2.rectangle(canvas, (lx - 1, yb - 7), (lx + lw, yb - 6 + lhh), grey, 1)
        vals = [(lambda q, Q=Q: Q['norm']['display_range']['lo'] + q *
                 (Q['norm']['display_range']['hi'] - Q['norm']['display_range']['lo'])) for Q in P]
        name = 'ensemble z-score' if a.ensemble else f"{L['maps'][0]['model']} value"
        put(canvas, (f'ink ({name}; left | right panel) over ' + ('dimmed CT' if a.ct_dim != 1.0 else 'grey'))
            if styled else f'ink ({name}; left | right panel), over grey', lx, yb - 18, small, fg, max(1, th1 - 1))
        for q in ((a.threshold, a.full) if styled else (a.threshold, 1.0)):
            xx = lx + int(round(q * (lw - 1)))
            cv2.line(canvas, (xx, yb - 6 + lhh), (xx, yb - 6 + lhh + 8), fg, 1)
            s_ = f'{vals[0](q):.2f} | {vals[1](q):.2f}'
            tw2 = text_size(s_, small, max(1, th1 - 1))[0]
            put(canvas, s_, min(xx - tw2 // 2, lx + lw - tw2), yb + lhh + 10 + int(22 * small), small, grey,
                max(1, th1 - 1))
        legend = [dict(mesh=Q['stem'], threshold_value=fmt(vals[k](a.threshold), 4), full_value=fmt(vals[k](a.full), 4),
                       top_value=fmt(vals[k](1.0), 4)) for k, Q in enumerate(P)]
    y = top + HC + 30 + bar_block
    for s_, sc_, t in bot_lines:
        y += lh
        put(canvas, s_, 30, y - int(0.25 * lh), sc_, fg, t)

    # ---------------------------------------------------------- letter sizes and markers (as in the one-mesh mode)
    marker_pos = []
    if letters:
        occupied = [tuple(L_['box']) for L_ in letters]
        rad = int(round(18 * fs / 1.3))
        gp = 8
        for i, L_ in enumerate(letters, 1):
            x0, y0, x1, y1 = L_['box']
            cx, cy = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
            d = rad + gp
            cands = [(cx, y0 - d), (cx, y1 + d), (x0 - d, cy), (x1 + d, cy), (x0 - d, y0 - d), (x1 + d, y0 - d),
                     (x0 - d, y1 + d), (x1 + d, y1 + d), (cx, y0 - 2 * d), (cx, y1 + 2 * d)]
            chosen = None
            for lim in ((0, 0, WC, HC), (-left + 4, -top + 4, WC + right - 4, HC + 20)):
                for px, py in cands:
                    bb = (px - rad - 2, py - rad - 2, px + rad + 2, py + rad + 2)
                    if any(bb[0] < o[2] and o[0] < bb[2] and bb[1] < o[3] and o[1] < bb[3] for o in occupied):
                        continue
                    if bb[0] < lim[0] or bb[1] < lim[1] or bb[2] > lim[2] or bb[3] > lim[3]:
                        continue
                    chosen = (px, py)
                    break
                if chosen is not None:
                    break
            if chosen is None:
                warn(f"no free place for marker {letter_number(L_, i)} ({L_['label']}) outside all letter boxes; "
                     f"marker omitted")
                marker_pos.append(None)
                continue
            occupied.append((chosen[0] - rad, chosen[1] - rad, chosen[0] + rad, chosen[1] + rad))
            marker_pos.append(chosen)

    def draw_markers(img):
        for i, mp in zip([letter_number(L_, k) for k, L_ in enumerate(letters, 1)], marker_pos):
            if mp is None:
                continue
            cx, cy = int(round(mp[0] + left)), int(round(mp[1] + top))
            rad = int(round(18 * fs / 1.3))
            cv2.circle(img, (cx, cy), rad, (0, 0, 0), -1, cv2.LINE_AA)
            cv2.circle(img, (cx, cy), rad, (0, 215, 255), 2, cv2.LINE_AA)
            s_ = str(i)
            ss = fs * 0.75
            tw, tht, _ = text_size(s_, ss, th1)
            put(img, s_, cx - tw // 2, cy + tht // 2, ss, (0, 215, 255), th1)

    main_img = canvas.copy()
    if letters and a.letter_markers == 'on':
        draw_markers(main_img)

    # ---------------------------------------------------------- write
    def write_png(path, arr):
        if not cv2.imwrite(path, arr, [cv2.IMWRITE_PNG_COMPRESSION, 6]):
            raise SystemExit(f'cannot write {path}')
        return dict(file=base(path), sha256=sha256_file(path), width_px=int(arr.shape[1]),
                    height_px=int(arr.shape[0]))

    if pats:
        hits = word_hits(pats, [('caption', s_) for s_, _, _ in top_lines + bot_lines] +
                         [('panel label', t) for t in stems] +
                         [('row label', r['label']) for r in rows] + [('warning', t) for t in WARNINGS])
        if hits:
            raise SystemExit('publication check failed, nothing written: ' + '; '.join(hits))
    outputs = dict(image=write_png(out_png, main_img))
    outputs['image']['data_panels'] = [dict(mesh=Q['stem'], x=left + ox, y=top + oy, width=Q['w'], height=Q['h'])
                                       for Q, (ox, oy) in zip(P, place)]
    outputs['image']['composite_origin'] = dict(x=left, y=top, width=WC, height=HC,
                                                note='image pixels of the composite frame (rows/letters "composite")')
    if letters:
        with open(sizes_csv, 'w', newline='') as fh:
            wr = csv.writer(fh, lineterminator='\n')
            ext = any('reading' in L_ or 'class' in L_ for L_ in letters)
            wr.writerow(['id', 'label'] + (['reading', 'class'] if ext else []) + ['row', 'mesh', 'width_px',
                                                                                  'height_px', 'width_mm', 'height_mm',
                                                                                  'x0', 'y0', 'x1', 'y1'])
            for i, L_ in enumerate(letters, 1):
                x0, y0, x1, y1 = L_['box']
                wr.writerow([letter_number(L_, i), L_['label']] + ([leiden(L_), L_.get('class', '')] if ext else []) +
                            [L_['row'], L_['mesh'], f'{x1 - x0:g}', f'{y1 - y0:g}',
                             f'{(x1 - x0) * mm:.2f}', f'{(y1 - y0) * mm:.2f}', f'{x0:g}', f'{y0:g}', f'{x1:g}',
                             f'{y1:g}'])
        outputs['letter_sizes_csv'] = dict(file=base(sizes_csv), sha256=sha256_file(sizes_csv),
                                           note='box coordinates in composite pixels (both panels in reading '
                                                'orientation side by side, origin at the top left of the panel band; '
                                                'x1, y1 exclusive); width and height in the render pixels of the '
                                                'letter\'s own mesh')
        if a.letter_markers == 'key':
            kimg = canvas.copy()
            draw_markers(kimg)
            knote = wrap(f'Key image: the numbers are the ids in {base(sizes_csv)} (letter width and height in px and '
                         f'mm). They are placed outside the measured letters; the image itself carries no markers.',
                         fs, th1, text_w)
            strip = np.empty((len(knote) * lh + 20, Wc, 3), np.uint8)
            strip[:] = bgc
            for i, s_ in enumerate(knote):
                put(strip, s_, 30, (i + 1) * lh - int(0.25 * lh), fs, (0, 215, 255), th1)
            kleg = key_legend_strip(letters, Wc, fs, th1, lh, bgc, (0, 215, 255))
            outputs['letter_key_image'] = write_png(key_png, np.vstack([kimg, strip] + ([kleg] if kleg is not None
                                                                                        else [])))
    if a.write_components:
        outputs['component_ct'] = write_png(comp_ct, comp_ct_a)
        if comp_ink_a is not None:
            outputs['component_ink'] = write_png(comp_ink, comp_ink_a)

    # ---------------------------------------------------------- sidecar
    side['panels'] = []
    for k, Q in enumerate(P):
        ox, oy = place[k]
        side['panels'].append(dict(
            position=('left', 'right')[k], mesh=Q['mesh'], orientation=Q['orient'], area=Q['area'], ct=Q['ct_info'],
            ink=Q['ink_info'],
            placement=dict(composite_x=ox, composite_y=oy, image_x=left + ox, image_y=top + oy, width=Q['w'],
                           height=Q['h'], note='top left of the area in the composite frame and in the image')))
    tot_nom = sum(Q['area']['papyrus_cm2_nominal'] for Q in P)
    side['area_total'] = dict(
        area_cm2=fmt(tot_cm2, 4), papyrus_cm2_nominal=fmt(tot_nom, 4),
        papyrus_cm2_mesh3d=fmt(sum(t3d), 4) if all(v is not None for v in t3d) else None,
        limit_cm2=a.max_cm2, within_limit=bool(tot_cm2 <= a.max_cm2 + 1e-9),
        mesh3d_within_limit=bool(sum(t3d) <= a.max_cm2 + 1e-9) if all(v is not None for v in t3d) else None,
        note='sums over both panels: area_cm2 = the two rectangles (width x height in render pixels); '
             'papyrus_cm2_nominal = their valid pixels; papyrus_cm2_mesh3d = the 3D mesh surface of the valid pixels')
    if unequal_note:
        seam['placement_note'] = unequal_note
    side['seam'] = seam
    side['composite'] = dict(width_px=WC, height_px=HC, gap_px=gap, separator_rgb='128,128,128',
                             note='the panel band: left area at x 0, right area at x = left width + gap; y as in '
                                  'placement; gap = the neutral separator line')
    side['overlay'] = overlay_record(a, legend, panels=True)
    side['scale_bar'] = dict(length_px=bar, px_per_cm=fmt(px_cm, 3), label='1 cm')
    side['rows'] = None if not a.rows else dict(file=base(a.rows), sha256=sha256_file(a.rows), frame=rows_frame,
                                                rows_composite_px=rows, color_rgb=a.row_color,
                                                thickness_px=a.row_thickness, dash=a.row_dash or 'solid')
    side['letters'] = None if not a.letters else dict(
        file=base(a.letters), sha256=sha256_file(a.letters), frame=letters_frame, markers=a.letter_markers,
        letters_composite_px=[sidecar_letter(L_, i) for i, L_ in enumerate(letters, 1)],
        marker_centres_composite_px=[None if p is None else [fmt(p[0], 1), fmt(p[1], 1)] for p in marker_pos])
    side['checks'] = checks
    side['warnings'] = WARNINGS
    side['outputs'] = outputs
    import zarr
    import tifffile
    side['software'] = dict(python=sys.version.split()[0], numpy=np.__version__, opencv=cv2.__version__,
                            zarr=zarr.__version__, tifffile=tifffile.__version__)
    side['command'] = command
    side['command_note'] = 'paths reduced to file names' + (
        '; the values of --geometry-sums and --forbid-words are not recorded'
        if (a.geometry_sums or a.forbid_words) else '')
    if pats:
        side['publication_check'] = dict(word_list_entries=len(pats), hits=0,
                                         checked='mesh folder names, text files of the meshes, input and output file '
                                                 'names, captions, labels, warnings, the command and this sidecar')
    txt = json.dumps(side, indent=1, ensure_ascii=False) + '\n'
    if pats:
        hits = word_hits(pats, [('sidecar', txt)])
        if hits:
            raise SystemExit(f'publication check failed on the sidecar: {"; ".join(hits)}. The image files were '
                             f'written, the sidecar {base(side_json)} was NOT; rename the inputs and rerun with --force')
    with open(side_json, 'w') as fh:
        fh.write(txt)
    print(f'wrote {base(out_png)} ({main_img.shape[1]} x {main_img.shape[0]} px), {base(side_json)}'
          + (f', {base(sizes_csv)}' if letters else '') + (f', {base(key_png)}' if 'letter_key_image' in outputs
                                                          else ''), flush=True)
    if WARNINGS:
        print(f'{len(WARNINGS)} warning(s), listed in {base(side_json)}', flush=True)
    return side


if __name__ == '__main__':
    main()
