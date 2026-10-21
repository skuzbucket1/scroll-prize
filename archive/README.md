# archive

These scripts are not for new work. They are kept because past runs on the site were made with them.

## one-off/: setup steps that are done

| script | what it did |
|---|---|
| `assemble_pherc0191.sh` | built PHerc0191's spiral-fit dataset once (the generic version is `pipeline/geometry/assemble_spiral_dataset.sh`) |
| `resume_volume_after_lasagna.sh`, `switch_lasagna_to_v2.sh` | managed the first PHerc0191 mirrors |
| `mirror_surf_band.sh`, `mirror_surf_band_l1.sh`, `mirror_surf_band_z11k.sh` | mirrored bands of PHerc0191's surface prediction |
| `mirror_band_pherc0813.sh` | mirrored PHerc0813's first band and its fit inputs (copy it for a new scroll) |
| `pilot_fit_pherc0191.sh`, `pilot_qa.sh` | the first pilot fit and its check |
| `snap_exp30k.sh`, `snap_newband.sh` | snapped two specific fits (now `pipeline/geometry/snap_band.sh`) |
| `prep_community.sh` | snapped and flattened the community PHerc0191 fit |
| `render_2p4um_crop1.sh`, `render_2p4um_crop1b.sh`, `infer_7p91_smoke.sh` | the day-one ink calibration on PHerc. Paris 4 |
| `candidates_survey.py` | the CT survey that chose between scrolls |
| `shape_features.py` | measured mark shapes to design the shape score (now part of `tools/stroke-score`) |

## superseded/: replaced by newer scripts

| script | replaced by |
|---|---|
| `mirror_s3.py` | `infra/box/mirror_s3_v2.py` |
| `hf_ink_extra.sh` | `pipeline/ink/ink343/fetch_checkpoints.sh` (checks every file's sha256) |
| `ink_triage.sh`, `ink_sheet.py` | the single-model fast pass, replaced by `pipeline/ink/band_models.sh` with any model set |
| `ensemble_windings.sh`, `three_model_windings.sh`, `band_three_model.sh`, `band_score3.sh` | `pipeline/ink/band_models.sh` + `pipeline/rank/band_post.sh` |
| `deep_look.sh`, `deep_score.sh` | four-model deep looks, replaced by six models at depth −15..+15 (`pipeline/ink/depth_sweep.sh` + `pipeline/review/deep_look_view.py`) |
| `stroke_rank.sh`, `stroke_watch.sh` | `pipeline/rank/rank_post.py` and the released `tools/stroke-score` |
| `triage_windings.sh` | `pipeline/render/triage_band.sh` (any fit, any scroll) |
| `winding_qa.sh` | 28-slice renders; replaced by 66-layer renders (`pipeline/render/render66.sh`) |
| `poc.sh`, `fleet_3model.sh`, `fleet_score.sh` | the first cloud runs (a one-map proof of concept and a three-model pass over a fleet of GPU instances, 10-09 / 10-10); cloud work now runs one instance per job |
| `status.sh` | a one-screen status of the PHerc0191 runs (no longer used) |
| `pull_preview.sh` | fetched a preview TIFF as a JPEG (no longer used) |
