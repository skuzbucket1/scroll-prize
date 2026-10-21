# pipeline: what works

This is the path from a CT scan to a short list of places worth a human look. Each step was checked on text we already
know is there before we trusted it on a scroll where we don't. The site's pipeline page explains the ideas; this file
says which script does what.

## Steps

1. **Geometry** (`geometry/`)
   - `assemble_spiral_dataset.sh`, `smooth_umbilicus.py`: the fitter's inputs for a new scroll.
   - `fit_band.sh`: spiral fit of one band (tracks only, grad_mag spacing, no outer shell, 30k steps).
   - `snap_band.sh` → `snap_meshes_nieuwlaar.py` (Erwin Nieuwlaar, MIT): each winding pulled onto the predicted papyrus
     surface.
   - `flatten_winding.sh`: Lasagna flattening, the step the organisers recommend before rendering.
   - `mesh_in_mask.py`, `ray_peaks.py`, `patch_qa.sh`: quick checks on a fit or a mesh.
2. **Render** (`render/`): `render66.sh` makes the 66-layer stack. `triage_band.sh` does flatten → render → CT preview for a
   whole fit. `fetch_mesh_chunks.py` fetches only the CT chunks a mesh needs.
3. **Ink** (`ink/`): `band_models.sh` runs any set of models and depths over a fit's windings. `depth_sweep.sh` runs the
   six-model depth sweep for a deep look. `ink343/` holds Erwin Nieuwlaar's scripts (MIT, see its README and licence),
   which every run goes through.
4. **Rank** (`rank/`): `band_post.sh` → `post_models.py` builds the mean-z ensemble, the stroke score, the row score and
   previews. `rank_post.py` ranks the results with the stroke-score 0.2 rules. The stroke score itself is the released
   tool in `../tools/stroke-score/`. `stroke_score.py` is the older box version, still used by the AWS fleet scripts.
5. **Review** (`review/`): `candidate_view.py` (a window at full resolution), `neighbour_view.py` (the same place on the
   neighbouring turns), `deep_look_view.py` (six models × depth), `review_post.py`, `viz_strokes.py`, `viz_looked.py`
   (where we have looked), `viewer_links.py` (for the offline viewer), and small preview helpers.
6. **Controls** (`controls/`): `control343.sh` and `control343_ensemble.sh` run the PHerc. 343 winning segment through
   everything above. `control_eval.py` scores our maps against a reference on PHerc0139 and PHerc0841. `side_check.py`
   checks that the reading side is the written face. `triage_eval.py` and `band_nulls.py` measure the hit rate on known
   text and the false-alarm rate on bare windings.

## Shared by every step (`common/`)

- `conventions.py`: map file names, depths, voxel sizes, valid-pixel masks, AUC with ties, normals. One place for the
  things a script must not get slightly wrong on its own.
- `scroll_ids.py`: one name for each scroll, winding and window (`PHerc0139/z7680/w044/n64m128`), read from every older
  name form we use, and one name for each face of the sheet (`reading`, `back`).
- `platform_config.py` with `platform.example.toml`: where things are (machines and their GPUs, paths, volumes, model files
  with checksums, result pages), read from one config file instead of being written into each script.
  `python3 platform_config.py check <file>` validates a config.
- `tests/`: `python3 -m unittest discover -s pipeline/common/tests`.

## What it has been checked on

- PHerc. Paris 4: three readable lines of Greek.
- PHerc. 343: the First Letters winning segment. The letters show, with the ensemble.
- PHerc0139 w047 and PHerc0841 at 9.36 µm: the published scores reproduce. stroke-score 0.2 flags 14 of 15 strips of
  PHerc0841 text it never saw, and 8 of 294 bare winding-depths.
- Our reading side is the written face on both scrolls we search.

## Known limits

- The fit sometimes stacks two or three windings on one sheet, so some sheets are searched twice and others not at all.
  It is being measured (`../experiments/geometry-coverage`).
- Cracks, holes and structure that repeats from turn to turn can score like writing. Every flag gets looked at by eye
  next to its neighbours before we call it anything.

## Runs

`runs/` keeps the launch scripts of search runs, which are the pipeline applied to a scroll. The outputs live on the GPU
box under `~/scroll-prizes/runs/<same name>/`.
