**In one sentence:** Windings straight out of the spiral fitter now record how far apart their vertices really are, so they render at true size and report the right area.

**One real example:** I took winding w090 from my PHerc0813 fit (z 12,000–13,000, step 20) and re-saved it with this branch. Its `meta.json` went from `scale [0.05, 0.05]`, `area_cm2 7.40` to `scale [0.0418, 0.0424]`, `area_cm2 12.33`. The coordinates didn't change, only the metadata.

**Before:** I ran into this on PHerc0191, where the same winding rendered up to a third smaller before flattening than after. The mesh says there's a vertex every 20 voxels. In the CT they're actually 23.9 apart along the winding and 23.6 across it on this PHerc0813 winding. The grid is regular in spiral space and the fit stretches it on the way into the scroll, but the writer still records 1/step. So `vc_render_tifxyz --scale 1` draws 20 px per node, which is about 0.84 px per voxel, and the ink models see letters 16 % smaller than they are. The area comes out 40 % low for the same reason (7.40 cm² instead of 12.33).

**After this PR:** The writers measure the real spacing between neighbouring vertices (the median, along columns and along rows) and the real area of the quads, and write those into `meta.json`. That is what tifxyz_format.md §5.1 says `scale` should be. The same w090 now renders at 1.0 px per voxel.

**Proof:** Same mesh, same `vc_render_tifxyz` build, `--scale 1 --num-slices 1`, PHerc0813 w090 (snapped). The last row is the Lasagna-flattened version of the same winding, which already had the right spacing:
```
                     scale in meta.json     real spacing       render         px per voxel   area_cm2
main                 0.05 / 0.05            23.9 / 23.6 vx     8680 x 1320    0.84           7.40
this branch          0.0418 / 0.0424        23.9 / 23.6 vx     10390 x 1558   1.00           12.33
flattened (Lasagna)  0.05 / 0.05            19.8 / 19.8 vx     12180 x 2060   1.01
```
As a check on the area, I compared against the flattened mesh of each winding, measured the same way (cm²). The new numbers land within 4–7 % of it; main is 30–39 % short:
```
                  main   this branch   flattened mesh
PHerc0813 w070    5.78      9.10           8.73
          w090    7.40     12.32          11.66
          w100    8.23     14.03          13.25
          w110    9.03     15.74          14.80
PHerc0191 w040    3.48      5.40           5.05
          w070    6.05      9.10           8.63
          w100    8.54     13.68          12.82
```
Tests: the full spiral-fitting suite on main gives 3 failed, 926 passed; on this branch, 933 passed. I added 4 tests in `tests/test_tifxyz_spacing.py`. The 3 failures on main are in `test_merge_concat_runs.py`, which calls `merge_concat_runs.save_tifxyz` without `layout_metadata`; I made that argument optional.

**Why / where this is useful:** The First Letters guide says flattening is optional, so people will render windings straight from the fit for quick looks and ink tests. Those renders now come out at the size the ink models expect. Anything that maps voxel positions to grid cells through `scale` (`interpolate_at_points`, since #1923) also lands on the right cells.

- [ X ] I personally verified that the example and proof above were produced by this PR on the stated data.

## Details

- The measuring lives in a small new numpy-only file, `spiral-fitting/tifxyz_spacing.py` (`grid_spacing_and_area`), shared by `tifxyz.save_tifxyz`, `tifxyz.save_combined_tifxyz` and `merge_concat_runs.save_tifxyz` so the last one stays torch-free. If an axis has no valid neighbours, or they all sit on top of each other, it falls back to `step_size`. Area is the valid quads split into two triangles each, rounded to whole voxels².
- Only `scale`, `area_vx2` and `area_cm2` change. `render_ink.read_step_and_voxel` reads the step from `1 / scale[0]` and the voxel size from `area_cm2 / area_vx2`, and both still work.
- Tested commit `92427265e` on top of main `25f3c93c6`, Ubuntu 24.04, `villa/spiral-fitting/.venv`, `vc_render_tifxyz` built from `12f21236a`.
- Data: my PHerc0813 fit `exp30k-z12000` and PHerc0191 fit `exp30k-z11200`, both with step 20, from the published spiral datasets. An earlier PHerc0191 fit (z 9,000–10,000) was worse, at 26–30 voxels.
- Meshes already on disk keep their old `meta.json` until they're re-saved or re-exported.
- One limitation: it's a single median spacing per axis, so local stretching inside a winding is still there, and flattening is still worth doing before reading. Another way to fix this would be to resample the grid to the declared step on export. Happy to switch to that if you'd rather.
