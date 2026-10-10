# Data layout (proposal, 2026-10-10)

Status: **proposal for review, nothing has been moved yet.** The current-to-new path map at the end is filled in
from the inventory in `notes/data-inventory-2026-10-10.md`.

## Why

The work moved fast and the folder tree grew with it: the same fit is spelled `exp-30k` in one place and `exp30k` in
another, four-model ensemble images live under `ink-triage/`, three-model ones under `ensemble3/`, cloud results sit
next to them as `aws-maps/` and `aws-ens/`, about forty job logs are loose in the top folder, and some analysis scripts
live in `tmp/`. Someone new could not follow it. This layout fixes that with one rule: **a path says which scroll,
which pipeline stage, which run, and which winding, in that order.**

## The tree

The same logical tree on the GPU box (`/mnt/nvme/scroll-prizes`, alias `~/scroll-prizes`) and on the Mac
(`scroll-prizes/`, where only small results are kept). Plain names, no numeric prefixes; the stage order is given here.

```
scroll-prizes/
  bin/                          code (mirrored into the public repo as box/bin/); see docs/CODE_DICTIONARY.md
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
  "where": "aws: 10 x g4dn.2xlarge (T4)",
  "code": {"repo_commit": "d92a377", "villa_commit": "12f21236a"},
  "command": "aws/fleet.sh 10 --yes ...",
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
2. Move within the same disk (`mv` on the NVMe is instant, no copying).
3. Leave a symlink at every old path, so running jobs, scripts, notes and agent memory keep working.
4. Update the scripts to the new paths one at a time (atomically: write `<script>.new`, check, rename).
5. Remove the symlinks only after nothing refers to the old paths for a few days (`grep` the scripts and notes).
6. Re-run the inventory and confirm the totals match before and after.

## Current to new

From `notes/data-inventory-2026-10-10.md` (box paths relative to `/mnt/nvme/scroll-prizes/`, `P` = `data/PHerc0191`).
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

### Mac

| Current | New | Class |
|---|---|---|
| `data/aws-results/run1`, `run2`, `fleet` (live run) | `data/PHerc0191/runs-aws/<date>_<run-id>/` with worker folders renamed `worker01…` | K |
| `data/aws-results/i-07316924655570581/` | `data/PHerc0343/runs-aws/2026-10-09_poc/` | K |
| `data/aws-stage/` | `scratch/aws-stage/` | X |
| `data/strokes/` (review crops) | `data/PHerc0191/reviews/2026-10-09_flagged-windings/` | K |
| `data/results/` (site images) | unchanged (the site builder reads it) | K |
| `data/prior-art/`, `data/catalog/`, `data/ref/` | unchanged | S |

### Disk this would free on the box

About 190 G: winding-model cache 104 G, VC3D remote cache 29 G, uv cache 24 G (rebuilds on demand), unused sidecar copy
17.6 G (after the old-fitter run ends), torch caches 6.4 G, smoke tests 3.7 G, `tmp/` 1.8 G, flatten snapshots 1.6 G,
small duplicates. The NVMe would go from 840 G to about 650 G used (about 69 %). Nothing is deleted without Ted's go-ahead.
