# Tuning the spiral fit: didn't work

**Idea.** On PHerc0191 the fitted spiral sat on the real sheet only about 46–49 % of the time. Changing the fit's settings
or giving it an outer boundary might move it onto the sheet.

**What we tried** (2026-10-09 to 2026-10-10, PHerc0191 z 9000–10000; `fit_experiment.sh` runs one controlled fit):
- **Track weight × 2** (exp-track2x): slightly worse.
- **30k steps** (exp-30k): the best of the fits (0.490), three points up. This one we kept, and it is the recipe in
  `pipeline/geometry/fit_band.sh`.
- **Outer shell from the CT mask** (`make_outer_shell.py`, `exp_shell105.sh`): no change at first, because the shell
  loss was silently zero. `shell_lookup_test.py` reproduces that tooling bug, reported as villa PR #2021. With a dense
  shell that actually works (`shell_dense_and_rerun.sh`, exp-shell105b), the outer winding moved out, and track
  satisfaction dropped.
- **Starting spacing 16 → 32 voxels** (exp-dr32): much worse. The starting value fixes the spiral's radial extent.
- **Weaker regularizer** (exp-dirlow): the outer boundary right, the inside wrong.

**Why it failed.** A crushed scroll has the same number of windings in every direction, but the spacing between them
varies about 2.5 times by sector. One spiral with one spacing rule cannot follow that, whatever the weights. The step
that did fix most of it came afterwards: snapping the fit onto the predicted surface, then flattening (in the pipeline).

Site: https://skuzbucket1.github.io/scroll-prize/#run-sector-audit
