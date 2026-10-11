# stroke-score

Ranks Herculaneum-scroll segments by how much **stroke-shaped ink** an ink-model ensemble shows on the reading side of a
sheet, compared with the **blind side of the same sheet**. It is a triage tool: it tells you which windings, depths and
4 cm² windows deserve a human look, and it writes review crops so that look is quick. It does not decide what is text.

Status: version 0.2 (draft), October 2026. Tested on three known-text segments at two scan types (PHerc. 0343 at 8.64 µm;
PHerc. 0139 and PHerc. 0841 at 9.36 µm) and several hundred windings of PHerc. 0191 and PHerc. 0813 with no text found.
New in 0.2: a row score, a stroke-shape score, a neighbour-recurrence check, any set of ink models, and a known-text control
kit that scores known text the way a search band of your height would see it. The 0.2 rule's thresholds are set per model set
from known text cut to band height and 294 null winding-depths; see "The 0.2 rule".

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


## New in 0.2: why, and what changed

**What we learned from known text at 9.36 µm.** We ran our full render-and-ink path on two public segments with known
text scanned like our target scrolls (9.36 µm, 113 keV): PHerc. 0139 w047, which none of ink_9um, dense_native or
Reader v2 trained on, and PHerc. 0841 auto_grown 20260221022814, from a scroll none of them trained on, with human ink labels.
Our maps reproduce the published AUCs on both, so the render and ink steps are sound. The 0.1 score sees the PHerc. 0139 text
the way it saw the PHerc. 0343 letters. On PHerc. 0841 it does not: the text covers a small part of the segment and that
scroll's blind side is noisy, so reading − blind stays at +0.001 to +0.009 and the best window at 1.0–1.4× the blind side.
The 0.1 rule flags it only on the stroke-area line, which damaged windings cross too (60 of 186 PHerc. 0191 winding-depths
crossed the 0.1 rule, mostly on that line alone; none of the 25 we checked by eye showed writing); the two lines that compare
the reading side with the blind side stay quiet, although the
letters are plain by eye at row scale. Text at this resolution shows as **rows** of short strokes, not as isolated marks.

**Row score.** In the best 2 × 2.4 cm window, the across-row profile of above-background pixel density is autocorrelated at
line-spacing lags (3.5–8 mm); the score is max(autocorrelation) × profile SD × 100. The profile is the median of four strips
along the window: a line of writing runs across all four, a lone bright blob sits in one. (Without the median, two blobs at
two heights scored like rows: on PHerc. 0813 w085 the blind side reached 2.2, and on w091 the reading side 1.4 from one
bright cluster plus a band along the mesh edge; with it, 0.8 and 0.4.) Rows with less than half their width valid are left
out, so short bands and meshes with gaps are still scored. Reported for both sides (`sides.<side>.row`).

**Stroke shape.** In the row window, the share of the marks' area (above-background components of at least 0.05 mm²) that
lies in marks at least 1 mm long and twice as long as wide (`sides.<side>.shape`). Letters are made of strokes; crack edges and
damage give round blobs. Known text in 1 cm strips: median 0.42–0.63 on the reading side, 0.00–0.40 on the blind side. On
PHerc. 0813 the windows with the highest row scores (rows of soft blobs over crack fields, checked by eye at full resolution)
score 0.15–0.21. Edge contrast and peak height of the marks did not separate text from blobs; elongation did. Also reported:
`horiz`, the share of the long marks lying within 30° of the winding direction (see Known false alarms).

**Search bands are short: calibrate on known text cut to your band height.** Our search windings are bands of about 10.3 mm
of mesh, so a winding shows at most two lines of text, while known-text segments are several centimetres tall. Scored over
the whole segment, known text looks far stronger than it could in a band like ours (row score 2.6–4.1 against 1.1–1.9 in
1 cm strips). `stroke-score control eval --band-mm 10.3` cuts the known text into strips as tall as your band, every 2 mm, and
scores each like a search winding. Compare your nulls with those numbers, not with the whole-segment ones.

**Neighbour recurrence.** Each result now carries the stroke density along the winding (`sides.<side>.profile`, 200 bins of the
segment length). `stroke-score rank` correlates a winding's reading-side profile with its neighbours (w−2..w+2, same depth and
model set) and reports the best correlation (`recur`). A bright zone that repeats turn after turn is sheet structure (a crack
zone, a fold); text columns do not line up turn after turn. Example: on PHerc. 0813, w088 scored strongest of eight windings
(reading − blind +0.021, window 2.9× the blind side), and w086, w087, w089 and w090 show the same reading-side zone.

**Any model set.** `--models auto` (the default) uses every model whose maps are present (ink_9um seeds 42/43, dense_native,
Hecate, Reader v2, d9v4C, in run_ink.sh naming); `--map-list` takes any naming.

**The 0.2 rule** (`flag_v02` in `stroke-score rank`): LOOK when the reading side shows rows of strokes: row score at least the
model set's row threshold and at least 1.8 × the blind side's (`--row-ratio`), and shape score at least the model set's shape
threshold. The 0.1 rule is still reported (`flag`). The row score's scale depends on the model set, so the thresholds are set per
model set (`V02_THRESHOLDS` in cli.py; `--row-thr` and `--shape-thr` override):

| model set | row ≥ | shape ≥ | null winding-depths passing | known-text 1 cm strips passing |
|---|---|---|---|---|
| ink_9um ×2 + dense_native | 1.2 | 0.35 | 0 of 194 (PHerc. 0191 clear band) | PHerc. 0139: 39–57 %; PHerc. 0841: 38 % |
| Reader v2 + d9v4C | 1.5 | 0.42 | 1 of 100 (PHerc. 0813 outer band) | PHerc. 0841: 31–46 % |
| any other set | 1.5 | 0.42 | not calibrated | not calibrated |

Read the last column as the chance that one 1 cm band through text, at one depth, gets flagged: the rule is a triage line set so
that our null windings almost never cross it, not a detector. The one PHerc. 0813 null that passes (w079, depth 0) is a crack
streak (Known false alarms).

## Known-text control kit

```
stroke-score control list                              # the controls, their CT volume and mesh URLs, who trained on what
stroke-score control fetch 0841-ag2814 controls/       # mesh + reference map + human labels (no CT; < 70 MB)
# render the mesh as a 66-layer surface volume from the public CT, run your model(s) on it (see `stroke-score control -h`)
stroke-score control eval --control 0841-ag2814 --fetched controls/ --maps maps/ --depth 1 --models auto
```

`eval` prints AUC and correlation against the reference (human labels inside the supervision mask for PHerc. 0841; a
2.4 µm / 78 keV ink prediction for PHerc. 0139), after finding the few-pixel shift between the 2.4 µm and 9 µm meshes, plus
the stroke and row scores, for each model and the ensemble, reading and blind side. It is a quick way to check a new ink model,
or a new render setting, on known text at the scan type the eligible scrolls were scanned at, scored exactly as a search winding.

| control | models | AUC (reading) | stroke area R / B | window R / B | row R / B |
|---|---|---|---|---|---|
| PHerc. 0139 w047, d −1 | ink_9um ×2 + dense_native | 0.84 | 0.030 / 0.006 | 0.054 / 0.016 | 2.67 / 0.23 |
| same, d +1 | same | 0.83 | 0.029 / 0.007 | 0.056 / 0.017 | 2.64 / 0.35 |
| same, d +1 | Reader v2 | 0.85 | 0.029 / 0.008 | 0.058 / 0.029 | 3.54 / 0.83 |
| PHerc. 0841 auto_grown, d −1 | ink_9um ×2 + dense_native | 0.78 | 0.029 / 0.020 | 0.048 / 0.034 | 2.64 / 1.08 |
| same, d +1 | same | 0.78 | 0.026 / 0.020 | 0.043 / 0.038 | 2.66 / 0.96 |
| same, d −1 | Reader v2 + d9v4C | 0.83 | 0.034 / 0.027 | 0.055 / 0.043 | 4.11 / 0.58 |
| same, d +1 | same | 0.82 | 0.037 / 0.027 | 0.054 / 0.048 | 4.11 / 0.78 |

Computed with `stroke-score control eval` without `--surface` (scored area = where every model's map has data); AUC is the
ensemble's, reading side. The same segments in 10.3 mm strips (`--band-mm 10.3`, strips every 2 mm), reading side:

| control | models | row score: median (lower quartile) / highest | blind highest | shape: median reading / blind |
|---|---|---|---|---|
| PHerc. 0139 w047, d −1 / +1 | ink_9um ×2 + dense_native | 1.80–1.86 (1.07) / 3.90 | 0.53 | 0.45–0.47 / 0.00–0.19 |
| same, d +1 | Reader v2 | 2.20 (1.63) / 4.74 | 1.23 | 0.42 / 0.06 |
| PHerc. 0841 auto_grown, d −1 / +1 | ink_9um ×2 + dense_native | 1.09–1.33 (0.57–0.83) / 1.94 | 1.52 | 0.46–0.49 / 0.13–0.22 |
| same, d −1 / +1 | Reader v2 + d9v4C | 1.54–1.91 (0.75–1.16) / 2.92 | 1.60 | 0.51–0.63 / 0.29–0.40 |

Null windings scored the same way (inside the render's mesh area): PHerc. 0191 clear band, 194 winding-depths with the three
models, row score median 0.42, highest 1.22; PHerc. 0813 outer band, 100 winding-depths with Reader v2 + d9v4C, median 0.87,
highest 2.62 (rows of crack blobs; their shape scores 0.15–0.21).

Published AUCs for comparison: PHerc. 0139 w047 dense_native 0.898, Reader v2 0.893, ink_9um 0.778 (78 keV reference);
PHerc. 0841 dense_native 0.800, Reader v2 0.824, d9v4C 0.830, ink_9um 0.733 (human labels).

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

For 0.2 see "The 0.2 rule" and the control kit above: three known-text segments (PHerc. 0343 at 8.64 µm; PHerc. 0139 w047
and PHerc. 0841 at 9.36 µm), 294 null winding-depths from two scrolls and two model sets. Still wanted: more known text at
8–9.4 µm, especially in short bands, and nulls from other scrolls.

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
- **Zones that repeat turn after turn** (0.2): a crack zone or fold that crosses several windings lights up the same place on
  neighbouring windings, sometimes strongly on the reading side only (PHerc. 0813 w088: reading − blind +0.021). The `recur`
  column catches it; look at the neighbours before believing a single winding.
- **Rows of crack blobs** (0.2): on a crack-rich sheet the models draw the edges of cracks running along the winding, and two
  crack edges a few mm apart look like lines of text to the row score (PHerc. 0813 w094 2.6, w102 2.4, w076 2.3 with Reader
  v2 + d9v4C). The marks are round blobs, so the shape score stays low (0.15–0.21) and the 0.2 rule does not flag them.
- **Crack-edge streaks** (0.2): a crack edge drawn as long horizontal streaks passes both the row and the shape score (PHerc.
  0813 w079, row 1.8, shape 0.55). Nearly all of its long marks run along the winding (`horiz` 0.92); in our known text at most
  0.61 do. Check `horiz` and the CT under the window.
- **Lone blobs and mesh borders** (0.2, fixed): two bright blobs at two heights, or the bright lines ink models draw along mesh
  borders, used to read as rows. The row profile is now the median of four strips along the window, and a 0.5 mm margin along
  the mesh edge is left out.

## Limits

- It ranks; it does not prove. A high score means "look here".
- Calibrated on a small number of known-text segments so far; thresholds will move as more are tested.
- It inherits the ink models' blind spots: if the models cannot see the ink, neither can the score.
- The row score's scale depends on the model set, on how much of the segment holds text and on the band height; compare
  like with like (`--band-mm`).
- In 1 cm bands even known text is flagged only in about a third to a half of the strips at one depth; a null from short bands
  is weaker evidence than one from tall bands.
- At 9.36 µm no public model makes the letters of these scrolls legible; the score points at rows of strokes worth a closer
  look (more depths, more models, Hecate), not at readable text.

## Credits

- Erwin Nieuwlaar, PHerc. 0343 First Letters (github.com/Nieuwlaar/pherc343-first-letters, MIT): the four-model
  ensemble, its normalisation, the 66-layer render convention and `run_ink.sh` naming.
- Ink models: `ink_9um` (ScrollPrize/villa), `dense_native` (Erwin Nieuwlaar), `scrollprize/hecate`, Reader v2 (Domenico Russo,
  DomRusso2/reader-v2, MIT), d9v4C (TAUIL-Abd-Elilah, 9um-reader-letter-shape, MIT).
- Known-text controls: PHerc. 0139 w047 and its 78 keV reference map, PHerc. 0841 auto_grown 20260221022814 and its human ink
  labels (Vesuvius Challenge / EduceLab, CC BY-NC 4.0). Which models trained on which segments: the Reader v2 and dense_native
  model cards and the ink_9um dataset README.
- Scan data: Vesuvius Challenge / EduceLab (CC BY-NC 4.0).

## Licence

MIT
