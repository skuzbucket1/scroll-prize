# Data layout (proposal, 2026-10-10)

Status: **approved by Ted and MIGRATED on 2026-10-10 (02:40 UTC)**, while no job was running. Disk cleanup freed 186 G first
(disk 91 % → 71 %). Every moved item left an absolute symlink at its old path, so old paths in scripts, notes and memory still
work; new work should use the new paths. Script: `scratch/migrate_layout.sh` on the GPU machine (dry-run output `scratch/migrate-dry.txt`).

**Changes from 2026-10-13 to 2026-10-21** (the public part; the rest of this file still holds):
- **Control renders on the second disk** (`/mnt/nvme2/scroll-prizes/controls/`): `c0139_w047_66.zarr`, `c0841_ag2814_66.zarr`,
  `c0841_w00_66.zarr`, and `official/`: the official ink-labelled segments rendered with our 66-layer recipe (PHerc0139 w030,
  w035, w039, w045; PHerc0841 ag144). CT crops of the controls: `data/controls-ct/`, `data/controls-ct24/` (2.4 µm).
  2.4 µm control material for PHerc0841: `data/controls24/PHerc0841/`.
- **Training sets of the fine-tune tests** (`data/train8um/`, `data/train-recipe0841/`, `data/train-chain0841/` on the second
  disk): all dead ends now (`dead-ends/model-8um-v1/` and the site's findings); kept until a disk clean-up.
- **`work/`** holds one working folder per task (deep-look crops, labelling, review pages); our private notes describe it.
- **`checkpoints/`**: the model files; their checksums are now kept in one config file (format:
  `pipeline/common/platform.example.toml`).
- **Disks on 2026-10-21:** first 84 % full, second 87 %.

**Changes on 2026-10-11 and 2026-10-12** (the rest of this file describes the 2026-10-10 layout, which still holds):
- **Second disk** `/mnt/nvme2/scroll-prizes` (916 G, since 2026-10-11): every scroll's `renders/` (`data/<scroll>/renders` is a
  symlink to it), `scratch/` (ink-first work folders, `run_ink.sh` temp), the known-text control renders (`controls/`) and
  `data/PHerc0841/ct-w00.zarr` (CT around the held-out mesh, `fetch_mesh_chunks.py`). The catalog scans it as a second root of
  host `box` (the scanner does not follow symlinks).
- **Tall bands, PHerc0813:** `geometry/`, `renders/` and `ink/` for fits `exp30k-z10500` (z 10,500–13,000) and `exp30k-z8000`
  (z 8,000–10,500); runs in `runs/2026-10-11_tallband-0813-z10500/` and `runs/2026-10-12_tallband-0813-z8000/` (claims, unit
  logs, `post/` scores, `ranking_v02.tsv`).
- **Ink first at scale:** plan `data/PHerc0175A/plan/blocks.tsv` (laptop; coarse CT on the GPU machine in
  `runs/2026-10-12_inkfirst-0175A/plan/`); AWS results `data/PHerc0175A/runs-aws/2026-10-12_inkfirst-{pilot,sweep}/w<i>/<block>/`
  (summary.npz, galleries, logs; laptop, copied to the GPU machine); whole-scroll products in `runs/2026-10-12_inkfirst-0175A/`
  (`map-interim/`, `map-final/`, `refs/`, `resort/`) with laptop copies in `data/PHerc0175A/`.
- **Tests and controls (GPU machine `runs/`, laptop copies in `data/results/` or `data/PHerc0343/`):** `2026-10-12_triage-eval/`,
  `2026-10-12_heldout-0841-w00/`, `2026-10-12_controls-render/`, `2026-10-12_inkfirst-343/` (results, results_persheet,
  letters, maps, views), `2026-10-12_ct-ink-signature/`, `2026-10-12_model-agreement/`, `2026-10-12_agreement-null/`,
  `2026-10-12_deeplook-0813-w079/`, `2026-10-12_ted-picks/` (neighbour views), `2026-10-12_sheet-tracer/`,
  `2026-10-12_viz-looked/`, `2026-10-12_viz-glow/`.
- **laptop only, private:** `data/viewer/` (preview images, `index.html`, `links.json`; built by `infra/site/build_viewer.py`).

**Changes on 2026-10-13:**
- **Cleanup** (approved by Ted). Tier 1, about 21 G: the torch compile cache in `/mnt/nvme2/scroll-prizes/scratch/`, the
  CT and prediction copies of the PHerc. 343 ink-first block, `scratch/inkfirst-dry2` and old `run_ink.sh` temp folders.
  Tier 2, 413 G (log `runs/2026-10-13_cleanup-tier2/log.txt`): the PHerc0191 CT mirror
  `data/PHerc0191/source/volume/20250821151635-9.362um-1.2m-113keV-masked.zarr` (410 G) and the old-phase renders
  `data/PHerc0191/renders/oldphase30k-z9000` (2.8 G); the dangling `data/PHerc0191/volumes` symlink went with them, and
  `data/PHerc0191/source/VOLUME_DELETED.txt` says where to re-download the CT. Kept: every band render (PHerc0813
  exp30k-z8000, z10500, z12000; PHerc0191 exp30k-z11200), ink maps, scores, meshes, fit inputs and the PHerc0813 CT mirror.
  disk 84 % → 40 % (562 G free); NVMe2 75 % (224 G free). New PHerc0191 renders now need the CT re-fetched, or only the
  chunks around a mesh (`pipeline/render/fetch_mesh_chunks.py`).
- **8.64 µm ink model:** training set `data/train8um/labels/pherc0343-nieuwlaar/` (villa's flat layout: 65-layer reversed
  `surface-volume.zarr`, ink labels, supervision and validation masks); run `runs/2026-10-13_model-8um/` (`build_dataset.py`,
  `train_v1.json`, checkpoints in `out_v1/`, evaluation in `eval_v1/`).
- **Damage map:** `runs/2026-10-13_damage-map/` (`tiles/*.npz` per render, `png/` pictures, `report.txt`).

**Cleanup Tier 1 done 2026-10-10 11:18 UTC** (approved by Ted; script and log in `runs/2026-10-10_cleanup-tier1/` on the GPU machine):
disk 825 G → 701 G (89 % → 76 %). Deleted: old-band renders `data/PHerc0191/renders/exp30k-z9000` (88 G; maps and scores
kept, renders regenerable), fibre fields `inputs/fields/fiber` (11 G), tracer tests (`geometry/tracer-tests`,
`renders/tracer-tests`, 8.7 G), `checkpoint_fitted.ckpt` of the 9 dropped fit experiments (pilot, expdirlow, expdirlow2,
expdr32, expshell105, expshell105b, exptrack2x, expwm, expwm2; meshes and metrics kept, ~8.5 G), the old-fitter worktree
`wt/spiral-0fb38c45` (6.9 G; its one local change is saved as `dead-ends/old-fitter/old-fitter-0fb38c45-fit_spiral.diff`), old QA
renders (`geometry/qa-legacy`, `geometry/pilot-z9000/qa`, 1.7 G), the day-1 smoke runs (1.1 G), idle scratch files; plus
the compatibility symlinks that pointed at them (no dangling links left). Still to clear: `scratch/torchinductor_tbienapfl`
(6.4 G) once Phase A3 ends. Tier 2 (PHerc0191 CT outside the clear band, Lasagna, tracks, ~400 G) waits for Gate A;
Tier 3 (clear-band renders, 85 G) waits for the Phase A4 decision.


Deviations from the plan below, on purpose:
- Folder names *inside* a stage keep the names the tools write (`snapped/wNNN_exp-30k/`, ink-map file names with
  `exp30k_snapped_wNNN_66`), so no script had to change. Flattened windings and renders were renamed to `wNNN/` and `wNNN.zarr`.
- The old stage folders (`spiral-output/`, `snapped/`, `flatten/`, `render66/`) are now folders of per-item symlinks;
  new fits still write into `spiral-output/` until the scripts are updated.
- The ~105 top-level job logs went to `runs/archive-2026-10-08_10/logs/` without symlinks (history only). New jobs still write
  `~/scroll-prizes/<job>.log` until their scripts are updated to `runs/<date>_<run-id>/`.
- laptop: AWS results are in `data/<SCROLL>/runs-aws/<date>_<run-id>/` (old `data/aws-results/runN` are symlinks), review crops in
  `data/PHerc0191/reviews/2026-10-09_flagged-windings/`, staging in `scratch/aws-stage/`.

## Why

The work moved fast and the folder tree grew with it: the same fit is spelled `exp-30k` in one place and `exp30k` in
another, four-model ensemble images live under `ink-triage/`, three-model ones under `ensemble3/`, cloud results sit
next to them as `aws-maps/` and `aws-ens/`, about forty job logs are loose in the top folder, and some analysis scripts
live in `tmp/`. Someone new could not follow it. This layout fixes that with one rule: **a path says which scroll,
which pipeline stage, which run, and which winding, in that order.**

## The tree

The same logical tree on the GPU machine (`/mnt/nvme/scroll-prizes`, alias `~/scroll-prizes`) and on the laptop
(`scroll-prizes/`, where only small results are kept). Plain names, no numeric prefixes; the stage order is given here.

```
scroll-prizes/
  bin/                          code, flat (in the public repo sorted by status; infra/box/sync_bin.py); see docs/CODE_DICTIONARY.md
  data/
    <SCROLL>/                   e.g. PHerc0191, PHerc0343, PHerc0800, PHercParis4
      source/                   public data mirrored as-is, read-only (re-downloadable)
        volume/                 CT OME-Zarr (all levels)
        surface-m7/             surface prediction, level 0 bands
        tracks/                 spiral tracks dataset
        lasagna/                Lasagna normals and gradient magnitude
        normal-grids/
        community/<source>/     other people's published meshes (credited; e.g. rodriguescarson-fit-z11600)
      inputs/                   our derived inputs that several runs share (spiral dataset, umbilicus, fields)
        spiral-dataset/
        fields/                 fibre fields, direction fields, signed distance fields
      geometry/<fit-id>/        one folder per geometry run
        fit/                    raw fitter output (checkpoints, meshes, metrics)
        snapped/<winding>/      tifxyz after the snap onto the surface prediction
        flattened/<winding>/    tifxyz after Lasagna flattening (what gets rendered)
        qa/                     triage previews, montages
      renders/<fit-id>/<winding>.zarr          66-layer renders (regenerable, ~1 GB each)
      ink/<fit-id>/<model-set>/<winding>/
        maps/                   raw ink maps (both sides, every depth run)
        ensemble/               ensemble images (reading + blind + CT)
      scores/<fit-id>/<model-set>/
        strokes/<winding>/      stroke-score json, png, review crops
        sqm/<winding>/          scan-quality maps (Scan-Quality-Map)
        ranking.tsv             one row per winding x depth, with the LOOK flag
      reviews/<date>_<topic>/   what a human actually looked at: crops, notes, verdict
  runs/<date>_<run-id>/         one folder per job: run.json + logs (replaces the loose *.log files)
  checkpoints/                  model weights (ink models, Hecate, dense_native)
  envs/  wt/  villa/            environments, git worktrees, upstream clone
  cache/                        caches safe to delete (uv, torch compile, chunk caches)
  scratch/                      temporary files; anything here may be deleted at any time
```

## Names

- **Scroll**: `PHerc0191` style everywhere (zero-padded, no dots).
- **Winding**: `w070` (three digits). Community windings keep their own numbering under their own fit id.
- **Fit id**: `<recipe>-z<start>` in lower case with hyphens, e.g. `exp30k-z9000`, `exp30k-z11200`,
  `oldphase30k-z9000`, `community-z11600`. One spelling, used in folder names, logs, the registry and the site.
- **Model set**: `ens4` (ink_9um seeds 42 + 43, dense_native, Hecate), `ens3` (the same without Hecate),
  `s42` (ink_9um seed 42 alone).
- **Run id**: `<stage>-<what>`, e.g. `fit-exp30k-z11200`, `ink-ens3-aws-run2`, `snap-community-z11600`.
- File names inside a winding folder keep the patterns the tools already write (`<name>__<model>__L66s<s>[_reverse].tif`
  and so on, see docs/DATA_DICTIONARY.md), so no tool has to change its output format.

## The run record (`runs/<date>_<run-id>/run.json`)

Every job writes one, so a result can always be traced back to the code and inputs that made it:

```json
{
  "run_id": "ink-ens3-aws-run2",
  "started": "2026-10-09T22:50:15Z", "finished": "2026-10-10T00:21:32Z",
  "where": "aws: 10 x cloud GPU instance (cloud GPU)",
  "code": {"repo_commit": "d92a377", "villa_commit": "12f21236a"},
  "command": "infra/aws/fleet.sh 10 --yes ...",
  "params": {"models": "ens3", "depths": [0, 1]},
  "inputs": ["data/PHerc0191/geometry/exp30k-z9000/flattened/w037", "..."],
  "outputs": ["data/PHerc0191/scores/exp30k-z9000/ens3/ranking.tsv", "..."],
  "cost_usd": 10.70,
  "result": "no ink; 8 window flags, all diffuse mottling by eye",
  "registry_id": "aws-fleet-run2"
}
```

`registry_id` links the run to its entry on the research site (`research/registry.json`).

## What is kept

| Class | Meaning | Examples | Rule |
|---|---|---|---|
| SOURCE | public, re-downloadable | CT volume, surface predictions, tracks | keep while in use; can be deleted and re-mirrored |
| REGENERABLE | recomputable from source + code | 66-layer renders, caches of fitter inputs | delete when the stage that needs them is done (renders after scoring) |
| KEEP | results or expensive to redo | fit outputs, ink maps of anything flagged or reviewed, rankings, reviews, run records | never delete without asking |
| SCRATCH | temporary | `scratch/`, `cache/` | delete any time |

## How the move would happen

1. Wait for a quiet moment between stages (no job writing to a folder being moved).
2. Move within the same disk (`mv` on the disk is instant, no copying).
3. Leave a symlink at every old path, so running jobs, scripts, notes and agent memory keep working.
4. Update the scripts to the new paths one at a time (atomically: write `<script>.new`, check, rename).
5. Remove the symlinks only after nothing refers to the old paths for a few days (`grep` the scripts and notes).
6. Re-run the inventory and confirm the totals match before and after.

## Current to new

From our data inventory of 2026-10-10 (GPU-machine paths relative to `/mnt/nvme/scroll-prizes/`, `P` = `data/PHerc0191`).
Sizes are as of 2026-10-10 01:30 UTC. Retention class in the last column (S = SOURCE, R = REGENERABLE, K = KEEP, X = SCRATCH).

### Box: sources and shared inputs

| Current | New | Size | Class |
|---|---|---|---|
| `P/volumes/20250821151635-9.362um-…zarr` | `P/source/volume/20250821151635-9.362um-…zarr` | 410 G | S |
| `P/surf-m7/…-m7-L0-th0.2.zarr` | `P/source/surface-m7/…-m7-L0-th0.2.zarr` | 5.0 G | S |
| `P/spiral/20250821151635/tracks/` | `P/source/tracks/20250821151635/` | 21 G | S |
| `P/lasagna/20250821151635-lasagna-…/` (stores) | `P/source/lasagna/20250821151635-lasagna-…/` | 18 G | S |
| `P/lasagna/…/*.respool_g2*` (sidecars the fits load) | stay next to the stores (the fitter finds them there) | 17.6 G | R |
| `P/normal-grids/` | `P/source/normal-grids/` | 5.6 G | S |
| `P/community-fit/` | `P/source/community/rodriguescarson-fit-z11600/` | 0.3 M | S |
| `P/spiral-dataset/` | `P/inputs/spiral-dataset/` (symlinks re-pointed) | 23 G | K (small files) |
| `P/spiral-dataset/lasagna_inputs/*.respool*` | delete (never loaded; duplicate of the sidecars above) | 17.6 G | X |
| `P/spiral-dataset/outer_shell_dz1/`, `outer_shell.v0/` | delete (duplicate / superseded) | 180 M | X |
| `P/spiral-dataset-old/` | `P/inputs/spiral-dataset-oldfitter/` | 44 K | K |
| `P/fiber/`, `P/winding/band9000-10000/winding_native_phase_ws8_ss96.zarr` | `P/inputs/fields/fiber-band8500-10500/`, delete the winding cache (export done) | 11 G, 104 G | R, X |
| `P/winding/band9000-10000/smoke*` | delete | 3.7 G | X |

### Box: geometry

| Current | New | Size | Class |
|---|---|---|---|
| `P/spiral-output/<date>_…_0-patch_<tag>/` (11 runs) | `P/geometry/<fit-id>/fit/` (e.g. `exp30k-z9000/fit/`) | 11 G | K for exp-30k and the new band, R for checkpoints of dropped experiments |
| `P/spiral-output-old/…old-phase-30k/` | `P/geometry/oldphase30k-z9000/fit/` | (running) | K |
| `P/snapped/exp-30k/wNNN_exp-30k/` | `P/geometry/exp30k-z9000/snapped/wNNN/` | 27 M | K |
| `P/snapped/community/wNNN/` | `P/geometry/community-z11600/snapped/wNNN/` | 0.3 M | K |
| `P/snapped/exp30k-z11200/` (new) | `P/geometry/exp30k-z11200/snapped/` | – | K |
| `P/flatten/exp-30k-snapped-wNNN/` | `P/geometry/exp30k-z9000/flattened/wNNN/` (drop `model_snapshots/`, 1.6 G) | 1.9 G | K |
| `P/flatten/community-snapped-wNNN/` | `P/geometry/community-z11600/flattened/wNNN/` | 10 M | K |
| `P/flatten/lasagna150/`, `P/grow-test/` | `P/geometry/tracer-tests/` | 5.3 G | R |
| `P/triage/previews/`, `P/winding-qa/`, `P/pilot-qa/`, `P/snapped/qa_*` | `P/geometry/<fit-id>/qa/` | 2.3 G | R |
| `P/flatten/exp-30k-snapped-w116/` (failed) | delete | 2.7 M | X |

### Box: renders, ink, scores

| Current | New | Size | Class |
|---|---|---|---|
| `P/render66/exp30k_snapped_wNNN_66.zarr` | `P/renders/exp30k-z9000/wNNN.zarr` | 90 G | R (delete after scoring) |
| `P/render66/lasagna150_66.zarr` | `P/renders/tracer-tests/lasagna150.zarr` | 3.5 G | R |
| `P/ink-triage/maps/` | `P/ink/exp30k-z9000/maps/` (one folder per fit; model and depth stay in the file names) | 2.0 G | K |
| `P/ink-triage/ensemble/wNNN/` | `P/ink/exp30k-z9000/ens4/wNNN/` | 528 M | K |
| `P/ink-triage/ensemble3/wNNN/` | `P/ink/exp30k-z9000/ens3/wNNN/` | 650 M | K |
| `P/ink-triage/previews/` | `P/ink/exp30k-z9000/s42-previews/` | 224 M | R |
| `P/ink-triage/claims*/`, `*.log` | `runs/…` (claims are job state; delete when the job ends) | 0.3 M | X |
| `P/sweeps/` | `P/ink/<fit-id>/sweeps/` | 474 M | K |
| `P/aws-maps/`, `P/aws-ens/` | `P/ink/exp30k-z9000/ens4/w073`, `w074` (they are fleet run 1 results) | 355 M | K |
| `data/strokes/wNNN/`, `box3m/`, `aws/`, `c343/` | `P/scores/exp30k-z9000/{ens4,ens3,s42}/strokes/wNNN/`; control → `data/PHerc0343/scores/control/` | 355 M | K |
| `data/strokes/ranking.tsv` | `P/scores/exp30k-z9000/ranking.tsv` (one ranker over all model sets) | – | K |
| `data/PHerc0343/control/` | `data/PHerc0343/{source/community/nieuwlaar-winner-mesh, renders/control/, ink/control/}` | 1.1 G | K |
| `data/PHerc0800/`, `data/PHercParis4/` | `data/<SCROLL>/source/…` | 5.3 G | S |

### Box: everything else

| Current | New | Size | Class |
|---|---|---|---|
| `*.log` × 105 at the top | `runs/<date>_<run-id>/` (old logs into `runs/archive-2026-10-08_10/`) | 2 M | K |
| `runs/` (day-1 smoke tests) | `runs/2026-10-08_smoke-*/` | 1.1 G | R |
| `tmp/` | `scratch/` (ad hoc scripts worth keeping go to `bin/` or `notes/`) | 1.8 G | X |
| `cache/`, `cache-root/` | `cache/` | 30 G | X |
| `/mnt/nvme/vc3d-remote-cache/` | delete when no render is running (PHerc0191 chunks duplicate the mirror) | 29 G | X |
| `villa/lasagna/torchinductor_tbienapfl/` | delete | 129 M | X |
| `build-vc3d.sh` | `bin/` | – | K |

### laptop

| Current | New | Class |
|---|---|---|
| `data/aws-results/run1`, `run2`, `fleet` (live run) | `data/PHerc0191/runs-aws/<date>_<run-id>/` with worker folders renamed `worker01…` | K |
| `data/aws-results/i-07316924655570581/` | `data/PHerc0343/runs-aws/2026-10-09_poc/` | K |
| `data/aws-stage/` | `scratch/aws-stage/` | X |
| `data/strokes/` (review crops) | `data/PHerc0191/reviews/2026-10-09_flagged-windings/` | K |
| `data/results/` (site images) | unchanged (the site builder reads it) | K |
| `data/prior-art/`, `data/catalog/`, `data/ref/` | unchanged | S |

### Disk this would free on the GPU machine

About 190 G: winding-model cache 104 G, VC3D remote cache 29 G, uv cache 24 G (rebuilds on demand), unused sidecar copy
17.6 G (after the old-fitter run ends), torch caches 6.4 G, smoke tests 3.7 G, `tmp/` 1.8 G, flatten snapshots 1.6 G,
small duplicates. The disk would go from 840 G to about 650 G used (about 69 %). Nothing is deleted without Ted's go-ahead.

## Tracking and backup (added 2026-10-11, agreed with Ted)

**One rule.** Every run writes into `runs/<date>_<run-id>/` (with `run.json`). When it is done, its results are promoted into
the canonical tree (`<scroll>/geometry`, `ink`, `scores`); AWS runs land in `data/<scroll>/runs-aws/<date>_<run-id>/` on the laptop
and are synced to the GPU machine. Folders created since the migration that follow this pattern: `data/controls9um/` (known-text
controls at 9 µm: PHerc0139 w047, PHerc0841 auto_grown; maps, references, evaluations), `runs/2026-10-11_tier23-newmodels/post/`
(scores and previews for any model set, from `pipeline/rank/post_models.py`).

**Catalog and results table (generated, never hand-edited).**
- `infra/backup/catalog.py <host> <root> <out.sqlite>` walks a host and writes one row per artifact (host, path, kind, scroll, fit,
  winding, model, depth, side, run, size, mtime, sha1 for critical files, critical flag). Zarr stores and tifxyz meshes are one
  artifact each; public scan inputs are listed per store without walking.
- `infra/backup/results_db.py <host> <root> <out.sqlite>` collects every score (stroke-score JSONs, post_models JSONs, row scores,
  control AUCs) into one `scores` table with provenance and the v0.1 LOOK flag recomputed; `--merge` combines hosts.
- Merged copies on the laptop: `data/catalog/catalog.sqlite`, `data/catalog/results.sqlite`; summary `docs/DATA_CATALOG.md`
  (`infra/backup/catalog_report.py`). Re-run all three after each run.

**Backup.** `infra/backup/backup_r2.sh mac|box` syncs the critical set to Ted's private object-storage bucket (rclone, with dated
`_archive/` copies of anything changed or deleted). Critical = memory, fits and meshes, umbilici, scores, run records, review
images, controls, AWS results, and the ink maps of the windings in `infra/backup/windings_of_interest.tsv`. Not backed up: scan data and
other public inputs, renders, resident pools, caches (all re-creatable).
