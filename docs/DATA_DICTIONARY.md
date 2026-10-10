# Data dictionary

> **2026-10-10:** the data was migrated to the layout in `docs/DATA_LAYOUT.md` (`source/`, `inputs/`, `geometry/<fit-id>/`, `renders/`, `ink/`, `scores/`, `runs/`, `scratch/`, `cache/`). The paths below are the pre-migration names; they still work through symlinks, and the current-to-new table in DATA_LAYOUT.md gives each new location.

2026-10-10

This document describes the datasets the project keeps on the GPU box `llm` and on Ted's Mac: what each one is, where
it lives, its format and size, which script produced it, and whether it can be deleted. It exists so that disk space
can be freed without losing results (the box NVMe was 91 % full on 2026-10-10), so that the inputs and outputs of any
step can be found, and so that ink maps and scores are read with the right conventions. The raw directory listing
behind it is `notes/data-inventory-2026-10-10.md`. Sizes are `du` figures taken read-only on 2026-10-10.

## Conventions

### Locations

- Box: `~/scroll-prizes` is a symlink to `/mnt/nvme/scroll-prizes`. Box paths below are relative to it unless absolute.
  In the dataset sections, `0191/` stands for `data/PHerc0191/` on the box.
- Mac: the repository root `/Users/tbienapfl/dev/vscode/scroll-prizes`. `data/`, `villa/`, `memory/`, `aws/state/`,
  `aws/spot.env` and all `*.tif` files are git-ignored.
- Scripts: box `bin/`, copied to `box/bin/` in the repository (in sync on 2026-10-10). `bin/ink343/` holds Erwin
  Nieuwlaar's ink scripts from the PHerc. 343 First Letters repository (MIT), unchanged. AWS scripts are in `aws/` (run on the Mac) and `aws/remote/` (run on the instances).
- Every job writes a log that ends with a marker `<NAME>-EXIT: <rc>`; waiter scripts poll for these markers.

### Names

- `wNNN` is a winding index from our spiral fit `exp-30k` on the band z 9000–10000; w020–w119 are in use. The
  community windings `w000`–`w009` come from a different fit (z 11600–12400) and use their own numbering.
- One winding passes through these names (example w070):

  | step | path |
  |---|---|
  | fitted mesh | `0191/spiral-output/<run>/meshes/fitted_exp-30k/w070_exp-30k` |
  | snapped mesh | `0191/snapped/exp-30k/w070_exp-30k` |
  | flattened mesh | `0191/flatten/exp-30k-snapped-w070/tifxyz/flatten.tifxyz` |
  | 66-layer render | `0191/render66/exp30k_snapped_w070_66.zarr` |
  | ink maps | `0191/ink-triage/maps/exp30k_snapped_w070_66__<model>__…` |
  | stroke scores | `data/strokes/w070/exp30k_snapped_w070_66__strokes…` |

  `<name>` below is the render stem without `.zarr`, e.g. `exp30k_snapped_w070_66`.
- Spiral-fit run directories: `<UTC start date>_PHerc0191_slice-<z0>-<z1>_0-patch_<tag>`; the tag is
  `FIT_SPIRAL_RUN_TAG` set by the launcher script.
- AWS worker directories `w01`–`w10` are worker numbers, not windings.

### Coordinates and volumes

- OME-Zarr arrays are indexed (z, y, x) in level-0 voxels; level n is downsampled by 2^n. VC3D and the `bbox` in
  tifxyz `meta.json` use (x, y, z).
- PHerc0191 CT: `20250821151635-9.362um-1.2m-113keV-masked.zarr`, 9.362 µm voxels, 113 keV, 1.2 m propagation
  distance (ESRF BM18 helical scan of 2025-07-20 per its `metadata.json`). Level-0 shape (z, y, x) = (18977, 8387, 8387),
  uint8, 128³ chunks, no compression, value 0 outside the scroll mask. Public at
  https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc0191/volumes/20250821151635-9.362um-1.2m-113keV-masked.zarr.
  1 mm = 106.8 voxels.
- PHerc0343 positive control: `PHerc0343/volumes/20250521140437-8.640um-1.2m-116keV-masked.zarr`, 8.64 µm voxels,
  116 keV, streamed from S3 (not mirrored).

### tifxyz meshes

- A folder with `x.tif`, `y.tif`, `z.tif` (per-vertex volume coordinates in level-0 voxels) and `meta.json`
  (`format: tifxyz`, `type: seg`, `uuid`, `scale`, `bbox` [[x0, y0, z0], [x1, y1, z1]], `area_vx2`, often `area_cm2`).
- `scale` is the grid sampling: `[0.05, 0.05]` means one vertex per 20 voxels.
- Flattened meshes (Lasagna) also hold `model.pt` and a `fit_config` block in `meta.json`.
- Raw spiral-fit winding meshes declare scale 0.05 but are spaced 26–30 voxels (friction log #10), so renders of
  unflattened windings are compressed by 25–33 % and their areas understated. Flattened meshes render at
  1.02 px per voxel.

### 66-layer renders

- `0191/render66/<name>.zarr`, written by `bin/render66.sh` (`vc_render_tifxyz --num-slices 66 --slice-step 1
  --scale 1`, local CT).
- Array `"0"`: shape (66, H, W), uint8, chunks (66, 128, 128), blosc-lz4. VC3D also writes pyramid levels 1–5;
  the ink scripts read level 0 only.
- Layer k samples the CT at (k − 32.5) voxels along the mesh normal. Depth d = layer − 33, so d = 0 is layer 33;
  positive d points away from the scroll axis.
- A pixel is valid when the CT is > 0 in all 66 layers.
- Older QA renders (`pilot-qa`, `winding-qa`, `snapped/qa_*`, `grow-test/qa*`) have 28 layers and their ink maps use
  villa's default layer choice. Their names (`<w>_seed42-75000[_reverse].tif`, `ink_seed43-75000…`,
  `*_preview-ds2.tif` = 2× downsampled preview, `.err` = stderr) do not follow the L66 convention below.

### Ink maps

Written by `bin/ink343/run_ink.sh <surface.zarr> <model> <d> <out_dir>`, one pair (both sides) per call.

| model | file name | value |
|---|---|---|
| villa models | `<name>__<model>__L66s<s>[_reverse].tif`, s = 25 + d | uint8 = trunc(255 · p) |
| Hecate | `<name>__hecate__L66zc<zc>[_reverse].png` and `.json`, zc = 32.5 + d | uint8 = round(255 · p) |

- `_reverse` = READING side (the text face). No suffix = BLIND side.
- `s` is the first layer of the 17-layer input window s … s+16, centred on layer 33 + d.
- Hecate reads 16 planes resampled to 9.6 µm around layer zc, so its map is about 2.5 % smaller than the render
  (1970 × 9733 for a 2020 × 9980 render). The scorers resize it bilinearly. The `.json` records checkpoint,
  `sampling_um`, `shape_yx`, `reverse_z`, `central_depth`, `precision`, `stride`.
- Reading values: `p` is the model output. `ensemble_maps.py` and `stroke_score.py` read villa maps as
  clip((v − 64) / 128, 0, 1) = (p − 0.25) / 0.5. This is a contrast stretch for the label-smoothed models, not a
  probability. Hecate values are read as v / 255.
- Models:

  | short name | model | checkpoint | author |
  |---|---|---|---|
  | `ink9-42` (s42) | `hybrid_3d2d-seed42` | `checkpoints/ink_9um/hybrid_3d2d-seed42/step-075000.pth` | Vesuvius Challenge (ink_9um) |
  | `ink9-43` (s43) | `hybrid_3d2d-seed43` | `checkpoints/ink_9um/hybrid_3d2d-seed43/step-075000.pth` | Vesuvius Challenge (ink_9um) |
  | `dnative` | dense_native, step 16000 | `checkpoints/ckpt343/dense_native-016000.pth` | Erwin Nieuwlaar |
  | `hecate` | Hecate 9.6 µm | `checkpoints/hecate/hecate_9.6um.pth` | Giorgio Angelotti |

- Depth lookup: d −1 = s24 / zc31.50; d 0 = s25 / zc32.50; d +1 = s26 / zc33.50; d +2 = s27 / zc34.50.

### Ensemble images

- `bin/ink343/ensemble_maps.py` writes `<name>__<stack>[_blind]__d+NN.png` with stack ∈ {ensemble, dnative, hecate,
  ink9-42, ink9-43}, plus `<name>__ct__d+NN.png` (CT layer 33 + d) and `<name>__stats.json` (every number used).
- No suffix = reading side. `_blind` = blind side, shown with the reading side's statistics.
- Per-model stretch: p1–p99.5 of the reading-side maps pooled over `--stat-depths`. Ensemble = mean of the per-model
  z-scores (pooled reading-side mean and SD), with one stretch for the ensemble. CT stretch over layers 18–48.
- Orientation: reading orientation = rotated 180° (high z at the top). Invalid pixels are black.
- Three-model ensembles (`ensemble3/`, AWS run 2) use the same names; `stats.json` lists the models.

### Stroke scores

Written by `bin/stroke_score.py`, called by `bin/stroke_rank.sh`, `bin/stroke_watch.sh`, `bin/three_model_windings.sh`,
`aws/fleet_score.sh` and on AWS workers by `aws/remote/run_batch.sh`.

Files:

| file | content |
|---|---|
| `<name>__strokes<tag>_d+NN.json` | parameters and results (fields below) |
| `<name>__strokes<tag>_d+NN.png` | 4 mm tile scores, reading grid left, blind grid right, reading orientation, common scale, enlarged 4× |
| `<name>__strokes<tag>_d+NN__topKK.png` | review crop around the K-th best reading tile: reading E, blind E, CT; E stretched −1 … 4; unused pixels dimmed; reading orientation |
| `<name>__valid.png` | cached valid-pixel mask |

Tags (the JSON field `models` is the only reliable record of the model set):

| tag | models | note |
|---|---|---|
| none | as given by `--models` (default all four) | three models in `data/strokes/box3m/` and AWS run 2, four elsewhere |
| `_s42` | ink9-42 only | `stroke_rank.sh` |
| `_3m` | dnative, ink9-42, ink9-43 | older format without the window metric; no producer script kept |
| `_s4243` | ink9-42, ink9-43 | older format without the window metric; no producer script kept |
| `_pm` | one model per file, no PNG | `tmp/permodel.sh` (not in `bin/`) |

Method (defaults):

1. Per model, z = (map − mean) / SD, with mean and SD of the reading-side map over valid pixels at this depth. The
   ensemble E is the mean of the model z-scores. The blind side uses the reading side's mean and SD.
2. Background = Gaussian mean of E over valid pixels, sigma 1.5 mm. Stroke pixels: E − background > 2.0.
3. Keep 8-connected components with an area of 0.02–1.5 mm² (letter-stroke size).
4. Used area = valid pixels minus a 0.5 mm margin at the segment edge (invalid holes < 0.5 mm² are filled first) minus
   CT voids (void mask off by default, `--void-frac 0`).

Metrics:

| metric | JSON field | ranking column | definition |
|---|---|---|---|
| area_R, area_B | `sides.reading.stroke_frac`, `sides.blind.stroke_frac` | `area_R`, `area_B` | share of used pixels covered by kept components, reading / blind side |
| R−B | — | `R-B` | area_R − area_B |
| best 4 mm tile | `sides.<side>.tiles.max` | `max_tile_R`, `max_tile_B` | 4 × 4 mm windows on a 1 mm grid; score = covered share of the tile's used pixels; tiles under 60 % used are skipped |
| window | `sides.<side>.window.max` | `window_R`, `window_B` | best 2 × 2 cm window (4 cm², First Letters scale), same score, at least 30 % used; the side is clamped to the render height when that is smaller (2020 px = 18.9 mm for w070) |
| damage | `top_reading_tiles[].damage` | `top_damage` | share of the top tile's valid pixels removed by the edge margin or void mask |
| top tile position | `top_reading_tiles[].read_y/read_x` (reading orientation), `raw_y/raw_x` (render orientation), `size_px` | `top_read_y`, `top_read_x` | |
| reading/blind ratio | `ratio_max_reading_over_max_blind` | — | first-version metric; unstable when the blind side is quiet (w073 showed 7.45× from a 0.0009 denominator); not used for ranking |

Other JSON fields: `name`, `depth`, `models`, `um`, `H`, `W`, `valid_px`, `used_px`, `void_px`, `ct_p1`, `ct_p99_5`,
`params`, `norm` (per-model mean and SD), `sides.<side>.components_kept/components_all`, `seconds`.

Ranking tables:

- Box `data/strokes/ranking.tsv` (`bin/stroke_rank.sh`, incremental; `FORCE=1` re-scores all): `name, set (s42 | ens4),
  depth, area_R, area_B, R-B, window_R, window_B, max_tile_R, max_tile_B, top_read_y, top_read_x, top_damage, flag`,
  sorted by area_R. Reference rows: the PHerc. 343 control.
- Mac `data/aws-results/run2/ranking.tsv` (`aws/fleet_rank.sh`): `winding, depth, models, area_R, area_B, R-B,
  window_R, window_B, top_read_y, top_read_x, top_damage, flag, crops`.

LOOK flag (identical in `stroke_rank.sh` and `fleet_rank.sh`): area_R ≥ 0.015, or R−B ≥ 0.010, or (window_R ≥ 0.030
with fewer than four models, ≥ 0.035 with four, and window_R ≥ 2 × window_B).

Calibration (2026-10-09, depths 0 and +1, from the header of `aws/fleet_rank.sh`):

| set | PHerc. 343 control area_R / R−B / window | PHerc0191 w068–w074, maximum |
|---|---|---|
| three models | 0.0354 / +0.030 / 0.050 | 0.0064 / +0.0021 / 0.017 |
| four models | 0.0335 / +0.031 / 0.048 | 0.0073 / +0.0057 / 0.023 |

The thresholds were set on three- and four-model ensembles. Single-model rows get flagged regardless: all 86 `s42`
rows in `data/strokes/ranking.tsv` carry LOOK, including PHerc0191 windings whose blind side scores nearly as high as
the reading side. Ignore the flag on `s42` rows.

### Spiral-fit metrics

- `satisfaction_metrics_fitted.json`, block `summary`:
  `satisfied_track_points_fraction` = satisfied_track_points / total_track_points;
  `satisfied_tracks_fraction` = satisfied_tracks / total_tracks. The patch fields are 0 because patches are disabled.
  Pilot 0.4607 / 0.083; best run `exp-30k` 0.4901 / 0.1018.
- Also in each run directory: `satisfied_fitted.json`, `mesh_in_mask.json` (`bin/mesh_in_mask.py`, share of each
  winding's vertices inside the CT mask), `non_liftable_patches.txt`, `spiral_on_{patches,tracks}_sNNNNN_fitted.png`.
- `snap_report.tsv` (`bin/snap_meshes_nieuwlaar.py`): `winding, n_valid, frac_with_sheet, frac_snapped, median_abs_off,
  p90_abs_off, frac_rejected, frac_already_on` (offsets in voxels).

### Retention classes

| class | meaning |
|---|---|
| SOURCE | public, can be downloaded again |
| REGENERABLE | can be recomputed from sources and code; the cost is given |
| KEEP | results, reviews, paid runs, or anything expensive or impossible to recreate |
| SCRATCH | safe to delete once no running job uses it |

## Disk use on the box (2026-10-10)

| area | size | main content |
|---|---|---|
| `data/` | 738 G | PHerc0191 732 G, PHercParis4 4.6 G, PHerc0343 1.1 G, PHerc0800 665 M, strokes 355 M |
| `cache-root/` | 30 G | uv cache 24 G, torch compile cache 6.2 G |
| `villa/` | 29 G | three `.venv` 21 G, VC3D build 4.9 G, `.git` 1.0 G |
| `wt/` | 9.5 G | four git worktrees |
| `checkpoints/` | 2.8 G | model weights |
| `tmp/` | 1.8 G | job temp files |
| `runs/` | 1.1 G | day-1 smoke tests |
| `bin/`, `cache/`, 105 top-level logs | 2.5 M | |
| `/mnt/nvme/vc3d-remote-cache/` (outside the project) | 29 G | VC3D remote-chunk cache |
| NVMe total | 840 G used of 938 G | 89 G free |

## Datasets

### 1. Public source mirrors and models

**PHerc0191 CT volume**
- What: the full CT scan of PHerc0191, all six pyramid levels.
- Where: box `0191/volumes/20250821151635-9.362um-1.2m-113keV-masked.zarr/`.
- Format, size: OME-Zarr v2 (see Conventions), 410 G (level 0 353 G, level 1 49 G, level 2 7.3 G, levels 3–5 1.6 G),
  209,814 objects.
- Made by: `bin/mirror_s3_v2.py`; log `0191/mirror-volume.log` (440 GB in 8.9 h). Read by `render66.sh`,
  `winding_band.sh`, `fiber_band.sh`, `make_outer_shell.py`, `assemble_pherc0191.sh`.
- Class: SOURCE. A re-download takes about 9 h. Without the local copy every render streams from S3 (the streamed
  control render took 280 s on the box; local winding renders take 21–107 s).

**Lasagna normal and gradient stores**
- What: the published Lasagna representation of PHerc0191: sheet normals (nx, ny) and gradient magnitude.
- Where: box `0191/lasagna/20250821151635-lasagna-20260419180421/PHerc0191_{nx,ny,grad_mag}.ome.zarr`, manifest
  `PHerc0191.lasagna.json`.
- Format, size: OME-Zarr uint8, levels 2–4 only (the manifest also names a `cos` group that was not mirrored);
  18.1 G.
- Made by: `bin/mirror_s3_v2.py`; logs `0191/mirror-lasagna-v2-PHerc0191_*.log`. The `mirror-lasagna-PHerc0191_*.log`
  files are from the abandoned first mirror (`bin/switch_lasagna_to_v2.sh`).
- Class: SOURCE (under 1 h per store at the second mirror's rate).

**Normal grids**
- What: published xy-plane normal grids, one file per z slice; required by the tracer and by `vc_gen_umbilicus`.
- Where: box `0191/normal-grids/` (`metadata.json`, `xy/NNNNNN.grid` × 18,977).
- Size: 5.6 G.
- Made by: mirror, log `0191/mirror-normalgrids.log` (5.9 GB in 0.97 h).
- Class: SOURCE.

**m7 surface prediction (partial)**
- What: the published surface-segmentation prediction for PHerc0191 (`…surface-m7-L0-th0.2.zarr`), only the bands we use.
- Where: box `0191/surf-m7/20250821151635-surface-20260413222639-surface-m7-L0-th0.2.zarr/`.
- Format, size: OME-Zarr uint8; level 0 z chunk rows 46–52 (z 8832–10176) and 57–65 (z 10944–12672), level 1 rows
  22–27; 5.0 G.
- Made by: `bin/mirror_surf_band.sh`, `bin/mirror_surf_band_z11k.sh`, `bin/mirror_surf_band_l1.sh`. Read by
  `snap_meshes_nieuwlaar.py` (via `SURF_ZARR`) and the surface-SDT build.
- Class: SOURCE.

**Surface tracks**
- What: track graph extracted from the m7 prediction (z 4500–17500); the main input of the spiral fitter.
- Where: box `0191/spiral/20250821151635/tracks/` (`PHerc0191_20250821151635_surface_m7_L0_th0.2.dbm` 9.9 G,
  `.dbm.crossings.npz` 2.4 G, `.dbm.vctracks/`, `.extract.json`). `0191/spiral-dataset/tracks` is a symlink to it.
- Size: 21 G.
- Made by: download, log `0191/tracks-download.log` (no URL recorded).
- Class: SOURCE (assumed; see Open questions).

**PHerc0343 control mesh**
- What: Erwin Nieuwlaar's published PHerc. 343 winning segment (MIT), our positive control.
- Where: box `data/PHerc0343/control/concat_w047-w048_R5B2_z9500-11000.tifxyz/`; also inside Mac
  `data/prior-art/pherc343-first-letters/`.
- Size: 528 K.
- Class: SOURCE.

**Community spiral-fit windings**
- What: ten windings w000–w009 (z 11600–12400) of the community PHerc0191 fit `rodriguescarson/eligible-scroll-spiral-fits`.
- Where: box `0191/community-fit/wNNN/` (tifxyz).
- Size: 312 K.
- Made by: download; the command is not in `bin/` (`prep_community.sh` only consumes it).
- Class: SOURCE.

**PHercParis4 segment 20231016151002**
- What: day-1 test data: the segment's meshes on three volumes and its 7.91 µm surface volume.
- Where: box `data/PHercParis4/segments/20231016151002/` (`mesh/` with three tifxyz, `surface-volumes/7.91um-54keV-volume-20230205180739.zarr`).
- Size: 4.6 G.
- Made by: surface volume by `bin/fetch_zarr.py` (log `dl-surfvol-7.91um.log`); the meshes were downloaded by hand.
- Class: SOURCE.

**PHerc0800 segments**
- What: six public auto-grown segments' 8.64 µm surface volumes (31 layers), used for a day-1 ink test.
- Where: box `data/PHerc0800/segments/<TS14>-auto_grown_<TS17>/surface-volumes/8.64um-1.2m-116keV-volume-20250521135224.zarr`.
- Size: 665 M (chunks missing on the server are absent here too).
- Made by: `bin/dl_pherc0800.sh`.
- Class: SOURCE.

**Model checkpoints**
- What: ink models (ink_9um seed 42 at steps 75000 and 40000, seed 43 at step 75000, dense_native, Hecate 9.6 µm and
  2.4 µm), the winding model `winding_model_9um`, and the Lasagna fiber model.
- Where: box `checkpoints/{ink_9um,dense_native,hecate,winding_model_9um,lasagna-fiber}/`. `checkpoints/ckpt343/` is
  the layout `run_ink.sh` expects: symlinks into the other folders plus `dense_native-016000.pth`.
- Size: 2.8 G, 70 files.
- Made by: Hugging Face downloads (`hf-*.log`, `bin/hf_ink_extra.sh`, `bin/hf_winding.sh`).
  `ckpt343/dense_native-016000.pth` was rebuilt from the safetensors by `bin/ink343/rebuild_dense_native_pth.py`.
- Class: SOURCE; the rebuilt `.pth` is REGENERABLE (seconds).

**Open-data catalog and prior art (Mac)**
- What: `data/catalog/metadata.json` (open-data metadata catalog, 17 M); `data/prior-art/` (Substack posts as HTML,
  text and API JSON, Nieuwlaar's `pherc343-first-letters` repository, the `scrollfiesta_public` repository, `sqm/`;
  256 M, 5,864 files).
- Class: SOURCE.

### 2. Geometry

**Spiral-fit dataset and umbilicus**
- What: the fitter's dataset directory: `spiral-scroll.json`, `umbilicus.json`, `umbilicus_raw.json`,
  `umbilicus_estimates.csv`, symlinks to the Lasagna stores and tracks, outer shell, surface SDT, winding supervision.
- Where: box `0191/spiral-dataset/`. `0191/spiral-dataset-old/` is a symlink farm for the old fitter whose
  `spiral-scroll.json` adds the surface SDT ("old" = old fitter, not old data).
- Made by: `bin/assemble_pherc0191.sh` (`vc_gen_umbilicus` from the normal grids, seed 1).
- Class: REGENERABLE (minutes). Keep: under 1 MB and referenced by every fit.

**Resident-pool sidecars (two copies)**
- What: packed bricks of the Lasagna normals (nx+ny pair) and gradient magnitude at level 2, loaded into memory by the fitter.
- Where and size:
  - box `0191/lasagna/<id>/PHerc0191_nx.ome.zarr.respool_g2_pair/` (12 G) and `PHerc0191_grad_mag.ome.zarr.respool_g2/`
    (5.6 G): no CT mask, built by the pilot fit on 2026-10-08 22:23 because the fitter looks for the sidecar next to
    the symlink target. The fits load this copy.
  - box `0191/spiral-dataset/lasagna_inputs/*.respool*` (17.6 G): CT-masked copy packed by `assemble_pherc0191.sh`
    at 22:17. No fit log shows it being loaded.
- Format: `brick_coords.npy`, `table.npy`, `channel_N.u8`, `meta.json`; zero-byte `.lock` files beside them.
- Class: the `lasagna/` copy is REGENERABLE (138 s to pack; a fit rebuilds it if missing). The
  `spiral-dataset/lasagna_inputs` copy is SCRATCH once the old-fitter run has ended and is confirmed not to read it.

**Outer shells**
- What: scroll outer boundary as a tifxyz-like grid (`x/y/z.tif`, `meta.json`, `shell_stats.json`), used by the fitter's
  shell loss.
- Where: box `0191/spiral-dataset/outer_shell/` (160 M, full scroll, dz = 1; the one the fitter reads),
  `outer_shell_dz1/` (160 M, identical copy), `outer_shell_band8500-10500/` (17 M), `outer_shell_dz8/` (20 M, the shell
  of exp-shell105), `outer_shell.v0/` (20 M, superseded).
- Made by: `bin/make_outer_shell.py` (445 s for the full scroll at dz 8), `bin/shell_dense_and_rerun.sh`.
- Class: REGENERABLE (minutes). `outer_shell_dz1/` and `outer_shell.v0/` are SCRATCH.

**Surface SDT**
- What: signed distance to the m7 surface for z 8936–10064, input of the old fitter's `phase` spacing mode.
- Where: box `0191/spiral-dataset/surf_sdt_band9000-10000.ome.zarr/` (1.4 G, levels 1–3, partial by design),
  `….respool_g1/` (4.6 G sidecar), `….done_tiles.json`, `….respool_g1.lock`.
- Made by: the old fitter's SDT builder, run by hand; command and output in `surf-sdt.log` (1,313 s). Not in `bin/`.
- Class: REGENERABLE (about 25 min). In use by the running old-fitter fit.

**Winding-model cache and supervision**
- What: native-phase cache of the public winding model over the band z 9000–10000 (winding step 8, seed spacing 96,
  7,102 slabs), and the compact supervision exported from it.
- Where: box `0191/winding/band9000-10000/winding_native_phase_ws8_ss96.zarr/` (104 G); export
  `0191/spiral-dataset/winding_inference/` (1.1 M: `manifest.json`, `shard_0/`, `shard_1/`); smoke test `smoke.zarr/`
  (3.7 G); leftovers `smoke.tmp/`, `winding_native_phase_ws8_ss96.tmp/`; logs and VRAM traces beside them.
- Made by: `bin/winding_smoke.sh`, `bin/winding_band.sh` (about 10,000 s on GPUs 2 + 3; the launcher's "WINDING-EXIT: 127"
  came from an argument bug after the inference had finished), `bin/export_wm.sh` (106 s).
- Class: the cache is REGENERABLE (about 2.8 h on two 3060-class GPUs). Its only consumer, the export, is done and
  the winding-model fits were neutral, so it is the largest candidate to drop. The export is KEEP (tiny, input of
  exp-wm and exp-wm2). `smoke.zarr` and the `.tmp` folders are SCRATCH.

**Spiral-fit runs**
- What: fitted spirals on the band z 9000–10000 (and, running, z 11200–12200): checkpoint, per-winding meshes,
  metrics, diagnostic PNGs.
- Where: box `0191/spiral-output/` (11 runs): `…_pilot-z9000-10000` (2026-10-08), `exp-30k`, `exp-dirlow`,
  `exp-dirlow2`, `exp-dr32`, `exp-shell105`, `exp-shell105b`, `exp-track2x`, `exp-wm`, `exp-wm2` (2026-10-09),
  `exp30k-z11200` (2026-10-10, running).
- Format, size: per run `checkpoint_fitted.ckpt` (~933 M), `meshes/fitted_<tag>/{wNNN_<tag>, wNNN_spliced_<tag>}`
  (tifxyz; 120 + 120 for exp-30k, 63 M), metrics JSON, 40 PNGs (11 M). 11 G in total, 9,314 files.
- Made by: `bin/pilot_fit_pherc0191.sh`, `bin/fit_experiment.sh <tag> <gpu> '<overrides>'` (also via
  `bin/exp_shell105.sh`, `bin/shell_dense_and_rerun.sh`, `bin/queue_after_winding.sh`, `bin/queue_wm.sh`). Logs
  `fit-<tag>.log` (overrides, metrics, FIT-EXIT) and `fit-<tag>-full.log`.
- Class: `exp-30k` is KEEP in full (every snapped winding derives from its meshes, and its checkpoint bootstraps the
  winding cache). For the other runs, metrics, PNGs and meshes are KEEP (about 70 M each); their checkpoints are
  REGENERABLE (30–45 min per 10k-step fit on one 3060; about 8.4 G together).

**Old-fitter run**
- What: the PHerc. 343 winner's fit recipe (surface SDT + phase spacing, 30k steps) with villa commit 0fb38c45.
- Where: box `0191/spiral-output-old/2026-10-09_…_old-phase-30k/` (empty until the run ends), inputs
  `0191/spiral-dataset-old/`, cache dir `cache/spiral-old/`, code and venv `wt/spiral-0fb38c45/`.
- Made by: `bin/fit_old_phase.sh`; logs `fit-old-phase-30k*.log` (attempts 1–4 failed).
- Class: running (8 h 15 min at 00:50 UTC); KEEP its output when it finishes.

**Snapped windings**
- What: fitted windings moved along the normal onto the nearest m7 surface sheet.
- Where: box `0191/snapped/exp-30k/wNNN_exp-30k/` × 100 (w020–w119, 27 M) and `0191/snapped/community/wNNN/` × 10
  (324 K), each with `windings.txt`, `snap_report.tsv`, `snap.log`.
- Made by: `bin/snap_exp30k.sh` and `bin/prep_community.sh`, both running `bin/snap_meshes_nieuwlaar.py` (Nieuwlaar,
  MIT) on level 0 of the m7 band.
- Class: REGENERABLE (minutes, needs the matching m7 band). Keep: small, and the meshes everything downstream uses.
- Pending: `bin/snap_newband.sh` waits for the `exp30k-z11200` fit and will write `0191/snapped/exp30k-z11200/`.

**Flattened windings**
- What: snapped windings flattened with Lasagna, the meshes that are rendered.
- Where: box `0191/flatten/exp-30k-snapped-wNNN/` × 100, `community-snapped-wNNN/` × 10, `lasagna150/`. Each holds
  `tifxyz/flatten.tifxyz/` (with `model.pt`), `model_final.pt`, `model_snapshots/` (10 × `model_stage0_NNNNNN.pt`),
  `flatten.log`, `flatten_input.json`.
- Size: 1.9 G, of which `model_snapshots/` 1.6 G.
- Made by: `bin/flatten_winding.sh` (Lasagna `fit.py configs/flatten_fast_nofilter.json`, 95–412 s per winding on a
  3060, median 142 s), called by `bin/triage_windings.sh` and `bin/prep_community.sh`.
- Class: REGENERABLE (about 4 h for all). Keep the `flatten.tifxyz` folders; `model_snapshots/` is SCRATCH.
  `exp-30k-snapped-w116/` is a failed run (rc 1, no mesh) and SCRATCH.

**Fiber outputs and direction fields**
- What: fibre-direction inference on z 8500–10500 and two direction fields for the tracer.
- Where: box `0191/fiber/band8500-10500/` (3.5 G: `fiber_{nx,ny,presence}.ome.zarr`, `dirfield.zarr`,
  `fiber.lasagna.json`, `inference.json`, logs) and `0191/fiber/dirfield_lasagna.zarr/` (6.8 G; x and y are symlinks
  to the Lasagna nx/ny, z is computed).
- Made by: `bin/fiber_band.sh` (about 1.6 h on one 3060), `bin/make_dirfield_zarr.py` (`dirfield-build.log`,
  `dirfield-lasagna-build.log`, 1,389 s).
- Class: REGENERABLE. The tracer tests that used them are concluded.

**Tracer patches**
- What: patches grown with `vc_grow_seg_from_seed` under different inputs, with QA renders and ink maps.
- Where: box `0191/grow-test/`: `out/`, `out2/`, `out3/`, `out_ct/` (one `auto_grown_<TS17>` tifxyz each), `qa/`,
  `qa2/`, `qa_ct/`, `dirfield/` (failed first attempt), `dirfield2/` (`out_<v>/`, `qa_<v>/`, `params_<v>.json`,
  `grow_<v>.log` for v ∈ 70, 150, ct70, lasagna70, lasagna150, ng70, ng100w3), `params*.json`, `seeds3.txt`, logs.
- Size: 5.2 G (patches about 4 M; QA renders and maps the rest).
- Made by: `bin/grow_qa.sh`, `bin/tracer_dirfield_test.sh`, `bin/tracer_dirfield_test2.sh`, `bin/tracer_lasagna_test.sh`.
- Class: patches, parameters and logs KEEP (small, cited on the site); QA renders and maps REGENERABLE (minutes each).

### 3. Renders

**66-layer renders of the windings**
- What: 66-layer surface volumes of the flattened windings (see Conventions).
- Where: box `0191/render66/exp30k_snapped_wNNN_66.zarr` × 99 (w020–w119 without w116; 0.27–1.60 G each),
  `lasagna150_66.zarr` (3.5 G, the 35.8 cm² Lasagna-field tracer patch), `render_wNNN.log` × 98 (w070's log is
  `render66-w070.log` at the top level).
- Size: 93 G.
- Made by: `bin/render66.sh`, called by `bin/triage_windings.sh` (21–107 s per winding from the local CT, median 51 s).
- Class: REGENERABLE (about 1.5 h for all 99). `run_ink.sh` and `stroke_score.py` need them (valid mask, CT crops),
  so re-render before re-scoring if deleted.

**Triage previews**
- What: CT at d = 0 of each render, 2× downsampled.
- Where: box `0191/triage/previews/wNNN_ct_d0.png` × 99 (202 M).
- Made by: `bin/triage_windings.sh`; `bin/ink_triage.sh` uses their presence as the "render finished" signal.
- Class: REGENERABLE (seconds each).

**QA renders (28 layers)**
- What: early renders and seed-42/43 ink maps of selected windings and patches.
- Where: box `0191/pilot-qa/` (w040, w070, w100; 794 M), `0191/winding-qa/{exp-30k,exp-wm}/` (w040, w070; 865 M),
  `0191/snapped/qa_exp-30k_w040_exp-30k/`, `qa_exp-30k_w070_exp-30k/` (410 M, with `selfcross.json`).
- Made by: `bin/pilot_qa.sh`, `bin/winding_qa.sh`, `bin/patch_qa.sh` (via `bin/snap_exp30k.sh`).
- Class: REGENERABLE (minutes). The site uses JPEG copies in Mac `data/results/`.

**PHerc. 343 control render**
- What: 66-layer render of the control mesh, streamed from S3 at 8.64 µm.
- Where: box `data/PHerc0343/control/control343_66.zarr/` (905 M), `render.log`.
- Made by: `bin/control343.sh`.
- Class: REGENERABLE (minutes plus about 4 GB streamed).

**Day-1 smoke tests**
- What: PHercParis4 crop renders and ink predictions, and PHerc0800 ink maps from three checkpoints.
- Where: box `runs/20231016151002-2.4um-g2-28-crop1/`, `…-crop1b/`, `20231016151002-7.91um-ink9um-s42-075k/`,
  `PHerc0800-ink9um/` (1.1 G).
- Made by: `bin/render_2p4um_crop1.sh`, `bin/render_2p4um_crop1b.sh`, `bin/infer_7p91_smoke.sh`, `bin/infer_pherc0800.sh`.
- Class: REGENERABLE. Results are on the site (`sample-*.jpg`, `PHerc0800-*.jpg`).

### 4. Ink maps and ensemble images

**PHerc0191 ink maps**
- What: ink maps of the windings, both sides.
- Where: box `0191/ink-triage/maps/` (333 entries, 2.0 G; `logs/` with 9 per-model logs).
  - seed 42: 29 windings (w033–w036, w060–w080, w103–w106); d 0 for 29, d +1 for 28, d +2 for 21, d −1 for 20.
  - seed 43 and dnative: 12 windings (w033–w036, w068–w072, w103–w105), d 0 / +1.
  - Hecate: 5 windings (w068–w072), d 0 / +1.
- Made by: `bin/ink_triage.sh` (seed 42, logs `wNNN_dN.log`), `bin/ensemble_windings.sh` (four models,
  `ensemble_wNNN.log`), `bin/three_model_windings.sh` (three models, `three_wNNN.log`), all through `bin/depth_sweep.sh`
  or `run_ink.sh` directly.
- Class: KEEP. They back the null results and cost GPU hours: about 4–9 min per villa map pair and depth and about
  31 min per Hecate depth on a 3060 (about 1.5 h per winding for four models at two depths).

**Seed-42 previews and work claims**
- What: 2× downsampled seed-42 maps (`wNNN_d{-1,+0,+1,+2}_{read,blind}.png`) and per-winding done markers; claim
  directories that let several GPUs share a winding list.
- Where: box `0191/ink-triage/previews/` (20 windings, 224 M), `0191/ink-triage/claims/wNNN/` × 21,
  `claims3/wNNN/` × 9 (each holds a file `gpu`).
- Class: previews REGENERABLE (seconds). Claims are SCRATCH after the jobs end; the stale `claims3/w032` and
  `claims3/w106` (job stopped at 00:27 on 2026-10-10) make `three_model_windings.sh` skip those windings until removed.

**Ensemble images**
- What: ensemble, per-model and CT images per winding at d 0 and +1 (see Conventions).
- Where: box `0191/ink-triage/ensemble/wNNN/` (four models, w068–w072, 528 M) and `0191/ink-triage/ensemble3/wNNN/`
  (three models, w033–w036 and w103–w105, 650 M).
- Made by: `bin/ensemble_windings.sh`, `bin/three_model_windings.sh` → `bin/ink343/ensemble_maps.py`.
- Class: REGENERABLE from the maps (minutes per winding).

**Depth sweeps (paused)**
- What: all four models over a range of depths on w070 (villa d −2 … +2, Hecate d −1 and 0) and on the lasagna150
  patch (partial).
- Where: box `0191/sweeps/exp30k_snapped_w070/` (236 M, with `logs/timings.tsv` and `images_early/`) and
  `0191/sweeps/lasagna150/` (239 M).
- Made by: `bin/depth_sweep.sh` → `bin/ink343/run_depth_sweep.sh`; the resume commands are in `sweep-w070.log` and
  `sweep-lasagna150.log`.
- Class: KEEP (hours of GPU time; resumable).

**PHerc. 343 control maps and images**
- What: seed-42 maps at d −1 … +2, seed 43 / dnative / Hecate at d +1, the ensemble images at d +1, and previews;
  the calibration reference for every score.
- Where: box `data/PHerc0343/control/maps/` (16 files, 74 M), `images/` (47 M), `preview_d*_{read,blind}.png`, logs.
- Made by: `bin/control343.sh`, `bin/control343_ensemble.sh`.
- Class: KEEP.

**Fleet run 1 maps and images on the box**
- What: copies of the AWS maps and ensemble images of w073 and w074, used for box-side scoring and the
  AWS-vs-box check.
- Where: box `0191/aws-maps/{w073,w074}/` (188 M), `0191/aws-ens/{w073,w074}/` (167 M).
- Made by: `aws/fleet_score.sh` (copy); originals in Mac `data/aws-results/run1/`.
- Class: KEEP one copy (paid compute). The box copy duplicates the Mac copy.

**GTX 1660 SUPER benchmark**
- What: evidence that GPU 1 writes all-zero ink maps (seed-42 maps from the 1660 in fp16 and fp32, plus a 3060 control).
- Where: box `0191/bench1660/` (9 files, 5.7 M).
- Class: KEEP.

### 5. Scores, rankings and reviews

**Stroke scores on the box**
- What: stroke-score JSON, tile PNGs and review crops per winding and depth, and the ranking table.
- Where: box `data/strokes/` (355 M, 638 files): `wNNN/` × 23 (w036, w060–w080, w103; tags none, `_s42`, `_3m`,
  `_s4243`, `_pm`), `box3m/wNNN/` × 7 (three models, no tag), `aws/{w073,w074}/` (four models from the AWS maps),
  `c343/` (control), `ranking.tsv` (97 rows), `rank-errors.log`, `rank-force.log`, `rank-last.log`.
- Made by: `bin/stroke_rank.sh` (via `bin/stroke_watch.sh`), `bin/three_model_windings.sh`, `aws/fleet_score.sh`,
  `tmp/permodel.sh`; `_3m` and `_s4243` by an earlier version of `stroke_score.py` run by hand.
- Class: KEEP (small; `ranking.tsv` and the reviewed crops are results). Each file can be recomputed in seconds to
  minutes if the maps and renders exist.
- Note: `ranking.tsv` was last built at 23:12 UTC on 2026-10-09. `stroke_watch.sh` stops once `ensemble_windings.sh`
  and `ink_triage.sh` have ended and does not wait for `three_model_windings.sh`, so the seed-42 rows for maps added
  later (w033–w036 d 0 / +1, w103–w106) are missing. Run `bin/stroke_rank.sh` to bring it up to date.

**Review crops (Mac)**
- What: images looked at during the eye checks: `v_wNNN_ensemble[_blind]_d+NN_K.jpg` (full-resolution ensemble
  strips), `m_wNNN_d+NN.jpg` (montages), `z_w083_*.jpg` (reading/blind/CT zoom), `wNNN_ens_d+NN_K.jpg`, copies of
  `__topNN.png` crops, `c343_d+01.png`, `w070_d+00.{json,png}`, `triage-candidates.jpg`.
- Where: Mac `data/strokes/` (45 files, 19 M). Working copies of the w083/w090/w100–w102 files are in box `tmp/flag/`.
- Made by: ad hoc commands; the `v_`/`m_`/`z_` prefixes are not produced by any kept script.
- Class: KEEP.

### 6. Cloud run results (Mac)

**AWS proof of concept**
- What: one on-demand g4dn.2xlarge rendering the PHerc. 343 control and one seed-42 map at d +1; matched the box
  within 1/255.
- Where: Mac `data/aws-results/i-07316924655570581/` (named by instance id; `control343/` with maps, previews, logs;
  `instance-info.txt`), 14 M.
- Made by: `aws/poc.sh`; logs `aws/state/poc-*.log`, `bootstrap-*.log`.
- Class: KEEP.

**AWS fleet run 1**
- What: two workers, w073 and w074, four models at d 0 / +1, maps fetched.
- Where: Mac `data/aws-results/run1/w01/`, `w02/` (maps, ensemble images, previews, logs, `timings.tsv`), 463 M, 146 files.
- Made by: `FETCH_MAPS=1 aws/fleet.sh 2 --yes w073 w074` (written to `data/aws-results/fleet/`, renamed afterwards).
- Class: KEEP (paid).

**AWS fleet run 2**
- What: ten workers, 59 windings (w037–w067, w075–w102), three models at d 0 / +1, stroke scores computed on the
  workers; lite fetch, so the raw maps were not copied and are gone with the instances.
- Where: Mac `data/aws-results/run2/wNN/` × 10 (6 segments each: `ensemble/` with ct/ensemble/ensemble_blind PNGs and
  `stats.json`, `strokes/`, logs, `timings.tsv`, `DONE`), `run2/ranking.tsv` (118 rows); 2.5 G, 1,855 files.
- Made by: `aws/fleet.sh 10 --yes …` with `aws/remote/run_batch.sh`, `chain_batch.sh`, `run_segment.sh`;
  `aws/fleet_rank.sh` for the ranking (its `crops` column still points to `data/aws-results/fleet/…`). Cost about $10.70.
- Class: KEEP (paid; the maps would need a new run).

**Staged meshes**
- What: copies of the box's flattened windings uploaded to the workers, and the run manifest.
- Where: Mac `data/aws-stage/segments/exp30k_snapped_wNNN/flatten.tifxyz` × 92, `manifest.tsv` (absolute Mac paths),
  `flattest/w005/` (an unflattened community winding); 204 M.
- Made by: `aws/stage_segments.sh`.
- Class: SCRATCH between runs (re-staged from the box in minutes).

**AWS run state**
- What: run logs (`poc-*.log`, `fleet-run-*.log`, `bootstrap-*.log`), user-data, `known_hosts`, `fleet/plan.tsv`,
  per-worker records (`fleet/wNN/` with instance id, IP, type, launch time, batch), and one SSH key file.
- Where: Mac `aws/state/` (376 K, not in git).
- Class: KEEP the logs and plan (provenance and cost record). The key file is sensitive and only useful while its
  key pair exists in AWS.

### 7. Site, registry and notes (Mac)

**Research registry**
- What: the record of the project: 5 phases, 33 experiments (question, technique, result, verdict, metrics, images,
  credits), 15 findings, 4 next items, 13 credits.
- Where: `research/registry.json` (48 K, in git).
- Class: KEEP.

**Research site**
- What: GitHub Pages site rendered from the registry.
- Where: `docs/index.html`, `docs/img/` (32 images, 25 M, copied from `data/results/`), `docs/.nojekyll`; this file.
- Made by: `scripts/build_site.py`.
- Class: REGENERABLE (seconds), tracked in git.

**Result images**
- What: the images the site and notes cite (JPEG/PNG, plus git-ignored TIFF originals).
- Where: `data/results/` (94 files, 82 M).
- Made by: `scripts/pull_preview.sh` and hand conversions of box previews.
- Class: KEEP.

**Notes and references**
- What: campaign plan, daily results notes, friction log, PR drafts and patch (`notes/`, 140 K, in git); reference
  images and the community atlas manifest (`data/ref/`, 12 M).
- Class: KEEP.

**Session memory**
- `memory/` (120 K, not in git) exists; its contents are not described here.

### 8. Caches, environments, worktrees and temporary files

**uv package cache**
- Where: box `cache-root/uv/` (24 G); `~/.cache/uv` on the root disk is a symlink to it.
- The project `.venv` folders are full copies, not hardlinks into this cache.
- Class: SCRATCH (`uv cache clean`; the next `uv sync` downloads again).

**PyTorch compile caches**
- Where: box `cache-root/torchinductor/` (6.2 G), `tmp/torchinductor_tbienapfl/` (216 M).
- Class: SCRATCH (recompiled on the next run; delete only when no GPU job is running).

**VC3D remote-chunk cache**
- Where: box `/mnt/nvme/vc3d-remote-cache/` (29 G, outside the project tree): PHerc0191 CT chunks (23 G, also in the
  local mirror), PHerc0343 CT chunks (4.2 G), PHercParis4 2.4 µm level 2 (2.4 G), m7 surface (42 M), `.vc_cache.lock` files.
- Made by: `vc_render_tifxyz` and the tracer when streaming from S3. `control343.sh` passed `cache/PHerc0343-l0/` as
  the cache, which stayed empty.
- Class: SCRATCH (re-filled on the next streamed render).

**Job temporary files**
- Where: box `tmp/` (1.8 G; `TMPDIR` of the ink jobs): `run_ink.XXXXXX/` × 6 (932 M, left by interrupted
  `run_ink.sh` calls), `appimg/` (486 M, VC3D AppImage test), `flag/` (141 M, review working copies), `t343/`, `w072/`,
  `win/` (old-format score tests), loose scripts (`patch6-8.py`, `airprof.py`, `profile.py`, `permodel.sh`, `win.sh`)
  and JPEGs.
- Class: SCRATCH (move `permodel.sh` to `bin/` first if the `_pm` scores are kept).

**villa clone and environments**
- Where: box `villa/` (29 G): branch `fix/install-volcomp` at 12f21236a with three modified files (`vesuvius/uv.lock`,
  `volume-cartographer/CMakeLists.txt`, an egg-info file); `.venv` of `spiral-fitting` (8.0 G), `vesuvius` (6.9 G),
  `lasagna` (6.4 G); VC3D build tree `volume-cartographer/build/` (4.9 G; binaries installed in `~/.local/bin`);
  `lasagna/torchinductor_tbienapfl/` (129 M, compile cache inside the repo). Mac `villa/` (1.9 G, branch
  `fix/install-volcomp`, fork remote).
- Made by: `villa-clone.log`, `uv-sync-*.log`, `build-vc3d.sh` / `build-vc3d.log`, `lasagna-env.log`.
- Class: REGENERABLE (clone, `uv sync` per package, VC3D build about 20 min). Keep the local modifications until they
  are upstreamed. `lasagna/torchinductor_tbienapfl/` is SCRATCH.

**Git worktrees**
- Where: box `wt/` (9.5 G): `fiber-lasagna-import/`, `shell-confidence/`, `track-cache-signature/` (about 890 M each,
  detached HEADs carrying the staged PR commits, clean); `spiral-0fb38c45/` (6.9 G including a 6.1 G `.venv`; one
  uncommitted change in `volume-cartographer/scripts/spiral/fit_spiral.py`; used by the running old-fitter fit).
- Class: KEEP the PR worktrees until the PRs are filed (or the commits are pushed). `spiral-0fb38c45` is in use;
  afterwards REGENERABLE, except its uncommitted change.

**Small caches**
- Where: box `cache/spiral/` (track-crossing cache pickle, 8 K), `cache/spiral-old/` and `cache/PHerc0343-l0/` (empty);
  zero-byte `*.lock` files beside the respool sidecars and in `volumes/…/.dl_cache/`.
- Class: SCRATCH.

**Job logs and scripts**
- Where: box top level `*.log` × 105 (2.0 M) and `0191/*.log` × 10 (download logs); scripts in `bin/` (528 K) and
  `build-vc3d.sh`.
- Class: KEEP (provenance and code; scripts are synced to `box/bin/` in git).

## Open questions

1. Which resident-pool copy does the old fitter (villa 0fb38c45) read? `spiral-dataset-old/lasagna_inputs/` symlinks to
   the CT-masked copy in `spiral-dataset/lasagna_inputs/`, but the fitters' logs print only base names. Confirm before
   deleting that copy (17.6 G).
2. Where did the surface tracks (`0191/spiral/20250821151635/tracks/`, 21 G) come from? `tracks-download.log` records
   no URL; `extract.json` names the m7 prediction on S3. Needed to confirm SOURCE.
3. How were the community windings (`0191/community-fit/`) and `data/ref/atlas/manifest.csv` fetched, and at which
   version? No script is kept.
4. What points VC3D's remote cache at `/mnt/nvme/vc3d-remote-cache/`? It is not set in `~/.bashrc` or `~/.profile`,
   and the `--volume` cache paths given by `control343.sh`, `grow_qa.sh` and `pilot_qa.sh` stayed empty.
5. The `_3m` and `_s4243` stroke files and the Mac review crops (`v_`, `m_`, `z_` prefixes) have no producer script.
   Recreate the commands in `bin/` or mark the files as historical.
6. The three-model pass stopped at 00:27 on 2026-10-10 with w032 and w106 unfinished (stale claims, `tmp/run_ink.nMRWSU`
   empty). Was this a deliberate stop to free GPUs for `exp30k-z11200` and the community flattening?
7. Keep or drop: the winding-model cache (104 G), the non-exp-30k fit checkpoints (8.4 G), the fiber outputs (11 G),
   the tracer QA renders (5.1 G) and the day-1 `runs/` (1.1 G). All are regenerable; the decision depends on whether
   those routes will be revisited.
8. `data/aws-results/fleet/` was renamed to `run1`/`run2` after each run, but `run2/ranking.tsv`,
   `notes/results-2026-10-09.md` (which cites `data/aws-results/fleet-run2-ranking.tsv`) and the fleet scripts still
   use the old path. Settle one naming scheme before the next fleet run.
