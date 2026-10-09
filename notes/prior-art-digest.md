# Prior art digest — what has already been tried (compiled 2026-10-09)

Sources: Scroll Prize Substack (API text in `data/prior-art/substack-*.txt`), the PHerc. 343 winner's repository
(`data/prior-art/pherc343-first-letters`, MIT), ScrollFiesta (`data/prior-art/scrollfiesta_public`), villa git history.
Discord export: pending (route 1).

## 1. The First Letters prize was won yesterday on PHerc. 343 (2026-10-08) — and the recipe is ours plus three steps

Erwin Nieuwlaar, `github.com/Nieuwlaar/pherc343-first-letters`. 8.64 µm scan, band z 9500–11000, letters on
windings w047+w048 joined across θ = 0; line 3 reads πα̣ντ̣ογιν̣ομ̣ ("everything that happens").

His chain (all open):
1. **Surface-prediction distance field.** `make_surf_sdt.py` on the m7 surface prediction at level 1, threshold 128,
   over the band ± 64 slices, masked by CT occupancy at level 4. Fed to the fitter as the dense-spacing evidence
   (`dense_spacing_mode: "phase"`), with tracks, Lasagna normals (group 2, scale 4), his own umbilicus, **no shell**
   (`loss_weight_shell_outer: 0`, one-line patch to make the `outer_shell/` folder optional), **30k steps**.
2. **Post-hoc snap** (`mesh/snap_meshes.py`, 181 lines, numpy/zarr/scipy): every mesh vertex moves along its normal to
   the centre of the nearest predicted-sheet run within ±15 voxels (parabolic sub-voxel refinement), offsets regularised
   (reject >6 vox jumps vs 5×5 median, fill by normalised convolution, Gaussian σ=1 cell). Vertices with no sheet keep
   their fitted position. Runs between `fit_spiral` and flattening. Copied to the box as `bin/snap_meshes_nieuwlaar.py`.
3. **Lasagna flattening** of each snapped winding: `lasagna/fit.py configs/flatten_fast_nofilter.json <input>.json`.
4. **66-layer render** (1 voxel apart; depth d = layer − 33; no `--flip-normals`, + is away from the axis) with VC3D.
5. **Ink: four 9 µm models averaged as z-scores** — ink_9um seeds 42/43 (75k), Hecate 9.6 µm (`scrollprize/hecate`),
   dense_native (his fine-tune on PHerc0139, `Nieuwlaar/ink9um-dense-native`) — each at every depth d = −15..+15,
   run twice (plain + zero-padded render) and merged by tile phase; one contrast stretch per model over all depths.
   The submission image is d = +1. Both Hecate and dense_native are now on the box (`checkpoints/hecate`,
   `checkpoints/dense_native`).
Hardware: one 24 GB GPU; ~6 h of ink sweeps per segment on a 4090.

Two more PHerc. 343 submissions found text (G. Munoz Mendonca; Ben Kyles' ScrollFiesta), so 343 is now taken.
PHerc. 191 is still open and is the worked example in the organisers' own First Letters tutorial.

## 2. The fitter the winner used no longer exists upstream
villa commit 38e391518 "Spiral simplification (#1871)", 2026-09-23, **removed surf-SDT support and the "phase"
dense-spacing bundle** (and `make_surf_sdt.py`, patch roles, influence tools, …). Current `main` offers only
`grad_mag` and `winding_model`. The winner fitted at 0fb38c45 (2026-08-18), before the removal. A worktree of that
commit is on the box (`/mnt/nvme/scroll-prizes/wt/spiral-0fb38c45`, old layout `volume-cartographer/scripts/spiral/`),
environment syncing, to reproduce the SDT + phase route on PHerc0191.

## 3. What the organisers recommend (tutorial, 2026-08-18)
Tracks + normals + umbilicus only; overrides `input_disable_patches, input_use_outer_shell: false,
loss_weight_shell_outer: 0, loss_weight_shell_patch_radius: 0, dense_spacing_mode: grad_mag, loss_weight_dense_spacing: 0`;
~1,000-slice band first; inspect geometry in VC3D before trusting ink ("in areas with strong local distortions the ink
models can … produce things that look very letter-like"); flatten with Lasagna; 28-slice render; ink_9um with
`--direction both`; then label/retrain. Fallback: local GrowPatch patches.

## 4. July 2026 Progress Prizes (what the community is building)
- **ScrollFiesta** (Ben Kyles et al., $20k): C/C++ pipeline from a surface-probability volume to registered per-cube
  meshes, welding, parameterisation, **snapping to raw CT intensity**, tifxyz output, VC3D integration; companion
  **Socratic Method** (`Hob3rMallow/socratic_method`) improves the surface prediction itself (cross-resolution
  distillation, dropout completion).
- **Will Stevens**: annealing-based optimisation to find consistently connected regions from noisy patches
  (`WillStevens/scrollreading`, report8.pdf); tifxyz output.
- Smaller: ROI inference, ink tutorial validation data, GPU MLS projection, zarr reading, spiral fitter on consumer
  GPUs (Shuhan Yang), spiral fitter fixes (N. Dolegieviez), metadata checkers, tifxyz metadata fixer (Nieuwlaar),
  tifxyz intersection detector (J. Carrera).
- Also referenced: a "diffeomorphic spiral fit" paper (WACV 2026), Ryan Chesler's 3D ink detection, the Kaggle surface
  detection competition winners, ScrollSlabViewer.

## 5. What this changes for us
- **Adopt the snap now.** Our fits put ~46–49% of track points within 6 voxels of the sheet; a ±15-voxel snap to the
  m7 prediction is designed for exactly this. Queued on exp-30k's windings (`bin/snap_exp30k.sh`).
- **Drop the shell pull** (every shell-active run lost ~4 points; the winner and the tutorial both set it to 0).
- **Reproduce the SDT + phase fit** at 0fb38c45 on our band, 30k steps, then snap → flatten → 66-layer render → 4-model
  depth sweep with his scripts.
- **Ink ensemble + depth sweep** instead of a single 28-slice window: letters appeared at d = +1 in 343.
- Judge geometry by the eye (fibre weave over a whole winding) before any ink claim; the tutorial warns about
  letter-like artefacts in distorted regions.
