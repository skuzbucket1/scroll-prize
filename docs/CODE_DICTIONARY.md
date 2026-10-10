# Code dictionary

This file lists every script in the repository and what it does. That covers the GPU-box scripts mirrored in `box/bin/` (including Erwin Nieuwlaar's scripts in `box/bin/ink343/`), the AWS scripts in `aws/`, and the Mac helpers in `scripts/`. Each entry is taken from the script's own header comment or argument parser and was then checked by hand against the code. Where a header and the code disagree, the entry follows the code, and the disagreement is listed at the end. The mirror in `box/bin/` was compared with the box copy (`~/scroll-prizes/bin/`) by checksum. The two copies are identical except for two box-only scripts, listed under "Not yet mirrored". The `aws/` entries describe the working tree on this date, including changes not yet committed (on-worker flattening, Scan-Quality-Map, `SNAPPED_DIR` staging).

Date: 2026-10-10

**The main path today** (updated 2026-10-10 midday; any scroll):
1. Assemble the spiral dataset (`assemble_spiral_dataset.sh` with `smooth_umbilicus.py`, `ray_peaks.py`).
2. Spiral fit (`fit_band.sh`; earlier PHerc. 0191 fits used `fit_experiment.sh`, `fit_old_phase.sh`).
3. Snap the windings onto the surface prediction (`snap_band.sh` → `snap_meshes_nieuwlaar.py`).
4. Flatten (`flatten_winding.sh`), then make a 66-layer render (`render66.sh`). `triage_band.sh` runs both and writes CT previews (`SCROLL=` for scrolls other than PHerc. 0191).
5. Make ink maps (`ink343/run_ink.sh`), run by `deep_look.sh` (four models, depth tiers) or `band_three_model.sh` (three models, d 0/+1).
6. Make ensemble images (`ink343/ensemble_maps.py`) and score and rank (`tools/stroke-score`), run by `deep_score.sh` / `band_score3.sh`.
7. Look at the flagged areas by eye.

The older path (PHerc. 0191, band z 9000–10000) used `snap_exp30k.sh`, `triage_windings.sh`, `depth_sweep.sh`, `ensemble_windings.sh`, `three_model_windings.sh`, `stroke_score.py`, `stroke_rank.sh` and the AWS fleet.

## Conventions

**Shorthand used below.** Box scripts are run as `bin/<script>` from `~/scroll-prizes` on the GPU box `llm`.
- `$S` = `~/scroll-prizes`, a symlink to `/mnt/nvme/scroll-prizes` (both spellings appear in the scripts). Job logs are `$S/*.log`.
- `$D` = `/mnt/nvme/scroll-prizes/data/PHerc0191`.
- Python environments: `$S/villa/vesuvius/.venv` (ink, zarr), `$S/villa/spiral-fitting` (`uv run`), `$S/villa/lasagna/.venv` (flattening).
- VC3D tools (`vc_render_tifxyz`, `vc_grow_seg_from_seed`, …) are in `~/.local/bin`.

**Scans.**
- PHerc. 0191: `PHerc0191/volumes/20250821151635-9.362um-1.2m-113keV-masked.zarr`. Voxels are 9.362 µm, 113 keV, 8387 × 8387 × 18977 at level 0. The source is the public bucket `vesuvius-challenge-open-data` (us-east-1). A local mirror is at `$D/volumes/`.
- PHerc. 0343 (the positive control): `PHerc0343/volumes/20250521140437-8.640um-1.2m-116keV-masked.zarr`. Voxels are 8.64 µm, 116 keV. It is streamed from S3, not mirrored.
- Winding names `wNNN` are winding indices of a spiral fit. For example, `exp30k_snapped_w070_66` is winding 70 of fit run exp-30k, snapped, flattened and rendered with 66 layers. The exp-30k windings used are w020–w119.

**66-layer render.** Made by `render66.sh`, `control343.sh` and `aws/remote/run_segment.sh`, all without `--flip-normals`.
- Layer index k = 0..65. Layer k samples the CT at k − 32.5 voxels along the mesh normal.
- Depth d = k − 33. Positive d points away from the scroll axis.
- villa ink models (ink_9um seeds 42 and 43, dense_native) read a 17-layer window, layers s..s+16, centred on layer 33 + d, with s = 25 + d. The file tag is `L66s<s>`; for example, d = +1 gives `L66s26`.
- Hecate reads 16 planes resampled to 9.6 µm, centred at zc = 32.5 + d. The file tag is `L66zc<zc>` with two decimals; for example, d = +1 gives `L66zc33.50`.
- Ink map names, written by `ink343/run_ink.sh`:
  - villa models: `<name>__<model>__L66s<s>[_reverse].tif`
  - Hecate: `<name>__hecate__L66zc<zc>[_reverse].png`
  - `<name>` is the render's folder name without `.zarr`. `<model>` is one of `hybrid_3d2d-seed42`, `hybrid_3d2d-seed43`, `dnative`, `hecate`.
  - `ensemble_maps.py` and `stroke_score.py` use the short names `ink9-42`, `ink9-43`, `dnative`, `hecate`.
- villa map values are uint8 = trunc(255 · p). Every preview uses the display stretch clip((v − 64) / 128, 0, 1), which equals (p − 0.25) / 0.5 and undoes the models' label smoothing.

**Sides and orientation.**
- `_reverse` maps show the READING side (the face with the text). Plain (forward) maps show the BLIND side, which serves as the null for the same sheet.
- This rule holds for the 66-layer route only. The older 28-layer QA renders (`pilot_qa.sh`, `winding_qa.sh`, `patch_qa.sh`, `grow_qa.sh`) used `--flip-normals` and the full layer stack, so the rule has not been established for their maps.
- Ensemble images (`ensemble_maps.py`, default `--orientation reading`) and stroke-score tile positions are in reading orientation: rotated 180° from the render (rows and columns reversed).
- Single-model previews (`*_d+N_read.png`, `*_d+N_blind.png`) are in render orientation.

**GPUs on the box.**
- Use only these three:
  - GPU 0: RTX 3060 12 GB, `GPU-2d9651e9-…`
  - GPU 2: RTX 3060 Ti 8 GB, `GPU-54088dd3-…`
  - GPU 3: RTX 3060 12 GB, `GPU-7937f33e-…`
- Scripts either take a full UUID for `CUDA_VISIBLE_DEVICES` or hard-code one.
- GPU 1 (GTX 1660 SUPER, `GPU-33b8aac6-6d34-6282-b644-f5407aa8f190`) is never used. Scripts that take a GPU argument refuse this UUID and exit with code 97. The check matches the UUID string only (see the inconsistencies at the end).

**Jobs on the box.**
- Pattern:
  1. Start the job in the background: `setsid -f bash -c 'bin/<script> …' > $S/<job>.log 2>&1 < /dev/null`.
  2. The job writes to that log.
  3. The job's last line is a completion marker, `<NAME>-EXIT: <rc>`.
- Waiter scripts poll other jobs' logs for markers (`until grep -q 'X-EXIT' <log>; do sleep 60; done`). Renaming a log therefore breaks its waiters.
- Most scripts print to stdout and the launcher chooses the log name. Log names marked "(launcher)" below are the names used so far. Entries say so when a script writes its own log.
- Many markers are printed as `: 0` whenever the loop finishes. For these, the marker means "finished", not "succeeded", and the entry says "always 0".

---

## 1. Data mirroring and setup

Copies of the public scroll data from the Vesuvius Challenge S3 bucket onto the box's NVMe, the model checkpoints, and the input dataset for the spiral fit.

#### `box/bin/mirror_s3_v2.py`
Mirrors a public S3 prefix (for example an OME-Zarr volume or one pyramid level) to local disk.
- **Usage:** `python3 bin/mirror_s3_v2.py <bucket-url> <prefix/> <dest-dir> [threads=32] [--levels 5,4,3,2,1,0] [--relist]`
- **In → out:** S3 keys → `<dest-dir>/…`. It also writes a cached listing `<dest-dir>/.mirror-listing.json` (refresh it with `--relist`) and failures to `<dest-dir>/.mirror-failed.txt`. It keeps one connection open per thread and resumes by exact file size.
- **Runs on:** GPU box (stdlib Python). **Log/marker:** launcher; for example `$D/mirror-lasagna-v2-PHerc0191_{nx,ny,grad_mag}.log` and `$D/mirror-normalgrids.log`. Marker `MIRROR-EXIT: 0|1`.
- **Status:** current. **Origin:** ours (MIT).

#### `box/bin/ink343/rebuild_dense_native_pth.py`
Wraps the public dense_native safetensors weights and training config into a checkpoint that villa can load.
- **Usage:** `python rebuild_dense_native_pth.py dense_native_016000.safetensors train_dense_native.json dense_native-016000.rebuilt.pth`
- **In → out:** weights and config (from Hugging Face `Nieuwlaar/ink9um-dense-native`) → `.pth`. Its maps match the original checkpoint's within 1/255.
- **Runs on:** GPU box and AWS worker (called by `aws/remote/setup_models.sh`). **Log/marker:** prints `written <path>`.
- **Status:** current. **Origin:** Nieuwlaar (MIT).

#### `box/bin/ink343/fetch_checkpoints.sh`
Downloads the public ink checkpoints and `hecate.py` listed in a `models.tsv`, checks every file's sha256, and rebuilds dense_native if the exact training file is missing.
- **Usage:** `fetch_checkpoints.sh [MODELS_TSV=/opt/pherc0343/models.tsv] [CKPT_DIR=/opt/ckpt]`
- **In → out:** `models.tsv` (not in this repo) → `CKPT_DIR/*` and `CKPT_DIR/SHA256SUMS.local`.
- **Runs on:** not run here. **Log/marker:** stdout.
- **Status:** unclear (unused here). On the box, `$S/checkpoints/ckpt343/` was laid out by hand. On AWS, `aws/remote/setup_models.sh` does the same job. **Origin:** Nieuwlaar (MIT).

#### `box/bin/mirror_band_pherc0813.sh`
Phase B1: mirrors one band of PHerc. 0813 (z 12000–13000) and the scroll-wide inputs a spiral fit needs into `data/PHerc0813/source/`.
- **Usage:** `bin/mirror_band_pherc0813.sh`
- **In → out:** S3 / dl.ash2txt.org → CT level 0 rows 93–101 (z 11904–13055) + levels 2–5, m7 surface prediction level 0 rows 62–67, normal grids, Lasagna nx/ny/grad_mag levels 2–4, the spiral tracks dataset. Resumable (size-verified). The top-level `.zgroup`/`.zattrs` of the CT are not copied; the B2 launcher fetches them.
- **Runs on:** GPU box (network). **Log/marker:** `runs/2026-10-10_mirror-pherc0813-band/`; `MIRROR0813-EXIT: 0`.
- **Status:** done 2026-10-10 (75 GB, 0 failed). **Origin:** ours (MIT).

#### `box/bin/assemble_spiral_dataset.sh`
Phase B2: assembles any scroll's spiral-fit dataset from its mirrored inputs (the generic successor of `assemble_pherc0191.sh`).
- **Usage:** `bin/assemble_spiral_dataset.sh <scroll> <audit z> [left_handed=false] [z_top_to_bottom=false] [um=9.362]`
- **In → out:** `data/<scroll>/source/` → `data/<scroll>/inputs/spiral-dataset/`: links to tracks and Lasagna stores, `spiral-scroll.json`, `umbilicus_raw.json` (vc_gen_umbilicus, every 16th slice, 5 seeded repeats) and the smoothed `umbilicus.json`, a ray audit on CT level 2 at the audit slice with a preview `qa/umbilicus_z<z>.png`, and resident-pool sidecars in `lasagna_inputs/`.
- **Runs on:** GPU box (CPU). **Log/marker:** launcher log; `ASSEMBLE-EXIT: 0|1` (0 if the umbilicus and the resident pools exist).
- **Status:** current. **Origin:** ours (MIT).

#### `box/bin/smooth_umbilicus.py`
Smooths a vc_gen_umbilicus result the way PHerc. 0191's was smoothed: local-median outlier rejection (> 400 voxels from the median of ±8 neighbours), then a ±4-point moving average of the inliers.
- **Usage:** `python3 bin/smooth_umbilicus.py <raw.json> <out.json> [--maxdev 400]`
- **In → out:** raw control points → smoothed control points (the raw file is untouched); prints outlier count and median step before/after.
- **Runs on:** anywhere (CPU). **Log/marker:** stdout. **Status:** current. **Origin:** ours (MIT).

### Older and one-off

#### `box/bin/mirror_s3.py`
First version of the S3 mirror. It lists keys, then downloads with a thread pool, retrying and resuming by size.
- **Usage:** `python3 bin/mirror_s3.py <bucket-url> <prefix/> <dest-dir> [threads=32] [--levels 5,4,3,2,1,0]`
- **In → out:** as in v2, but with no cached listing and one TLS handshake per object.
- **Runs on:** GPU box. **Log/marker:** launcher, `$D/mirror-volume.log` (the CT volume mirror). Marker `MIRROR-EXIT: 0|1`.
- **Status:** superseded by `mirror_s3_v2.py`. **Origin:** ours (MIT).

#### `box/bin/fetch_zarr.py`
Downloads selected pyramid levels of a remote zarr v2 group by computing the chunk keys from `.zarray`, without listing.
- **Usage:** `python3 bin/fetch_zarr.py <zarr URL> <dest dir> <levels, e.g. 0,1,2> [threads=16]`
- **In → out:** remote zarr → local copy (existing chunks are skipped; a 404 counts as a missing chunk).
- **Runs on:** GPU box. **Log/marker:** launcher, for example `$S/dl-surfvol-7.91um.log`. `DL-EXIT: 0` is printed only if no exception was raised.
- **Status:** one-off (day-1 downloads); `mirror_s3_v2.py --levels` covers the same need. **Origin:** ours (MIT).

#### `box/bin/dl_pherc0800.sh`
Downloads the pre-rendered 8.64 µm surface volumes (levels 0–5) of six public PHerc. 0800 auto_grown segments with `fetch_zarr.py`. It has no header comment.
- **Usage:** `bin/dl_pherc0800.sh`
- **In → out:** S3 → `$S/data/PHerc0800/segments/<seg>/surface-volumes/8.64um-1.2m-116keV-volume-20250521135224.zarr`
- **Runs on:** GPU box. **Log/marker:** launcher, `$S/dl-pherc0800.log`; `DL0800-EXIT: <rc>`.
- **Status:** one-off. **Origin:** ours (MIT).

#### `box/bin/mirror_surf_band.sh`
Mirrors level 0 of the m7 surface prediction for the pilot band (z chunk rows 46–52, z 8832–10176).
- **Usage:** `bin/mirror_surf_band.sh`
- **In → out:** S3 → `$D/surf-m7/20250821151635-surface-20260413222639-surface-m7-L0-th0.2.zarr/0/46..52`
- **Runs on:** GPU box. **Log/marker:** launcher, `$S/mirror-surf-band.log` (`snap_exp30k.sh` waits on it); `SURFMIRROR-EXIT: 0` (always 0).
- **Status:** one-off. **Origin:** ours (MIT).

#### `box/bin/mirror_surf_band_l1.sh`
The same as `mirror_surf_band.sh`, but for level 1, rows 22–27. It has no header comment.
- **Usage:** `bin/mirror_surf_band_l1.sh`
- **In → out:** S3 → `$D/surf-m7/…m7-L0-th0.2.zarr/1/22..27`
- **Runs on:** GPU box. **Log/marker:** stdout; `SURFMIRRORL1-EXIT: 0` (always 0).
- **Status:** one-off. **Origin:** ours (MIT).

#### `box/bin/resume_volume_after_lasagna.sh`
Waits until the three Lasagna v2 stores have finished mirroring, then resumes the paused CT volume mirror with SIGCONT.
- **Usage:** `bin/resume_volume_after_lasagna.sh`
- **In → out:** waits for `MIRROR-EXIT` in `$D/mirror-lasagna-v2-PHerc0191_{nx,ny,grad_mag}.log`, then signals `pgrep -f 'mirror_s3.py.*volumes/'`.
- **Runs on:** GPU box. **Log/marker:** launcher, `$S/resume-volume.log`. It prints "volume mirror RESUMED" and has no EXIT marker.
- **Status:** one-off (done). **Origin:** ours (MIT).

#### `box/bin/switch_lasagna_to_v2.sh`
Stops the v1 Lasagna mirrors, deletes their `.part` files, rewrites `assemble_pherc0191.sh` and `resume_volume_after_lasagna.sh` in place (with `sed -i`) to wait on the v2 logs, and relaunches both.
- **Usage:** `bin/switch_lasagna_to_v2.sh`
- **In → out:** edits two scripts and kills and restarts processes.
- **Runs on:** GPU box. **Log/marker:** stdout; `SWITCH-OK <date>`.
- **Status:** one-off (done; the edits are already in the mirrored copies). Do not re-run it. **Origin:** ours (MIT).

#### `box/bin/assemble_pherc0191.sh`
Phase 1: builds the spiral-fit dataset once the mirrors have landed. It runs `vc_gen_umbilicus` on the normal grids and `pack_resident_pools.py` on the Lasagna stores.
- **Usage:** `bin/assemble_pherc0191.sh`
- **In → out:**
  - Waits for `MIRROR-EXIT: 0` in the normal-grid and Lasagna v2 logs, and for the CT mirror to start level 1.
  - Writes `$D/spiral-dataset/umbilicus.json` and `umbilicus_estimates.csv` (every 16th slice, `--repeats 5`, seed 1).
  - Writes resident-pool sidecars in `$D/spiral-dataset/lasagna_inputs/`.
  - The `umbilicus.json` in use was later smoothed; the raw copy is `umbilicus_raw.json`.
- **Runs on:** GPU box. **Log/marker:** launcher, `$S/assemble-pherc0191.log`; `ASSEMBLE-EXIT: 0|1` (0 if the umbilicus and the resident pools exist).
- **Status:** one-off (done 2026-10-08). **Origin:** ours (MIT).

#### `box/bin/hf_winding.sh`
Downloads the public winding model.
- **Usage:** `bin/hf_winding.sh`
- **In → out:** Hugging Face `scrollprize/winding_model_9um` → `$S/checkpoints/winding_model_9um/` (`ckpt_final.pth`)
- **Runs on:** GPU box. **Log/marker:** stdout; `HFWIND-EXIT: <rc>`.
- **Status:** one-off (done). **Origin:** ours (MIT).

#### `box/bin/hf_ink_extra.sh`
Downloads the Hecate and dense_native ink models. It has no header comment.
- **Usage:** `bin/hf_ink_extra.sh`
- **In → out:** `scrollprize/hecate` → `$S/checkpoints/hecate/`; `Nieuwlaar/ink9um-dense-native` → `$S/checkpoints/dense_native/`
- **Runs on:** GPU box. **Log/marker:** stdout; `HFINK-EXIT` (it reports the exit code of the final `ls`, not of the download).
- **Status:** one-off (done). **Origin:** ours (MIT).

---

## 2. Geometry

Turning the CT into winding surfaces: spiral fitting and its inputs (umbilicus, outer shell, winding-model supervision), snapping fitted windings onto the surface prediction, flattening, patch growing (tracer tests), and checks of the resulting geometry.

#### `box/bin/fit_experiment.sh`
Runs one controlled spiral fit on PHerc. 0191 with the current villa fitter.
- **Usage:** `bin/fit_experiment.sh <tag> <GPU UUID> '<extra overrides JSON>'`
- **In → out:**
  - Base overrides: z 9000–10000, 10k steps, tracks on, `grad_mag` dense spacing, and no shell, patches, fibres or point clouds. The extra JSON is merged on top. Keys not found in `villa/spiral-fitting/config.py` are dropped and listed on stderr.
  - Input: `$D/spiral-dataset/`.
  - Output: `$D/spiral-output/<run>*<tag>*/` (`meshes/fitted_<tag>/wNNN_<tag>/`, `satisfaction_metrics_fitted.json`, `checkpoint_fitted.ckpt`). Cache: `/mnt/nvme/scroll-prizes/cache/spiral`.
- **Runs on:** GPU box (GPU). **Log/marker:** the script writes the full log `$S/fit-<tag>-full.log`. Its summary goes to the launcher log `$S/fit-<tag>.log`. `FIT-EXIT: <rc>` follows the satisfied-track fractions.
- **Status:** current. **Origin:** ours (MIT).

#### `box/bin/fit_old_phase.sh`
Applies the PHerc. 343 winner's fit recipe to our band, using the fitter from before villa simplified it (worktree at villa `0fb38c45`): surface SDT plus phase spacing, no shell, `track_crossing_mode` count, 30k steps.
- **Usage:** `bin/fit_old_phase.sh [tag=old-phase-30k] [GPU UUID=GPU 0]`
- **In → out:**
  - Waits for `SDT-EXIT` in `$S/surf-sdt.log` (the SDT is built outside `bin/`).
  - Input: `$D/spiral-dataset-old/`. Output: `$D/spiral-output-old/*<tag>*/`. Cache: `cache/spiral-old`.
- **Runs on:** GPU box (GPU). **Log/marker:** full log `$S/fit-<tag>-full.log`; launcher `$S/fit-old-phase-30k.log`. `FIT-EXIT: <rc>`, or 90 if the SDT build failed.
- **Status:** current. **Origin:** ours (MIT).

#### `box/bin/snap_meshes_nieuwlaar.py`
Snaps each vertex of the fitted windings along its normal onto the nearest predicted sheet, with outlier rejection and smoothing.
- **Usage:** `SURF_ZARR=<m7 surface zarr> python bin/snap_meshes_nieuwlaar.py <meshes_dir> <scroll> <out_dir> --windings windings.txt [--z0 Z0 --z1 Z1] [--max-off 15] [--jump 6] [--sigma 1.0] [--level 0] [--procs 8]`
- **In → out:** tifxyz windings plus `SURF_ZARR` (for us `$D/surf-m7/…m7-L0-th0.2.zarr`) → `<out_dir>/<winding>/{x,y,z}.tif` + `meta.json`, plus `<out_dir>/snap_report.tsv` (appended). `--procs` defaults to `$RANK_PROCS` or 8.
- **Runs on:** GPU box (CPU). **Log/marker:** stdout.
- **Status:** current. **Origin:** Nieuwlaar (MIT), a copy of `mesh/snap_meshes.py`. Licence: `box/bin/LICENSE-snap_meshes_nieuwlaar`.

#### `box/bin/flatten_winding.sh`
Flattens one tifxyz segment with Lasagna, the step the organisers recommend before rendering.
- **Usage:** `bin/flatten_winding.sh <tifxyz dir (abs)> <out dir (abs)> [GPU UUID=GPU 3]`
- **In → out:** tifxyz → `<out>/tifxyz/flatten.tifxyz` (plus `<out>/flatten_input.json`). Config: `villa/lasagna/configs/flatten_fast_nofilter.json`.
- **Runs on:** GPU box (GPU). **Log/marker:** the script writes `<out>/flatten.log` itself and appends `FLATTEN-EXIT: <rc>` to it.
- **Status:** current. **Origin:** ours (MIT).

#### `box/bin/make_outer_shell.py`
Derives the fitter's `outer_shell/` tifxyz from the masked CT, using the boundary of the largest non-zero component in each slice.
- **Usage:** `python bin/make_outer_shell.py <volume.zarr> <umbilicus.json> <out_dir> [--level 2] [--dz 8] [--z-begin 0] [--z-end N] [--theta-bins 720] [--radius-percentile 100]`
- **In → out:** CT + umbilicus → `<out_dir>/{x,y,z}.tif` (rows are z samples, columns are theta bins, −1 means empty), `meta.json` and `shell_stats.json`. Use `--dz 1`.
- **Runs on:** GPU box (CPU). **Log/marker:** launcher, `$S/outer-shell.log`; the launcher appends `SHELL-EXIT` (the script prints no marker).
- **Status:** current. **Origin:** ours (MIT).

#### `box/bin/mesh_in_mask.py`
For each winding of a fit run, reports the fraction of vertices that fall inside the papyrus (non-zero CT) and the mean radius from the umbilicus.
- **Usage:** `python bin/mesh_in_mask.py <run_dir> <volume.zarr> <umbilicus.json> [--level 2] [--stride 4]`
- **In → out:** `<run_dir>/meshes/*/wNNN_*` (spliced meshes skipped) → table on stdout and `<run_dir>/mesh_in_mask.json`.
- **Runs on:** GPU box (CPU). **Log/marker:** stdout.
- **Status:** current. **Origin:** ours (MIT).

#### `box/bin/ray_peaks.py`
Audits the winding count and umbilicus on one CT slice by casting rays from a centre and counting sheet peaks along each ray.
- **Usage:** `python bin/ray_peaks.py <volume.zarr> <z_full_res> [--level 2] [--center X Y] [--umbilicus umbilicus.json] [--rays 12] [--step 1.0]`
- **In → out:** CT slice → table on stdout (distance to the first sheet, peak counts at three prominence levels, autocorrelation period, check of the core disk).
- **Runs on:** GPU box (CPU). **Log/marker:** launcher, for example `$S/ray-peaks-9500.log`.
- **Status:** current. **Origin:** ours (MIT).

#### `box/bin/patch_qa.sh`
Quick QA of one tifxyz mesh:
1. Geometry stats (PCA aspect ratio, self-intersection via `vc_tifxyz_selfcross`).
2. A 28-slice render streamed from S3.
3. ink_9um seeds 42 and 43 in both directions.
4. Previews.
- **Usage:** `bin/patch_qa.sh <tifxyz mesh dir> <out dir> <GPU UUID>`
- **In → out:** mesh → `<out>/selfcross.json`, `render.zarr`, `render.log`, `render_z14_ds2.tif`, `ink_seed4N-75000[_reverse].tif`, `*_preview-ds2.tif`, and `volume_cache/`.
- **Runs on:** GPU box (GPU). **Log/marker:** stdout; `PATCHQA-EXIT` is 1 if the render fails and 0 otherwise, even if inference failed.
- **Status:** current for geometry checks. Its ink part is the older 28-layer route (`--flip-normals`). **Origin:** ours (MIT).

#### `box/bin/fit_band.sh`
Spiral fit of one z band of any scroll with our best recipe (exp-30k: tracks only, `grad_mag` spacing, no outer shell, 30k steps).
- **Usage:** `bin/fit_band.sh <scroll> <fit-id> <GPU UUID> <z0> <z1> [steps=30000]`
- **In → out:** `data/<scroll>/inputs/spiral-dataset/` → `data/<scroll>/geometry/<fit-id>/fit-runs/<run>/`, linked as `geometry/<fit-id>/fit`; full log `geometry/<fit-id>/fit-full.log`. Cache `cache/spiral-<scroll>`. Refuses GPU 1 by UUID and by index.
- **Runs on:** GPU box (GPU). **Log/marker:** launcher log; `FIT-EXIT: <rc>` after the satisfied-track fractions.
- **Status:** current. **Origin:** ours (MIT).

#### `box/bin/snap_band.sh`
Snaps every fitted winding of one fit of any scroll onto its m7 surface prediction (`snap_meshes_nieuwlaar.py`, 3 processes, level 0).
- **Usage:** `bin/snap_band.sh <scroll> <fit-id> <z0> <z1>`
- **In → out:** `geometry/<fit-id>/fit/meshes/fitted_*/wNNN` + `data/<scroll>/source/surface-m7/*.zarr` → `geometry/<fit-id>/snapped/<winding>/`, `snap_report.tsv`, `snap.log`.
- **Runs on:** GPU box (CPU). **Log/marker:** launcher log; `SNAP-EXIT: <rc>`. **Status:** current. **Origin:** ours (MIT).

### Older and one-off

#### `box/bin/pilot_fit_pherc0191.sh`
Phase 2 pilot: fits the band z 9000–10000 via the minimal input route (tracks + Lasagna normals + umbilicus).
- **Usage:** `bin/pilot_fit_pherc0191.sh`
- **In → out:** waits for `ASSEMBLE-EXIT` in `$S/assemble-pherc0191.log`. Writes `$D/spiral-output/*pilot-z9000-10000*/`. GPU 0 is hard-coded.
- **Runs on:** GPU box (GPU). **Log/marker:** full log `$S/pilot-fit-full.log`; launcher `$S/pilot-fit.log`. `PILOT-EXIT: <rc>`, or 90 if the assembly failed.
- **Status:** superseded by `fit_experiment.sh` (same base overrides, but with parameters). **Origin:** ours (MIT).

#### `box/bin/exp_shell105.sh`
A gated launcher. After `SHELL-EXIT: 0` it runs `fit_experiment.sh exp-shell105` on GPU index 2, with the real outer shell, `shell_outer_winding_idx` 105 and the gap expander at 110.
- **Usage:** `bin/exp_shell105.sh`
- **In → out:** `$D/spiral-dataset/outer_shell/` → a fit run tagged `exp-shell105`.
- **Runs on:** GPU box. **Log/marker:** the script writes `$S/fit-exp-shell105.log` itself; `FIT-EXIT` comes from `fit_experiment.sh`.
- **Status:** one-off. **Origin:** ours (MIT).

#### `box/bin/shell_dense_and_rerun.sh`
Does three things in order:
1. Builds a dense (dz 1) outer shell for z 8500–10500 and swaps it into `spiral-dataset/outer_shell`, keeping the old one as `outer_shell_dz8`.
2. Launches `fit_experiment.sh exp-shell105b` on GPU index 2.
3. Builds the full-scroll dz-1 shell as `outer_shell_dz1`.
- **Usage:** `bin/shell_dense_and_rerun.sh`
- **In → out:** CT + umbilicus → `$D/spiral-dataset/outer_shell_band8500-10500`, `outer_shell`, `outer_shell_dz1`. The fit logs to `$S/fit-exp-shell105b.log`.
- **Runs on:** GPU box. **Log/marker:** the script writes `$S/shell-dense.log` itself; markers `SHELLBAND-EXIT`, `SHELLDZ1-EXIT`.
- **Status:** one-off. **Origin:** ours (MIT).

#### `box/bin/queue_after_winding.sh`
Launches two gated fits:
- `exp-dirlow` on GPU 3 after `WINDING-EXIT`: `sym_dirichlet` weight 2.5, shell index 125.
- `exp-wm` on GPU 2 after `EXPORT-EXIT: 0`: `dense_spacing_mode winding_model`.
- **Usage:** `bin/queue_after_winding.sh`
- **In → out:** watches `$S/winding-band.log`. The fits log to `$S/fit-exp-dirlow.log` and `$S/fit-exp-wm.log`.
- **Runs on:** GPU box. **Log/marker:** the script writes `$S/queue-after-winding.log` itself; `QUEUE-EXIT: 0` (always 0).
- **Status:** one-off. **Origin:** ours (MIT).

#### `box/bin/queue_wm.sh`
Only the `exp-wm` half of `queue_after_winding.sh`. It uses the same log and marker.
- **Usage:** `bin/queue_wm.sh`
- **In → out / Runs on / Log:** as in `queue_after_winding.sh`.
- **Status:** one-off (a duplicate). **Origin:** ours (MIT).

#### `box/bin/shell_lookup_test.py`
Checks `fit_spiral.ShellPolarMap` empirically on our `outer_shell`: it builds the table as the fitter does (z 8840–10160, 720 bins) and queries random points at z 9525, radii 10–30 mm.
- **Usage:** no arguments. Run it from `villa/spiral-fitting`, because it imports `config`, `tifxyz` and `fit_spiral` from the working directory.
- **In → out:** `$D/spiral-dataset/{outer_shell,umbilicus.json}` → statistics on stdout.
- **Runs on:** GPU box (CPU). **Log/marker:** stdout.
- **Status:** one-off (reproduction for a friction-log item). **Origin:** ours (MIT).

#### `box/bin/winding_smoke.sh`
Smoke test of winding-model native-phase inference on z 9000–10000 (256 slabs).
- **Usage:** `bin/winding_smoke.sh`
- **In → out:**
  - Waits until CT chunk dir `0/85` is present and both `fit-exp-30k` and `fit-exp-track2x` have printed `FIT-EXIT`.
  - Picks the fit with the best `satisfied_track_points_fraction`. GPU 3 is hard-coded.
  - Writes `$D/winding/band9000-10000/smoke.zarr`, `smoke_bs<bs>.log` and `smoke_bs<bs>_vram.txt`.
- **Runs on:** GPU box (GPU). **Log/marker:** the script writes `$S/winding-smoke.log` itself; `SMOKE-EXIT: <rc>`.
- **Status:** one-off (done). **Origin:** ours (MIT).

#### `box/bin/winding_band.sh`
Builds the full winding-model native-phase cache for a band, then exports it as Spiral supervision.
- **Usage:** `bin/winding_band.sh <winding-step> <seed-spacing> [batch-size=2] [gpu-uuid=GPU 3] [z0=9000] [z1=10000] [wfirst=10] [wlast=110]`
- **In → out:**
  - Bootstraps from the best fit run. Writes `$D/winding/band<z0>-<z1>/winding_native_phase_ws<step>_ss<spacing>.zarr`, `band_ws*_ss*.log`, `band_vram.txt` and `export_ws*_ss*.log`.
  - Writes the store `$D/spiral-dataset/winding_inference`; an older store is moved to `.bak.<ts>`.
  - The header promises a disk guard that aborts, but the code only prints the numbers.
- **Runs on:** GPU box (GPU). **Log/marker:** the script writes `$S/winding-band.log` itself; markers `WINDING-EXIT: <rc>` and `EXPORT-EXIT: <rc>`.
- **Status:** one-off. It produced the 104 GB `ws8_ss96` cache, which can be deleted now that it has been exported. **Origin:** ours (MIT).

#### `box/bin/export_wm.sh`
Re-runs only the export step for the `ws8_ss96` cache (4 workers) and validates the store.
- **Usage:** `bin/export_wm.sh`
- **In → out:** `$D/winding/band9000-10000/winding_native_phase_ws8_ss96.zarr` → `$D/spiral-dataset/winding_inference`. Its own log is `…/export_ws8_ss96.log`.
- **Runs on:** GPU box. **Log/marker:** appends to `$S/winding-band.log`; `EXPORT-EXIT: <rc>` triggers `queue_wm.sh`.
- **Status:** one-off. **Origin:** ours (MIT).

#### `box/bin/fiber_band.sh`
Runs Fiber-direction inference (SD2 checkpoint, the README's 9 µm transfer recipe) on z 8500–10500 at level 0 from the local mirror.
- **Usage:** `bin/fiber_band.sh`
- **In → out:** waits for `HFSD2-EXIT`, `MIRROR-EXIT` and two `FIT-EXIT`s. GPU 0 is hard-coded. Writes `$D/fiber/band8500-10500/fiber.lasagna.json` and `infer.log`.
- **Runs on:** GPU box (GPU). **Log/marker:** launcher, `$S/fiber-band.log`; `FIBER-EXIT: <rc>`.
- **Status:** one-off. **Origin:** ours (MIT).

#### `box/bin/make_dirfield_zarr.py`
Builds a direction-field root (`x/<L>`, `y/<L>`, `z/<L>`) for `vc_grow_seg_from_seed` from a Lasagna-style nx/ny pair. x and y are symlinks; only z is computed.
- **Usage:** `python bin/make_dirfield_zarr.py <nx.ome.zarr> <ny.ome.zarr> <out_root> --level 2 [--slab 64]`
- **In → out:** nx/ny pyramids → `<out_root>`. It was used for `$D/fiber/band8500-10500/dirfield.zarr` and `$D/fiber/dirfield_lasagna.zarr`.
- **Runs on:** GPU box (CPU). **Log/marker:** launcher, `$S/dirfield-build.log` and `$S/dirfield-lasagna-build.log`; the launcher appends `DIRFIELD-EXIT` / `DIRFIELDL-EXIT`.
- **Status:** one-off experiment (the tracer route is not in use). **Origin:** ours (MIT).

#### `box/bin/snap_exp30k.sh`
Snaps windings w020–w119 of the exp-30k fit onto the m7 surface prediction (level 0, z 9000–10000), then runs `patch_qa.sh` on w040 and w070.
- **Usage:** `bin/snap_exp30k.sh`
- **In → out:** waits for `SURFMIRROR-EXIT: 0` in `$S/mirror-surf-band.log`. Writes `$D/snapped/exp-30k/` (`windings.txt`, `snap.log`, `snap_report.tsv`, `wNNN_exp-30k/`), with QA in `$D/snapped/qa_exp-30k_<w>/`. QA runs on GPU 3 (hard-coded).
- **Runs on:** GPU box. **Log/marker:** launcher, `$S/snap-exp30k.log`; `SNAP-EXIT: <rc of the snap>`.
- **Status:** one-off (done; its output feeds `triage_windings.sh`). **Origin:** ours (MIT); it uses Nieuwlaar's snap script.

#### `box/bin/tracer_dirfield_test.sh`
After Fiber inference, grows patches with `vc_grow_seg_from_seed` using the Fiber field as a "horizontal" direction field (70 and 150 generations, seed 5259 2852 9404), then runs `patch_qa.sh` on each.
- **Usage:** `bin/tracer_dirfield_test.sh`
- **In → out:** waits for `FIBER-EXIT` in `$S/fiber-band.log`. Writes `$D/grow-test/dirfield/{params_<gen>.json,out_<gen>/,grow_<gen>.log,qa_<gen>/}`.
- **Runs on:** GPU box. **Log/marker:** launcher, `$S/tracer-dirfield.log`; `DIRTEST-EXIT` is 90 if the Fiber run failed and 0 otherwise.
- **Status:** superseded by `tracer_dirfield_test2.sh`. **Origin:** ours (MIT).

#### `box/bin/tracer_dirfield_test2.sh`
Tracer test, second attempt: uses the Fiber field converted by `make_dirfield_zarr.py` as a "normal" field, weighted by Fiber presence.
- **Usage:** `bin/tracer_dirfield_test2.sh`
- **In → out:** waits for `DIRFIELD-EXIT` in `$S/dirfield-build.log`. Writes `$D/grow-test/dirfield2/{params_<gen>.json,out_<gen>/,grow_<gen>.log,qa_<gen>/}`.
- **Runs on:** GPU box. **Log/marker:** launcher, `$S/tracer-dirfield2.log`; `DIRTEST2-EXIT` is 1 if any run failed.
- **Status:** one-off experiment. **Origin:** ours (MIT).

#### `box/bin/tracer_lasagna_test.sh`
Tracer test using the community Lasagna normals as the direction field, plus the normal grids (70 generations, same seed).
- **Usage:** `bin/tracer_lasagna_test.sh`
- **In → out:** waits for `DIRFIELDL-EXIT` in `$S/dirfield-lasagna-build.log`. Writes `$D/grow-test/dirfield2/{params_lasagna70.json,out_lasagna70/,grow_lasagna70.log,qa_lasagna70/}`.
- **Runs on:** GPU box. **Log/marker:** launcher, `$S/tracer-lasagna.log`; `LASTRACE-EXIT: <rc>`.
- **Status:** one-off experiment. **Origin:** ours (MIT).

#### `box/bin/grow_qa.sh`
Renders and inks the 31 cm² patch grown by `vc_grow_seg_from_seed` (seed 5326 2948 9500, 150 generations).
- **Usage:** `bin/grow_qa.sh`
- **In → out:** the latest `$D/grow-test/out/auto_grown_*` → `$D/grow-test/qa/` (`patch.zarr`, `patch.render.log`, `patch_render_z14_ds4.tif`, `patch_seed4N-75000[_reverse].tif`, previews). GPU 3 is hard-coded.
- **Runs on:** GPU box (GPU). **Log/marker:** launcher, `$S/grow-qa.log`; `GROWQA-EXIT` is 1 if the render fails and 0 otherwise.
- **Status:** superseded by `patch_qa.sh`. **Origin:** ours (MIT).

#### `box/bin/pilot_qa.sh`
Renders and inks windings w040, w070 and w100 of the newest fit run. It reads the local CT if the band is mirrored and streams from S3 otherwise.
- **Usage:** `bin/pilot_qa.sh`
- **In → out:** `$D/spiral-output/<newest>/meshes/fitted_*/` → `$D/pilot-qa/` (`<w>.zarr`, `<w>.render.log`, `<w>_render_z14_ds2.tif`, `<w>_seed4N-75000[_reverse].tif`). GPU 0 is hard-coded. With the current code, the preview glob `<w>_s4*.tif` does not match the map names, so no previews are written.
- **Runs on:** GPU box (GPU). **Log/marker:** launcher, `$S/pilot-qa.log`; `PILOTQA-EXIT: 0` (always 0).
- **Status:** superseded by `winding_qa.sh`. **Origin:** ours (MIT).

#### `box/bin/winding_qa.sh`
Renders (28 slices, `--flip-normals`) and inks (seeds 42 and 43) selected windings of a fit run.
- **Usage:** `bin/winding_qa.sh <run dir> <out dir> <GPU UUID> [w040 w070 …]` (default w040 w070 w100)
- **In → out:** `<run>/meshes/fitted_*/<w>_*` → `<out>/<w>.zarr`, `<w>.render.log`, `<w>_render_z14_ds2.tif`, `<w>_ink_seed4N-75000[_reverse].tif` and previews.
- **Runs on:** GPU box (GPU). **Log/marker:** stdout; `WINDINGQA-EXIT: 0` (always 0).
- **Status:** superseded for ink work by the 66-layer route (`triage_windings.sh` → ensemble). It is still usable for a quick look at a fit run. **Origin:** ours (MIT).

---

## 3. Rendering

Sampling the CT around each flattened winding into a 66-layer surface volume, the input for every ink model.

#### `box/bin/render66.sh`
Makes a 66-layer surface volume of a (flattened) tifxyz from a local CT mirror (PHerc. 0191 by default; `CT=<volume.zarr>` for another scroll, added 2026-10-10).
- **Usage:** `[CT=<volume.zarr>] bin/render66.sh <segment.tifxyz> <out.zarr> [threads=4] [cache_gb=8]`
- **In → out:** tifxyz → `<out.zarr>` (array `0`, 66 × H × W uint8). It reads only the local mirror; there is no S3 fallback.
- **Runs on:** GPU box (CPU). **Log/marker:** stdout; `RENDER66-EXIT: <rc>`.
- **Status:** current. **Origin:** ours (MIT).

#### `box/bin/triage_windings.sh`
For every snapped exp-30k winding, starting at w070 and working outwards: flattens it, renders 66 layers, and writes a CT preview of layer 33 (d = 0). Windings already done are skipped.
- **Usage:** `bin/triage_windings.sh <GPU UUID>` (the GPU is used for flattening only)
- **In → out:** `$D/snapped/exp-30k/wNNN_exp-30k/` → `$D/flatten/exp-30k-snapped-wNNN/tifxyz/flatten.tifxyz`, `$D/render66/exp30k_snapped_wNNN_66.zarr` (+ `render66/render_wNNN.log`), and `$D/triage/previews/wNNN_ct_d0.png` (2× downsampled, render orientation).
- **Runs on:** GPU box. **Log/marker:** launcher, `$S/triage-windings.log`; `TRIAGE-EXIT: 0` (always 0).
- **Status:** current (finished its run on 2026-10-09). **Origin:** ours (MIT).

#### `box/bin/triage_band.sh`
Phase A1 geometry triage of one fit's snapped windings: Lasagna flatten → 66-layer render → CT preview of the surface layer, from w070 outwards. Several GPUs share the list through claims.
- **Usage:** `bin/triage_band.sh <fit-id> <GPU UUID> [first=20] [last=119]`
- **In → out:** `geometry/<fit-id>/snapped/` → `geometry/<fit-id>/flattened/wNNN`, `renders/<fit-id>/wNNN.zarr`, `geometry/<fit-id>/qa/triage/previews/wNNN_ct_d0.png`.
- **Usage for another scroll:** `SCROLL=PHerc0813 bin/triage_band.sh <fit-id> <GPU UUID> <first> <last>` (paths under `data/<scroll>/`, CT from `data/<scroll>/source/volume/`).
- **Runs on:** GPU box (GPU + CPU). **Log/marker:** launcher log; `TRIAGEBAND-EXIT: 0`. **Status:** current. **Origin:** ours (MIT).

### Older and one-off

#### `box/bin/render_2p4um_crop1.sh`
Crop render of PHerc. Paris 4 segment 20231016151002 from the remote 2.4 µm volume at level 2 (9.6 µm/px): 28 slices, a 6500 × 2100 px crop of the main text block.
- **Usage:** `bin/render_2p4um_crop1.sh`
- **In → out:** waits for `DL-EXIT` and `UV-SYNC-EXIT` and cleans the uv cache first. Writes `$S/runs/20231016151002-2.4um-g2-28-crop1/render.zarr` and `vc_render.log`.
- **Runs on:** GPU box (CPU). **Log/marker:** stdout; `RENDER-EXIT: <rc>`.
- **Status:** superseded by `render_2p4um_crop1b.sh`. **Origin:** ours (MIT).

#### `box/bin/render_2p4um_crop1b.sh`
The same render as `crop1`, gated on `DL0800-EXIT` instead. Its header comment is identical to `crop1`'s.
- **Usage:** `bin/render_2p4um_crop1b.sh`
- **In → out:** → `$S/runs/20231016151002-2.4um-g2-28-crop1b/render.zarr`
- **Runs on:** GPU box (CPU). **Log/marker:** stdout; `RENDER-EXIT: <rc>`.
- **Status:** one-off. **Origin:** ours (MIT).

---

## 4. Ink detection

Running the ink models on the renders: a single model, the four-model ensemble (ink_9um seeds 42 and 43, dense_native, Hecate), three-model passes without Hecate, depth sweeps, and the PHerc. 343 positive control.

#### `box/bin/ink343/run_ink.sh`
Makes one ink map pair (reading side + blind side) for one 66-layer render, one model and one depth d.
- **Usage:** `run_ink.sh <surface.zarr> <model> <d> <out_dir>`, where model is one of `dnative`, `hybrid_3d2d-seed42`, `hybrid_3d2d-seed43`, `hecate` and d runs from −15 to +15.
- **Environment:** `CKPT_DIR`, `PY`, `HECATE_PY`, `PREP_PY`, `N_LAYERS` (66), `NATIVE_UM` (8.64; 9.362 for PHerc. 0191), `VILLA_BATCH`, `HEC_BATCH`, `HEC_DEVICE`, `TMPDIR`.
- **In → out:** render → `<name>__<model>__L66s<s>[_reverse].tif` or `<name>__hecate__L66zc<zc>[_reverse].png` (+ `.json`). See Conventions.
- **Runs on:** GPU box and AWS worker (GPU). **Log/marker:** stdout. Exit codes: 2 for usage, unknown model or depth out of range; 3 for a missing checkpoint; 4 for no output.
- **Status:** current. **Origin:** Nieuwlaar (MIT). Licence: `box/bin/ink343/LICENSE-pherc343-first-letters`.

#### `box/bin/ink343/run_depth_sweep.sh`
Runs all four models (or `MODELS`), both directions, at every depth in [D_MIN, D_MAX]: d = 0 first, then outwards. Existing maps are skipped.
- **Usage:** `run_depth_sweep.sh <surface.zarr> <out_dir> [D_MIN=-15] [D_MAX=15]`. Environment: `MODELS`, `P_VILLA`, `P_HEC` (number of parallel jobs), plus `run_ink.sh`'s variables.
- **In → out:** render → maps in `<out_dir>`, `<out_dir>/logs/<model>_d<d>.log` and `<out_dir>/logs/timings.tsv`.
- **Runs on:** GPU box (GPU). **Log/marker:** stdout. It exits 1 if any job failed.
- **Status:** current. **Origin:** Nieuwlaar (MIT).

#### `box/bin/ink343/hecate_prep.py`
Resamples a render into Hecate's input: isotropic 9.6 µm in x, y and z, exactly `--nz` planes centred at `--z-center`.
- **Usage:** `python hecate_prep.py --src <zarr-group|tifdir> --out out.zarr --native-um <µm> [--native-um-z <µm>] [--target-um 9.6] --z-center <32.5+d> [--nz 16] [--crop y0 x0 h w]`
- **In → out:** render → temporary `prep.zarr` (called by `run_ink.sh`).
- **Runs on:** GPU box and AWS worker (CPU). **Log/marker:** stdout.
- **Status:** current. **Origin:** Nieuwlaar (MIT).

#### `box/bin/ink343/ensemble_maps.py`
Makes grayscale images of each model's maps, their z-score ensemble (reading and blind side) and the CT, all with fixed stretches pooled from the reading side. Missing models are skipped, so it also works for three-model sets.
- **Usage:** `python ensemble_maps.py --surface <name>.zarr --maps <dir> --out <dir> [--name N] [--stat-depths -15..15] [--write-depths 0] [--orientation reading|raw]`
- **In → out:** render + `run_ink.sh` maps → `<name>__{ensemble,dnative,hecate,ink9-42,ink9-43}__d±NN.png` (reading side), the same names with `_blind`, `<name>__ct__d±NN.png`, and `<name>__stats.json`. Images are in reading orientation by default.
- **Runs on:** GPU box and AWS worker (CPU). **Log/marker:** stdout.
- **Status:** current. **Origin:** Nieuwlaar (MIT).

#### `box/bin/depth_sweep.sh`
The box wrapper around `run_depth_sweep.sh`: sets the box checkpoint paths, `NATIVE_UM=9.362` and one villa plus one Hecate job in parallel.
- **Usage:** `bin/depth_sweep.sh <surface_66.zarr> <out_dir> <GPU UUID> [DMIN=-15] [DMAX=15]` (`MODELS` is passed through)
- **In → out:** as in `run_depth_sweep.sh`. Checkpoints come from `$S/checkpoints/ckpt343/`. Paused sweeps live in `$D/sweeps/`.
- **Runs on:** GPU box (GPU). **Log/marker:** stdout; `SWEEP-EXIT: <rc>`.
- **Status:** current. Note that it is PHerc. 0191 only, because of the fixed µm value. **Origin:** ours (MIT).

#### `box/bin/ensemble_windings.sh`
Runs the four-model ensemble at d = 0 and +1 on the given windings, reusing existing seed-42 maps, then makes ensemble images for each winding.
- **Usage:** `bin/ensemble_windings.sh <GPU UUID> w070 w069 …`
- **In → out:** `$D/render66/exp30k_snapped_<w>_66.zarr` → maps in `$D/ink-triage/maps/`, sweep log `$D/ink-triage/ensemble_<w>.log`, and images plus `ensemble.log` in `$D/ink-triage/ensemble/<w>/`.
- **Runs on:** GPU box (GPU). **Log/marker:** launcher, `$S/ensemble-windings.log`; `ENSWIND-EXIT: 0` (always 0).
- **Status:** current (its queue w068–w072 has finished). **Origin:** ours (MIT).

#### `box/bin/three_model_windings.sh`
Runs the three-model pass (seeds 42 and 43 + dense_native, no Hecate) at d = 0 and +1 on windings the AWS fleet did not cover, then makes ensemble images and stroke scores. Several GPUs can share one list through claim folders.
- **Usage:** `bin/three_model_windings.sh <GPU UUID> w036 w103 …`
- **In → out:** render → maps in `$D/ink-triage/maps/`, sweep log `$D/ink-triage/three_<w>.log`, images in `$D/ink-triage/ensemble3/<w>/`, scores in `$S/data/strokes/box3m/<w>/` (errors in `box3m/errors.log`). Claims are kept in `$D/ink-triage/claims3/<w>/gpu`.
- **Runs on:** GPU box (GPU). **Log/marker:** launcher, `$S/three-model.log`; `THREEM-EXIT: 0` once per GPU (always 0).
- **Status:** current. **Origin:** ours (MIT).

#### `box/bin/control343.sh`
Positive control: runs the PHerc. 343 winning segment through our pipeline unchanged. It makes a 66-layer render streamed from S3, runs ink_9um seed 42 at d = +1, 0, +2, −1, and writes previews.
- **Usage:** `bin/control343.sh <GPU UUID>`
- **In → out:**
  - Input: `$S/data/PHerc0343/control/concat_w047-w048_R5B2_z9500-11000.tifxyz` (Nieuwlaar's mesh), streamed with the cache `/mnt/nvme/scroll-prizes/cache/PHerc0343-l0`.
  - Output: `control/control343_66.zarr`, `control/maps/`, `control/render.log`, `control/ink_d<d>.log` and `control/preview_d±N_{read,blind}.png`.
- **Runs on:** GPU box (GPU). **Log/marker:** stdout; `CONTROL-EXIT` is 1 if the render fails and 0 otherwise.
- **Status:** current. **Origin:** ours (MIT); the mesh is Nieuwlaar's (MIT).

#### `box/bin/control343_ensemble.sh`
The four-model ensemble at d = +1 on the PHerc. 343 control: adds seed 43, dense_native and Hecate to the seed-42 map from `control343.sh`, then makes ensemble images.
- **Usage:** `bin/control343_ensemble.sh [GPU UUID=GPU 3]` (there is no GPU 1 guard)
- **In → out:** `$S/data/PHerc0343/control/control343_66.zarr` → `control/maps/`, `control/ink_<model>_d1.log`, `control/images/` (+ `ensemble.log`).
- **Runs on:** GPU box (GPU). **Log/marker:** stdout; `ENSEMBLE343-EXIT: 0` (always 0).
- **Status:** current. **Origin:** ours (MIT).

#### `box/bin/deep_look.sh`
Phase A3: four-model ink maps (seeds 42/43, dense_native, Hecate) for chosen windings, depth tier by tier (0, +1, then −1, +2, then −2, +3). Units (winding, model, depth) are shared by several GPUs through claims.
- **Usage:** `bin/deep_look.sh <fit-id> <GPU UUID> <hecate-first|villa-first> <hec_batch> w073 …`
- **In → out:** `renders/<fit-id>/wNNN.zarr` → `ink/<fit-id>/maps/`; claims `ink/<fit-id>/claims-a3/`; unit logs `runs/2026-10-10_deeplook-<fit-id>/units/`.
- **Runs on:** GPU box (GPU). **Log/marker:** `runs/…/gpuN.log`; `DEEPLOOK-EXIT: 0` (always 0). **Status:** done for exp30k-z11200 (168/168 units). **Origin:** ours (MIT).

#### `box/bin/band_three_model.sh`
Phase A4: three-model ink maps (seeds 42/43 + dense_native) at d 0 and +1 on the rendered windings of one fit of any scroll. Units shared by several GPUs through claims.
- **Usage:** `bin/band_three_model.sh <scroll> <fit-id> <GPU UUID> <run dir> w020 …`
- **In → out:** `renders/<fit-id>/wNNN.zarr` → `ink/<fit-id>/maps/`; claims `ink/<fit-id>/claims-a4/`; unit logs `<run dir>/units/`. Refuses GPU 1 by UUID and by index.
- **Runs on:** GPU box (GPU). **Log/marker:** `<run dir>/gpuN.log`; `A4INK-EXIT: 0`. **Status:** current. **Origin:** ours (MIT).

### Older, one-off and unused

#### `box/bin/ink_triage.sh`
Fast single-model pass: ink_9um seed 42 at d = +1, 0, +2, −1 on each triaged winding as its render appears, with previews. Several GPUs can share the work through claim folders.
- **Usage:** `bin/ink_triage.sh <GPU UUID>`
- **In → out:** `$D/render66/exp30k_snapped_<w>_66.zarr` → `$D/ink-triage/maps/`, `$D/ink-triage/previews/<w>_d±N_{read,blind}.png` + `<w>_done`, `$D/ink-triage/<w>_d<d>.log`, and claims in `$D/ink-triage/claims/<w>/gpu`. It stops after `TRIAGE-EXIT`.
- **Runs on:** GPU box (GPU). **Log/marker:** launcher, `$S/ink-triage.log`; `INKTRIAGE-EXIT: 0` (always 0).
- **Status:** superseded by `three_model_windings.sh` and `aws/fleet_3model.sh`. It was stopped on 2026-10-09 because the positive control showed that single-model nulls are not evidence. Its seed-42 maps are still reused. **Origin:** ours (MIT).

#### `box/bin/infer_7p91_smoke.sh`
First ink-inference smoke test: ink_9um seed 42 on the pre-rendered 7.91 µm surface volume of PHerc. Paris 4 segment 20231016151002.
- **Usage:** `bin/infer_7p91_smoke.sh`
- **In → out:** waits for `UV-SYNC-EXIT` and `DL-EXIT`. Writes `$S/runs/20231016151002-7.91um-ink9um-s42-075k/pred.tif`. GPU 0 is hard-coded.
- **Runs on:** GPU box (GPU). **Log/marker:** stdout; `INFER-EXIT: <rc>` (90 or 91 if a gate failed).
- **Status:** one-off (day 1). **Origin:** ours (MIT).

#### `box/bin/infer_pherc0800.sh`
Ink inference on the six public PHerc. 0800 auto_grown segments (pre-rendered 8.64 µm, 31 layers) with three checkpoints, both directions.
- **Usage:** `bin/infer_pherc0800.sh`
- **In → out:** waits for `DL0800-EXIT`. Writes `$S/runs/PHerc0800-ink9um/<seg timestamp>_seed4N-<step>.tif` + `_preview-ds2.tif`. GPU 3 is hard-coded.
- **Runs on:** GPU box (GPU). **Log/marker:** stdout; `P0800-EXIT: <number of failures>`.
- **Status:** one-off. **Origin:** ours (MIT).

#### `box/bin/ink343/pad_render.py`
Copies a 66-layer render with zero rows and columns added on top and left, so that a shifted part of a joined mesh falls on the models' tile phase.
- **Usage:** `python pad_render.py <render.zarr> <padded.zarr> [--pad-rows 40] [--pad-cols 200]`
- **In → out:** render → padded render (level 0 only).
- **Runs on:** not run here. **Log/marker:** stdout.
- **Status:** unclear (unused here; specific to Nieuwlaar's joined w047–w048 mesh). **Origin:** Nieuwlaar (MIT).

#### `box/bin/ink343/merge_tile_phase.py`
Merges the maps of the plain and the padded render of a joined mesh (w047 pixels come from the padded run, everything else from the plain run).
- **Usage:** `python merge_tile_phase.py --plain <dir> --plain-name <name> --padded <dir> --padded-name <name> --node-source <…_node_source.npz> --out <dir> --out-name <name> [--pad-rows 40] [--pad-cols 200]`
- **In → out:** two map sets → one map set with `run_ink.sh` names.
- **Runs on:** not run here. **Log/marker:** stdout.
- **Status:** unclear (unused here; specific to the PHerc. 343 joined mesh). **Origin:** Nieuwlaar (MIT).

#### `box/bin/ink343/make_submission_image.py`
Makes a First Letters submission image: ink over a fibre-visible CT layer, at most 4 cm², in reading orientation, with a 1 cm scale bar, row annotations, a letter-size table, and a sidecar JSON with sha256 checks and a publication word check.
- **Usage:** `python make_submission_image.py --mesh <x.tifxyz> --umbilicus <umbilicus.json> --ct <render.zarr> --ct-layer d0 --ink <maps…> --ensemble --ink-stats <name>__stats.json --area x0,y0,x1,y1 [--area-frame reading] --rows rows.json --letters letters.json --out-dir out/` (see its header for all options)
- **In → out:** mesh, render, maps and hand-placed rows and letters → `<mesh name>.png`, a key image and a sidecar JSON.
- **Runs on:** GPU box or Mac (CPU). **Log/marker:** stdout.
- **Status:** unclear (not used yet; kept for a possible submission). **Origin:** Nieuwlaar (MIT).

---

## 5. Scoring and ranking

Turning ink maps into numbers and pictures: a stroke score per winding and depth, ranking tables with a LOOK flag, and preview images and montages.

#### `box/bin/stroke_score.py`
Scores how much stroke-sized ink the ensemble shows on the reading side compared with the blind side (the null) of one render at one depth. It reports tiles and the best 2 × 2 cm window.
- **Usage:** `python bin/stroke_score.py --surface <name>.zarr --maps <dir> --out <dir> --um 9.362|8.64 --depth <d> [--name N] [--models dnative,hecate,ink9-42,ink9-43] [--tag _s42] [--crops 3] [--window-mm 20] [--thr 2.0] [--bg-mm 1.5] [--amin-mm2 0.02] [--amax-mm2 1.5] [--tile-mm 4] [--step-mm 1] …`
- **In → out:** render + maps → `<name>__strokes<tag>_d±NN.json` (parameters, per-side statistics, top reading tiles in reading orientation), `<name>__strokes<tag>_d±NN.png`, and the review crops `…_d±NN__topNN.png` (reading E | blind E | CT). The valid-pixel mask is cached as `<name>__valid.png`.
- **Runs on:** GPU box and AWS worker (CPU). **Log/marker:** prints a JSON summary line.
- **Status:** current. **Origin:** ours (MIT).

#### `box/bin/stroke_rank.sh`
Scores every winding that has ink maps (seed 42 alone where its maps exist; four models where all four exist) at d = −1..+2, plus the PHerc. 343 control as a reference, and writes one ranking table. Only new or changed maps are re-scored.
- **Usage:** `[FORCE=1] bin/stroke_rank.sh [maps dir=$D/ink-triage/maps]`
- **In → out:** maps + `$D/render66/<name>.zarr` → `$S/data/strokes/ranking.tsv`. The table is sorted by `area_R`, with columns name, set (s42 or ens4), depth, area_R, area_B, R−B, window_R, window_B, max_tile_R, max_tile_B, top_read_y, top_read_x, top_damage and flag (LOOK). It also writes per-winding output in `$S/data/strokes/<w>/`, control output in `$S/data/strokes/c343/`, and errors in `$S/data/strokes/rank-errors.log`.
- **Runs on:** GPU box (CPU, nice 19). **Log/marker:** stdout; `RANK-EXIT: 0` (always 0). A forced re-score was logged to `$S/data/strokes/rank-force.log`.
- **Status:** current. **Origin:** ours (MIT).

#### `box/bin/stroke_watch.sh`
Every 10 minutes, re-runs `stroke_rank.sh` if any file in `ink-triage/maps` is newer than `ranking.tsv`. It stops after a final run once neither `ensemble_windings.sh` nor `ink_triage.sh` is running.
- **Usage:** `bin/stroke_watch.sh`
- **In → out:** → `$S/data/strokes/ranking.tsv` and `$S/data/strokes/rank-last.log`.
- **Runs on:** GPU box (CPU). **Log/marker:** launcher, `$S/stroke-watch.log`; `STROKEWATCH-EXIT: 0`.
- **Status:** current, but its stop condition predates `three_model_windings.sh`, and the three-model scores are not in `ranking.tsv`. **Origin:** ours (MIT).

#### `box/bin/triage_montage.py`
Stacks the triage CT previews into one labelled JPEG, one row per winding.
- **Usage:** `python bin/triage_montage.py <previews dir> <out.jpg> [width=2400] [w068 w069 …]`
- **In → out:** `<dir>/wNNN_ct_d0.png` (from `triage_windings.sh`) → JPEG. The width label assumes previews downsampled 2×.
- **Runs on:** GPU box or Mac (CPU). **Log/marker:** stdout.
- **Status:** current. **Origin:** ours (MIT).

#### `box/bin/tif_preview.py`
Block-mean downsamples a prediction TIFF to an 8-bit preview.
- **Usage:** `python bin/tif_preview.py in.tif out.tif [factor=8] [--rescale9um]` (`--rescale9um` applies (p − 0.25) / 0.5)
- **In → out:** TIFF → 8-bit TIFF.
- **Runs on:** GPU box (CPU). **Log/marker:** stdout.
- **Status:** current (used by the QA scripts). **Origin:** ours (MIT).

#### `box/bin/zarr_slice_preview.py`
Writes an 8-bit, downsampled, percentile-stretched (1–99) preview of one z slice of a zarr.
- **Usage:** `python bin/zarr_slice_preview.py path.zarr out.tif [level=0] [z=middle] [factor=4]`
- **In → out:** zarr → 8-bit TIFF.
- **Runs on:** GPU box (CPU). **Log/marker:** stdout.
- **Status:** current. **Origin:** ours (MIT).

#### `box/bin/ink_sheet.py`
Stacks one winding's fast-ink previews (all depths, one side) into a labelled sheet.
- **Usage:** `python bin/ink_sheet.py <previews dir> <winding> <read|blind> <out.jpg> [width=2400]`
- **In → out:** `<dir>/<w>_d±N_<side>.png` (from `ink_triage.sh`) → JPEG.
- **Runs on:** GPU box or Mac (CPU). **Log/marker:** stdout.
- **Status:** unclear (its input, the `ink_triage.sh` previews, is no longer produced). **Origin:** ours (MIT).

---

#### `tools/stroke-score/` (`stroke-score score|rank`)
The packaged stroke score (v0.1): scores a 66-layer render plus any set of ink maps, ranks many results with the LOOK flag, writes review crops. See its README. The box runs it from source (`PYTHONPATH=tools/stroke-score/src python -m stroke_score.cli`).
- **Status:** current (supersedes `box/bin/stroke_score.py` and `stroke_rank.sh` for new work). **Origin:** ours (MIT).

#### `box/bin/deep_score.sh`
Phase A3 scorer: when all four models exist for a (winding, depth), writes the ensemble images (`ensemble_maps.py`) and the stroke score with crops, then re-ranks.
- **Usage:** `bin/deep_score.sh <fit-id> w073 …`
- **In → out:** maps → `ink/<fit-id>/ens4/<w>/`, `scores/<fit-id>/ens4/<w>/`, `scores/<fit-id>/ens4/ranking.tsv`.
- **Runs on:** GPU box (CPU). **Log/marker:** `runs/…/scorer.log`; `DEEPSCORE-EXIT: 0` after every DEEPLOOK-EXIT. **Status:** done for exp30k-z11200. **Origin:** ours (MIT).

#### `box/bin/band_score3.sh`
Phase A4 scorer: as `deep_score.sh` for the three-model set, plus render cleanup. When both depths of a winding are scored and no row is near the flag line (LOOK, area_R ≥ 0.012, R − B ≥ 0.008 or window ≥ 0.025), the winding's render is deleted.
- **Usage:** `bin/band_score3.sh <scroll> <fit-id> <run dir> <workers> w020 …`
- **In → out:** maps → `ink/<fit-id>/ens3/<w>/`, `scores/<fit-id>/ens3/<w>/`, `scores/<fit-id>/ens3/ranking.tsv`; `<run dir>/kept_renders.txt`, `deleted_renders.txt`.
- **Runs on:** GPU box (CPU). **Log/marker:** `<run dir>/scorer.log`; `A4SCORE-EXIT: 0` after `<workers>` A4INK-EXIT lines. **Status:** current. **Origin:** ours (MIT).

## 6. Cloud (AWS) orchestration

Runs render + ink on EC2 GPU instances in us-east-1, next to the open data, driven from the Mac. See `aws/README.md`. These runs are paid: every launch needs Ted's explicit go-ahead. The `spot_*` scripts also launch on-demand instances when `MARKET=ondemand`.

### Setup and shared parts

#### `aws/lib.sh`
Shared helpers, sourced by the other scripts and not run directly.
- **Usage:** `source "$(dirname "$0")/lib.sh"`
- **In → out:**
  - Loads `aws/spot.env` (git-ignored; the template is `aws/spot.env.example`).
  - Defines `check_account` (refuses any account other than `EXPECTED_ACCOUNT_ID`, exit 3), `awsc`, `rssh`, `rsync_to`/`rsync_from`, `require_net` and `set_env`.
  - State goes to `aws/state/` (git-ignored), or to `$ISTATE` per fleet worker.
- **Runs on:** Mac (`set_env` uses the macOS form `sed -i ""`). **Log/marker:** none.
- **Status:** current. **Origin:** ours (MIT).

#### `aws/vpc_up.sh`
Creates or reuses a dedicated tagged VPC (10.77.0.0/16) with an internet gateway, a route table and one public subnet per call.
- **Usage:** `aws/vpc_up.sh [zone=us-east-1c]` (run it again with another zone to add a subnet)
- **In → out:** AWS resources tagged `Project=scroll-prize`. Writes `VPC_ID` and `SUBNET_IDS` into `aws/spot.env`.
- **Runs on:** Mac. **Log/marker:** stderr.
- **Status:** current (setup). **Origin:** ours (MIT).

#### `aws/vpc_down.sh`
Removes the tagged VPC and everything in it. It refuses while instances are alive (exit 4).
- **Usage:** `aws/vpc_down.sh`
- **In → out:** deletes the security groups, subnets, route table, internet gateway and VPC, and clears `VPC_ID`/`SUBNET_IDS`.
- **Runs on:** Mac. **Log/marker:** stderr.
- **Status:** current. **Origin:** ours (MIT).

#### `aws/spot_check.sh`
Read-only readiness check: account, subnets and their default routes, current spot prices, the GPU vCPU quota and the AMI.
- **Usage:** `aws/spot_check.sh`
- **In → out:** stdout only; it creates nothing.
- **Runs on:** Mac. **Log/marker:** stdout.
- **Status:** current. **Origin:** ours (MIT).

#### `aws/userdata.sh.tmpl`
EC2 user-data template, run once as root at first boot. `spot_up.sh` fills in `@MAX_MINUTES@`, `@VILLA_COMMIT@` and `@VC3D_RELEASE@`. At boot it:
1. Schedules the hard power-off (shutdown terminates the instance).
2. Installs uv and clones villa at the pinned commit, then runs `uv sync --extra models` (without the compiled VC package).
3. Extracts the VC3D AppImage, for `vc_render_tifxyz`.
4. Downloads the checkpoints from Hugging Face: ink_9um seeds 42 and 43, Hecate (Giorgio Angelotti) with `hecate.py`, and the dense_native weights and config (Nieuwlaar).
- **Usage:** not run by hand; filled into `aws/state[/fleet/<w>]/userdata.sh`.
- **In → out:** writes `/opt/scroll/{villa,vc3d,hf}/` and info files `/opt/scroll/{bootstrap.times,torch.txt,vc3d.txt,nvidia-smi.txt}`.
- **Runs on:** AWS worker. **Log/marker:** `/var/log/scroll-bootstrap.log`; marker files `/opt/scroll/BOOTSTRAP-DONE` or `BOOTSTRAP-FAILED`.
- **Status:** current. **Origin:** ours (MIT).

### Single instance

#### `aws/spot_up.sh`
Requests one instance, waits for it to bootstrap, and records it.
- **Usage:** `aws/spot_up.sh` (environment from `spot.env`, plus `ISTATE`, `WORKER_NAME`, `FLEET_MAX_HOURS`, `MARKET`, `INSTANCE_TYPES`, `RETRY_MINUTES`)
- **In → out:**
  - Creates the key pair (private key kept in `aws/state/`) and a security group allowing SSH from this Mac's IP, if they are missing.
  - Tries each instance type × subnet, at spot, or on-demand if `MARKET=ondemand`.
  - Writes `$ISTATE/{instance_id,instance_ip,launched_at,instance_type,userdata.sh,run-instances.err}`.
- **Runs on:** Mac. **Log/marker:** stderr; it ends with `READY: <id> <ip>`. Exit codes: 4 if an instance is already recorded, 7 if the request or bootstrap failed, 8 on bootstrap timeout (45 min).
- **Status:** current. It spends money. **Origin:** ours (MIT).

#### `aws/spot_push.sh`
Copies the pipeline to the instance and finishes the model setup.
- **Usage:** `aws/spot_push.sh`
- **In → out:**
  - Copies `box/bin/ink343/`, `aws/remote/*` and `box/bin/stroke_score.py` to `/opt/scroll/bin/`, then runs `remote/setup_models.sh`.
  - Installs Scan-Quality-Map (jcooperkai-sys/Scan-Quality-Map, MIT) into `/opt/scroll/sqm-venv`. This step is non-fatal.
  - With `FLATTEN=1`, also bootstraps the Lasagna environment for flattening on the worker.
- **Runs on:** Mac. **Log/marker:** prints `SETUP-MODELS-DONE`, then `SQM-OK` or `SQM-INSTALL-FAILED`, then (with `FLATTEN=1`) `LASAGNA-OK` or `LASAGNA-FAILED`.
- **Status:** current. **Origin:** ours (MIT).

#### `aws/spot_run.sh`
Uploads one segment, runs `remote/run_segment.sh` detached and waits for it.
- **Usage:** `aws/spot_run.sh <name> <local segment.tifxyz dir> <volume zarr URL> <native_um> <models,comma> <depths,comma>`
- **In → out:** segment → `/opt/scroll/jobs/<name>/`. Results land in `/opt/scroll/results/<name>/`.
- **Runs on:** Mac. **Log/marker:** polls once a minute for `RUN-EXIT` in `/opt/scroll/results/<name>/run.log`.
- **Status:** current (the single-instance path; used by `poc.sh`). **Origin:** ours (MIT).

#### `aws/spot_fetch.sh`
Copies the results back, without the renders.
- **Usage:** `aws/spot_fetch.sh`
- **In → out:** `/opt/scroll/results/` → `data/aws-results/<instance id>/` (+ `instance-info.txt`).
- **Runs on:** Mac. **Log/marker:** stderr.
- **Status:** current. **Origin:** ours (MIT).

#### `aws/spot_down.sh`
Terminates the recorded instance, or every instance tagged `Project=<tag>` with `--all`. With `--cleanup` it also deletes the security group and key pair. It never touches untagged resources.
- **Usage:** `aws/spot_down.sh [--all] [--cleanup]`
- **In → out:** terminates instances, clears `$ISTATE/instance_*`, and prints a rough cost.
- **Runs on:** Mac. **Log/marker:** stderr.
- **Status:** current. **Origin:** ours (MIT).

#### `aws/spot_status.sh`
Lists every tagged instance with its state, type, zone, age and current spot price.
- **Usage:** `aws/spot_status.sh`
- **Runs on:** Mac. **Log/marker:** stdout.
- **Status:** current. **Origin:** ours (MIT).

#### `aws/poc.sh`
Proof of concept, end to end:
1. `spot_up.sh`, then `spot_push.sh`.
2. One ink map (seed 42, d = +1) on the PHerc. 343 control mesh, `data/prior-art/pherc343-first-letters/outputs/concat_w047-w048_R5B2_z9500-11000.tifxyz`.
3. `spot_fetch.sh`.
4. `spot_down.sh`, which runs on exit even after a failure, unless `--keep` is given.
- **Usage:** `aws/poc.sh [--keep]`
- **In → out:** → `data/aws-results/<instance id>/control343/` (for example `previews/hybrid_3d2d-seed42_d+1_read.png`) and `aws/state/bootstrap-<instance id>.log`.
- **Runs on:** Mac. **Log/marker:** launcher, `aws/state/poc-<timestamp>.log` (the latest path is in `aws/state/last_poc_log`).
- **Status:** one-off (passed 2026-10-09). **Origin:** ours (MIT); the mesh is Nieuwlaar's (MIT).

### Fleet

#### `aws/stage_segments.sh`
Pulls flattened winding meshes from the GPU box and writes the fleet manifest.
- **Usage:** `aws/stage_segments.sh [--skip-done] [w070 w069 … | all]`. Environment: `MODELS` (default all four), `DEPTHS` (0,1), `FLATTEN_PREFIX` (exp-30k-snapped), `NAME_PREFIX` (exp30k_snapped), `SNAPPED_DIR`, `BOX`.
- **In → out:**
  - Default: box `$D/flatten/<prefix>-wNNN/tifxyz/flatten.tifxyz` → `data/aws-stage/segments/<name>/flatten.tifxyz`.
  - With `SNAPPED_DIR=<box dir>`: ships snapped, unflattened windings → `data/aws-stage/segments/<name>/<snapped dir>`. The workers flatten these, which needs `FLATTEN=1` at launch.
  - Both modes write `data/aws-stage/manifest.tsv` (name, segment, volume URL, µm, models, depths).
  - `--skip-done` leaves out windings that already have `ink-triage/ensemble/<w>` on the box.
- **Runs on:** Mac (ssh/rsync from the box). **Log/marker:** stdout.
- **Status:** current. **Origin:** ours (MIT).

#### `aws/fleet_plan.sh`
Splits the manifest across N workers and estimates wall time and cost. It makes no AWS calls.
- **Usage:** `aws/fleet_plan.sh N [minutes_per_segment=35]`
- **In → out:** `data/aws-stage/manifest.tsv` → `aws/state/fleet/plan.tsv` (workers w01..wN, round-robin). It prints a suggested `FLEET_MAX_HOURS`.
- **Runs on:** Mac. **Log/marker:** stdout.
- **Status:** current. **Origin:** ours (MIT).

#### `aws/fleet_up.sh`
Launches, bootstraps and pushes every worker in the plan, in parallel.
- **Usage:** `aws/fleet_up.sh --yes [max_hours]`
- **In → out:** `plan.tsv` → `aws/state/fleet/<w>/` (instance state) and `aws/state/fleet/<w>.up.log` (`READY` or `FAILED`).
- **Runs on:** Mac. **Log/marker:** per-worker `.up.log`.
- **Status:** current. It spends money. **Origin:** ours (MIT).

#### `aws/fleet_run.sh`
Uploads each worker's segments and batch list and starts `remote/run_batch.sh` detached. With `--chain`, the new batch is queued behind the one already running.
- **Usage:** `[SQM=1] aws/fleet_run.sh [--chain]`
- **In → out:** `plan.tsv` → `aws/state/fleet/<w>/batch.tsv`, copied to `/opt/scroll/jobs/batch.tsv` on the worker. With `SQM=1` it writes the flag file `/opt/scroll/jobs/sqm.on`.
- **Runs on:** Mac. **Log/marker:** worker log `/opt/scroll/results/batch.log`.
- **Status:** current. **Origin:** ours (MIT).

#### `aws/fleet_status.sh`
Shows each worker's last progress line, its count of finished segments, and a running cost estimate.
- **Usage:** `aws/fleet_status.sh`
- **In → out:** reads `/opt/scroll/results/progress.txt` and `*/DONE` on each worker.
- **Runs on:** Mac. **Log/marker:** stdout; the worker's progress line ends with `BATCH-EXIT`.
- **Status:** current. **Origin:** ours (MIT).

#### `aws/fleet_fetch.sh`
Copies results from every worker, in parallel. By default it is a light copy: stroke scores, ensemble, ensemble_blind and CT images, logs and timings.
- **Usage:** `aws/fleet_fetch.sh [--maps]` (`--maps` adds the raw maps; `FETCH_FULL=1` adds the per-model images and previews)
- **In → out:** `/opt/scroll/results/` → `data/aws-results/fleet/<worker>/<segment>/…`
- **Runs on:** Mac. **Log/marker:** stderr.
- **Status:** current. **Origin:** ours (MIT).

#### `aws/fleet_down.sh`
Terminates every tagged instance (`spot_down.sh --all`) and clears the fleet instance state. The plan and the results stay.
- **Usage:** `aws/fleet_down.sh`
- **Runs on:** Mac. **Log/marker:** stderr.
- **Status:** current. **Origin:** ours (MIT).

#### `aws/fleet.sh`
One command for the whole run:
1. Stage, plan and launch N workers, then start the runs.
2. Every 5 minutes, check status and fetch, until every worker prints `BATCH-EXIT` or none is running.
3. Do a final fetch, then tear down. Teardown also runs on failure or Ctrl-C.
- **Usage:** `aws/fleet.sh N --yes [windings | all]` or `aws/fleet.sh N --yes --resume`. Environment: `MIN_PER_SEGMENT` (35), `FETCH_MAPS=1`, plus `MODELS`/`DEPTHS` for staging.
- **In → out:** → `data/aws-results/fleet/<worker>/<segment>/{ensemble,strokes,…}`
- **Runs on:** Mac. **Log/marker:** launcher, `aws/state/fleet-run-<timestamp>.log` (the latest path is in `aws/state/last_fleet_log`).
- **Status:** current. It spends money. **Origin:** ours (MIT).

#### `aws/fleet_3model.sh`
Runs the three-model pass (seeds 42 and 43 + dense_native) at d = 0 and +1 on every flattened PHerc. 0191 winding not in `EXCLUDE`, by calling `fleet.sh`.
- **Usage:** `aws/fleet_3model.sh N --yes`. Environment: `BOX`, `EXCLUDE` (default w068–w074), `DEPTHS`.
- **In → out:** lists the box's flattened windings over ssh → the same outputs as `fleet.sh`.
- **Runs on:** Mac. **Log/marker:** as for `fleet.sh`.
- **Status:** current. It spends money. **Origin:** ours (MIT).

#### `aws/fleet_rebootstrap.sh`
Re-runs the user-data script on workers that are already running and pushes the pipeline again. This avoids new launches after a bootstrap failure that was not the instance's fault. The hard limit starts again.
- **Usage:** `aws/fleet_rebootstrap.sh [max_hours=2]`, then `aws/fleet.sh N --yes --resume`
- **Runs on:** Mac. **Log/marker:** `aws/state/fleet/<w>.up.log`; it prints `READY` or `FAILED` for each worker.
- **Status:** current (recovery). **Origin:** ours (MIT).

#### `aws/fleet_rank.sh`
Ranks every fleet segment by its stroke score and flags those that need a look. Its header documents the LOOK rule and the calibration. It makes no AWS calls.
- **Usage:** `aws/fleet_rank.sh [results dir=data/aws-results/fleet]`
- **In → out:** `<dir>/*/*/strokes/*__strokes*_d*.json` → TSV on stdout (winding, depth, models, area_R, area_B, R−B, window_R, window_B, top tile, damage, flag, crops path).
- **Runs on:** Mac. **Log/marker:** stdout; the summary goes to stderr.
- **Status:** current. **Origin:** ours (MIT).

#### `aws/fleet_score.sh`
After a fleet run with `FETCH_MAPS=1`, copies each segment's maps to the box, runs `stroke_score.py` there, and compares the AWS seed-42 maps with the box's own maps. The header says "every depth", but the code scores d = 0 and +1 only.
- **Usage:** `aws/fleet_score.sh`
- **In → out:** `data/aws-results/fleet/*/exp30k_snapped_w*/maps` → box `$D/aws-maps/<w>/` and `$S/data/strokes/aws/<w>/`.
- **Runs on:** Mac, driving the GPU box over ssh. **Log/marker:** stdout.
- **Status:** current. **Origin:** ours (MIT).

### Worker side (`aws/remote/`)

#### `aws/remote/setup_models.sh`
Lays out the four checkpoints the way `run_ink.sh` expects (symlinks) and builds `dense_native-016000.pth`.
- **Usage:** `bash /opt/scroll/bin/setup_models.sh` (called by `spot_push.sh`)
- **In → out:** `/opt/scroll/hf/` → `/opt/scroll/ckpt343/`
- **Runs on:** AWS worker. **Log/marker:** `SETUP-MODELS-DONE`.
- **Status:** current. **Origin:** ours (MIT).

#### `aws/remote/run_segment.sh`
Renders one segment with 66 layers straight from S3, makes ink maps for the given models and depths, and writes quick previews. If the segment is not named `flatten.tifxyz`, it first flattens it with Lasagna on the worker. It resumes where it stopped.
- **Usage:** `run_segment.sh <name> <segment.tifxyz dir> <volume zarr URL> <native_um> <models,comma> <depths,comma>`
- **In → out:** segment → (`/opt/scroll/results/<name>/flatten/tifxyz/flatten.tifxyz`, `flatten.log`) → `/opt/scroll/work/<name>_66.zarr` and `/opt/scroll/results/<name>/{maps/,previews/<model>_d±N_{read,blind}.png,timings.tsv,render.log,ink_<m>_d<d>.log,gpu.txt}`
- **Runs on:** AWS worker. **Log/marker:** `RUN-EXIT` is 1 if the flatten or the render fails and 0 otherwise, even if a map failed.
- **Status:** current. **Origin:** ours (MIT).

#### `aws/remote/run_batch.sh`
Works through every line of the batch. For each segment it:
1. Runs `run_segment.sh`.
2. Runs `ensemble_maps.py` and writes a `DONE` marker if it succeeds.
3. Runs `stroke_score.py` for each depth, with the batch's models.
4. Deletes the render.
Scan-Quality-Map can run alongside on the CPU.
- **Usage:** `bash /opt/scroll/bin/run_batch.sh` (started by `fleet_run.sh`)
- **In → out:** `/opt/scroll/jobs/batch.tsv` → `/opt/scroll/results/<name>.run.log` and `/opt/scroll/results/<name>/{ensemble/,strokes/,strokes.log,DONE,sqm/}`, plus `sqm-progress.txt`.
- **Runs on:** AWS worker. **Log/marker:** `/opt/scroll/results/progress.txt` ends with `BATCH-EXIT: 0` (always 0).
- **Status:** current. **Origin:** ours (MIT).

#### `aws/remote/chain_batch.sh`
Waits for the running `run_batch.sh` to finish, then runs it again on the updated `batch.tsv`. Segments with `DONE` are skipped.
- **Usage:** `bash /opt/scroll/bin/chain_batch.sh` (started by `fleet_run.sh --chain`)
- **Runs on:** AWS worker. **Log/marker:** appends to `/opt/scroll/results/batch.log`.
- **Status:** current. **Origin:** ours (MIT).

---

## 7. Site and reporting

The public research log (GitHub Pages site under `docs/`) and pulling images from the box.

#### `scripts/build_site.py`
Renders the research registry into a static site that needs no build step and works without JavaScript.
- **Usage:** `python3 scripts/build_site.py`
- **In → out:** `research/registry.json` → `docs/index.html` and `docs/.nojekyll`. Images it references are copied from `data/results/` to `docs/img/`.
- **Runs on:** Mac. **Log/marker:** none.
- **Status:** current. **Origin:** ours (MIT).

#### `scripts/pull_preview.sh`
Pulls a preview TIFF from the GPU box and converts it to JPEG.
- **Usage:** `scripts/pull_preview.sh <remote path under ~/scroll-prizes/> [local-name]`
- **In → out:** box file → `data/results/<name>.jpg` (converted with `sips`, macOS only). It reaches the box by its LAN address, while the `aws/` scripts use the Tailscale address.
- **Runs on:** Mac. **Log/marker:** prints the output path and size.
- **Status:** current. **Origin:** ours (MIT).

---

## 8. Utilities, status and miscellaneous

Status display and small one-off helpers.

#### `box/bin/status.sh`
Shows one screen of status: mirrors, the day-1 chain (assemble, pilot fit, resume volume), matching processes, disk, GPU memory and Ollama units.
- **Usage:** `bin/status.sh`
- **Runs on:** GPU box. **Log/marker:** stdout.
- **Status:** unclear (stale). It covers only the day-1 jobs of 2026-10-08. **Origin:** ours (MIT).

#### `box/bin/candidates_survey.py`
Makes a montage of CT cross-sections (level 4, at 40 % and 65 % of height) of PHerc. 0125, 0211, 0813, 0826 and 0257, streamed from S3. It has no header comment.
- **Usage:** `python bin/candidates_survey.py`
- **In → out:** S3 → `/tmp/candidates_survey.tif`
- **Runs on:** GPU box. **Log/marker:** launcher, `$S/candidates-survey.log`; `MONTAGE-EXIT: 0`.
- **Status:** one-off. **Origin:** ours (MIT).

#### `box/bin/inspect_fiber_ckpt.py`
Prints the top-level keys and config-like entries of a PyTorch checkpoint. It has no header comment.
- **Usage:** `python bin/inspect_fiber_ckpt.py <checkpoint.pt>`
- **In → out:** → lines starting with `INSPECT` on stdout.
- **Runs on:** GPU box. **Log/marker:** launcher, `$S/fiber-ckpt-inspect.log`.
- **Status:** one-off. **Origin:** ours (MIT).

---

## Not yet mirrored

These two scripts exist only on the GPU box, in `~/scroll-prizes/bin/`, and are not yet in `box/bin/`.

#### `~/scroll-prizes/bin/prep_community.sh` (box only)
Snaps (with Nieuwlaar's `snap_meshes.py`) and flattens (Lasagna) the windings of the community PHerc. 0191 fit (rodriguescarson/eligible-scroll-spiral-fits, z 11600–12400), so that they can go through render + ink like our own windings.
- **Usage:** `bin/prep_community.sh <GPU UUID for flatten>`
- **In → out:** waits for `SURFMIRROR-EXIT: 0` in `$S/mirror-surf-z11k.log`. Reads `$D/community-fit/wNNN`. Writes `$D/snapped/community/` (`windings.txt`, `snap.log`, `snap_report.tsv`) and `$D/flatten/community-snapped-wNNN/tifxyz/flatten.tifxyz`, which can be staged with `FLATTEN_PREFIX=community-snapped aws/stage_segments.sh`.
- **Runs on:** GPU box. **Log/marker:** stdout; `PREPCOMM-EXIT: 0` (always 0).
- **Status:** current (the newest script). **Origin:** ours (MIT); it uses Nieuwlaar's snap script and the community fit meshes by rodriguescarson.

#### `~/scroll-prizes/bin/mirror_surf_band_z11k.sh` (box only)
Mirrors level 0 of the m7 surface prediction for z chunk rows 57–65 (z 10944–12672), the band of the community fit.
- **Usage:** `bin/mirror_surf_band_z11k.sh`
- **In → out:** S3 → `$D/surf-m7/…m7-L0-th0.2.zarr/0/57..65`
- **Runs on:** GPU box. **Log/marker:** launcher, `$S/mirror-surf-z11k.log`; `SURFMIRROR-EXIT: 0` (always 0).
- **Status:** one-off. **Origin:** ours (MIT).

---

## Known inconsistencies

1. Many markers print `: 0` whatever happened (ENSWIND, THREEM, TRIAGE, PATCHQA, RANK, BATCH, PREPCOMM, SURFMIRROR …). Suggestion: print the failure count instead.
2. The GPU 1 guard matches only the UUID string, so index `1` gets through; `control343_ensemble.sh` has no guard; older scripts hard-code UUIDs. Suggestion: one shared guard, with the GPU always passed as an argument.
3. Some scripts write their own log while most rely on the launcher, and log names differ from script names (`three_model_windings.sh` → `three-model.log`). Suggestion: each script writes `$S/<script>.log` itself.
4. Paths mix `~/scroll-prizes/data` and `/mnt/nvme/scroll-prizes/data`, which are the same place. Suggestion: one root variable.
5. Stroke scores sit in four trees (`strokes/<w>`, `strokes/box3m`, `strokes/aws`, `aws-results/fleet`). `stroke_rank.sh` reads only one of them, and the LOOK rule is copied into two scripts. Suggestion: one ranker over all score files.
6. `ink-triage/` holds all ink maps and ensemble images, not only the triage pass, and `ensemble/` vs `ensemble3/` is easy to misread. Suggestion: rename to `ink/` with `ens4/` and `ens3/`.
7. `tracer_lasagna_test.sh` writes into `grow-test/dirfield2/`, the folder of Fiber attempt 2. Suggestion: give it its own folder.
8. There are near-copies: `mirror_surf_band*.sh`, `render_2p4um_crop1{,b}.sh`, `queue_wm.sh`, `export_wm.sh`, and four QA scripts. Suggestion: keep one version with parameters and move the rest to an attic folder.
9. Some comments contradict the code: `winding_band.sh`'s disk guard never aborts, `assemble_pherc0191.sh` says "3 repeats" but passes 5, and `fleet_score.sh` says "every depth" but scores 0 and +1. Suggestion: fix the comments or the code.
10. The `spot_*` scripts also launch on-demand instances. Suggestion: rename them `worker_*`, or document this.
11. No script builds the box's `checkpoints/ckpt343/`. Suggestion: add a box version of `aws/remote/setup_models.sh`.
