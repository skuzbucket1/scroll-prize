# stroke-score

Ranks Herculaneum-scroll segments by how much **stroke-shaped ink** an ink-model ensemble shows on the reading side of a
sheet, compared with the **blind side of the same sheet**. It is a triage tool: it tells you which windings, depths and
4 cm² windows deserve a human look, and it writes review crops so that look is quick. It does not decide what is text.

Status: version 0.1, October 2026. Calibrated on one known-text segment (the PHerc. 0343 First Letters winner) and 109
windings of PHerc. 0191 with no text found. More known-text segments are being tested; see Validation.

## Why

An ink search produces a lot of images: two sides, several models, several depths per winding. Real text in these
scrolls is faint, and the models also light up on cracks, voids and distorted geometry. Scrolling through every image
by eye does not scale past a few dozen windings.

## What it measures

For one 66-layer render at one depth:

1. **Ensemble.** Each model's map becomes a z-score using the reading side's mean and standard deviation over valid
   pixels; the ensemble is the mean of the z-scores. This is the normalisation of Erwin Nieuwlaar's
   `ensemble_maps.py` (PHerc. 0343 First Letters).
2. **Background.** A masked Gaussian mean (σ = 1.5 mm) is subtracted, so slow brightness trends do not count as ink.
3. **Strokes.** Pixels more than 2.0 above the background, kept as connected components of 0.02–1.5 mm² (the size of
   pen strokes). Specks and broad blooms are dropped.
4. **Usable area.** Pixels with CT data in every render layer, minus a 0.5 mm margin at the edges; holes smaller than
   0.5 mm² are filled first so isolated zero voxels do not punch margins into the surface.
5. **The same on the blind side**, with the reading side's normalisation. Text should raise the reading side only.
6. **Scores.**
   - `area_R` / `area_B`: share of the usable area covered by strokes, reading / blind.
   - `R - B`: their difference.
   - `window`: the best 2 × 2 cm square (4 cm², the First Letters area), clamped to the segment height.
   - `tiles`: the best 4 × 4 mm squares, with a damage fraction (how much of the tile was lost to edges and holes).

`stroke-score rank` puts many results in one table and flags rows with three or more models as **LOOK** when any of:
`area_R ≥ 0.015`, `R - B ≥ 0.010`, or `window ≥ 0.030` (three models; `0.035` for four) and at least twice the blind
side's best window. All thresholds are options.

## Install

```
pip install ./tools/stroke-score        # or: pip install -e ./tools/stroke-score[test]
```

Needs Python ≥ 3.10, numpy, opencv-python-headless, tifffile, zarr.

## Use

Score a render whose ink maps were made with Nieuwlaar's `run_ink.sh` (file names
`<name>__<model>__L66s<25+d>[_reverse].tif` and `<name>__hecate__L66zc<32.5+d>[_reverse].png`; `_reverse` is the reading side):

```
stroke-score score --surface w070.zarr --name exp30k_snapped_w070_66 --maps maps/ --um 9.362 --depth 1 --out scores/ --crops 3
stroke-score score ... --models ink9-42,ink9-43,dnative            # three-model set (no Hecate)
```

Any other naming: list the files in a JSON and pass `--map-list`:

```json
{"ink9-42": {"reading": "maps/a_reverse.tif", "blind": "maps/a.tif"},
 "dnative": {"reading": "maps/b_reverse.tif", "blind": "maps/b.tif"}}
```

Rank everything:

```
stroke-score rank scores/ --out ranking.tsv
```

The render is a zarr group whose array `0` has shape (layers, H, W) with depth 0 at layer 33 (`--mid-layer` otherwise).

## Outputs

- `<name>__strokes_d±NN.json`: parameters, per-model normalisation, per-side scores, the top reading tiles (positions in
  reading orientation = rotated 180°, and in render pixels), damage fractions.
- `<name>__strokes_d±NN.png`: the tile score map, reading next to blind.
- `<name>__strokes_d±NN__topNN.png` (with `--crops N`): reading ensemble | blind ensemble | CT for each top tile, fixed
  stretch, reading orientation.
- `ranking.tsv` from `rank`.

## Validation so far

| Segment | Models | area_R | R − B | best 4 cm² window |
|---|---|---|---|---|
| PHerc. 0343 winning segment (known letters), depth +1 | four | 0.0335 | +0.031 | 0.048 |
| same | three (no Hecate) | 0.0354 | +0.030 | 0.050 |
| PHerc. 0191, 109 windings (99 of band z 9,000–10,000 + 10 community), depths 0 and +1, no text found by eye | three or four | ≤ 0.018 | ≤ +0.015 | ≤ 0.038 |

The packaged tool reproduces the original research script exactly on these data (identical scores and top tiles).

In progress: more known-text segments as positives (the other published PHerc. 0343 text segments and any other text
shown on 8–9.4 µm scans), and a measured false-alarm rate per threshold on the null windings.

## Known false alarms

Every flag so far on PHerc. 0191 was one of these, found by looking at the review crops:

- **CT voids and cracks**: the models fire around air gaps; the bright patch sits next to a dark crack in the CT crop
  and is often bright on the blind side too. The damage fraction is usually high.
- **Recurring bright zones**: diffuse mottling at the same position on neighbouring windings, a property of the scan
  or the sheet, not text (text does not line up turn after turn).
- **Distorted geometry near the core**: windings that cross several layers or pass through air give many edges and
  inflate `area_R` on both sides; the CT crop shows folded layers instead of one clean sheet.
- **Tiny meshes** (under about 1 cm²): too small for stable statistics; no window fits.
- **Quiet blind sides**: the old reading/blind *ratio* exploded when the blind side was unusually quiet; this is why
  the tool ranks by absolute measures.

## Limits

- It ranks; it does not prove. A high score means "look here".
- Calibrated on a small number of known-text segments so far; thresholds will move as more are tested.
- It inherits the ink models' blind spots: if the models cannot see the ink, neither can the score.

## Credits

- Erwin Nieuwlaar, PHerc. 0343 First Letters (github.com/Nieuwlaar/pherc343-first-letters, MIT): the four-model
  ensemble, its normalisation, the 66-layer render convention and `run_ink.sh` naming.
- Ink models: `ink_9um` (ScrollPrize/villa), `dense_native`, `scrollprize/hecate`.
- Scan data: Vesuvius Challenge / EduceLab (CC BY-NC 4.0).

## Licence

MIT
