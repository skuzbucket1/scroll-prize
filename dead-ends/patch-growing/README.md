# Growing a surface from a seed: didn't work well enough

**Idea.** Skip the global spiral. Grow a surface patch from one seed point on a sheet and let the CT and a direction field
keep it on that sheet.

**What we tried.**
- **VC3D's patch tracer** (2026-10-09, PHerc0191). `vc_grow_seg_from_seed` was run without guidance, then with direction
  fields: the Fiber model (`fiber_band.sh`, `make_dirfield_zarr.py`, `inspect_fiber_ckpt.py`), the normal grids the docs
  call required, and the community Lasagna normals. The test scripts are `tracer_*_test*.sh`; `grow_qa.sh` renders and
  inks a grown patch.
- **The sheet tracer model** (2026-10-12, PHerc0813 tall band). We seeded it from our w090 and compared it with our mesh
  using `tracer_vs_mesh.py`.

**What it showed.**
- Without guidance, VC3D grew flat discs that ignore the data.
- With normal grids and Lasagna normals, the best patch (35.8 cm²) was about half on one sheet. The other half showed
  layers crossing.
- The sheet tracer stopped after 2–4 rows at its default threshold. At threshold 0.2, one seed ran 40 rows but on the
  neighbouring winding. Where it did stay, it agreed with our snapped mesh to a median of 3 voxels.

**Why it failed.** Neither stays on one sheet over an area big enough to search. Meanwhile fit + snap + flatten gave
whole windings with clean weave, so that became the pipeline.

**What would change it.** A clearer region or another scroll for the sheet tracer. We may retry it there.

Site: https://skuzbucket1.github.io/scroll-prize/#run-tracer-lasagna150
